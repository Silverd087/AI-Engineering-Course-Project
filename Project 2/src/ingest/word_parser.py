from docx import Document  # pip install python-docx
from pathlib import Path
from .models import ParsedDocument, DocumentMetadata
from .parsers import DocumentParser
import logging

logger = logging.getLogger(__name__)


class WordParser(DocumentParser):
    """
    Parse Word (.docx) files and extract text with metadata.
    
    Extracts:
        - Paragraphs and text
        - Headings and structure
        - Tables
    """
    
    def can_parse(self, file_path: Path) -> bool:
        """Return True if this is a Word document."""
        return file_path.suffix.lower() in [".docx", ".doc"]
    
    def parse(self, file_path: Path, metadata: DocumentMetadata) -> ParsedDocument:
        """
        Parse a Word document and extract its content.
        
        Args:
            file_path: Path to the Word file
            metadata: Base metadata (will be updated with extracted info)
        
        Returns:
            ParsedDocument with extracted text and metadata
        """
        logger.info(f"Parsing Word file: {file_path.name}")
        
        try:
            doc = Document(file_path)
            text_parts = []
            sections = []
            tables_text = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
                    
                    # Track headings
                    if para.style.name.startswith("Heading"):
                        sections.append((para.text, "heading"))
            
            # Extract tables
            for table_idx, table in enumerate(doc.tables):
                table_text = []
                for row_idx, row in enumerate(table.rows):
                    row_cells = [cell.text.strip() for cell in row.cells]
                    row_text = " | ".join(row_cells)
                    table_text.append(row_text)
                
                if table_text:
                    tables_text.append("\n".join(table_text))
            
            full_text = "\n".join(text_parts)
            
            logger.info(f"  ✓ Extracted {len(full_text)} characters")
            logger.info(f"    Paragraphs: {len(doc.paragraphs)}, Tables: {len(doc.tables)}")
            
            return ParsedDocument(
                metadata=metadata,
                text=full_text,
                sections=sections,
                tables=tables_text
            )
        
        except Exception as e:
            logger.error(f"  ✗ Failed to parse {file_path.name}: {e}")
            raise