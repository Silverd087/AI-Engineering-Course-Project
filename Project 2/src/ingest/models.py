import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


def _slug(source_path: str) -> str:
    """Filesystem-stable id for a document, derived from its file stem."""
    stem = Path(source_path).stem
    return re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower() or "doc"


@dataclass
class DocumentMetadata:
    """
    Metadata for a MedTech course syllabus or academic regulation.
    
    Extracted from the filename, folder structure, and document content.
    """
    # Basic identification
    title: str                          # "CS434 Data Science" or "Grading Regulations"
    course_code: Optional[str]          # "CS434"
    source_path: str                    # Full path to the original file
    
    # Academic context
    programmes: List[str]                      # "AI Engineering", "Computer Science", etc.
    year: int                           # 2026
    semester: str                       # "Fall", "Spring"
    
    # Document classification
    source_type: str                    # "syllabus", "regulation", "handbook", "exam-rules"
    section: Optional[str]              # "Grading", "Prerequisites" (for multi-section documents)
    
    # Course information (extracted from document)
    prerequisites: Optional[List[str]]  # ["CS280", "CS300"]
    corequisites: Optional[List[str]]   # ["CS500"]
    recommended: Optional[List[str]]    # ["CS200", "CS250"]
    credits: Optional[str]              # "4 Credits / 4 Hours"
    
    # For tracking
    raw_text: str = ""                  # Full text (set by parser)
 
 
@dataclass
class ParsedDocument:
    """
    A document after parsing, ready to chunk.
    
    Contains the extracted text, metadata, and structural information.
    """
    
    metadata: DocumentMetadata          # Updated metadata
    text: str                           # Full extracted text
    sections: List[tuple]               # List of (heading, content) tuples
    tables: List[str]                   # List of extracted tables (as text)
    doc_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Deterministic, stable across ingestion runs: downstream chunk_ids
        # (f"{doc_id}::{chunk_idx}") and Qdrant point ids are derived from this,
        # so a random id here would orphan old points and invalidate any eval
        # set that pins relevant_chunk_ids on every re-ingest.
        if not self.doc_id:
            self.doc_id = _slug(self.metadata.source_path)

    def summary(self) -> dict:
        """Return a summary of the document."""
        return {
            "title": self.metadata.title,
            "course_code": self.metadata.course_code,
            "text_length": len(self.text),
            "num_sections": len(self.sections),
            "num_tables": len(self.tables),
            "prerequisites": self.metadata.prerequisites,
            "credits": self.metadata.credits,
        }
 