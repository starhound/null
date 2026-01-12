"""DAO for SSH hosts."""

from __future__ import annotations

from typing import Any

from .base import BaseDAO


class SshHostDAO(BaseDAO):
    """Data Access Object for SSH hosts."""

    def init_table(self):
        """Initialize ssh_hosts table."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS ssh_hosts (
                alias TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                username TEXT,
                port INTEGER DEFAULT 22,
                key_path TEXT,
                description TEXT
            )
            """
        )
        self.commit()

    def add(self, host_data: dict[str, Any]):
        """Add or update an SSH host."""
        self.execute(
            """
            INSERT INTO ssh_hosts (alias, hostname, username, port, key_path, description)
            VALUES (:alias, :hostname, :username, :port, :key_path, :description)
            ON CONFLICT(alias) DO UPDATE SET
                hostname = excluded.hostname,
                username = excluded.username,
                port = excluded.port,
                key_path = excluded.key_path,
                description = excluded.description
            """,
            host_data,
        )
        self.commit()

    def get(self, alias: str) -> dict[str, Any] | None:
        """Get host by alias."""
        row = self.fetch_one("SELECT * FROM ssh_hosts WHERE alias = ?", (alias,))
        if row:
            return dict(row)
        return None

    def list_all(self) -> list[dict[str, Any]]:
        """List all SSH hosts."""
        rows = self.fetch_all("SELECT * FROM ssh_hosts ORDER BY alias")
        return [dict(row) for row in rows]

    def delete(self, alias: str):
        """Delete host by alias."""
        self.execute("DELETE FROM ssh_hosts WHERE alias = ?", (alias,))
        self.commit()
