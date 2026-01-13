"""AI Model Cache - TTL-based caching for model lists."""

import asyncio
import time
from dataclasses import dataclass, field

from config.defaults import DEFAULT_MODEL_CACHE_TTL


@dataclass
class CacheEntry:
    """A cached model list with timestamp."""

    models: list[str]
    timestamp: float = field(default_factory=time.time)

    def is_expired(self, ttl: float) -> bool:
        """Check if entry has exceeded TTL."""
        return (time.time() - self.timestamp) > ttl


class ModelCache:
    """Thread-safe TTL-based cache for AI model lists.

    Caches model lists per provider to avoid repeated API calls.
    Uses asyncio.Lock for thread-safety in async contexts.
    """

    def __init__(self, ttl: float | None = None):
        """Initialize cache with optional custom TTL.

        Args:
            ttl: Cache TTL in seconds. Defaults to DEFAULT_MODEL_CACHE_TTL.
        """
        self._ttl = ttl if ttl is not None else DEFAULT_MODEL_CACHE_TTL
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    @property
    def ttl(self) -> float:
        """Get current TTL in seconds."""
        return self._ttl

    async def get_models(self, provider_id: str) -> list[str] | None:
        """Get cached models for a provider.

        Args:
            provider_id: Provider identifier (e.g., 'openai', 'anthropic')

        Returns:
            List of model names if cache hit and not expired, None otherwise.
        """
        async with self._lock:
            entry = self._cache.get(provider_id)
            if entry is None:
                return None
            if entry.is_expired(self._ttl):
                del self._cache[provider_id]
                return None
            return entry.models.copy()

    async def set_models(self, provider_id: str, models: list[str]) -> None:
        """Cache models for a provider.

        Args:
            provider_id: Provider identifier
            models: List of model names to cache
        """
        async with self._lock:
            self._cache[provider_id] = CacheEntry(models=models.copy())

    async def invalidate(self, provider_id: str) -> bool:
        """Invalidate cache for a specific provider.

        Args:
            provider_id: Provider identifier to invalidate

        Returns:
            True if entry was removed, False if not found.
        """
        async with self._lock:
            if provider_id in self._cache:
                del self._cache[provider_id]
                return True
            return False

    async def clear_all(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries cleared.
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def get_cached_providers(self) -> list[str]:
        """Get list of providers with cached data.

        Returns:
            List of provider IDs with non-expired cache entries.
        """
        async with self._lock:
            valid = []
            expired = []
            for provider_id, entry in self._cache.items():
                if entry.is_expired(self._ttl):
                    expired.append(provider_id)
                else:
                    valid.append(provider_id)
            # Clean up expired entries
            for provider_id in expired:
                del self._cache[provider_id]
            return valid
