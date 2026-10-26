"""indexing/config.py

Configuration parameters for Qdrant collection, embedding models,
batch sizes, and payload index fields.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexConfig:
    collection: str = "chunks"
    dense_model: str = "BAAI/bge-small-en-v1.5"
    sparse_model: str = "Qdrant/bm25"
    batch_size: int = 64
    # Payload fields to index in Qdrant for fast query-time filtering.
    # Update these tuples to match the metadata keys extracted during ingestion.
    keyword_fields: tuple[str, ...] = (
        "course_code",
        "programmes",
        "semester",
        "source_type",
    )
    integer_fields: tuple[str, ...] = ("year",)