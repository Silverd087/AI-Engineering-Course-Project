from abc import ABC, abstractmethod
from pathlib import Path
from .models import ParsedDocument, DocumentMetadata
import logging
 
logger = logging.getLogger(__name__)
 
 
class DocumentParser(ABC):
    """
    Abstract base class for all document parsers.
    
    Each parser (PDF, Word, etc.) must implement these methods.
    """
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file type.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if this parser can handle it, False otherwise
        
        Example:
            def can_parse(self, file_path: Path) -> bool:
                return file_path.suffix.lower() == ".pdf"
        """
        pass
    
    @abstractmethod
    def parse(self, file_path: Path, metadata: DocumentMetadata) -> ParsedDocument:
        """
        Parse a document and return a ParsedDocument object.
        
        Args:
            file_path: Path to the file to parse
            metadata: Base metadata (already filled with title, course code, year, etc.)
        
        Returns:
            ParsedDocument with:
                - metadata: Updated with any new info extracted from the document
                - text: Full extracted text
                - sections: List of (heading, text) tuples (optional)
                - tables: List of extracted tables (optional)
        
        Raises:
            Exception: If parsing fails
        
        Example:
            def parse(self, file_path: Path, metadata: DocumentMetadata) -> ParsedDocument:
                with open(file_path) as f:
                    text = f.read()
                return ParsedDocument(
                    metadata=metadata,
                    text=text,
                    sections=[],
                    tables=[]
                )
        """
        pass