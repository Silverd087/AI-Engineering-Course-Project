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
import signal
import sqlite3
import sys
import tempfile
from pathlib import Path

TIMEOUT_SECONDS = 5
FLOAT_TOL = 1e-6


class QueryTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise QueryTimeout(f"query exceeded {TIMEOUT_SECONDS}s")


def run_query(db_path, sql, timeout=TIMEOUT_SECONDS):
    """Executes a single SQL statement read-only, with a wall-clock timeout.

    Returns (rows, error_str). rows is None if an error occurred.
    """
    uri = f"file:{db_path}?mode=ro"
    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(timeout)
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            return rows, None
        finally:
            conn.close()
    except QueryTimeout as e:
        return None, f"timeout: {e}"
    except sqlite3.Error as e:
        return None, f"sql_error: {e}"
    except Exception as e:
        return None, f"error: {e}"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


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
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            items[obj["id"]] = obj
    return items


def load_candidates(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def score(items_path, db_path, out_path, candidates_path=None, self_test=False):
    items = load_items(items_path)

    if self_test:
        candidates = [{"id": i, "model": "self_test", "sql": it["reference_sql"]} for i, it in items.items()]
    else:
        candidates = load_candidates(candidates_path)

    out_rows = []
    n_correct = 0
    for cand in candidates:
        item = items.get(cand["id"])
        if item is None:
            out_rows.append({
                "id": cand["id"], "model": cand.get("model", ""), "correct": 0,
                "error": "unknown item id", "candidate_sql": cand.get("sql", ""),
            })
            continue

        ref_rows, ref_err = run_query(db_path, item["reference_sql"])
        if ref_err:
            # Reference query itself is broken -- this is a data bug, not a model failure.
            raise RuntimeError(f"Reference SQL for {item['id']} failed: {ref_err}")

        cand_rows, cand_err = run_query(db_path, cand["sql"])
        correct = (cand_err is None) and rows_match(ref_rows, cand_rows)
        n_correct += int(correct)

        out_rows.append({
            "id": cand["id"],
            "model": cand.get("model", ""),
            "correct": int(correct),
            "error": cand_err or "",
            "candidate_sql": cand["sql"],
            "reference_sql": item["reference_sql"],
        })

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "model", "correct", "error", "candidate_sql", "reference_sql"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    total = len(out_rows)
    print(f"{n_correct}/{total} correct -> {out_path}")
    return n_correct, total


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
