"""File parser module for extracting text from various file formats."""

from src.file_parser.base import FileParser, ParsedDocument
from src.file_parser.pdf_parser import PdfParser
from src.file_parser.text_parser import TextParser

__all__ = [
    "FileParser",
    "ParsedDocument",
    "PdfParser",
    "TextParser",
]


def get_parser_for_file(filename: str) -> FileParser | None:
    """Get the appropriate parser for a file based on its extension.
    
    Args:
        filename: Name of the file to parse.
    
    Returns:
        FileParser instance if a parser is available, None otherwise.
    """
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    
    if extension == "pdf":
        return PdfParser()
    elif extension in ("txt", "md", "rst", "text"):
        return TextParser()
    
    return None
