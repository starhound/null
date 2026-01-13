"""In-memory index for fast command history search."""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.storage import StorageManager

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Represents a single history entry."""

    id: int
    command: str
    timestamp: str
    exit_code: int


@dataclass
class HistoryIndex:
    """In-memory index for fast command history and session search.

    Builds inverted indexes for command text to enable fast substring
    and token-based searching without repeated database queries.
    """

    _entries: dict[int, HistoryEntry] = field(default_factory=dict)
    _token_index: dict[str, set[int]] = field(default_factory=lambda: defaultdict(set))
    _storage: "StorageManager | None" = field(default=None, repr=False)

    def __post_init__(self):
        if self._token_index is None:
            self._token_index = defaultdict(set)

    @classmethod
    def from_storage(cls, storage: "StorageManager") -> "HistoryIndex":
        """Build index from StorageManager."""
        index = cls(_storage=storage)
        index.rebuild_index()
        return index

    def rebuild_index(self) -> int:
        """Rebuild the entire index from storage.

        Returns:
            Number of entries indexed.
        """
        self._entries.clear()
        self._token_index.clear()

        if self._storage is None:
            logger.warning("No storage manager attached, index will be empty")
            return 0

        cursor = self._storage.conn.cursor()
        cursor.execute(
            "SELECT id, command, timestamp, exit_code FROM history ORDER BY id"
        )

        count = 0
        for row in cursor.fetchall():
            entry = HistoryEntry(
                id=row["id"],
                command=row["command"],
                timestamp=row["timestamp"],
                exit_code=row["exit_code"],
            )
            self._add_to_index(entry)
            count += 1

        logger.debug("Rebuilt history index with %d entries", count)
        return count

    def _tokenize(self, text: str) -> list[str]:
        """Split text into searchable tokens."""
        # Split on whitespace and common separators, lowercase
        tokens = re.split(r"[\s/\\|:;,.\-_=]+", text.lower())
        return [t for t in tokens if t and len(t) >= 2]

    def _add_to_index(self, entry: HistoryEntry) -> None:
        """Add an entry to the in-memory index."""
        self._entries[entry.id] = entry

        # Index by tokens
        tokens = self._tokenize(entry.command)
        for token in tokens:
            self._token_index[token].add(entry.id)

    def add_entry(self, command: str, exit_code: int = 0) -> int | None:
        """Add a new entry to both storage and index.

        Returns:
            Entry ID if added, None if duplicate or empty.
        """
        if not command.strip():
            return None

        if self._storage is None:
            logger.warning("No storage manager attached, cannot add entry")
            return None

        # Check for consecutive duplicate
        if self._entries:
            last_id = max(self._entries.keys())
            if self._entries[last_id].command == command:
                return None

        # Add to storage
        self._storage.add_history(command, exit_code)

        # Get the newly added entry
        cursor = self._storage.conn.cursor()
        cursor.execute(
            "SELECT id, command, timestamp, exit_code FROM history ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row["command"] == command:
            entry = HistoryEntry(
                id=row["id"],
                command=row["command"],
                timestamp=row["timestamp"],
                exit_code=row["exit_code"],
            )
            self._add_to_index(entry)
            return entry.id

        return None

    def search(self, query: str, limit: int = 20) -> list[HistoryEntry]:
        """Search for commands matching query.

        Uses token-based matching for fast lookup, then filters by substring.

        Args:
            query: Search query string.
            limit: Maximum results to return.

        Returns:
            List of matching HistoryEntry objects, newest first.
        """
        if not query.strip():
            # Return most recent entries
            entries = sorted(self._entries.values(), key=lambda e: e.id, reverse=True)
            return entries[:limit]

        query_lower = query.lower()
        tokens = self._tokenize(query)

        if not tokens:
            # Fallback to substring search on all entries
            matches = [
                e for e in self._entries.values() if query_lower in e.command.lower()
            ]
            matches.sort(key=lambda e: e.id, reverse=True)
            return matches[:limit]

        # Find candidate IDs from token index
        candidate_ids: set[int] | None = None
        for token in tokens:
            # Find all tokens that contain this token as substring
            matching_ids: set[int] = set()
            for indexed_token, ids in self._token_index.items():
                if token in indexed_token:
                    matching_ids.update(ids)

            if candidate_ids is None:
                candidate_ids = matching_ids
            else:
                candidate_ids &= matching_ids

            if not candidate_ids:
                break

        if not candidate_ids:
            return []

        # Filter candidates by full substring match and sort
        matches = []
        for entry_id in candidate_ids:
            entry = self._entries.get(entry_id)
            if entry and query_lower in entry.command.lower():
                matches.append(entry)

        matches.sort(key=lambda e: e.id, reverse=True)
        return matches[:limit]

    def search_prefix(self, prefix: str, limit: int = 10) -> list[HistoryEntry]:
        """Search for commands starting with prefix.

        Args:
            prefix: Command prefix to match.
            limit: Maximum results to return.

        Returns:
            List of matching HistoryEntry objects, newest first.
        """
        if not prefix:
            entries = sorted(self._entries.values(), key=lambda e: e.id, reverse=True)
            return entries[:limit]

        prefix_lower = prefix.lower()
        matches = [
            e
            for e in self._entries.values()
            if e.command.lower().startswith(prefix_lower)
        ]
        matches.sort(key=lambda e: e.id, reverse=True)
        return matches[:limit]

    def get_recent(self, limit: int = 50) -> list[HistoryEntry]:
        """Get most recent history entries.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of HistoryEntry objects, oldest first (for up-arrow nav).
        """
        entries = sorted(self._entries.values(), key=lambda e: e.id, reverse=True)
        return list(reversed(entries[:limit]))

    def clear(self) -> None:
        """Clear the in-memory index."""
        self._entries.clear()
        self._token_index.clear()

    @property
    def count(self) -> int:
        """Number of entries in the index."""
        return len(self._entries)
