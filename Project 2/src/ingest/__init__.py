"""
Document ingestion module for the Librarian project.

Loads, parses, and processes course syllabi and academic regulations.

Main entry point:
    from src.ingest import ingest_documents
    
    docs = ingest_documents(
        raw_folder="data/raw",
        output_folder="data/processed"
    )
"""

from .ingest import ingest_documents
from .loader import DocumentLoader
from .models import DocumentMetadata, ParsedDocument
from .metadata_extractor import MetadataExtractor
from .pdf_parser import PDFParser
from .word_parser import WordParser

__all__ = [
    "ingest_documents",
    "DocumentLoader",
    "DocumentMetadata",
    "ParsedDocument",
    "MetadataExtractor",
    "PDFParser",
    "WordParser",
]