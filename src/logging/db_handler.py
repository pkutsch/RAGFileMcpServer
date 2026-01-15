"""SQLite-based logging handler for persistent, queryable logs."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from src.logging.models import LogLevel


class SQLiteHandler(logging.Handler):
    """Custom logging handler that stores logs in SQLite database.
    
    This handler provides persistent storage of log records in SQLite,
    enabling log filtering, searching, and display in the Streamlit UI.
    
    Attributes:
        db_path: Path to the SQLite database file.
    """
    
    # SQL statements
    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            level_no INTEGER NOT NULL,
            logger_name TEXT NOT NULL,
            message TEXT NOT NULL,
            module TEXT,
            function TEXT,
            line_number INTEGER,
            exception TEXT,
            extra_data TEXT
        )
    """
    
    CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)",
        "CREATE INDEX IF NOT EXISTS idx_logs_logger ON logs(logger_name)",
    ]
    
    INSERT_LOG_SQL = """
        INSERT INTO logs (
            timestamp, level, level_no, logger_name, message,
            module, function, line_number, exception, extra_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    def __init__(self, db_path: str = "./data/logs.db"):
        """Initialize the SQLite logging handler.
        
        Args:
            db_path: Path to the SQLite database file. Parent directories
                    will be created if they don't exist.
        """
        super().__init__()
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection.
        
        Returns:
            SQLite connection for the current thread.
        """
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create table
        cursor.execute(self.CREATE_TABLE_SQL)
        
        # Create indexes
        for index_sql in self.CREATE_INDEXES_SQL:
            cursor.execute(index_sql)
        
        conn.commit()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Store a log record in the database.
        
        Args:
            record: The log record to store.
        """
        try:
            # Format the message
            message = self.format(record)
            
            # Extract exception info if present
            exception_text = None
            if record.exc_info:
                exception_text = "".join(
                    traceback.format_exception(*record.exc_info)
                )
            
            # Extract extra data (custom fields added to log record)
            extra_data = self._extract_extra_data(record)
            
            # Get timestamp
            timestamp = datetime.fromtimestamp(record.created).isoformat()
            
            # Insert into database
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    self.INSERT_LOG_SQL,
                    (
                        timestamp,
                        record.levelname,
                        record.levelno,
                        record.name,
                        message,
                        record.module,
                        record.funcName,
                        record.lineno,
                        exception_text,
                        json.dumps(extra_data) if extra_data else None,
                    ),
                )
                conn.commit()
                
        except Exception:
            # Don't raise exceptions from the handler
            self.handleError(record)
    
    def _extract_extra_data(self, record: logging.LogRecord) -> dict[str, Any] | None:
        """Extract custom extra data from log record.
        
        Args:
            record: The log record to extract extra data from.
            
        Returns:
            Dictionary of extra data, or None if no extra data.
        """
        # Standard LogRecord attributes to exclude
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "taskName", "message",
        }
        
        extra = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)
        
        return extra if extra else None
    
    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            delattr(self._local, "connection")
        super().close()
