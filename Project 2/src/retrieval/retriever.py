"""retrieval/retriever.py"""

from typing import Literal
from qdrant_client import models
from indexing.repository import QdrantHybridRepository


class HybridRetriever:
    def __init__(self, repository: QdrantHybridRepository) -> None:
        self.repo = repository

    def retrieve(
        self,
        query: str,
        *,
        mode: Literal["dense", "sparse", "hybrid"] = "hybrid",
        k: int = 5,
        metadata_filter: models.Filter | None = None,
    ) -> list[models.ScoredPoint]:
        return self.repo.search(
            query=query,
            mode=mode,
            k=k,
            query_filter=metadata_filter,
        )