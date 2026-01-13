"""Tests for SSH Connection Pool Manager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.ssh import SSHConnectionInfo, SSHConnectionPool, SSHConnectionState


class TestSSHConnectionState:
    def test_all_states_defined(self):
        assert SSHConnectionState.DISCONNECTED.value == "disconnected"
        assert SSHConnectionState.CONNECTING.value == "connecting"
        assert SSHConnectionState.CONNECTED.value == "connected"
        assert SSHConnectionState.ERROR.value == "error"
        assert SSHConnectionState.RECONNECTING.value == "reconnecting"


class TestSSHConnectionInfo:
    def test_init_defaults(self):
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        assert info.host == "example.com"
        assert info.port == 22
        assert info.username == "user"
        assert info.state == SSHConnectionState.DISCONNECTED
        assert info.connection is None
        assert info.retry_count == 0

    def test_is_connected_false_when_disconnected(self):
        info = SSHConnectionInfo(
            host="example.com", port=22, username=None, key="example.com:22:default"
        )
        assert info.is_connected is False

    def test_is_connected_true_when_connected(self):
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username=None,
            key="example.com:22:default",
            state=SSHConnectionState.CONNECTED,
            connection=MagicMock(),
        )
        assert info.is_connected is True

    def test_uptime_zero_when_not_connected(self):
        info = SSHConnectionInfo(
            host="example.com", port=22, username=None, key="example.com:22:default"
        )
        assert info.uptime == 0.0

    def test_to_dict(self):
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        data = info.to_dict()
        assert data["host"] == "example.com"
        assert data["port"] == 22
        assert data["username"] == "user"
        assert data["state"] == "disconnected"
        assert data["uptime"] == 0.0


class TestSSHConnectionPool:
    def test_init_defaults(self):
        pool = SSHConnectionPool()
        assert pool._keep_alive_interval == 30.0
        assert pool._max_idle_time == 300.0
        assert pool._auto_reconnect is True
        assert pool._running is False

    def test_init_custom_params(self):
        pool = SSHConnectionPool(
            keep_alive_interval=60.0,
            max_idle_time=600.0,
            auto_reconnect=False,
        )
        assert pool._keep_alive_interval == 60.0
        assert pool._max_idle_time == 600.0
        assert pool._auto_reconnect is False

    def test_get_connection_key(self):
        pool = SSHConnectionPool()
        assert pool._get_connection_key("host.com", 22, "user") == "host.com:22:user"
        assert pool._get_connection_key("host.com", 22, None) == "host.com:22:default"
        assert (
            pool._get_connection_key("host.com", 2222, "root") == "host.com:2222:root"
        )

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        pool = SSHConnectionPool()
        await pool.start()
        assert pool._running is True
        assert pool._keep_alive_task is not None
        await pool.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self):
        pool = SSHConnectionPool()
        await pool.start()
        await pool.stop()
        assert pool._running is False
        assert pool._keep_alive_task is None

    @pytest.mark.asyncio
    async def test_get_connection_creates_new_connection(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            info = await pool.get_connection(
                host="example.com",
                port=22,
                username="user",
            )

            assert info.host == "example.com"
            assert info.port == 22
            assert info.username == "user"
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_reuses_existing(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            info1 = await pool.get_connection(host="example.com", username="user")
            info2 = await pool.get_connection(host="example.com", username="user")

            assert info1.key == info2.key
            assert mock_connect.call_count == 1

    @pytest.mark.asyncio
    async def test_close_connection(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_conn.wait_closed = AsyncMock()
            mock_connect.return_value = mock_conn

            info = await pool.get_connection(host="example.com")
            await pool.close_connection(info.key)

            assert info.state == SSHConnectionState.DISCONNECTED
            assert info.connection is None
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_connection(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_conn.wait_closed = AsyncMock()
            mock_connect.return_value = mock_conn

            info = await pool.get_connection(host="example.com")
            key = info.key
            await pool.remove_connection(key)

            assert key not in pool._connections

    def test_list_connections_empty(self):
        pool = SSHConnectionPool()
        assert pool.list_connections() == []

    @pytest.mark.asyncio
    async def test_list_connections_with_data(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            await pool.get_connection(host="host1.com")
            await pool.get_connection(host="host2.com")

            connections = pool.list_connections()
            assert len(connections) == 2

    def test_get_status(self):
        pool = SSHConnectionPool()
        status = pool.get_status()

        assert status["running"] is False
        assert status["total_connections"] == 0
        assert status["connected_count"] == 0
        assert status["keep_alive_interval"] == 30.0
        assert status["max_idle_time"] == 300.0
        assert status["auto_reconnect"] is True

    def test_set_keep_alive_interval(self):
        pool = SSHConnectionPool()
        pool.set_keep_alive_interval(60.0)
        assert pool._keep_alive_interval == 60.0
        pool.set_keep_alive_interval(1.0)
        assert pool._keep_alive_interval == 5.0

    def test_set_max_idle_time(self):
        pool = SSHConnectionPool()
        pool.set_max_idle_time(600.0)
        assert pool._max_idle_time == 600.0
        pool.set_max_idle_time(30.0)
        assert pool._max_idle_time == 60.0

    def test_set_auto_reconnect(self):
        pool = SSHConnectionPool()
        pool.set_auto_reconnect(False)
        assert pool._auto_reconnect is False
        pool.set_auto_reconnect(True)
        assert pool._auto_reconnect is True

    def test_add_state_callback(self):
        pool = SSHConnectionPool()
        callback = MagicMock()
        pool.add_state_callback(callback)
        assert callback in pool._state_callbacks

    def test_remove_state_callback(self):
        pool = SSHConnectionPool()
        callback = MagicMock()
        pool.add_state_callback(callback)
        pool.remove_state_callback(callback)
        assert callback not in pool._state_callbacks

    @pytest.mark.asyncio
    async def test_restore_session(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            info = await pool.restore_session(
                host="example.com",
                username="user",
                password="pass",
            )

            assert info.state == SSHConnectionState.CONNECTED
            assert info.retry_count == 0

    @pytest.mark.asyncio
    async def test_connection_error_sets_error_state(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            info = await pool.get_connection(host="example.com")

            assert info.state == SSHConnectionState.ERROR
            assert "Connection failed" in info.error_message

    @pytest.mark.asyncio
    async def test_state_callback_called_on_connect(self):
        pool = SSHConnectionPool()
        callback = MagicMock()
        pool.add_state_callback(callback)

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            await pool.get_connection(host="example.com")

            assert callback.call_count >= 1

    def test_get_connection_by_host(self):
        pool = SSHConnectionPool()
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        pool._connections[info.key] = info

        result = pool.get_connection_by_host("example.com", 22, "user")
        assert result == info

        result_none = pool.get_connection_by_host("other.com", 22, "user")
        assert result_none is None

    def test_get_connection_info(self):
        pool = SSHConnectionPool()
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        pool._connections[info.key] = info

        result = pool.get_connection_info("example.com:22:user")
        assert result == info

        result_none = pool.get_connection_info("nonexistent")
        assert result_none is None
