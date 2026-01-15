"""Data models for the logging module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(str, Enum):
    """Log level enumeration matching Python's logging levels."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    @classmethod
    def from_int(cls, level: int) -> "LogLevel":
        """Convert numeric logging level to LogLevel enum."""
        level_map = {
            10: cls.DEBUG,
            20: cls.INFO,
            30: cls.WARNING,
            40: cls.ERROR,
            50: cls.CRITICAL,
        }
        return level_map.get(level, cls.INFO)
    
    def to_int(self) -> int:
        """Convert LogLevel enum to numeric logging level."""
        level_map = {
            self.DEBUG: 10,
            self.INFO: 20,
            self.WARNING: 30,
            self.ERROR: 40,
            self.CRITICAL: 50,
        }
        return level_map[self]


@dataclass
class LogEntry:
    """Represents a single log entry."""
    
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    id: int | None = None
    module: str | None = None
    function: str | None = None
    line_number: int | None = None
    exception: str | None = None
    extra_data: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert log entry to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "logger_name": self.logger_name,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "exception": self.exception,
            "extra_data": self.extra_data,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """Create log entry from dictionary."""
        return cls(
            id=data.get("id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) 
                if isinstance(data["timestamp"], str) 
                else data["timestamp"],
            level=LogLevel(data["level"]) 
                if isinstance(data["level"], str) 
                else data["level"],
            logger_name=data["logger_name"],
            message=data["message"],
            module=data.get("module"),
            function=data.get("function"),
            line_number=data.get("line_number"),
            exception=data.get("exception"),
            extra_data=data.get("extra_data"),
        )


@dataclass
class LogQuery:
    """Query parameters for filtering and retrieving logs."""
    
    levels: list[LogLevel] | None = None
    logger_names: list[str] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    search_text: str | None = None
    limit: int = 100
    offset: int = 0
    order_desc: bool = True  # Newest first by default
    
    def to_dict(self) -> dict[str, Any]:
        """Convert query to dictionary for serialization."""
        return {
            "levels": [l.value for l in self.levels] if self.levels else None,
            "logger_names": self.logger_names,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "search_text": self.search_text,
            "limit": self.limit,
            "offset": self.offset,
            "order_desc": self.order_desc,
        }


@dataclass
class LogStats:
    """Statistics about stored logs."""
    
    total_count: int
    counts_by_level: dict[LogLevel, int] = field(default_factory=dict)
    counts_by_logger: dict[str, int] = field(default_factory=dict)
    oldest_timestamp: datetime | None = None
    newest_timestamp: datetime | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_count": self.total_count,
            "counts_by_level": {k.value: v for k, v in self.counts_by_level.items()},
            "counts_by_logger": self.counts_by_logger,
            "oldest_timestamp": self.oldest_timestamp.isoformat() if self.oldest_timestamp else None,
            "newest_timestamp": self.newest_timestamp.isoformat() if self.newest_timestamp else None,
        }
