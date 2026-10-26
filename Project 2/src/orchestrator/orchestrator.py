import logging
from pathlib import Path
from typing import List
from datetime import datetime
from src.core.models import PipelineResult,Chunk,IndexResult
 
# Ingestion imports
from src.ingest import ingest_documents, DocumentLoader, ParsedDocument
from src.chunking.chunker import DocumentChunker
from src.indexing.repository import QdrantHybridRepository
from src.indexing.config import IndexConfig
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    """
    Orchestrates the entire ingestion → chunking → indexing pipeline.
    
    Usage:
        orchestrator = IngestionOrchestrator()
        result = orchestrator.run()
    """
    
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
        """
        Initialize the orchestrator.
        
        Args:
            raw_folder: Where source documents are
            processed_folder: Where to save processed outputs
            vector_store_path: Where to save indexes
            chunk_size: Target chunk size for chunking
            overlap: Overlap between chunks
            embedding_model: Model for embeddings
            skip_errors: Continue on errors vs. fail fast
        """
        self.raw_folder = Path(raw_folder)
        self.processed_folder = Path(processed_folder)
        self.vector_store_path = Path(vector_store_path)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.dense_model: str = dense_model
        self.sparse_model: str = sparse_model
        self.skip_errors = skip_errors
        self.qdrant_client = qdrant_client
        
        # Create output folders
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"IngestionOrchestrator initialized")
        logger.info(f"  Raw folder: {self.raw_folder}")
        logger.info(f"  Output folder: {self.processed_folder}")
        logger.info(f"  Indexes folder: {self.vector_store_path}")
    
    def run(self) -> PipelineResult:
        """
        Run the complete pipeline: ingest → chunk → index.
        
        Returns:
            PipelineResult with all outputs
        """
        logger.info("")
        logger.info("="*80)
        logger.info("LIBRARIAN PIPELINE ORCHESTRATION")
        logger.info("="*80)
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
            manifest_path=str(self.processed_folder / "manifest.json")
        )
        
        # Print summary
        logger.info("")
        logger.info("PIPELINE COMPLETE")
        logger.info("-" * 80)
        self._print_summary(result)
        
        return result
    
    def _stage_ingestion(self) -> List[ParsedDocument]:
        """Run ingestion stage."""
        logger.info("Loading documents from %s", self.raw_folder)
        
        try:
            documents = ingest_documents(
                raw_folder=self.raw_folder,
                output_folder=self.processed_folder
            )
            
            logger.info("✓ Ingestion complete: %d documents loaded", len(documents))
            logger.info("  Manifest saved to data/processed/manifest.json")
            
            # Print summary
            total_chars = sum(len(d.text) for d in documents)
            logger.info("  Total text: %d characters", total_chars)
            
            with_prereqs = [d for d in documents if d.metadata.prerequisites]
            logger.info("  Documents with prerequisites: %d", len(with_prereqs))
            
            return documents
        
        except Exception as e:
            logger.error("✗ Ingestion failed: %s", e)
            if not self.skip_errors:
                raise
            return []
    
    def _stage_chunking(self, documents: List[ParsedDocument]) -> List[Chunk]:
        """Run chunking stage."""
        if not documents:
            logger.warning("⚠ No documents to chunk")
            return []
        
        logger.info("Chunking %d documents (size=%d, overlap=%d)",
                   len(documents), self.chunk_size, self.chunk_overlap)
        
        try:
            chunker = DocumentChunker(self.chunk_size,self.chunk_overlap)
            chunk_iterator = chunker.split_all(documents)
            chunks = []
            logger.info("✓ Chunking complete: %d chunks created", len(chunks))
            
            # Statistics
            if chunk_iterator:
                for chunk in chunk_iterator:
                    chunks.append(chunk)
                avg_length = sum(len(c.text) for c in chunks) / len(chunks)
                logger.info("  Average chunk length: %.0f characters", avg_length)
                logger.info("  Min/max length: %d/%d characters",
                           min(len(c.text) for c in chunks),
                           max(len(c.text) for c in chunks))
            
            return chunk_iterator
        
        except Exception as e:
            logger.error("✗ Chunking failed: %s", e)
            if not self.skip_errors:
                raise
            return []
    
    def _stage_indexing(self, chunks: List[Chunk]) -> IndexResult:
        """Run indexing stage."""
        if not chunks:
            logger.warning("⚠ No chunks to index")
            return IndexResult(
                vector_store_path="",
                bm25_index_path="",
                num_chunks=0,
                dense_model=self.dense_model,
                sparse_model=self.sparse_model
                bm25_stats={},
                vector_stats={}
            )
        
        logger.info("Building indexes for %d chunks", len(chunks))
        logger.info("  Embedding model: %s", self.embedding_model)
        
        try:
            index_config = IndexConfig(
                dense_model=self.dense_model,
                sparse_model=self.sparse_model
                )
            indexer = QdrantHybridRepository(self.qdrant_client,index_config)
            index_result = indexer.add_chunks(chunks)
            
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
                embedding_model=self.embedding_model,
                bm25_stats={},
                vector_stats={}
            )
    
    def _print_summary(self, result: PipelineResult):
        """Print final summary."""
        summary = result.summary()
        
        logger.info("")
        logger.info("SUMMARY")
        logger.info("-" * 80)
        logger.info("Timestamp: %s", summary["timestamp"])
        logger.info("Documents loaded: %d", summary["documents_loaded"])
        logger.info("Total text: %d characters", summary["total_text_chars"])
        logger.info("Chunks created: %d", summary["chunks_created"])
        logger.info("Average chunk length: %.0f characters", summary["avg_chunk_length"])
        logger.info("")
        logger.info("Index Configuration:")
        logger.info("  Embedding model: %s", summary["index_stats"]["embedding_model"])
        logger.info("  Vector store: %s", summary["index_stats"]["vector_store"])
        logger.info("")
        logger.info("="*80)
        logger.info("")
 
 
def build_pipeline(
    raw_folder: str = "data/raw",
    processed_folder: str = "data/processed",
    vector_store_path: str = "data/indexes",
    chunk_size: int = 384,
    chunk_overlap: int = 64,
    embedding_model: str = "sentence-transformers/multilingual-e5-base",
    skip_errors: bool = True
) -> IngestionOrchestrator:
    """
    Factory function to create and configure the pipeline orchestrator.
    
    Args:
        raw_folder: Where source documents are stored
        processed_folder: Where to save processed outputs
        vector_store_path: Where to save vector and keyword indexes
        chunk_size: Target size for document chunks
        overlap: Overlap between consecutive chunks
        embedding_model: Transformer model for embeddings
        skip_errors: Continue on errors vs fail fast
    
    Returns:
        Configured IngestionOrchestrator ready to run
    
    Example:
        pipeline = build_pipeline(
            chunk_size=512,
            embedding_model="sentence-transformers/multilingual-e5-base"
        )
        result = pipeline.run()
        print(f"Indexed {result.index.num_chunks} chunks")
    """
    return IngestionOrchestrator(
        raw_folder=Path(raw_folder),
        processed_folder=Path(processed_folder),
        vector_store_path=Path(vector_store_path),
        chunk_size=chunk_size,
        overlap=chunk_overlap,
        embedding_model=embedding_model,
        skip_errors=skip_errors
    )
 