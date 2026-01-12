"""DAO for command history."""

from __future__ import annotations

from .base import BaseDAO


class HistoryDAO(BaseDAO):
    """Data Access Object for command history."""

    def init_table(self):
        """Initialize history table."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_cwd TEXT,
                exit_code INTEGER
            )
            """
        )
        self.commit()

    def add(self, command: str, cwd: str = "", exit_code: int = 0):
        """Add command to history."""
        self.execute(
            """
            INSERT INTO history (command, context_cwd, exit_code)
            VALUES (?, ?, ?)
            """,
            (command, cwd, exit_code),
        )
        self.commit()

    def get_recent(self, limit: int = 50) -> list[str]:
        """Get recent unique commands."""
        # Using a subquery/group by to get unique commands, ordered by most recent use
        # This prevents the up-arrow history from showing duplicates
        query = """
            SELECT command
            FROM history
            GROUP BY command
            ORDER BY MAX(timestamp) DESC
            LIMIT ?
        """
        rows = self.fetch_all(query, (limit,))
        # Reverse to have oldest first (for up-arrow navigation typically expecting stack)
        # But for 'recent', usually we want list from most recent.
        # StorageManager.get_last_history returned list of strings.
        return [row["command"] for row in rows][::-1]

    def clear(self):
        """Clear all history."""
        self.execute("DELETE FROM history")
        self.commit()
