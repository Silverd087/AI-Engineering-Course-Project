from pathlib import Path
from typing import List, Optional, Callable
from .models import ParsedDocument, DocumentMetadata
from .pdf_parser import PDFParser
from .word_parser import WordParser
from .metadata_extractor import MetadataExtractor
import logging

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    Load and parse all documents from a folder.
    
    Supports:
        - PDF files
    
    Automatically extracts metadata from filenames and folders.
    """
    
    def __init__(self):
        """Initialize the loader with all available parsers."""
        self.parsers = [PDFParser(),WordParser()]
        self.metadata_extractor = MetadataExtractor()
        logger.info(f"DocumentLoader initialized with {len(self.parsers)} parsers")
    
    def load_from_folder(
        self,
        folder_path: Path,
        custom_metadata_extractor: Optional[Callable] = None,
        skip_errors: bool = True
    ) -> List[ParsedDocument]:
        """
        Load all parseable documents from a folder (recursively).
        
        Args:
            folder_path: Path to data/raw/ or similar
            custom_metadata_extractor: Optional function to override metadata extraction.
                                       Function signature: (file_path: Path) -> DocumentMetadata
            skip_errors: If True, skip files that fail to parse. If False, raise exception.
        
        Returns:
            List of ParsedDocument, sorted by course code and title
        
        Raises:
            FileNotFoundError: If folder does not exist
            Exception: If a file fails to parse and skip_errors=False
        """
        folder_path = Path(folder_path)
        
        logger.info(f"Loading documents from: {folder_path}")
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder_path}")
        
        documents = []
        failed_files = []
        skipped_files = []
        
        # Find all parseable files (recursive)
        all_files = sorted(folder_path.rglob("*"))
        parseable_files = [f for f in all_files if f.is_file() and self._find_parser(f)]
        
        logger.info(f"Found {len(parseable_files)} parseable files")
        
        for file_path in parseable_files:
            parser = self._find_parser(file_path)
            
            if parser is None:
                skipped_files.append(file_path)
                logger.debug(f"  Skipping {file_path.name} (no parser)")
                continue
            
            # Extract metadata
            try:
                if custom_metadata_extractor:
                    metadata = custom_metadata_extractor(file_path)
                else:
                    metadata = self.metadata_extractor.extract_from_filename(file_path)
            except Exception as e:
                logger.error(f"  Failed to extract metadata from {file_path.name}: {e}")
                failed_files.append((file_path, str(e)))
                if not skip_errors:
                    raise
                continue
            
            # Parse the file
            try:
                doc = parser.parse(file_path, metadata)
                documents.append(doc)
                
                # Log summary
                prog = f"[{metadata.programmes}]" if metadata.programmes else ""
                course = f"{metadata.course_code or 'N/A':<10}" if metadata.course_code else "N/A       "
                logger.info(f"  ✓ {course} {metadata.semester:<7} {metadata.year} {prog}")
            
            except Exception as e:
                logger.error(f"  ✗ {file_path.name}: {e}")
                failed_files.append((file_path, str(e)))
                if not skip_errors:
                    raise
        
        # Summary
        logger.info("")
        logger.info(f"✓ Successfully loaded {len(documents)} documents")
        if skipped_files:
            logger.warning(f"⊘ Skipped {len(skipped_files)} files (no parser)")
        if failed_files:
            logger.warning(f"✗ Failed to parse {len(failed_files)} files")
            for path, error in failed_files[:3]:  # Show first 3 errors
                logger.warning(f"    {path.name}: {error}")
            if len(failed_files) > 3:
                logger.warning(f"    ... and {len(failed_files) - 3} more")
        
        # Sort by course code and title
        documents.sort(
            key=lambda d: (d.metadata.course_code or "zzz", d.metadata.title)
        )
        
        return documents
    
    def _find_parser(self, file_path: Path):
        """Find the appropriate parser for this file, or None."""
        for parser in self.parsers:
            try:
                if parser.can_parse(file_path):
                    return parser
            except Exception:
                pass
        return None