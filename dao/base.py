"""Base DAO for SQLite access."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class BaseDAO:
    """Base class for Data Access Objects."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        """Execute a SQL query."""
        try:
            return self.conn.execute(sql, params)
        except sqlite3.Error as e:
            # Re-raise or log as needed; for now, let's bubble up
            raise e

    def commit(self):
        """Commit transaction."""
        if self._conn:
            self._conn.commit()

    def fetch_one(self, sql: str, params: tuple | dict = ()) -> Any:
        """Execute query and fetch one row."""
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def fetch_all(self, sql: str, params: tuple | dict = ()) -> list[Any]:
        """Execute query and fetch all rows."""
        cursor = self.execute(sql, params)
        return cursor.fetchall()
