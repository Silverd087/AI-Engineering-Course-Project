from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from qdrant_client import QdrantClient

from evaluation.metrics import first_relevant_rank, hit_at_k, mrr, percentile
from indexing.config import IndexConfig
from indexing.repository import QdrantHybridRepository
from retrieval.retriever import HybridRetriever

MODES = ("dense", "sparse", "hybrid")
KS = (1, 3, 5)


def load_questions(path: Path) -> list[dict]:
    questions = json.loads(path.read_text(encoding="utf-8"))
    for i, q in enumerate(questions):
        if not q.get("question"):
            raise ValueError(f"Question {i} has no 'question' text")
        answerable = q.get("answerable", True)
        if answerable and not q.get("relevant_chunk_ids"):
            raise ValueError(f"Answerable question {i} has no 'relevant_chunk_ids'")
    return questions


def run_mode(
    retriever: HybridRetriever,
    questions: list[dict],
    mode: str,
    k: int,
) -> list[dict]:
    rows = []
    for q in questions:
        start = time.perf_counter()
        hits = retriever.retrieve(q["question"], mode=mode, k=k)
        latency_ms = (time.perf_counter() - start) * 1000

        retrieved_ids = [h.payload["chunk_id"] for h in hits]
        rank = first_relevant_rank(retrieved_ids, set(q["relevant_chunk_ids"]))
        rows.append({
            "question": q["question"],
            "rank": rank,
            "latency_ms": round(latency_ms, 2),
            "retrieved_ids": retrieved_ids,
            "relevant_ids": q["relevant_chunk_ids"],
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    ranks = [r["rank"] for r in rows]
    latencies = [r["latency_ms"] for r in rows]
    summary = {f"hit@{k}": round(hit_at_k(ranks, k), 3) for k in KS}
    summary["mrr"] = round(mrr(ranks), 3)
    summary["retrieval_p50_ms"] = round(percentile(latencies, 50), 1)
    summary["retrieval_p95_ms"] = round(percentile(latencies, 95), 1)
    summary["num_questions"] = len(rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", type=Path, default=Path("data/eval/questions.json"))
    parser.add_argument("--out", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument(
        "--k",
        type=int,
        default=max(KS),
        help=f"Results retrieved per question; must be at least {max(KS)}",
    )
    args = parser.parse_args()

    if args.k < max(KS):
        raise SystemExit(f"--k must be at least {max(KS)} to report hit@{max(KS)}")

    questions = load_questions(args.questions)
    retrieval_questions = [q for q in questions if q.get("answerable", True)]
    if not retrieval_questions:
        raise SystemExit("No answerable questions to evaluate")

    retriever = HybridRetriever(
        QdrantHybridRepository(
            client=QdrantClient(url=args.qdrant_url),
            config=IndexConfig(),
        )
    )

    args.out.mkdir(parents=True, exist_ok=True)
    table: dict[str, dict] = {}
    for mode in MODES:
        rows = run_mode(retriever, retrieval_questions, mode, args.k)
        summary = summarize(rows)
        table[mode] = summary
        (args.out / f"{mode}.json").write_text(
            json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print(f"{'mode':<8} {'hit@1':>6} {'hit@3':>6} {'hit@5':>6} {'mrr':>6} {'p50ms':>8} {'p95ms':>8}")
    for mode, s in table.items():
        print(
            f"{mode:<8} {s['hit@1']:>6} {s['hit@3']:>6} {s['hit@5']:>6} "
            f"{s['mrr']:>6} {s['retrieval_p50_ms']:>8} {s['retrieval_p95_ms']:>8}"
        )


if __name__ == "__main__":
    main()