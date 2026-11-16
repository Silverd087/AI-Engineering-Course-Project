"""One command for the whole benchmark: build DB -> self-test scorer -> run models -> score -> cost -> report.

    python src/bench.py                 # everything
    python src/bench.py --models local  # only (re)run some models, then rebuild all tables
    python src/bench.py --skip-run      # just rescore + rebuild tables/report from raw_outputs.jsonl

Extra arguments after --models are passed straight to run.py.
"""
import argparse
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
PY = sys.executable


def step(*args):
    print(f"\n$ python {' '.join(str(a) for a in args)}")
    subprocess.run([PY, *map(str, args)], check=True, cwd=ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="top,cheap,local")
    ap.add_argument("--skip-run", action="store_true")
    ap.add_argument("--no-report", action="store_true")
    args = ap.parse_args()

    step(ROOT / "data" / "build_db.py")
    step(SRC / "score.py", "--items", "data/items.jsonl", "--db", "data/bookstore.db",
         "--self-test", "--out", "results/self_test.csv")
    if not args.skip_run:
        step(SRC / "run.py", "--models", args.models)
    step(SRC / "score.py", "--items", "data/items.jsonl", "--db", "data/bookstore.db",
         "--candidates", "results/raw_outputs.jsonl", "--out", "results/per_item.csv")
    step(SRC / "cost.py")
    if not args.no_report:
        step(SRC / "report.py")


if __name__ == "__main__":
    main()
