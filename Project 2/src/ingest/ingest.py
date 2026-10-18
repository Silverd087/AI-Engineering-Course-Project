from pathlib import Path
from .loader import DocumentLoader
from .models import ParsedDocument
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def ingest_documents(
    raw_folder: Path = Path("data/raw"),
    output_folder: Path = Path("data/processed")
) -> list:
    """
    Load raw documents, parse them, and save a manifest.
    
    Args:
        raw_folder: Path to data/raw/ (contains source documents)
        output_folder: Path to data/processed/ (will contain parsed documents)
    
    Returns:
        List of ParsedDocument objects
    """
    raw_folder = Path(raw_folder)
    output_folder = Path(output_folder)
    
    # Create output folder if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info("")
    logger.info("="*80)
    logger.info("DOCUMENT INGESTION")
    logger.info("="*80)
    logger.info(f"Source: {raw_folder}")
    logger.info(f"Output: {output_folder}")
    logger.info("")
    
    # Load documents
    loader = DocumentLoader()
    documents = loader.load_from_folder(raw_folder, skip_errors=True)
    
    # Build manifest
    manifest = _build_manifest(documents)
    
    # Save manifest
    manifest_path = output_folder / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    logger.info("")
    logger.info(f"Manifest saved to {manifest_path}")
    logger.info("")
    
    # Print summary
    _print_summary(documents, manifest)
    
    return documents


def _build_manifest(documents: list) -> dict:
    """Build a manifest of all loaded documents."""
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "count": len(documents),
        "by_programme": {},
        "by_year": {},
        "by_type": {},
        "documents": []
    }
    
    for doc in documents:
        entry = {
            "title": doc.metadata.title,
            "course_code": doc.metadata.course_code,
            "source_path": doc.metadata.source_path,
            "programmes": doc.metadata.programmes,
            "year": doc.metadata.year,
            "semester": doc.metadata.semester,
            "source_type": doc.metadata.source_type,
            "prerequisites": doc.metadata.prerequisites,
            "corequisites": doc.metadata.corequisites,
            "credits": doc.metadata.credits,
            "text_length": len(doc.text),
            "num_sections": len(doc.sections),
            "num_tables": len(doc.tables)
        }
        manifest["documents"].append(entry)
        
        # Index by programme, year, and type
        year = doc.metadata.year
        dtype = doc.metadata.source_type

        for prog in doc.metadata.programmes:
            if prog not in manifest["by_programme"]:
                manifest["by_programme"][prog] = 0
            manifest["by_programme"][prog] += 1
        
        if year not in manifest["by_year"]:
            manifest["by_year"][year] = 0
        manifest["by_year"][year] += 1
        
        if dtype not in manifest["by_type"]:
            manifest["by_type"][dtype] = 0
        manifest["by_type"][dtype] += 1
    
    return manifest


def _print_summary(documents: list, manifest: dict) -> None:
    """Print a summary of the loaded documents."""
    logger.info("SUMMARY")
    logger.info("-" * 80)
    logger.info(f"Total documents: {manifest['count']}")
    logger.info("")
    
    if manifest["by_programme"]:
        logger.info("By Programme:")
        for prog, count in sorted(manifest["by_programme"].items()):
            logger.info(f"  {prog}: {count}")
        logger.info("")
    
    if manifest["by_year"]:
        logger.info("By Year:")
        for year, count in sorted(manifest["by_year"].items()):
            logger.info(f"  {year}: {count}")
        logger.info("")
    
    if manifest["by_type"]:
        logger.info("By Document Type:")
        for dtype, count in sorted(manifest["by_type"].items()):
            logger.info(f"  {dtype}: {count}")
        logger.info("")
    
    # Statistics
    total_chars = sum(len(d.text) for d in documents)
    total_sections = sum(len(d.sections) for d in documents)
    total_tables = sum(len(d.tables) for d in documents)
    
    logger.info("Statistics:")
    logger.info(f"  Total text: {total_chars:,} characters")
    logger.info(f"  Total sections: {total_sections}")
    logger.info(f"  Total tables: {total_tables}")
    logger.info("")
    
    # Documents with prerequisites
    with_prereqs = [d for d in documents if d.metadata.prerequisites]
    logger.info(f"Documents with prerequisites: {len(with_prereqs)}")
    for doc in with_prereqs[:5]:
        logger.info(f"  {doc.metadata.course_code}: {', '.join(doc.metadata.prerequisites)}")
    if len(with_prereqs) > 5:
        logger.info(f"  ... and {len(with_prereqs) - 5} more")
    
    logger.info("="*80)
    logger.info("")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )
    
    # Run ingestion
    docs = ingest_documents()
    print(f"\nIngest complete: {len(docs)} documents loaded")