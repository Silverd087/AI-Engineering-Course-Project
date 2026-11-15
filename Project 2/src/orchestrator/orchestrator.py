"""orchestrator/orchestrator.py"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from core.models import Chunk, IndexResult, PipelineResult
from indexing.config import IndexConfig
from indexing.repository import QdrantHybridRepository
from ingest import DocumentLoader, ParsedDocument, ingest_documents
from qdrant_client import QdrantClient

from chunking.chunker import DocumentChunker

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """Orchestrates the entire ingestion → chunking → indexing pipeline."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        raw_folder: Path = Path("data/raw"),
        processed_folder: Path = Path("data/processed"),
        vector_store_path: Path = Path("data/indexes"),
        chunk_size: int = 384,
        chunk_overlap: int = 64,
        dense_model: str = "BAAI/bge-small-en-v1.5",
        sparse_model: str = "Qdrant/bm25",
        skip_errors: bool = True,
    ):
        self.raw_folder = Path(raw_folder)
        self.processed_folder = Path(processed_folder)
        self.vector_store_path = Path(vector_store_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.dense_model: str = dense_model
        self.sparse_model: str = sparse_model
        self.skip_errors = skip_errors
        self.qdrant_client = qdrant_client

        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)

        logger.info("IngestionOrchestrator initialized")
        logger.info("  Raw folder: %s", self.raw_folder)
        logger.info("  Output folder: %s", self.processed_folder)
        logger.info("  Indexes folder: %s", self.vector_store_path)

    def run(self) -> PipelineResult:
        logger.info("")
        logger.info("=" * 80)
        logger.info("LIBRARIAN PIPELINE ORCHESTRATION")
        logger.info("=" * 80)
        logger.info("")

        # Stage 1: Ingestion
        logger.info("STAGE 1: INGESTION")
        logger.info("-" * 80)
        documents = self._stage_ingestion()

        # Stage 2: Chunking
        logger.info("")
        logger.info("STAGE 2: CHUNKING")
        logger.info("-" * 80)
        chunks = self._stage_chunking(documents)

        # Stage 3: Indexing
        logger.info("")
        logger.info("STAGE 3: INDEXING")
        logger.info("-" * 80)
        index_result = self._stage_indexing(chunks)

        # Build result
        result = PipelineResult(
            timestamp=datetime.now().isoformat(),
            documents=documents,
            chunks=chunks,
            index=index_result,
            manifest_path=str(self.processed_folder / "manifest.json"),
        )

        logger.info("")
        logger.info("PIPELINE COMPLETE")
        logger.info("-" * 80)
        self._print_summary(result)

        return result

    def _stage_ingestion(self) -> List[ParsedDocument]:
        logger.info("Loading documents from %s", self.raw_folder)

        try:
            documents = ingest_documents(
                raw_folder=self.raw_folder,
                output_folder=self.processed_folder,
            )

            logger.info("✓ Ingestion complete: %d documents loaded", len(documents))
            logger.info("  Manifest saved to %s", self.processed_folder / "manifest.json")

            total_chars = sum(len(d.text) for d in documents)
            logger.info("  Total text: %d characters", total_chars)

            with_prereqs = [
                d for d in documents if getattr(getattr(d, "metadata", None), "prerequisites", None)
            ]
            logger.info("  Documents with prerequisites: %d", len(with_prereqs))

            return documents

        except Exception as e:
            logger.error("✗ Ingestion failed: %s", e)
            if not self.skip_errors:
                raise
            return []

    def _stage_chunking(self, documents: List[ParsedDocument]) -> List[Chunk]:
        if not documents:
            logger.warning("⚠ No documents to chunk")
            return []

        logger.info(
            "Chunking %d documents (size=%d, overlap=%d)",
            len(documents),
            self.chunk_size,
            self.chunk_overlap,
        )

        try:
            chunker = DocumentChunker(self.chunk_size, self.chunk_overlap)
            chunks: List[Chunk] = list(chunker.split_all(documents))
            logger.info("✓ Chunking complete: %d chunks created", len(chunks))

            if chunks:
                avg_length = sum(len(c.text) for c in chunks) / len(chunks)
                logger.info("  Average chunk length: %.0f characters", avg_length)
                logger.info(
                    "  Min/max length: %d/%d characters",
                    min(len(c.text) for c in chunks),
                    max(len(c.text) for c in chunks),
                )

            return chunks

        except Exception as e:
            logger.error("✗ Chunking failed: %s", e)
            if not self.skip_errors:
                raise
            return []

    def _stage_indexing(self, chunks: List[Chunk]) -> IndexResult:
        if not chunks:
            logger.warning("⚠ No chunks to index")
            return IndexResult(
                vector_store_path="",
                bm25_index_path="",
                num_chunks=0,
                dense_model=self.dense_model,
                sparse_model=self.sparse_model,
                bm25_stats={},
                vector_stats={},
            )

        logger.info("Building indexes for %d chunks", len(chunks))
        logger.info("Dense Embedding model: %s", self.dense_model)

        try:
            index_config = IndexConfig(
                dense_model=self.dense_model,
                sparse_model=self.sparse_model,
            )
            indexer = QdrantHybridRepository(self.qdrant_client, index_config)
            indexer.init_schema()

            # Pass iter(chunks) if QdrantHybridRepository expects an iterator,
            # or pass chunks directly if it accepts a Sequence/List:
            index_result = indexer.add_chunks(iter(chunks))

            logger.info("✓ Indexing complete")
            logger.info("  Vector store: %s", index_result.vector_store_path)
            logger.info("  BM25 index: %s", index_result.bm25_index_path)
            logger.info("  Chunks indexed: %d", index_result.num_chunks)

            return index_result

        except Exception as e:
            logger.error("✗ Indexing failed: %s", e)
            if not self.skip_errors:
                raise
            return IndexResult(
                vector_store_path="",
                bm25_index_path="",
                num_chunks=0,
                dense_model=self.dense_model,
                sparse_model=self.sparse_model,
                bm25_stats={},
                vector_stats={},
            )

    def _print_summary(self, result: PipelineResult):
        summary = result.summary()

        logger.info("")
        logger.info("SUMMARY")
        logger.info("-" * 80)
        logger.info("Timestamp: %s", summary.get("timestamp"))
        logger.info("Documents loaded: %d", summary.get("documents_loaded", 0))
        logger.info("Total text: %d characters", summary.get("total_text_chars", 0))
        logger.info("Chunks created: %d", summary.get("chunks_created", 0))
        logger.info("Average chunk length: %.0f characters", summary.get("avg_chunk_length", 0))
        logger.info("")
        
        index_stats = summary.get("index_stats", {})
        logger.info("Index Configuration:")
        logger.info("  Dense model: %s", index_stats.get("dense_embedding_model", self.dense_model))
        logger.info("  Vector store: %s", index_stats.get("vector_store", "qdrant"))
        logger.info("")
        logger.info("=" * 80)
        logger.info("")


def build_pipeline(
    raw_folder: str = "data/raw",
    processed_folder: str = "data/processed",
    vector_store_path: str = "data/indexes",
    chunk_size: int = 384,
    chunk_overlap: int = 64,
    dense_model: str = "BAAI/bge-small-en-v1.5",
    sparse_model: str = "Qdrant/bm25",
    skip_errors: bool = True,
) -> IngestionOrchestrator:
    return IngestionOrchestrator(
        qdrant_client=QdrantClient(url="http://localhost:6333"),
        raw_folder=Path(raw_folder),
        processed_folder=Path(processed_folder),
        vector_store_path=Path(vector_store_path),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        dense_model=dense_model,
        sparse_model=sparse_model,
        skip_errors=skip_errors,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    pipeline = build_pipeline()
    pipeline.run()