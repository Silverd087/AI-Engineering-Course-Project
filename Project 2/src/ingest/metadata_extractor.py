from pathlib import Path
from .models import DocumentMetadata
import re
import logging
from typing import List,Optional

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """
    Extract metadata from filename and folder structure.
    
    Supports filenames like:
        - CS434-SYLLABUS-F26.pdf
        - CS496-EXAM-RULES-S26.pdf
        - GRADING-REGULATIONS-2026.pdf
        - CS434-EXAM-RULES-F26.pdf
    """
    
    # Map of document type keywords to source_type
    DOC_TYPE_MAP = {
        "syllabus": "syllabus",
        "exam": "exam-rules",
        "rules": "regulation",
        "regulation": "regulation",
        "regulations": "regulation",
        "handbook": "handbook",
        "grading": "regulation",
        "prerequisites": "regulation",
    }
    
    # Valid course code prefixes
    COURSE_CODE_PATTERN = r'^[A-Z]{2,3}\d{3,}$'
    
    @staticmethod
    def extract_from_filename(
        file_path: Path,
        default_programmes: Optional[List[str]] = None
    ) -> DocumentMetadata:
        """
        Extract metadata from a filename.
        
        Args:
            file_path: Path to the document file
            default_programme: Default programme if not detected
        
        Returns:
            DocumentMetadata with extracted information
        
        Example:
            >>> extractor = MetadataExtractor()
            >>> meta = extractor.extract_from_filename(Path("CS434-SYLLABUS-F26.pdf"))
            >>> print(meta.course_code)
            CS434
            >>> print(meta.semester)
            Fall
        """
        stem = file_path.stem  # "CS434-SYLLABUS-F26"
        parts = stem.split("-")
        
        course_code = None
        doc_type = "syllabus"  # default
        semester = "Fall"      # default
        year = 2026            # default
        
        logger.debug(f"Extracting metadata from: {stem}")
        logger.debug(f"  Parts: {parts}")
        
        # Try to identify course code (first part, e.g., "CS434")
        if len(parts) >= 1 and re.match(MetadataExtractor.COURSE_CODE_PATTERN, parts[0]):
            course_code = parts[0]
            logger.debug(f"  Found course code: {course_code}")
        
        # Identify document type (second part or later, e.g., "SYLLABUS", "EXAM", "RULES")
        if len(parts) >= 2:
            for i, part in enumerate(parts[1:], start=1):
                part_lower = part.lower()
                if part_lower in MetadataExtractor.DOC_TYPE_MAP:
                    doc_type = MetadataExtractor.DOC_TYPE_MAP[part_lower]
                    logger.debug(f"  Found doc type: {doc_type} (from '{part}')")
                    break
        
        # Extract year and semester (last part, e.g., "F26", "S26", "2026")
        if len(parts) >= 1:
            last_part = parts[-1]
            
            # Pattern: F26, S26, etc.
            if len(last_part) >= 2 and last_part[0] in 'FSfsx':
                if last_part[0] in 'Ff':
                    semester = "Fall"
                elif last_part[0] in 'Ss':
                    semester = "Spring"
                elif last_part[0] in 'Xx':
                    semester = "Summer"
                
                # Extract year from the digits
                if last_part[1:].isdigit():
                    year_digits = int(last_part[1:])
                    year = 2000 + year_digits if year_digits < 100 else year_digits
                
                logger.debug(f"  Found semester/year: {semester} {year}")
            
            # Pattern: just a year (2026, 2025, etc.)
            elif last_part.isdigit() and len(last_part) == 4:
                year = int(last_part)
                logger.debug(f"  Found year: {year}")
        
        # Build title
        if course_code:
            title = f"{course_code} {doc_type.replace('-', ' ').title()}"
        else:
            title = doc_type.replace('-', ' ').title()
        
        logger.debug(f"  Final title: {title}")
        
        return DocumentMetadata(
            title=title,
            course_code=course_code,
            source_path=str(file_path),
            programmes=default_programmes or [], 
            year=year,
            semester=semester,
            source_type=doc_type,
            section=None,
            prerequisites=None,
            corequisites=None,
            recommended=None,
            credits=None,
            raw_text=""
        )


if __name__ == "__main__":
    # Test it
    logging.basicConfig(level=logging.DEBUG)
    
    test_files = [
        "CS434-SYLLABUS-F26.pdf",
        "CS496-EXAM-RULES-S26.pdf",
        "GRADING-REGULATIONS-2026.pdf",
        "CS280-SYLLABUS-F26.pdf",
        "CS434-EXAM-RULES-F26.pdf",
    ]
    
    extractor = MetadataExtractor()
    
    print("\n" + "="*80)
    print("Testing MetadataExtractor")
    print("="*80 + "\n")
    
    for fname in test_files:
        meta = extractor.extract_from_filename(Path(fname))
        print(f"✓ {fname}")
        print(f"    Title: {meta.title}")
        print(f"    Course: {meta.course_code}")
        print(f"    Type: {meta.source_type}")
        print(f"    Semester: {meta.semester} {meta.year}")
        print()