from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient

from generation.answerer import Answer, Answerer
from generation.llm import OpenAIClient
from indexing.config import IndexConfig
from indexing.repository import QdrantHybridRepository
from retrieval.query_rewriter import QueryRewriter, needs_rewrite
from retrieval.reranker import CrossEncoderReranker
from retrieval.retriever import HybridRetriever

DEFAULT_RERANK_CANDIDATES = 15


@dataclass(frozen=True)
class PipelineResult:
    answer: Answer
    retrieved_chunk_ids: list[str]
    rewritten_queries: list[str]
    retrieval_ms: float
    total_ms: float


def _merge_by_chunk_id(hit_lists: list[list[Any]]) -> list[Any]:
    """Union hits across queries, keeping each chunk's best score, ranked by score desc."""
    best: dict[str, Any] = {}
    for hits in hit_lists:
        for hit in hits:
            chunk_id = hit.payload.get("chunk_id", "")
            if chunk_id not in best or hit.score > best[chunk_id].score:
                best[chunk_id] = hit
    return sorted(best.values(), key=lambda h: h.score, reverse=True)


class RagPipeline:
    def __init__(
        self,
        retriever: HybridRetriever,
        answerer: Answerer,
        reranker: CrossEncoderReranker | None = None,
        rewriter: QueryRewriter | None = None,
    ) -> None:
        self.retriever = retriever
        self.answerer = answerer
        self.reranker = reranker
        self.rewriter = rewriter

    def ask(
        self,
        question: str,
        mode: str = "hybrid",
        k: int = 5,
        metadata_filter: Any | None = None,
    ) -> PipelineResult:
        if k < self.answerer.max_chunks:
            raise ValueError(
                f"k ({k}) must be at least max_chunks ({self.answerer.max_chunks})"
            )

        total_start = time.perf_counter()

        retrieval_start = time.perf_counter()
        if self.rewriter and needs_rewrite(question):
            queries = self.rewriter.rewrite(question)
        else:
            queries = [question]
        candidate_k = max(k, DEFAULT_RERANK_CANDIDATES) if self.reranker else k
        hit_lists = [
            self.retriever.retrieve(q, mode=mode, k=candidate_k, metadata_filter=metadata_filter)
            for q in queries
        ]
        candidates = hit_lists[0] if len(hit_lists) == 1 else _merge_by_chunk_id(hit_lists)

        if self.reranker is not None:
            hits = self.reranker.rerank(question, candidates, top_k=k)
        else:
            hits = candidates[:k]
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        answer = self.answerer.answer(question, hits)
        total_ms = (time.perf_counter() - total_start) * 1000

        return PipelineResult(
            answer=answer,
            retrieved_chunk_ids=[h.payload.get("chunk_id", "") for h in hits],
            rewritten_queries=queries,
            retrieval_ms=round(retrieval_ms, 2),
            total_ms=round(total_ms, 2),
        )


def build_pipeline(
    qdrant_url: str = "http://localhost:6333",
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    max_chunks: int = 5,
    use_reranker: bool = False,  # Week 8: off by default, see optimisation.md
    use_rewriter: bool = True,
) -> RagPipeline:
    repo = QdrantHybridRepository(
        client=QdrantClient(url=qdrant_url),
        config=IndexConfig(),
    )
    retriever = HybridRetriever(repo)
    llm = OpenAIClient(model=model, api_key=api_key)
    answerer = Answerer(llm=llm, max_chunks=max_chunks)
    reranker = CrossEncoderReranker() if use_reranker else None
    rewriter = QueryRewriter(llm=llm) if use_rewriter else None
    return RagPipeline(retriever, answerer, reranker=reranker, rewriter=rewriter)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default="hybrid")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--reranker", action="store_true", help="Enable the cross-encoder reranker (off by default since Week 8, see optimisation.md)")
    parser.add_argument("--no-rewriter", action="store_true")
    args = parser.parse_args()

    pipeline = build_pipeline(
        model=args.model,
        max_chunks=args.k,
        use_reranker=args.reranker,
        use_rewriter=not args.no_rewriter,
    )
    result = pipeline.ask(args.question, mode=args.mode, k=args.k)
    answer = result.answer

    if result.rewritten_queries != [args.question]:
        print("Rewritten queries:", result.rewritten_queries)
        print()
    print(answer.text)
    print()
    print("Sources:")
    for s in answer.sources:
        marker = "cited" if s.number in answer.cited_numbers else "retrieved"
        print(f"  [{s.number}] {s.header or s.chunk_id} ({marker}, score {s.score:.3f})")
    print()
    print(
        f"retrieval {result.retrieval_ms} ms | llm {answer.llm_latency_ms} ms | "
        f"total {result.total_ms} ms | tokens in {answer.input_tokens} out {answer.output_tokens}"
    )


if __name__ == "__main__":
    main()