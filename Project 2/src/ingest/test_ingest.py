import pytest
from pathlib import Path
from .loader import DocumentLoader
from .metadata_extractor import MetadataExtractor
from .pdf_parser import PDFParser
from .word_parser import WordParser


class TestMetadataExtractor:
    """Test metadata extraction from filenames."""
    
    def test_extract_syllabus_filename(self):
        """Test extracting metadata from a syllabus filename."""
        extractor = MetadataExtractor()
        meta = extractor.extract_from_filename(Path("CS434-SYLLABUS-F26.pdf"))
        
        assert meta.course_code == "CS434"
        assert meta.source_type == "syllabus"
        assert meta.semester == "Fall"
        assert meta.year == 2026
        assert "CS434" in meta.title
    
    def test_extract_exam_rules_filename(self):
        """Test extracting metadata from exam rules filename."""
        extractor = MetadataExtractor()
        meta = extractor.extract_from_filename(Path("CS496-EXAM-RULES-S26.pdf"))
        
        assert meta.course_code == "CS496"
        assert meta.source_type == "exam-rules"
        assert meta.semester == "Spring"
        assert meta.year == 2026
    
    def test_extract_regulations_filename(self):
        """Test extracting metadata from regulations filename."""
        extractor = MetadataExtractor()
        meta = extractor.extract_from_filename(Path("GRADING-REGULATIONS-2026.pdf"))
        
        assert meta.course_code is None
        assert meta.source_type == "regulation"
        assert meta.year == 2026
    
    def test_extract_with_spring_semester(self):
        """Test Spring semester extraction."""
        extractor = MetadataExtractor()
        meta = extractor.extract_from_filename(Path("CS300-SYLLABUS-S25.pdf"))
        
        assert meta.semester == "Spring"
        assert meta.year == 2025

class TestWordParser:
    """Test Word document parsing."""
    
    def test_word_can_parse(self):
        """Test that WordParser recognizes Word files."""
        parser = WordParser()
        assert parser.can_parse(Path("test.docx"))
        assert parser.can_parse(Path("Test.DOCX"))
        assert parser.can_parse(Path("test.doc"))
        assert not parser.can_parse(Path("test.pdf"))
        assert not parser.can_parse(Path("test.txt"))

class TestPDFParser:
    """Test PDF parsing."""
    
    def test_pdf_can_parse(self):
        """Test that PDFParser recognizes PDF files."""
        parser = PDFParser()
        assert parser.can_parse(Path("test.pdf"))
        assert parser.can_parse(Path("Test.PDF"))
        assert not parser.can_parse(Path("test.docx"))
        assert not parser.can_parse(Path("test.txt"))
    
    def test_extract_prerequisites_with_two_courses(self):
        """Test extracting multiple prerequisites."""
        parser = PDFParser()
        
        text = """
            Prerequisites
            CS280 Introduction to Artificial Intelligence
            CS300 Data Structures
        """
        
        result = parser._extract_prerequisites(text)
        assert result == ["CS280", "CS300"]
    
    def test_extract_prerequisites_with_and(self):
        """Test prerequisites separated by 'and'."""
        parser = PDFParser()
        
        text = """
            Prerequisites
            CS280 and CS300
        """
        
        result = parser._extract_prerequisites(text)
        assert set(result) == {"CS280", "CS300"}
    
    def test_extract_prerequisites_with_commas(self):
        """Test prerequisites separated by commas."""
        parser = PDFParser()
        
        text = """
            Prerequisites
            CS280, CS300, CS400
        """
        
        result = parser._extract_prerequisites(text)
        assert set(result) == {"CS280", "CS300", "CS400"}
    
    def test_no_prerequisites_found(self):
        """Test when there are no prerequisites."""
        parser = PDFParser()
        
        text = """
            Course Learning Outcomes
            Students will learn data science concepts.
        """
        
        result = parser._extract_prerequisites(text)
        assert result is None
    
    def test_extract_credits(self):
        """Test extracting credit hours."""
        parser = PDFParser()
        
        text = "CS434 DATA SCIENCE 4 Credits / 4 Hours"
        result = parser._extract_credits(text)
        
        assert result is not None
        assert "4" in result
        assert "Credits" in result or "credits" in result

    def test_extract_programmes(self):
        """Test extracting programmes."""
        parser = PDFParser()
        
        text = """
            Position in the Educational System

            The course is a single subject course at the South Mediterranean University.
            CSE, SWE, REE | Required
        """
        
        programmes = parser._extract_programmes(text)
        
        assert set(programmes) == {"CSE", "SWE", "REE"}

    def test_extract_programmes_elective(self):
        """Test extracting."""
        parser = PDFParser()
        
        text = """
            Position in the Educational System

            CSE, SWE | Elective
        """
        
        programmes = parser._extract_programmes(text)
        
        assert set(programmes) == {"CSE", "SWE"}



class TestDocumentLoader:
    """Test document loading from a folder."""
    
    def test_loader_initialization(self):
        """Test that loader initializes with all parsers."""
        loader = DocumentLoader()
        assert len(loader.parsers) == 2
        assert isinstance(loader.parsers[0], PDFParser)
    
    def test_load_from_nonexistent_folder(self):
        """Test loading from a folder that doesn't exist."""
        loader = DocumentLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load_from_folder(Path("nonexistent/folder"))
    
    def test_load_from_real_corpus(self):
        """Test loading from the actual data/raw/ folder."""
        raw_folder = Path("data/raw")
        
        if not raw_folder.exists():
            pytest.skip(f"Corpus folder not found at {raw_folder}")
        
        loader = DocumentLoader()
        documents = loader.load_from_folder(raw_folder)
        
        # Should load at least one document
        assert len(documents) > 0, "No documents loaded from data/raw/"
        
        # Each document should have valid metadata
        for doc in documents:
            assert doc.metadata.title, "Document missing title"
            assert doc.metadata.year > 2000, "Invalid year"
            assert doc.metadata.semester in ["Fall", "Spring", "Summer"], "Invalid semester"
            assert len(doc.text) > 0, "Document has no text"
        
        # Print loaded documents
        print(f"\nLoaded {len(documents)} documents:")
        for doc in documents:
            print(f"  {doc.metadata.course_code or 'N/A':>6} | {doc.metadata.title:<40} | {len(doc.text):>6} chars")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])