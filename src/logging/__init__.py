"""Logging module with SQLite storage for filterable, searchable logs."""

from src.logging.db_handler import SQLiteHandler
from src.logging.log_manager import LogManager
from src.logging.models import LogEntry, LogLevel, LogQuery

import logging
from pathlib import Path


def setup_logging(
    db_path: str = "./data/logs.db",
    level: str = "INFO",
    also_console: bool = True,
) -> SQLiteHandler:
    """Configure application logging with SQLite handler.
    
    Args:
        db_path: Path to SQLite database file for logs.
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        also_console: If True, also log to console.
    
    Returns:
        The configured SQLiteHandler instance.
    """
    # Ensure data directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create SQLite handler
    sqlite_handler = SQLiteHandler(db_path)
    sqlite_handler.setLevel(getattr(logging, level.upper()))
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    sqlite_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(sqlite_handler)
    
    # Optionally add console handler
    if also_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    return sqlite_handler


__all__ = [
    "SQLiteHandler",
    "LogManager",
    "LogEntry",
    "LogLevel",
    "LogQuery",
    "setup_logging",
]
