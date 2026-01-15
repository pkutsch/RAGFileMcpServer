"""Tests for the logging module."""

import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.logging import setup_logging, LogManager, SQLiteHandler
from src.logging.models import LogEntry, LogLevel, LogQuery, LogStats


class TestLogModels:
    """Tests for log data models."""
    
    def test_log_level_from_int(self):
        """Test converting numeric level to LogLevel enum."""
        assert LogLevel.from_int(10) == LogLevel.DEBUG
        assert LogLevel.from_int(20) == LogLevel.INFO
        assert LogLevel.from_int(30) == LogLevel.WARNING
        assert LogLevel.from_int(40) == LogLevel.ERROR
        assert LogLevel.from_int(50) == LogLevel.CRITICAL
        # Unknown level defaults to INFO
        assert LogLevel.from_int(999) == LogLevel.INFO
    
    def test_log_level_to_int(self):
        """Test converting LogLevel to numeric level."""
        assert LogLevel.DEBUG.to_int() == 10
        assert LogLevel.INFO.to_int() == 20
        assert LogLevel.WARNING.to_int() == 30
        assert LogLevel.ERROR.to_int() == 40
        assert LogLevel.CRITICAL.to_int() == 50
    
    def test_log_entry_to_dict(self):
        """Test LogEntry serialization."""
        entry = LogEntry(
            id=1,
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.INFO,
            logger_name="test.logger",
            message="Test message",
            module="test_module",
            function="test_func",
            line_number=42,
        )
        
        data = entry.to_dict()
        
        assert data["id"] == 1
        assert data["level"] == "INFO"
        assert data["logger_name"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["module"] == "test_module"
        assert data["function"] == "test_func"
        assert data["line_number"] == 42
    
    def test_log_entry_from_dict(self):
        """Test LogEntry deserialization."""
        data = {
            "id": 1,
            "timestamp": "2024-01-15T10:30:00",
            "level": "WARNING",
            "logger_name": "test",
            "message": "Warning message",
        }
        
        entry = LogEntry.from_dict(data)
        
        assert entry.id == 1
        assert entry.level == LogLevel.WARNING
        assert entry.message == "Warning message"
    
    def test_log_query_defaults(self):
        """Test LogQuery default values."""
        query = LogQuery()
        
        assert query.levels is None
        assert query.logger_names is None
        assert query.start_time is None
        assert query.end_time is None
        assert query.search_text is None
        assert query.limit == 100
        assert query.offset == 0
        assert query.order_desc is True


class TestSQLiteHandler:
    """Tests for SQLiteHandler."""
    
    def test_handler_creates_database(self):
        """Test that handler creates database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_logs.db"
            
            handler = SQLiteHandler(str(db_path))
            
            assert db_path.exists()
            handler.close()
    
    def test_handler_logs_record(self):
        """Test that handler stores log records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_logs.db"
            handler = SQLiteHandler(str(db_path))
            
            # Create test logger
            logger = logging.getLogger("test_handler")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            # Log a message
            logger.info("Test log message")
            
            # Verify log was stored
            manager = LogManager(str(db_path))
            logs = manager.get_logs()
            
            assert len(logs) >= 1
            assert any("Test log message" in log.message for log in logs)
            
            handler.close()
    
    def test_handler_logs_exception(self):
        """Test that handler stores exception tracebacks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_logs.db"
            handler = SQLiteHandler(str(db_path))
            
            logger = logging.getLogger("test_exception")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            # Log an exception
            try:
                raise ValueError("Test exception")
            except ValueError:
                logger.exception("An error occurred")
            
            # Verify exception was stored
            manager = LogManager(str(db_path))
            logs = manager.get_logs(LogQuery(levels=[LogLevel.ERROR]))
            
            assert len(logs) >= 1
            error_log = [l for l in logs if "An error occurred" in l.message][0]
            assert error_log.exception is not None
            assert "ValueError" in error_log.exception
            
            handler.close()


class TestLogManager:
    """Tests for LogManager."""
    
    @pytest.fixture
    def log_manager(self):
        """Create a LogManager with test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_logs.db"
            handler = SQLiteHandler(str(db_path))
            
            # Create test logger
            logger = logging.getLogger("test_manager")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            
            # Add test logs
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            manager = LogManager(str(db_path))
            yield manager
            
            handler.close()
    
    def test_get_logs(self, log_manager):
        """Test retrieving logs."""
        logs = log_manager.get_logs()
        assert len(logs) >= 4
    
    def test_filter_by_level(self, log_manager):
        """Test filtering logs by level."""
        query = LogQuery(levels=[LogLevel.ERROR])
        logs = log_manager.get_logs(query)
        
        assert all(log.level == LogLevel.ERROR for log in logs)
    
    def test_filter_by_logger(self, log_manager):
        """Test filtering logs by logger name."""
        query = LogQuery(logger_names=["test_manager"])
        logs = log_manager.get_logs(query)
        
        assert all(log.logger_name == "test_manager" for log in logs)
    
    def test_search_logs(self, log_manager):
        """Test searching logs."""
        logs = log_manager.search("Warning")
        
        assert len(logs) >= 1
        assert any("Warning" in log.message for log in logs)
    
    def test_get_stats(self, log_manager):
        """Test getting log statistics."""
        stats = log_manager.get_stats()
        
        assert isinstance(stats, LogStats)
        assert stats.total_count >= 4
        assert LogLevel.INFO in stats.counts_by_level
    
    def test_get_logger_names(self, log_manager):
        """Test getting unique logger names."""
        names = log_manager.get_logger_names()
        
        assert "test_manager" in names
    
    def test_export_csv(self, log_manager):
        """Test exporting logs to CSV."""
        csv_data = log_manager.export_csv()
        
        assert "ID,Timestamp,Level" in csv_data
        assert "test_manager" in csv_data
    
    def test_export_json(self, log_manager):
        """Test exporting logs to JSON."""
        import json
        
        json_data = log_manager.export_json()
        data = json.loads(json_data)
        
        assert isinstance(data, list)
        assert len(data) >= 4
    
    def test_clear_old_logs(self, log_manager):
        """Test clearing old logs."""
        # Clear logs older than 0 days (all logs)
        deleted = log_manager.clear_old_logs(days=0)
        
        # Verify logs were deleted
        remaining = log_manager.get_logs()
        assert len(remaining) == 0 or deleted > 0


class TestSetupLogging:
    """Tests for setup_logging function."""
    
    def test_setup_logging_creates_handler(self):
        """Test that setup_logging creates SQLiteHandler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_logs.db"
            
            handler = setup_logging(
                db_path=str(db_path),
                level="DEBUG",
                also_console=False,
            )
            
            assert isinstance(handler, SQLiteHandler)
            assert db_path.exists()
            
            handler.close()
    
    def test_setup_logging_with_console(self):
        """Test that setup_logging can add console handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_logs.db"
            
            handler = setup_logging(
                db_path=str(db_path),
                level="INFO",
                also_console=True,
            )
            
            # Check that root logger has multiple handlers
            root_logger = logging.getLogger()
            handler_types = [type(h).__name__ for h in root_logger.handlers]
            
            assert "SQLiteHandler" in handler_types
            assert "StreamHandler" in handler_types
            
            handler.close()
