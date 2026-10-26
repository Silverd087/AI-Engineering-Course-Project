# src/orchestrator/__init__.py

"""
Orchestrator module: Coordinates ingestion, chunking, and indexing.

Main entry point:
    from src.orchestrator import build_pipeline
    
    pipeline = build_pipeline()
    result = pipeline.run()
"""

from .orchestrator import (
    IngestionOrchestrator,
    build_pipeline,
    PipelineResult,
    Chunk,
    IndexResult,
    chunk_documents,
    build_indexes,
)

__all__ = [
    "IngestionOrchestrator",
    "build_pipeline",
    "PipelineResult",
    "Chunk",
    "IndexResult",
    "chunk_documents",
    "build_indexes",
]