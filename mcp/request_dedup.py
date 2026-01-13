"""Request deduplication for MCP tool calls."""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CachedResult:
    """A cached tool call result."""

    result: Any
    timestamp: float
    tool_name: str


@dataclass
class RequestDeduplicator:
    """Deduplicates MCP tool calls within a configurable time window.

    Tracks recent requests by hash (tool name + arguments) and returns
    cached results for duplicate requests within the time window.
    """

    dedup_window: float = 1.0
    enabled: bool = True
    _cache: dict[str, CachedResult] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _make_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Create a hash key from tool name and arguments."""
        payload = json.dumps(
            {"tool": tool_name, "args": arguments}, sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    async def get_cached(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[bool, Any]:
        """Check for a cached result.

        Returns:
            (hit, result): hit is True if cache hit, result is the cached value
        """
        if not self.enabled:
            return False, None

        key = self._make_key(tool_name, arguments)
        now = time.monotonic()

        async with self._lock:
            if key in self._cache:
                cached = self._cache[key]
                if now - cached.timestamp <= self.dedup_window:
                    return True, cached.result
                del self._cache[key]

        return False, None

    async def cache_result(
        self, tool_name: str, arguments: dict[str, Any], result: Any
    ) -> None:
        """Cache a tool call result."""
        if not self.enabled:
            return

        key = self._make_key(tool_name, arguments)

        async with self._lock:
            self._cache[key] = CachedResult(
                result=result, timestamp=time.monotonic(), tool_name=tool_name
            )

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count of removed entries."""
        now = time.monotonic()
        removed = 0

        async with self._lock:
            expired_keys = [
                k
                for k, v in self._cache.items()
                if now - v.timestamp > self.dedup_window
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1

        return removed

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Current number of cached entries."""
        return len(self._cache)
