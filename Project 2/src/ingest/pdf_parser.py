import pymupdf  # pip install pymupdf
from pathlib import Path
from .models import ParsedDocument, DocumentMetadata
from .parsers import DocumentParser
import re
import logging

logger = logging.getLogger(__name__)


class PDFParser(DocumentParser):
    """
    Parse PDF files and extract text with metadata.
    
    Extracts:
        - Full text
        - Prerequisites from the Prerequisites section
        - Credits/hours
        - Sections based on headings
    """
    
    def can_parse(self, file_path: Path) -> bool:
        """Return True if this is a PDF file."""
        return file_path.suffix.lower() == ".pdf"
    
    def parse(self, file_path: Path, metadata: DocumentMetadata) -> ParsedDocument:
        """
        Parse a PDF and extract its content.
        """
        logger.info(f"Parsing PDF: {file_path.name}")
        
        try:
            doc = pymupdf.open(file_path)
            text_parts = []
            
            # Extract text from all pages
            page_count = doc.page_count
            for page_num, page in enumerate(doc):
                text = page.get_text()
                text_parts.append(text)
            
            full_text = "\n".join(text_parts)
            doc.close()
            
            # Extract metadata from content
            prerequisites = self._extract_prerequisites(full_text)
            corequisites = self._extract_corequisites(full_text)
            credits = self._extract_credits(full_text)
            programmes = self._extract_programmes(full_text)
            
            # Update metadata
            metadata.prerequisites = prerequisites
            metadata.corequisites = corequisites
            metadata.credits = credits
            if programmes:
                metadata.programmes = programmes  # NEW

            
            logger.info(f"  ✓ Extracted {len(full_text)} characters from {page_count} pages")
            if programmes:
                logger.info(f"    Programmes: {', '.join(programmes)}")
            if prerequisites:
                logger.info(f"    Prerequisites: {', '.join(prerequisites)}")
            if credits:
                logger.info(f"    Credits: {credits}")
            
            return ParsedDocument(
                metadata=metadata,
                text=full_text,
                sections=[],
                tables=[]
            )
        
        except Exception as e:
            logger.error(f"  ✗ Failed to parse {file_path.name}: {e}")
            raise
    def _extract_prerequisites(self, text: str) -> list:
        """
        Extract course codes from the Prerequisites section only.
        
        Handles patterns like:
            - "CS280 Introduction to Artificial Intelligence"
            - "CS280 and CS300"
            - "CS280, CS300, CS400"
            - "Prerequisite: CS280"
            - Multiple prerequisites on separate lines
        
        Returns:
            List of unique course codes sorted, or None if no prerequisites found
        """
        # Find the Prerequisites section
        prereq_section = self._find_section(text, "Prerequisites")
        
        if not prereq_section:
            logger.debug("  No Prerequisites section found")
            return None
        
        logger.debug(f"  Prerequisites section found ({len(prereq_section)} chars)")
        
        # Extract course codes from this section only
        # Pattern: CS/AI/SE/REE/IS/BI followed by 3+ digits
        pattern = r'(?:CS|AI|SE|REE|IS|BI)\d{3,}'
        matches = re.findall(pattern, prereq_section)
        
        if matches:
            # Remove duplicates and sort
            unique_codes = sorted(set(matches))
            logger.info(f"    Found {len(unique_codes)} prerequisite(s): {', '.join(unique_codes)}")
            return unique_codes
        
        logger.debug("  No course codes found in Prerequisites section")
        return None
    
    def _extract_corequisites(self, text: str) -> list:
        """
        Extract course codes from the Corequisites section.
        
        Returns:
            List of course codes, or None if no corequisites found
        """
        coreq_section = self._find_section(text, "Corequisites")
        
        if not coreq_section:
            return None
        
        pattern = r'(?:CS|AI|SE|REE|IS|BI)\d{3,}'
        matches = re.findall(pattern, coreq_section)
        
        if matches:
            unique_codes = sorted(set(matches))
            logger.info(f"    Found {len(unique_codes)} corequisite(s): {', '.join(unique_codes)}")
            return unique_codes
        
        return None
    
    def _find_section(self, text: str, section_name: str) -> str:
        """
        Find a section by name and return its content until the next section.
        
        Args:
            text: Full document text
            section_name: Name of the section (e.g., "Prerequisites")
        
        Returns:
            Section text, or None if section not found
        
        Example:
            >>> section = self._find_section(text, "Prerequisites")
            >>> # Returns everything from "Prerequisites" until the next heading
        """
        # Look for the section header (case-insensitive)
        # Capture everything until the next heading or end of document
        pattern = rf'{section_name}.*?(?=\n[A-Z][A-Za-z\s]+\n|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(0)
        return None
    
    def _extract_credits(self, text: str) -> str:
        """
        Extract credit hours information.
        
        Handles patterns like:
            - "4 Credits / 4 Hours"
            - "3 Credits"
            - "4 Credits/4 Hours"
        
        Returns:
            Credit string, or None if not found
        """
        pattern = r'(\d+\s+Credits?\s*/?[\s\d]*(?:Hours?)?)'
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    def _extract_programmes(self, text: str) -> list[str]:
        """
        Extract programmes (CSE, SWE, REE, etc.) 
        from the "Position in the Educational System" section.
        
        Looks for patterns like:
            - "CSE, SWE, REE | Required"
            - "Computer Science Engineering, Software Engineering | Elective"
            - "CSE | Required"
        
        Returns:
            programmes_list
            Example: ["CSE", "SWE", "REE"]
        """
        # Find the "Position in the Educational System" section
        section = self._find_section(text, "Position in the Educational System")
        
        if not section:
            logger.debug("  No 'Position in the Educational System' section found")
            return None, None
        
        logger.debug(f"  Found position section: {section[:200]}")
        
        # Look for patterns like "CSE, SWE, REE | Required"
        # Pattern: uppercase letters (programme codes) separated by commas/and, 
        # then a pipe, then a status word
        pattern = r'([A-Z]{2,3}(?:\s*,\s*[A-Z]{2,3})*)\s*\|\s*(Required|Elective|Recommended)'
        match = re.search(pattern, section)
        
        if match:
            programmes_str = match.group(1)
            
            # Parse programme codes (CSE, SWE, REE)
            programmes = [p.strip() for p in programmes_str.split(',')]
            
            logger.info(f"    Found programmes: {programmes}")
            return programmes
        
        logger.debug("  No programme pattern found in position section")
        return None, None