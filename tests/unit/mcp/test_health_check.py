"""Unit tests for MCP health check functionality."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.health_check import HealthStatus, MCPHealthChecker, ServerHealth


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.clients = {}
    manager.reconnect_server = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.is_connected = True
    client._send_request = AsyncMock(return_value={})
    return client


class TestHealthStatus:
    def test_enum_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.DISCONNECTED.value == "disconnected"


class TestServerHealth:
    def test_creation(self):
        health = ServerHealth(
            name="test-server",
            status=HealthStatus.HEALTHY,
            last_check=time.time(),
        )
        assert health.name == "test-server"
        assert health.status == HealthStatus.HEALTHY
        assert health.consecutive_failures == 0
        assert health.last_error is None

    def test_with_error(self):
        health = ServerHealth(
            name="test-server",
            status=HealthStatus.DEGRADED,
            last_check=time.time(),
            consecutive_failures=2,
            last_error="Timeout",
        )
        assert health.consecutive_failures == 2
        assert health.last_error == "Timeout"


class TestMCPHealthChecker:
    def test_init_defaults(self, mock_manager):
        checker = MCPHealthChecker(mock_manager)
        assert checker.check_interval == 30.0
        assert not checker.is_running
        assert checker.get_all_health() == {}

    def test_init_custom_interval(self, mock_manager):
        checker = MCPHealthChecker(mock_manager, check_interval=10.0)
        assert checker.check_interval == 10.0

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_manager):
        checker = MCPHealthChecker(mock_manager, check_interval=1.0)
        await checker.start()
        assert checker.is_running

        await checker.stop()
        assert not checker.is_running

    @pytest.mark.asyncio
    async def test_start_idempotent(self, mock_manager):
        checker = MCPHealthChecker(mock_manager, check_interval=1.0)
        await checker.start()
        await checker.start()
        assert checker.is_running
        await checker.stop()

    @pytest.mark.asyncio
    async def test_check_healthy_server(self, mock_manager, mock_client):
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        health = await checker.check_now()

        assert "test-server" in health
        assert health["test-server"].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_disconnected_server(self, mock_manager, mock_client):
        mock_client.is_connected = False
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        health = await checker.check_now()

        assert health["test-server"].status == HealthStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_check_ping_error_fallback_success(self, mock_manager, mock_client):
        mock_client._send_request = AsyncMock(
            side_effect=[Exception("ping not supported"), {}]
        )
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        health = await checker.check_now()

        assert health["test-server"].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_timeout_degraded(self, mock_manager, mock_client):
        mock_client._send_request = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        health = await checker.check_now()

        assert health["test-server"].status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_status_change_callback(self, mock_manager, mock_client):
        callback = MagicMock()
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager, on_status_change=callback)

        await checker.check_now()
        mock_client.is_connected = False
        await checker.check_now()

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "test-server"
        assert args[1] == HealthStatus.HEALTHY
        assert args[2] == HealthStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_disconnect(self, mock_manager, mock_client):
        mock_client.is_connected = False
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        await checker.check_now()
        await asyncio.sleep(0.1)

        mock_manager.reconnect_server.assert_called_once_with("test-server")

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracked(self, mock_manager, mock_client):
        mock_client._send_request = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        await checker.check_now()
        await checker.check_now()
        await checker.check_now()

        health = checker.get_health("test-server")
        assert health is not None
        assert health.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_failures_reset_on_healthy(self, mock_manager, mock_client):
        mock_client._send_request = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        await checker.check_now()
        await checker.check_now()

        mock_client._send_request = AsyncMock(return_value={})
        await checker.check_now()

        health = checker.get_health("test-server")
        assert health is not None
        assert health.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_removed_server_cleaned_up(self, mock_manager, mock_client):
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager)

        await checker.check_now()
        assert "test-server" in checker.get_all_health()

        mock_manager.clients = {}
        await checker.check_now()
        assert "test-server" not in checker.get_all_health()

    def test_get_health_nonexistent(self, mock_manager):
        checker = MCPHealthChecker(mock_manager)
        assert checker.get_health("nonexistent") is None

    @pytest.mark.asyncio
    async def test_periodic_check_loop(self, mock_manager, mock_client):
        mock_manager.clients = {"test-server": mock_client}
        checker = MCPHealthChecker(mock_manager, check_interval=0.1)

        await checker.start()
        await asyncio.sleep(0.25)
        await checker.stop()

        assert mock_client._send_request.call_count >= 2
