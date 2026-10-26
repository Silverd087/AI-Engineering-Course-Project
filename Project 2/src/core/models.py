"""core/models.py"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Any, List

from src.ingest import ParsedDocument

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


@dataclass
class IndexResult:
    """Result of building the indexes."""
    vector_store_path: str               # Path to vector database
    bm25_index_path: str                 # Path to BM25 index
    num_chunks: int                      # Total chunks indexed
    embedding_model: str                 # Name of embedding model used
    bm25_stats: Dict[str, Any]           # BM25 statistics
    vector_stats: Dict[str, Any]         # Vector store statistics

@dataclass
class PipelineResult:
    """Final result from the entire pipeline."""
    timestamp: str                       # When pipeline was run
    documents: List[ParsedDocument]      # Parsed documents from ingestion
    chunks: List[Chunk]                  # Chunks from chunking stage
    index: IndexResult                   # Result from indexing stage
    manifest_path: str                   # Path to ingestion manifest
    
    def summary(self) -> Dict[str, Any]:
        """Return a summary of the pipeline result."""
        return {
            "timestamp": self.timestamp,
            "documents_loaded": len(self.documents),
            "total_text_chars": sum(len(d.text) for d in self.documents),
            "chunks_created": len(self.chunks),
            "avg_chunk_length": (
                sum(len(c.text) for c in self.chunks) / len(self.chunks)
                if self.chunks else 0
            ),
            "index_stats": {
                "vector_store": self.index.vector_store_path,
                "num_chunks": self.index.num_chunks,
                "embedding_model": self.index.embedding_model,
            }
        }