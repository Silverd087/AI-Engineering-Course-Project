"""retrieval/reranker.py"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentence_transformers import CrossEncoder


@dataclass(frozen=True)
class RerankedHit:
    """Duck-types a Qdrant ScoredPoint (score + payload) so it drops into the
    existing generation.prompt.build_sources / evaluation code unchanged."""

    score: float
    payload: dict[str, Any]


class CrossEncoderReranker:
    """Reorders retrieval candidates with a cross-encoder scored on (query, chunk) pairs."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, hits: list[Any], top_k: int) -> list[RerankedHit]:
        if not hits:
            return []
        pairs = [(query, h.payload.get("text", "")) for h in hits]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(hits, scores), key=lambda pair: pair[1], reverse=True)
        return [
            RerankedHit(score=float(score), payload=hit.payload)
            for hit, score in ranked[:top_k]
        ]
