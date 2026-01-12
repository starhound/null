"""DAO for application configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseDAO

if TYPE_CHECKING:
    pass


class ConfigDAO(BaseDAO):
    """Data Access Object for configuration settings."""

    def init_table(self):
        """Initialize config table."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.commit()

    def get(self, key: str) -> str | None:
        """Get configuration value by key."""
        row = self.fetch_one("SELECT value FROM config WHERE key = ?", (key,))
        return row["value"] if row else None

    def set(self, key: str, value: str):
        """Set configuration value."""
        self.execute(
            """
            INSERT INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        self.commit()

    def list_all(self) -> dict[str, str]:
        """List all configuration entries."""
        rows = self.fetch_all("SELECT key, value FROM config")
        return {row["key"]: row["value"] for row in rows}

    def delete(self, key: str):
        """Delete configuration entry."""
        self.execute("DELETE FROM config WHERE key = ?", (key,))
        self.commit()
