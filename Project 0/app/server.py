"""Small web frontend for the bake-off.

    python app/server.py          # then open http://127.0.0.1:5000

Three views:
  * Results    -- summary table, failure breakdown and per-item grid, read from results/*.csv
  * Playground -- ask one question (a test item or your own) to any of the three models,
                  see the SQL, the rows it returns and, for test items, right/wrong
  * Data       -- the schema and every labelled item

It reuses run.generate (same prompt, settings and parser as the benchmark) and
score.score_one (same scorer), so what you see here is what the benchmark measures.
Playground calls are NOT written to results/: the reported numbers only come from run.py.
"""
import csv
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import run  # noqa: E402
import score  # noqa: E402

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"), static_url_path="/static")


def _items():
    return {it["id"]: it for it in run.load_items(config.ITEMS_PATH)}


def _query_with_columns(sql, timeout=score.TIMEOUT_SECONDS, limit=200):
    """Read-only execution that also returns column names, for display."""
    if not sql:
        return None, None, "parse_error: no SQL found in model output"
    uri = f"file:{config.DB_PATH.as_posix()}?mode=ro"
    deadline = time.monotonic() + timeout
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
            cur = conn.execute(sql)
            cols = [d[0] for d in cur.description or []]
            return cols, cur.fetchmany(limit), None
        finally:
            conn.close()
    except sqlite3.Error as e:
        return None, None, f"sql_error: {e}"


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/meta")
def meta():
    ollama_ok = False
    try:
        import requests
        ollama_ok = requests.get(f"{config.OLLAMA_URL}/api/version", timeout=1).ok
    except Exception:
        pass
    key_ok = bool(os.environ.get("OPENAI_API_KEY"))
    models = {role: {**spec, "available": ollama_ok if spec["provider"] == "ollama" else key_ok}
              for role, spec in config.MODELS.items()}
    return jsonify({
        "models": models,
        "settings": {"max_output_tokens": config.MAX_OUTPUT_TOKENS, "temperature_local": config.TEMPERATURE,
                     "reasoning_effort": config.REASONING_EFFORT, "timeout_s": config.REQUEST_TIMEOUT_S},
        "schema": config.SCHEMA_PATH.read_text(encoding="utf-8"),
        "prompt": config.PROMPT_PATH.read_text(encoding="utf-8"),
        "items": [{k: it.get(k) for k in ("id", "question", "split", "category", "reference_sql")}
                  for it in _items().values()],
    })


@app.get("/api/results")
def results():
    per_item = config.RESULTS / "per_item.csv"
    summary = config.RESULTS / "summary.csv"
    if not per_item.exists() or not summary.exists():
        return jsonify({"available": False})
    cost = config.RESULTS / "cost_model.json"
    return jsonify({
        "available": True,
        "summary": list(csv.DictReader(open(summary, encoding="utf-8"))),
        "per_item": [{k: r.get(k, "") for k in ("id", "split", "category", "model", "correct", "failure", "error",
                                                "candidate_sql", "reference_sql", "expected_rows", "actual_rows",
                                                "latency_ms", "raw_output")}
                     for r in csv.DictReader(open(per_item, encoding="utf-8"))],
        "cost_model": json.loads(cost.read_text(encoding="utf-8")) if cost.exists() else None,
    })


@app.post("/api/ask")
def ask():
    body = request.get_json(force=True)
    role = body.get("model")
    if role not in config.MODELS:
        return jsonify({"error": f"unknown model {role}"}), 400
    item = _items().get(body.get("item_id") or "")
    question = item["question"] if item else (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "empty question"}), 400

    gen = run.generate(role, question, retries=1)
    out = {k: gen.get(k) for k in ("model", "model_name", "sql", "raw_output", "status", "error",
                                   "latency_ms", "input_tokens", "output_tokens", "eval_tokens_per_s")}
    if gen["status"] == "ok":
        cols, rows, err = _query_with_columns(gen["sql"])
        out.update(columns=cols, rows=rows, sql_error=err)
    if item:
        scored = score.score_one(config.DB_PATH, item, gen)
        out.update(correct=scored["correct"], failure=scored["failure"])
        ecols, erows, _ = _query_with_columns(item["reference_sql"])
        out.update(expected_columns=ecols, expected_rows=erows, reference_sql=item["reference_sql"])
    return jsonify(out)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Bake-off UI on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
