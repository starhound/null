import pytest
import httpx
from unittest.mock import AsyncMock, patch

from ai.connection_pool import (
    ConnectionPoolManager,
    ConnectionPoolConfig,
    get_pool,
    get_pooled_client,
    close_pool,
)


@pytest.fixture
def pool_config():
    return ConnectionPoolConfig(
        max_connections=50,
        max_keepalive_connections=10,
        keepalive_expiry=15.0,
        connect_timeout=5.0,
        read_timeout=60.0,
    )


@pytest.fixture
async def fresh_pool():
    await ConnectionPoolManager.shutdown()
    yield
    await ConnectionPoolManager.shutdown()


class TestConnectionPoolConfig:
    def test_default_values(self):
        config = ConnectionPoolConfig()
        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.keepalive_expiry == 30.0
        assert config.connect_timeout == 10.0
        assert config.read_timeout == 120.0

    def test_custom_values(self, pool_config):
        assert pool_config.max_connections == 50
        assert pool_config.max_keepalive_connections == 10


class TestConnectionPoolManager:
    @pytest.mark.asyncio
    async def test_singleton_pattern(self, fresh_pool):
        pool1 = await ConnectionPoolManager.get_instance()
        pool2 = await ConnectionPoolManager.get_instance()
        assert pool1 is pool2

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self, fresh_pool):
        pool = await ConnectionPoolManager.get_instance()
        client = pool.get_client("test-provider")
        assert isinstance(client, httpx.AsyncClient)
        assert "test-provider" in pool.active_clients

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self, fresh_pool):
        pool = await ConnectionPoolManager.get_instance()
        client1 = pool.get_client("test-provider")
        client2 = pool.get_client("test-provider")
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_different_keys_different_clients(self, fresh_pool):
        pool = await ConnectionPoolManager.get_instance()
        client1 = pool.get_client("provider-a")
        client2 = pool.get_client("provider-b")
        assert client1 is not client2

    @pytest.mark.asyncio
    async def test_configure_pool(self, fresh_pool, pool_config):
        pool = await ConnectionPoolManager.get_instance()
        pool.configure(pool_config)
        assert pool._config.max_connections == 50

    @pytest.mark.asyncio
    async def test_close_client(self, fresh_pool):
        pool = await ConnectionPoolManager.get_instance()
        pool.get_client("to-close")
        assert "to-close" in pool.active_clients
        await pool.close_client("to-close")
        assert "to-close" not in pool.active_clients

    @pytest.mark.asyncio
    async def test_close_all(self, fresh_pool):
        pool = await ConnectionPoolManager.get_instance()
        pool.get_client("client-1")
        pool.get_client("client-2")
        await pool.close()
        assert pool.is_closed()
        assert len(pool.active_clients) == 0

    @pytest.mark.asyncio
    async def test_get_client_after_close_raises(self, fresh_pool):
        pool = await ConnectionPoolManager.get_instance()
        await pool.close()
        with pytest.raises(RuntimeError, match="closed"):
            pool.get_client("should-fail")

    @pytest.mark.asyncio
    async def test_shutdown_resets_singleton(self, fresh_pool):
        pool1 = await ConnectionPoolManager.get_instance()
        await ConnectionPoolManager.shutdown()
        pool2 = await ConnectionPoolManager.get_instance()
        assert pool1 is not pool2


class TestGlobalFunctions:
    @pytest.mark.asyncio
    async def test_get_pool(self, fresh_pool):
        pool = await get_pool()
        assert isinstance(pool, ConnectionPoolManager)

    @pytest.mark.asyncio
    async def test_get_pooled_client(self, fresh_pool):
        client = await get_pooled_client("global-test")
        assert isinstance(client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_close_pool(self, fresh_pool):
        await get_pool()
        await close_pool()
        pool = await get_pool()
        assert not pool.is_closed()
