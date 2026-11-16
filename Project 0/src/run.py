"""Calls the three models on every item with the same prompt and settings.

Usage:
    python src/run.py                         # all models, all items (dev + test)
    python src/run.py --models local          # just the local model
    python src/run.py --split test --limit 5  # quick smoke run

Writes one JSON line per (item, model) to results/raw_outputs.jsonl:
    {"id", "model", "model_name", "sql", "raw_output", "status", "error",
     "latency_ms", "input_tokens", "output_tokens", "eval_tokens_per_s",
     "stop_reason", "run_date"}

Calls are made one after the other (no concurrency), so latency is per-request,
and items are always sent in file order. Rows already in the output file are
skipped (except api_error rows), so an interrupted run can be resumed.
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

RETRYABLE_HTTP = {429, 500, 502, 503, 529}


# ---------------------------------------------------------------- prompt + parser
def build_prompt(question):
    template = config.PROMPT_PATH.read_text(encoding="utf-8")
    schema = config.SCHEMA_PATH.read_text(encoding="utf-8").strip()
    return template.format(schema=schema, question=question)


_FENCE = re.compile(r"```(?:sql|sqlite)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_START = re.compile(r"\b(WITH|SELECT)\b", re.IGNORECASE)


def extract_sql(text):
    """The one parser used for all three models.

    1. Take the first ```sql fenced block if there is one; otherwise the whole text.
    2. Drop anything before the first SELECT/WITH keyword.
    3. Keep only the first statement (up to the first ';').
    Returns "" when no query can be found -> scored as a parse error.
    """
    if not text:
        return ""
    m = _FENCE.search(text)
    body = m.group(1) if m else text
    s = _START.search(body)
    if not s:
        return ""
    body = body[s.start():]
    body = body.split(";")[0].strip()
    return body + ";" if body else ""


# ---------------------------------------------------------------- providers
_openai_client = None


def _openai(model_name, prompt):
    global _openai_client
    import openai
    if _openai_client is None:
        # max_retries=0: we retry ourselves so a retried call's latency isn't counted.
        _openai_client = openai.OpenAI(max_retries=0, timeout=config.REQUEST_TIMEOUT_S)
    kwargs = {"model": model_name, "input": prompt, "max_output_tokens": config.MAX_OUTPUT_TOKENS, "store": False}
    if config.is_reasoning_model(model_name):
        kwargs["reasoning"] = {"effort": config.REASONING_EFFORT}  # these reject temperature
    else:
        kwargs["temperature"] = config.TEMPERATURE
    t0 = time.perf_counter()
    try:
        resp = _openai_client.responses.create(**kwargs)
    except openai.APITimeoutError as e:
        return {"status": "timeout", "error": f"timeout: {e}", "latency_ms": round((time.perf_counter() - t0) * 1000)}
    except openai.APIStatusError as e:
        if e.status_code in RETRYABLE_HTTP:
            raise _Retry(str(e))
        return {"status": "api_error", "error": f"api_error {e.status_code}: {e.message}"}
    except openai.APIConnectionError as e:
        raise _Retry(str(e))
    latency_ms = round((time.perf_counter() - t0) * 1000)

    refusal = ""
    for item in resp.output or []:
        for c in getattr(item, "content", None) or []:
            if getattr(c, "type", "") == "refusal":
                refusal = c.refusal
    usage = resp.usage
    out = {
        "raw_output": resp.output_text or "",
        "latency_ms": latency_ms,
        "input_tokens": usage.input_tokens if usage else "",
        "output_tokens": usage.output_tokens if usage else "",  # includes reasoning tokens (billed as output)
        "stop_reason": resp.status if resp.status != "incomplete" else
                       f"incomplete:{getattr(resp.incomplete_details, 'reason', '')}",
        "status": "ok",
    }
    if refusal:
        out.update(status="refusal", error=f"refusal: {refusal[:200]}")
    return out


def _ollama(model_name, prompt):
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{config.OLLAMA_URL}/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": config.TEMPERATURE, "num_predict": config.MAX_OUTPUT_TOKENS, "seed": 0},
            },
            timeout=config.REQUEST_TIMEOUT_S,
        )
    except requests.Timeout as e:
        return {"status": "timeout", "error": f"timeout: {e}", "latency_ms": round((time.perf_counter() - t0) * 1000)}
    except requests.ConnectionError as e:
        raise _Retry(f"cannot reach Ollama at {config.OLLAMA_URL}: {e}")
    latency_ms = round((time.perf_counter() - t0) * 1000)
    if r.status_code != 200:
        return {"status": "api_error", "error": f"ollama {r.status_code}: {r.text[:200]}"}
    j = r.json()
    eval_count = j.get("eval_count", 0)
    eval_ns = j.get("eval_duration", 0)
    return {
        "raw_output": j.get("message", {}).get("content", ""),
        "latency_ms": latency_ms,
        "input_tokens": j.get("prompt_eval_count", 0),
        "output_tokens": eval_count,
        "eval_tokens_per_s": round(eval_count / (eval_ns / 1e9), 1) if eval_ns else "",
        "stop_reason": j.get("done_reason", ""),
        "status": "ok",
    }


class _Retry(Exception):
    pass


def generate(role, question, retries=3):
    """One model call for one question. Shared by the batch runner and the web app."""
    spec = config.MODELS[role]
    prompt = build_prompt(question)
    fn = _openai if spec["provider"] == "openai" else _ollama
    last = ""
    for attempt in range(retries + 1):
        try:
            out = fn(spec["name"], prompt)
            break
        except _Retry as e:
            last = str(e)
            time.sleep(2 ** attempt * 2)
        except Exception as e:  # e.g. missing credentials -- infrastructure, not model behaviour
            out = {"status": "api_error", "error": f"{type(e).__name__}: {e}"}
            break
    else:
        out = {"status": "api_error", "error": f"gave up after {retries + 1} attempts: {last}"}
    out.setdefault("raw_output", "")
    out["sql"] = extract_sql(out["raw_output"]) if out["status"] == "ok" else ""
    out["model"] = role
    out["model_name"] = spec["name"]
    out["run_date"] = dt.date.today().isoformat()
    return out


# ---------------------------------------------------------------- batch runner
def load_items(path, split=None):
    items = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [it for it in items if split in (None, "all") or it.get("split") == split]


def preflight(roles):
    """Fail fast with a clear message instead of writing 60 api_error rows."""
    import os
    problems = []
    for role in roles:
        spec = config.MODELS[role]
        if spec["provider"] == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                problems.append(f"{role}: set OPENAI_API_KEY in Project 0/.env or your environment (never commit it).")
        else:
            try:
                tags = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3).json()
                names = {m["name"] for m in tags.get("models", [])}
                if spec["name"] not in names:
                    problems.append(f"{role}: model not pulled -> run `ollama pull {spec['name']}`")
            except requests.RequestException:
                problems.append(f"{role}: Ollama is not running at {config.OLLAMA_URL} -> install it and run `ollama serve`")
    if problems:
        sys.exit("Cannot start:\n  " + "\n  ".join(dict.fromkeys(problems)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=str(config.ITEMS_PATH))
    ap.add_argument("--out", default=str(config.RESULTS / "raw_outputs.jsonl"))
    ap.add_argument("--models", default="top,cheap,local", help="comma list of roles: top,cheap,local")
    ap.add_argument("--split", default="all", choices=["all", "dev", "test"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--fresh", action="store_true", help="ignore existing rows and start over")
    args = ap.parse_args()

    roles = [r.strip() for r in args.models.split(",") if r.strip()]
    preflight(roles)
    items = load_items(args.items, args.split)[: args.limit]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    kept = []
    if out_path.exists() and not args.fresh:
        kept = [json.loads(l) for l in out_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Only infrastructure failures (bad key, server down) are re-attempted on resume.
    # Timeouts and refusals are real model behaviour and stay in as wrong answers.
    done = {(r["id"], r["model"]) for r in kept if r.get("status") != "api_error"}
    kept = [r for r in kept if (r["id"], r["model"]) in done]
    out_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")

    for role in roles:
        name = config.MODELS[role]["name"]
        print(f"\n== {role}: {name} ==")
        for it in items:
            if (it["id"], role) in done:
                continue
            res = generate(role, it["question"])
            res["id"] = it["id"]
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            print(f"  {it['id']} {res['status']:<9} {res.get('latency_ms', ''):>6} ms  {res['sql'][:70]}")
    print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
