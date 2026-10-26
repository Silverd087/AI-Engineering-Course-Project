"""indexing/repository.py"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator
from typing import Literal

from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient, models

from core.models import Chunk
from indexing.config import IndexConfig

DENSE = "dense"
SPARSE = "sparse"
_ID_NAMESPACE = uuid.UUID("b3c1f0a2-5d4e-4c8a-9a57-3e1f6d2a7c10")


class QdrantHybridRepository:
    """Repository handling hybrid vector upserts and queries in Qdrant."""

    def __init__(self, client: QdrantClient, config: IndexConfig) -> None:
        self.client = client
        self.config = config
        self.dense_embedder = TextEmbedding(config.dense_model)
        self.sparse_embedder = SparseTextEmbedding(config.sparse_model)
        self.dense_dim = len(next(iter(self.dense_embedder.embed(["probe"]))))

    def _point_id(self, chunk_id: str) -> str:
        return str(uuid.uuid5(_ID_NAMESPACE, chunk_id))

    def init_schema(self, recreate: bool = False) -> None:
        if recreate and self.client.collection_exists(self.config.collection):
            self.client.delete_collection(self.config.collection)
        if self.client.collection_exists(self.config.collection):
            return

        self.client.create_collection(
            collection_name=self.config.collection,
            vectors_config={
                DENSE: models.VectorParams(
                    size=self.dense_dim, distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
        for name in self.config.keyword_fields:
            self.client.create_payload_index(
                self.config.collection, name, models.PayloadSchemaType.KEYWORD
            )
        for name in self.config.integer_fields:
            self.client.create_payload_index(
                self.config.collection, name, models.PayloadSchemaType.INTEGER
            )

    def add_chunks(self, chunks: Iterable[Chunk]) -> int:
        total = 0
        batch: list[Chunk] = []

        for item in chunks:
            batch.append(item)
            if len(batch) == self.config.batch_size:
                total += self._upsert_batch(batch)
                batch = []
        if batch:
            total += self._upsert_batch(batch)
        return total

    def _upsert_batch(self, batch: list[Chunk]) -> int:
        texts = [c.text for c in batch]
        dense_vecs = [v.tolist() for v in self.dense_embedder.embed(texts)]
        sparse_vecs = [
            models.SparseVector(indices=s.indices.tolist(), values=s.values.tolist())
            for s in self.sparse_embedder.embed(texts)
        ]

        points = [
            models.PointStruct(
                id=self._point_id(chunk.chunk_id),
                vector={DENSE: dense, SPARSE: sparse},
                payload={**chunk.metadata, "chunk_id": chunk.chunk_id, "text": chunk.text},
            )
            for chunk, dense, sparse in zip(batch, dense_vecs, sparse_vecs, strict=True)
        ]
        self.client.upsert(collection_name=self.config.collection, points=points)
        return len(points)