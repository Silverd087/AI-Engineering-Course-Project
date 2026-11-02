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
from retrieval.retriever import HybridRetriever


@dataclass(frozen=True)
class PipelineResult:
    answer: Answer
    retrieved_chunk_ids: list[str]
    retrieval_ms: float
    total_ms: float


class RagPipeline:
    def __init__(self, retriever: HybridRetriever, answerer: Answerer) -> None:
        self.retriever = retriever
        self.answerer = answerer

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
        hits = self.retriever.retrieve(
            question,
            mode=mode,
            k=k,
            metadata_filter=metadata_filter,
        )
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        answer = self.answerer.answer(question, hits)
        total_ms = (time.perf_counter() - total_start) * 1000

        return PipelineResult(
            answer=answer,
            retrieved_chunk_ids=[h.payload.get("chunk_id", "") for h in hits],
            retrieval_ms=round(retrieval_ms, 2),
            total_ms=round(total_ms, 2),
        )


def build_pipeline(
    qdrant_url: str = "http://localhost:6333",
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    max_chunks: int = 5,
) -> RagPipeline:
    repo = QdrantHybridRepository(
        client=QdrantClient(url=qdrant_url),
        config=IndexConfig(),
    )
    retriever = HybridRetriever(repo)
    answerer = Answerer(
        llm=OpenAIClient(model=model, api_key=api_key),
        max_chunks=max_chunks,
    )
    return RagPipeline(retriever, answerer)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default="hybrid")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    pipeline = build_pipeline(model=args.model, max_chunks=args.k)
    result = pipeline.ask(args.question, mode=args.mode, k=args.k)
    answer = result.answer

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