"""HTTP connection pooling for AI provider clients."""

import asyncio
from typing import Any

import httpx


class ConnectionPoolConfig:
    """Configuration for HTTP connection pooling."""

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        connect_timeout: float = 10.0,
        read_timeout: float = 120.0,
        write_timeout: float = 30.0,
        pool_timeout: float = 10.0,
    ):
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.pool_timeout = pool_timeout


class ConnectionPoolManager:
    """Manages shared httpx.AsyncClient instances with connection pooling.

    Provides connection reuse across requests and graceful cleanup.
    Thread-safe singleton pattern for global access.
    """

    _instance: "ConnectionPoolManager | None" = None
    _lock: asyncio.Lock | None = None

    def __new__(cls) -> "ConnectionPoolManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._config = ConnectionPoolConfig()
        self._closed = False

    @classmethod
    async def get_instance(cls) -> "ConnectionPoolManager":
        """Get or create the singleton instance (async-safe)."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def configure(self, config: ConnectionPoolConfig) -> None:
        """Update pool configuration. Must be called before getting clients."""
        self._config = config

    def _create_limits(self) -> httpx.Limits:
        """Create httpx.Limits from config."""
        return httpx.Limits(
            max_connections=self._config.max_connections,
            max_keepalive_connections=self._config.max_keepalive_connections,
            keepalive_expiry=self._config.keepalive_expiry,
        )

    def _create_timeout(
        self,
        connect: float | None = None,
        read: float | None = None,
        write: float | None = None,
        pool: float | None = None,
    ) -> httpx.Timeout:
        """Create httpx.Timeout with optional overrides."""
        return httpx.Timeout(
            connect=connect or self._config.connect_timeout,
            read=read or self._config.read_timeout,
            write=write or self._config.write_timeout,
            pool=pool or self._config.pool_timeout,
        )

    def get_client(
        self,
        key: str,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        connect_timeout: float | None = None,
        read_timeout: float | None = None,
    ) -> httpx.AsyncClient:
        """Get or create a pooled AsyncClient for a given key.

        Args:
            key: Unique identifier for this client (e.g., "ollama", "openai").
            base_url: Optional base URL for all requests.
            headers: Optional default headers.
            connect_timeout: Override default connect timeout.
            read_timeout: Override default read timeout.

        Returns:
            A shared httpx.AsyncClient instance.
        """
        if self._closed:
            raise RuntimeError("ConnectionPoolManager is closed")

        if key not in self._clients:
            timeout = self._create_timeout(
                connect=connect_timeout,
                read=read_timeout,
            )
            kwargs: dict[str, Any] = {
                "timeout": timeout,
                "limits": self._create_limits(),
            }
            if base_url:
                kwargs["base_url"] = base_url
            if headers:
                kwargs["headers"] = headers
            self._clients[key] = httpx.AsyncClient(**kwargs)
        return self._clients[key]

    async def close_client(self, key: str) -> None:
        """Close and remove a specific client."""
        if key in self._clients:
            await self._clients[key].aclose()
            del self._clients[key]

    async def close(self) -> None:
        """Close all clients and cleanup resources."""
        if self._closed:
            return
        self._closed = True
        close_tasks = [client.aclose() for client in self._clients.values()]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        self._clients.clear()

    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown the global pool manager."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            cls._lock = None

    def is_closed(self) -> bool:
        """Check if the pool manager is closed."""
        return self._closed

    @property
    def active_clients(self) -> list[str]:
        """List of active client keys."""
        return list(self._clients.keys())


# Global convenience functions
_pool: ConnectionPoolManager | None = None


async def get_pool() -> ConnectionPoolManager:
    """Get the global connection pool manager."""
    global _pool
    if _pool is None or _pool.is_closed():
        _pool = await ConnectionPoolManager.get_instance()
    return _pool


async def get_pooled_client(
    key: str,
    base_url: str | None = None,
    headers: dict[str, str] | None = None,
    connect_timeout: float | None = None,
    read_timeout: float | None = None,
) -> httpx.AsyncClient:
    """Get a pooled client from the global pool."""
    pool = await get_pool()
    return pool.get_client(
        key,
        base_url=base_url,
        headers=headers,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )


async def close_pool() -> None:
    """Close the global connection pool."""
    await ConnectionPoolManager.shutdown()
