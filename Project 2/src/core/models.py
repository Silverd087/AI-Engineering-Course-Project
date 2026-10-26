"""core/models.py"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    """Output from the ingestion phase."""

    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """The canonical transfer model between chunking and indexing."""

    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def make_chunk_id(source: str, text: str) -> str:
    """Deterministic hash fallback for chunk IDs."""
    digest = hashlib.sha256(f"{source}\n{text}".encode()).hexdigest()
    return digest[:16]