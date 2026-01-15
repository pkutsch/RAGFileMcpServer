"""Base classes and protocols for file parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class ParsedDocument:
    """Represents a parsed document with extracted text and metadata.
    
    Attributes:
        text: The extracted text content from the document.
        metadata: Document metadata (title, author, page count, etc.).
        source_path: Path to the original source file.
        parse_timestamp: When the document was parsed.
    """
    
    text: str
    source_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)
    parse_timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def filename(self) -> str:
        """Get the filename without the full path."""
        return self.source_path.name
    
    @property
    def extension(self) -> str:
        """Get the file extension (without dot)."""
        return self.source_path.suffix.lstrip(".")
    
    @property
    def text_length(self) -> int:
        """Get the length of extracted text."""
        return len(self.text)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "source_path": str(self.source_path),
            "filename": self.filename,
            "extension": self.extension,
            "text_length": self.text_length,
            "metadata": self.metadata,
            "parse_timestamp": self.parse_timestamp.isoformat(),
        }


@runtime_checkable
class FileParser(Protocol):
    """Protocol for file parsers.
    
    All file parsers must implement this protocol to ensure
    consistent interface across different file types.
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        """List of file extensions this parser supports (without dots)."""
        ...
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.
        
        Args:
            file_path: Path to the file to check.
            
        Returns:
            True if this parser can handle the file, False otherwise.
        """
        ...
    
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a file and extract text content.
        
        Args:
            file_path: Path to the file to parse.
            
        Returns:
            ParsedDocument containing extracted text and metadata.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is not supported.
            Exception: If parsing fails for any reason.
        """
        ...


class BaseFileParser(ABC):
    """Abstract base class for file parsers.
    
    Provides common functionality and enforces the FileParser protocol.
    """
    
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """List of file extensions this parser supports (without dots)."""
        pass
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file.
        
        Args:
            file_path: Path to the file to check.
            
        Returns:
            True if this parser can handle the file, False otherwise.
        """
        extension = file_path.suffix.lstrip(".").lower()
        return extension in [ext.lower() for ext in self.supported_extensions]
    
    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a file and extract text content.
        
        Args:
            file_path: Path to the file to parse.
            
        Returns:
            ParsedDocument containing extracted text and metadata.
        """
        pass
    
    def _validate_file(self, file_path: Path) -> None:
        """Validate that the file exists and is supported.
        
        Args:
            file_path: Path to validate.
            
        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file format is not supported.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self.can_parse(file_path):
            raise ValueError(
                f"Unsupported file format: {file_path.suffix}. "
                f"Supported formats: {self.supported_extensions}"
            )
