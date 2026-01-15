"""Tests for the file parser module."""

import tempfile
from pathlib import Path

import pytest

from src.file_parser import get_parser_for_file, PdfParser, TextParser
from src.file_parser.base import ParsedDocument


class TestGetParserForFile:
    """Tests for get_parser_for_file function."""
    
    def test_get_pdf_parser(self):
        """Test getting parser for PDF files."""
        parser = get_parser_for_file("document.pdf")
        assert isinstance(parser, PdfParser)
    
    def test_get_text_parser_txt(self):
        """Test getting parser for TXT files."""
        parser = get_parser_for_file("document.txt")
        assert isinstance(parser, TextParser)
    
    def test_get_text_parser_md(self):
        """Test getting parser for MD files."""
        parser = get_parser_for_file("document.md")
        assert isinstance(parser, TextParser)
    
    def test_get_text_parser_rst(self):
        """Test getting parser for RST files."""
        parser = get_parser_for_file("document.rst")
        assert isinstance(parser, TextParser)
    
    def test_unsupported_format(self):
        """Test getting parser for unsupported format."""
        parser = get_parser_for_file("document.docx")
        assert parser is None
    
    def test_no_extension(self):
        """Test getting parser for file without extension."""
        parser = get_parser_for_file("document")
        assert parser is None


class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""
    
    def test_filename_property(self):
        """Test filename property."""
        doc = ParsedDocument(
            text="Test content",
            source_path=Path("/path/to/document.pdf"),
        )
        assert doc.filename == "document.pdf"
    
    def test_extension_property(self):
        """Test extension property."""
        doc = ParsedDocument(
            text="Test content",
            source_path=Path("/path/to/document.pdf"),
        )
        assert doc.extension == "pdf"
    
    def test_text_length_property(self):
        """Test text_length property."""
        doc = ParsedDocument(
            text="Test content",
            source_path=Path("/path/to/document.txt"),
        )
        assert doc.text_length == 12
    
    def test_to_dict(self):
        """Test to_dict serialization."""
        doc = ParsedDocument(
            text="Test content",
            source_path=Path("/path/to/document.txt"),
            metadata={"author": "Test Author"},
        )
        
        data = doc.to_dict()
        
        assert data["text"] == "Test content"
        assert data["filename"] == "document.txt"
        assert data["extension"] == "txt"
        assert data["text_length"] == 12
        assert data["metadata"]["author"] == "Test Author"


class TestTextParser:
    """Tests for TextParser."""
    
    @pytest.fixture
    def parser(self):
        """Create TextParser instance."""
        return TextParser()
    
    def test_supported_extensions(self, parser):
        """Test supported extensions."""
        assert "txt" in parser.supported_extensions
        assert "md" in parser.supported_extensions
        assert "rst" in parser.supported_extensions
    
    def test_can_parse_txt(self, parser):
        """Test can_parse for TXT files."""
        assert parser.can_parse(Path("document.txt"))
    
    def test_can_parse_md(self, parser):
        """Test can_parse for MD files."""
        assert parser.can_parse(Path("document.md"))
    
    def test_cannot_parse_pdf(self, parser):
        """Test can_parse for PDF files."""
        assert not parser.can_parse(Path("document.pdf"))
    
    def test_parse_utf8_file(self, parser):
        """Test parsing UTF-8 text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, World!\nThis is a test.")
            f.flush()
            
            result = parser.parse(Path(f.name))
            
            assert "Hello, World!" in result.text
            assert "This is a test." in result.text
            assert result.metadata["encoding"] == "utf-8"
            assert result.metadata["line_count"] == 2
    
    def test_parse_multilingual_file(self, parser):
        """Test parsing file with multilingual content."""
        content = "English text\nDeutscher Text\n日本語テキスト\nالنص العربي"
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", 
                                         delete=False, encoding="utf-8") as f:
            f.write(content)
            f.flush()
            
            result = parser.parse(Path(f.name))
            
            assert "English text" in result.text
            assert "Deutscher Text" in result.text
            assert "日本語テキスト" in result.text
            assert "النص العربي" in result.text
    
    def test_parse_markdown_file(self, parser):
        """Test parsing Markdown file."""
        content = "# Heading\n\nParagraph with **bold** text."
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            
            result = parser.parse(Path(f.name))
            
            assert "# Heading" in result.text
            assert result.metadata["file_type"] == "Markdown"
    
    def test_parse_nonexistent_file(self, parser):
        """Test parsing non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.txt"))
    
    def test_parse_unsupported_format(self, parser):
        """Test parsing unsupported format raises error."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            f.flush()
            
            with pytest.raises(ValueError):
                parser.parse(Path(f.name))


class TestPdfParser:
    """Tests for PdfParser."""
    
    @pytest.fixture
    def parser(self):
        """Create PdfParser instance."""
        return PdfParser()
    
    def test_supported_extensions(self, parser):
        """Test supported extensions."""
        assert parser.supported_extensions == ["pdf"]
    
    def test_can_parse_pdf(self, parser):
        """Test can_parse for PDF files."""
        assert parser.can_parse(Path("document.pdf"))
    
    def test_cannot_parse_txt(self, parser):
        """Test can_parse for TXT files."""
        assert not parser.can_parse(Path("document.txt"))
    
    def test_parse_nonexistent_file(self, parser):
        """Test parsing non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.pdf"))
    
    def test_parse_unsupported_format(self, parser):
        """Test parsing unsupported format raises error."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            f.flush()
            
            with pytest.raises(ValueError):
                parser.parse(Path(f.name))
    
    # Note: Testing actual PDF parsing requires a valid PDF file
    # The following test is a placeholder for integration testing
    @pytest.mark.skip(reason="Requires valid PDF test file")
    def test_parse_pdf_file(self, parser):
        """Test parsing actual PDF file."""
        # This test would require a valid PDF file
        # parser.parse(Path("tests/fixtures/sample.pdf"))
        pass
