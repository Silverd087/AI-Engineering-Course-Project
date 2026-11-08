from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient

from chunking.chunker import DocumentChunker
from core.models import Chunk, Document, IndexResult, PipelineResult
from indexing.config import IndexConfig
from indexing.repository import QdrantHybridRepository
from ingest import ParsedDocument, ingest_documents

logger = logging.getLogger(__name__)


def to_document(parsed: ParsedDocument) -> Document:
    """Convert an ingestion output into the Document type the chunker expects."""
    meta = parsed.metadata
    source_path = str(meta.source_path)
    return Document(
        doc_id=hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16],
        text=parsed.text,
        metadata={
            "title": meta.title,
            "course_code": meta.course_code,
            "source_path": source_path,
            "programmes": list(meta.programmes or []),
            "year": meta.year,
            "semester": meta.semester,
            "source_type": meta.source_type,
            "section": meta.section,
            "prerequisites": list(meta.prerequisites or []),
            "corequisites": list(meta.corequisites or []),
            "credits": meta.credits,
        },
    )


class IngestionOrchestrator:
    """Runs ingestion, chunking and indexing in order.

    Usage:
        orchestrator = IngestionOrchestrator(QdrantClient(url="http://localhost:6333"))
        result = orchestrator.run()
    """

    def __init__(
        self,
        qdrant_client: QdrantClient,
        raw_folder: Path = Path("data/raw"),
        processed_folder: Path = Path("data/processed"),
        chunk_size: int = 384,
        chunk_overlap: int = 64,
        dense_model: str = "BAAI/bge-small-en-v1.5",
        sparse_model: str = "Qdrant/bm25",
        skip_errors: bool = True,
    ) -> None:
        self.qdrant_client = qdrant_client
        self.raw_folder = Path(raw_folder)
        self.processed_folder = Path(processed_folder)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.dense_model = dense_model
        self.sparse_model = sparse_model
        self.skip_errors = skip_errors

        self.processed_folder.mkdir(parents=True, exist_ok=True)
        logger.info("Orchestrator ready: raw=%s processed=%s", self.raw_folder, self.processed_folder)

    def run(self) -> PipelineResult:
        logger.info("Starting ingestion pipeline")

        documents = self._stage_ingestion()
        chunks = self._stage_chunking(documents)
        index_result = self._stage_indexing(chunks)

        result = PipelineResult(
            timestamp=datetime.now().isoformat(),
            documents=documents,
            chunks=chunks,
            index=index_result,
            manifest_path=str(self.processed_folder / "manifest.json"),
        )
        self._print_summary(result)
        return result

    def _stage_ingestion(self) -> list[ParsedDocument]:
        try:
            documents = ingest_documents(
                raw_folder=self.raw_folder,
                output_folder=self.processed_folder,
            )
        except Exception as e:
            logger.error("Ingestion failed: %s", e)
            if not self.skip_errors:
                raise
            return []

        logger.info("Ingestion complete: %d documents", len(documents))
        return documents

    def _stage_chunking(self, documents: list[ParsedDocument]) -> list[Chunk]:
        if not documents:
            logger.warning("No documents to chunk")
            return []

        logger.info(
            "Chunking %d documents (size=%d, overlap=%d)",
            len(documents), self.chunk_size, self.chunk_overlap,
        )
        try:
            chunker = DocumentChunker(self.chunk_size, self.chunk_overlap)
            docs = [to_document(d) for d in documents]
            chunks = list(chunker.split_all(docs))
        except Exception as e:
            logger.error("Chunking failed: %s", e)
            if not self.skip_errors:
                raise
            return []

        logger.info("Chunking complete: %d chunks", len(chunks))
        if chunks:
            lengths = [len(c.text) for c in chunks]
            logger.info(
                "Chunk length: avg %.0f, min %d, max %d",
                sum(lengths) / len(lengths), min(lengths), max(lengths),
            )
        return chunks

    def _stage_indexing(self, chunks: list[Chunk]) -> IndexResult:
        if not chunks:
            logger.warning("No chunks to index")
            return self._empty_index_result()

        logger.info(
            "Indexing %d chunks (dense=%s, sparse=%s)",
            len(chunks), self.dense_model, self.sparse_model,
        )
        try:
            repo = QdrantHybridRepository(
                self.qdrant_client,
                IndexConfig(dense_model=self.dense_model, sparse_model=self.sparse_model),
            )
            repo.init_schema()
            index_result = repo.add_chunks(chunks)
        except Exception as e:
            logger.error("Indexing failed: %s", e)
            if not self.skip_errors:
                raise
            return self._empty_index_result()

        logger.info("Indexing complete: %d chunks in %s", index_result.num_chunks, index_result.vector_store_path)
        return index_result

    def _empty_index_result(self) -> IndexResult:
        return IndexResult(
            vector_store_path="",
            bm25_index_path="",
            num_chunks=0,
            dense_model=self.dense_model,
            sparse_model=self.sparse_model,
            bm25_stats={},
            vector_stats={},
        )

    def _print_summary(self, result: PipelineResult) -> None:
        summary = result.summary()
        logger.info(
            "Pipeline complete: %d documents, %d chunks, collection %s",
            summary["documents_loaded"],
            summary["chunks_created"],
            summary["index_stats"]["vector_store"],
        )


def build_pipeline(
    qdrant_url: str = "http://localhost:6333",
    raw_folder: str = "data/raw",
    processed_folder: str = "data/processed",
    chunk_size: int = 384,
    chunk_overlap: int = 64,
    dense_model: str = "BAAI/bge-small-en-v1.5",
    sparse_model: str = "Qdrant/bm25",
    skip_errors: bool = True,
) -> IngestionOrchestrator:
    return IngestionOrchestrator(
        qdrant_client=QdrantClient(url=qdrant_url),
        raw_folder=Path(raw_folder),
        processed_folder=Path(processed_folder),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        dense_model=dense_model,
        sparse_model=sparse_model,
        skip_errors=skip_errors,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_pipeline().run()