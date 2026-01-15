"""Plain text file parser with encoding detection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chardet

from src.file_parser.base import BaseFileParser, ParsedDocument

logger = logging.getLogger(__name__)


class TextParser(BaseFileParser):
    """Parser for plain text files with automatic encoding detection.
    
    Supports .txt, .md, .rst file formats with intelligent
    encoding detection for multilingual content.
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        """List of supported file extensions."""
        return ["txt", "md", "rst", "text"]
    
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a text file and extract content.
        
        Args:
            file_path: Path to the text file.
            
        Returns:
            ParsedDocument with text content and metadata.
            
        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file format is not supported.
            Exception: If text parsing fails.
        """
        self._validate_file(file_path)
        
        logger.info(f"Parsing text file: {file_path}")
        
        try:
            # Read raw bytes for encoding detection
            raw_bytes = file_path.read_bytes()
            
            # Detect encoding
            encoding = self._detect_encoding(raw_bytes)
            
            # Decode text
            text = raw_bytes.decode(encoding)
            
            # Extract metadata
            metadata = self._extract_metadata(file_path, text, encoding)
            
            logger.info(
                f"Successfully parsed text file: {file_path.name}, "
                f"encoding: {encoding}, "
                f"text length: {len(text)}"
            )
            
            return ParsedDocument(
                text=text,
                source_path=file_path,
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse text file {file_path}: {e}")
            raise
    
    def _detect_encoding(self, raw_bytes: bytes) -> str:
        """Detect the encoding of raw bytes.
        
        Args:
            raw_bytes: Raw file bytes.
            
        Returns:
            Detected encoding string.
        """
        # Try UTF-8 first as it's most common
        try:
            raw_bytes.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass
        
        # Use chardet for detection
        result = chardet.detect(raw_bytes)
        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0)
        
        logger.debug(
            f"Detected encoding: {encoding} (confidence: {confidence:.2f})"
        )
        
        # Fall back to utf-8 if detection failed or low confidence
        if not encoding or confidence < 0.5:
            encoding = "utf-8"
        
        return encoding
    
    def _extract_metadata(
        self, 
        file_path: Path, 
        text: str, 
        encoding: str
    ) -> dict[str, Any]:
        """Extract metadata from text file.
        
        Args:
            file_path: Path to the text file.
            text: Decoded text content.
            encoding: Detected encoding.
            
        Returns:
            Dictionary of metadata.
        """
        # Count lines
        lines = text.splitlines()
        
        # Get file stats
        stat = file_path.stat()
        
        metadata: dict[str, Any] = {
            "encoding": encoding,
            "line_count": len(lines),
            "word_count": len(text.split()),
            "character_count": len(text),
            "file_size_bytes": stat.st_size,
            "file_type": self._get_file_type(file_path),
        }
        
        return metadata
    
    def _get_file_type(self, file_path: Path) -> str:
        """Get human-readable file type description.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            File type description.
        """
        extension = file_path.suffix.lstrip(".").lower()
        
        type_map = {
            "txt": "Plain Text",
            "text": "Plain Text",
            "md": "Markdown",
            "rst": "reStructuredText",
        }
        
        return type_map.get(extension, "Text")
