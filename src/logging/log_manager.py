"""Log manager for querying, filtering, and exporting logs."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.logging.models import LogEntry, LogLevel, LogQuery, LogStats


class LogManager:
    """Manager for querying, filtering, and exporting logs from SQLite.
    
    Provides a high-level interface for log retrieval with filtering,
    searching, pagination, and export capabilities.
    
    Attributes:
        db_path: Path to the SQLite database file.
    """
    
    def __init__(self, db_path: str = "./data/logs.db"):
        """Initialize the log manager.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection.
        
        Returns:
            SQLite connection with row factory set.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_logs(self, query: LogQuery | None = None) -> list[LogEntry]:
        """Retrieve logs matching the query criteria.
        
        Args:
            query: Query parameters for filtering. If None, returns
                  the most recent logs with default limits.
        
        Returns:
            List of LogEntry objects matching the query.
        """
        if query is None:
            query = LogQuery()
        
        sql, params = self._build_query(query)
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [self._row_to_entry(row) for row in rows]
        finally:
            conn.close()
    
    def _build_query(self, query: LogQuery) -> tuple[str, list[Any]]:
        """Build SQL query from LogQuery parameters.
        
        Args:
            query: Query parameters.
            
        Returns:
            Tuple of (SQL string, list of parameters).
        """
        conditions = []
        params: list[Any] = []
        
        # Filter by levels
        if query.levels:
            placeholders = ",".join("?" * len(query.levels))
            conditions.append(f"level IN ({placeholders})")
            params.extend([l.value for l in query.levels])
        
        # Filter by logger names
        if query.logger_names:
            placeholders = ",".join("?" * len(query.logger_names))
            conditions.append(f"logger_name IN ({placeholders})")
            params.extend(query.logger_names)
        
        # Filter by time range
        if query.start_time:
            conditions.append("timestamp >= ?")
            params.append(query.start_time.isoformat())
        
        if query.end_time:
            conditions.append("timestamp <= ?")
            params.append(query.end_time.isoformat())
        
        # Search in message
        if query.search_text:
            conditions.append("message LIKE ?")
            params.append(f"%{query.search_text}%")
        
        # Build SQL
        sql = "SELECT * FROM logs"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        # Order
        order = "DESC" if query.order_desc else "ASC"
        sql += f" ORDER BY timestamp {order}"
        
        # Pagination
        sql += " LIMIT ? OFFSET ?"
        params.extend([query.limit, query.offset])
        
        return sql, params
    
    def _row_to_entry(self, row: sqlite3.Row) -> LogEntry:
        """Convert database row to LogEntry.
        
        Args:
            row: SQLite row object.
            
        Returns:
            LogEntry object.
        """
        extra_data = None
        if row["extra_data"]:
            try:
                extra_data = json.loads(row["extra_data"])
            except json.JSONDecodeError:
                extra_data = None
        
        return LogEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            level=LogLevel(row["level"]),
            logger_name=row["logger_name"],
            message=row["message"],
            module=row["module"],
            function=row["function"],
            line_number=row["line_number"],
            exception=row["exception"],
            extra_data=extra_data,
        )
    
    def get_stats(self) -> LogStats:
        """Get statistics about stored logs.
        
        Returns:
            LogStats object with counts and time range info.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Total count
            cursor.execute("SELECT COUNT(*) FROM logs")
            total_count = cursor.fetchone()[0]
            
            # Counts by level
            cursor.execute(
                "SELECT level, COUNT(*) as count FROM logs GROUP BY level"
            )
            counts_by_level = {
                LogLevel(row["level"]): row["count"] 
                for row in cursor.fetchall()
            }
            
            # Counts by logger
            cursor.execute(
                "SELECT logger_name, COUNT(*) as count FROM logs "
                "GROUP BY logger_name ORDER BY count DESC"
            )
            counts_by_logger = {
                row["logger_name"]: row["count"] 
                for row in cursor.fetchall()
            }
            
            # Time range
            cursor.execute(
                "SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM logs"
            )
            row = cursor.fetchone()
            oldest = datetime.fromisoformat(row["oldest"]) if row["oldest"] else None
            newest = datetime.fromisoformat(row["newest"]) if row["newest"] else None
            
            return LogStats(
                total_count=total_count,
                counts_by_level=counts_by_level,
                counts_by_logger=counts_by_logger,
                oldest_timestamp=oldest,
                newest_timestamp=newest,
            )
        finally:
            conn.close()
    
    def get_logger_names(self) -> list[str]:
        """Get list of all unique logger names.
        
        Returns:
            List of logger names sorted alphabetically.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT logger_name FROM logs ORDER BY logger_name"
            )
            return [row["logger_name"] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def search(self, text: str, limit: int = 100) -> list[LogEntry]:
        """Search for logs containing the specified text.
        
        Args:
            text: Text to search for in log messages.
            limit: Maximum number of results.
        
        Returns:
            List of matching LogEntry objects.
        """
        query = LogQuery(search_text=text, limit=limit)
        return self.get_logs(query)
    
    def export_csv(self, query: LogQuery | None = None) -> str:
        """Export logs matching query to CSV format.
        
        Args:
            query: Query parameters for filtering.
        
        Returns:
            CSV string of logs.
        """
        logs = self.get_logs(query)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "Timestamp", "Level", "Logger", "Message",
            "Module", "Function", "Line", "Exception"
        ])
        
        # Data
        for log in logs:
            writer.writerow([
                log.id,
                log.timestamp.isoformat(),
                log.level.value,
                log.logger_name,
                log.message,
                log.module,
                log.function,
                log.line_number,
                log.exception or "",
            ])
        
        return output.getvalue()
    
    def export_json(self, query: LogQuery | None = None) -> str:
        """Export logs matching query to JSON format.
        
        Args:
            query: Query parameters for filtering.
        
        Returns:
            JSON string of logs.
        """
        logs = self.get_logs(query)
        return json.dumps(
            [log.to_dict() for log in logs],
            indent=2,
            default=str,
        )
    
    def clear_old_logs(self, days: int = 30) -> int:
        """Delete logs older than the specified number of days.
        
        Args:
            days: Number of days to retain. Logs older than this
                 will be deleted.
        
        Returns:
            Number of logs deleted.
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM logs WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()
    
    def clear_all_logs(self) -> int:
        """Delete all logs from the database.
        
        Returns:
            Number of logs deleted.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM logs")
            count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM logs")
            conn.commit()
            return count
        finally:
            conn.close()
    
    def get_log_by_id(self, log_id: int) -> LogEntry | None:
        """Get a specific log entry by ID.
        
        Args:
            log_id: The log entry ID.
        
        Returns:
            LogEntry if found, None otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            conn.close()
