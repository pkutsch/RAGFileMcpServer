"""PDF file parser using pypdf for text extraction."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from src.file_parser.base import BaseFileParser, ParsedDocument

logger = logging.getLogger(__name__)


class PdfParser(BaseFileParser):
    """Parser for PDF files using pypdf.
    
    Extracts text content from PDF files with support for
    multilingual content through Unicode handling.
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        """List of supported file extensions."""
        return ["pdf"]
    
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a PDF file and extract text content.
        
        Args:
            file_path: Path to the PDF file.
            
        Returns:
            ParsedDocument with extracted text and metadata.
            
        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file is not a PDF.
            Exception: If PDF parsing fails.
        """
        self._validate_file(file_path)
        
        logger.info(f"Parsing PDF file: {file_path}")
        
        try:
            reader = PdfReader(str(file_path))
            
            # Extract text from all pages
            text_parts: list[str] = []
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num}: {e}"
                    )
            
            text = "\n\n".join(text_parts)
            
            # Extract metadata
            metadata = self._extract_metadata(reader, file_path)
            
            logger.info(
                f"Successfully parsed PDF: {file_path.name}, "
                f"pages: {len(reader.pages)}, "
                f"text length: {len(text)}"
            )
            
            return ParsedDocument(
                text=text,
                source_path=file_path,
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise
    
    def _extract_metadata(
        self, 
        reader: PdfReader, 
        file_path: Path
    ) -> dict[str, Any]:
        """Extract metadata from PDF reader.
        
        Args:
            reader: pypdf PdfReader instance.
            file_path: Path to the PDF file.
            
        Returns:
            Dictionary of metadata.
        """
        metadata: dict[str, Any] = {
            "page_count": len(reader.pages),
            "file_size_bytes": file_path.stat().st_size,
        }
        
        # Extract PDF info if available
        if reader.metadata:
            pdf_info = reader.metadata
            
            # Common metadata fields
            if pdf_info.title:
                metadata["title"] = pdf_info.title
            if pdf_info.author:
                metadata["author"] = pdf_info.author
            if pdf_info.subject:
                metadata["subject"] = pdf_info.subject
            if pdf_info.creator:
                metadata["creator"] = pdf_info.creator
            if pdf_info.producer:
                metadata["producer"] = pdf_info.producer
            if pdf_info.creation_date:
                metadata["creation_date"] = str(pdf_info.creation_date)
            if pdf_info.modification_date:
                metadata["modification_date"] = str(pdf_info.modification_date)
        
        return metadata
