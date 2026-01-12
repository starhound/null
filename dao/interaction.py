"""DAO for interactions (saved sessions)."""

from __future__ import annotations

import json
from typing import Any

from .base import BaseDAO


class InteractionDAO(BaseDAO):
    """Data Access Object for interactions (blocks)."""

    def init_table(self):
        """Initialize interactions table."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                type TEXT,
                content_input TEXT,
                content_output TEXT,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.commit()

    def save_session(self, blocks: list[Any]):
        """Save current session (replace all interactions)."""
        # Transactional replace
        self.execute("BEGIN TRANSACTION")
        try:
            self.execute("DELETE FROM interactions")
            for block in blocks:
                self.execute(
                    """
                    INSERT INTO interactions (id, type, content_input, content_output, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        block.id,
                        block.type.value
                        if hasattr(block.type, "value")
                        else str(block.type),
                        block.content_input,
                        block.content_output,
                        json.dumps(block.metadata),
                    ),
                )
            self.commit()
        except Exception as e:
            self.execute("ROLLBACK")
            raise e

    def load_session(self) -> list[dict[str, Any]]:
        """Load saved session blocks."""
        rows = self.fetch_all("SELECT * FROM interactions ORDER BY timestamp")
        result = []
        for row in rows:
            data = dict(row)
            try:
                data["metadata"] = (
                    json.loads(data["metadata"]) if data["metadata"] else {}
                )
            except json.JSONDecodeError:
                data["metadata"] = {}
            result.append(data)
        return result
