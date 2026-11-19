"""Scores generated SQL against reference SQL by executing both and comparing results.

Usage:
    # Self-test: runs each item's own reference_sql as the "candidate" (should be 100% correct)
    python src/score.py --items data/items.jsonl --db data/bookstore.db --self-test --out results/self_test.csv

    # Real scoring: candidates is a JSONL file with one row per (item id, model, sql)
    #   {"id": "q001", "model": "top", "sql": "SELECT ..."}
    python src/score.py --items data/items.jsonl --db data/bookstore.db --candidates results/raw_outputs.jsonl --out results/per_item.csv

A result is "correct" if executing the candidate SQL returns the same set of
rows as executing the reference SQL (order-independent, small float tolerance).
Any exception, parse error, or timeout while running the candidate counts as wrong.
"""
import argparse
import csv
import json
import math
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

TIMEOUT_SECONDS = 5
FLOAT_TOL = 1e-6


class QueryTimeout(Exception):
    pass


def run_query(db_path, sql, timeout=TIMEOUT_SECONDS):
    """Executes a single SQL statement read-only, with a wall-clock timeout.

    Returns (rows, error_str). rows is None if an error occurred.

    The timeout uses sqlite3's progress handler (called every N VM steps) rather
    than signal.SIGALRM, which does not exist on Windows.
    """
    if not sql or not sql.strip():
        return None, "parse_error: no SQL found in model output"
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    deadline = time.monotonic() + timeout
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            # Returning non-zero aborts the running statement with "interrupted".
            conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
            cur = conn.execute(sql)
            rows = cur.fetchall()
            return rows, None
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        if time.monotonic() > deadline:
            return None, f"timeout: query exceeded {timeout}s"
        return None, f"sql_error: {e}"
    except sqlite3.Error as e:
        return None, f"sql_error: {e}"
    except Exception as e:
        return None, f"error: {e}"


def _normalize_cell(v):
    if isinstance(v, float):
        return round(v, 6)
    return v


def rows_match(a, b):
    if a is None or b is None:
        return False
    norm_a = sorted(tuple(_normalize_cell(v) for v in row) for row in a)
    norm_b = sorted(tuple(_normalize_cell(v) for v in row) for row in b)
    if len(norm_a) != len(norm_b):
        return False
    for ra, rb in zip(norm_a, norm_b):
        if len(ra) != len(rb):
            return False
        for va, vb in zip(ra, rb):
            if isinstance(va, float) and isinstance(vb, float):
                if not math.isclose(va, vb, abs_tol=FLOAT_TOL):
                    return False
            elif va != vb:
                return False
    return True


def load_items(path):
    items = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            items[obj["id"]] = obj
    return items


def load_candidates(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


# Fields copied from run.py output into per_item.csv so every table can be built from that one file.
PASSTHROUGH = ["model_name", "status", "latency_ms", "input_tokens", "output_tokens",
               "eval_tokens_per_s", "stop_reason", "run_date", "raw_output"]
FIELDNAMES = ["id", "split", "category", "model", "correct", "failure", "error",
              "candidate_sql", "reference_sql", "expected_rows", "actual_rows"] + PASSTHROUGH


def classify(cand, cand_err, correct):
    """One failure label per row, so the report can show parse errors/refusals/timeouts in their own column."""
    if correct:
        return ""
    status = cand.get("status", "ok")
    if status and status != "ok":
        return status  # api_error / refusal / timeout / truncated, set by run.py
    if cand_err:
        if cand_err.startswith("parse_error"):
            return "parse_error"
        if cand_err.startswith("timeout"):
            return "timeout"
        return "sql_error"
    return "wrong_result"


def score_one(db_path, item, cand):
    """Scores one candidate against one item. Used by the CLI and by the web frontend."""
    ref_rows, ref_err = run_query(db_path, item["reference_sql"])
    if ref_err:
        # Reference query itself is broken -- this is a data bug, not a model failure.
        raise RuntimeError(f"Reference SQL for {item['id']} failed: {ref_err}")
    status = cand.get("status", "ok")
    if status and status != "ok":
        cand_rows, cand_err = None, cand.get("error") or status
    else:
        cand_rows, cand_err = run_query(db_path, cand.get("sql", ""))
    correct = (cand_err is None) and rows_match(ref_rows, cand_rows)
    return {
        "id": item["id"],
        "split": item.get("split", ""),
        "category": item.get("category", ""),
        "model": cand.get("model", ""),
        "correct": int(correct),
        "failure": classify(cand, cand_err, correct),
        "error": cand_err or "",
        "candidate_sql": cand.get("sql", ""),
        "reference_sql": item["reference_sql"],
        "expected_rows": json.dumps(ref_rows[:20], default=str),
        "actual_rows": json.dumps(cand_rows[:20], default=str) if cand_rows is not None else "",
        **{k: cand.get(k, "") for k in PASSTHROUGH},
    }


def score(items_path, db_path, out_path, candidates_path=None, self_test=False):
    items = load_items(items_path)

    if self_test:
        candidates = [{"id": i, "model": "self_test", "sql": it["reference_sql"]} for i, it in items.items()]
    else:
        candidates = load_candidates(candidates_path)

    out_rows = []
    for cand in candidates:
        item = items.get(cand["id"])
        if item is None:
            out_rows.append({"id": cand["id"], "model": cand.get("model", ""), "correct": 0,
                             "failure": "unknown_item", "error": "unknown item id",
                             "candidate_sql": cand.get("sql", "")})
            continue
        out_rows.append(score_one(db_path, item, cand))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    by_model = {}
    for r in out_rows:
        m = by_model.setdefault(r["model"], [0, 0])
        m[0] += int(r["correct"])
        m[1] += 1
    for model, (c, t) in by_model.items():
        print(f"{model:>10}: {c}/{t} correct (all splits)")
    print(f"-> {out_path}")
    n_correct = sum(int(r["correct"]) for r in out_rows)
    return n_correct, len(out_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True, help="path to items.jsonl")
    ap.add_argument("--db", required=True, help="path to the SQLite database")
    ap.add_argument("--candidates", help="path to JSONL of {id, model, sql} rows from run.py")
    ap.add_argument("--self-test", action="store_true", help="score reference_sql against itself")
    ap.add_argument("--out", required=True, help="output CSV path")
    args = ap.parse_args()

    if not args.self_test and not args.candidates:
        sys.exit("error: pass --candidates <file> or --self-test")

    # Defensive: never query a DB file sitting inside a synced/networked folder in place.
    # Copy to a local temp path first, run everything against the copy.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_db = Path(tmp) / "scoring.db"
        shutil.copy(args.db, tmp_db)
        score(args.items, tmp_db, args.out, candidates_path=args.candidates, self_test=args.self_test)


if __name__ == "__main__":
    main()
