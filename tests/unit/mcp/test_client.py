import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.client import MCPClient
from mcp.config import MCPServerConfig


@pytest.fixture
def server_config():
    return MCPServerConfig(
        name="test_server", command="python", args=["-m", "server"], env={"TEST": "1"}
    )


@pytest.fixture
def client(server_config):
    return MCPClient(server_config)


@pytest.mark.asyncio
async def test_connect_success(client):
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_exec.return_value = mock_process

        # Patch _read_loop to prevent infinite loop or race conditions during test
        with patch.object(client, "_read_loop", new_callable=AsyncMock):
            # Patch _send_request to simulate successful initialization
            with patch.object(client, "_send_request", return_value=True):
                # Patch discovery methods
                with patch.object(client, "_discover_tools", new_callable=AsyncMock):
                    with patch.object(
                        client, "_discover_resources", new_callable=AsyncMock
                    ):
                        success = await client.connect()

        assert success is True
        assert client.is_connected


@pytest.mark.asyncio
async def test_connect_failure(client):
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Failed")):
        success = await client.connect()
        assert success is False
        assert not client.is_connected


@pytest.mark.asyncio
async def test_disconnect(client):
    client.process = AsyncMock()
    client._connected = True

    # Mock _read_task as a Future that is already done
    future = asyncio.Future()
    future.set_result(None)
    client._read_task = future

    await client.disconnect()

    assert not client.is_connected
    assert client.process is None


@pytest.mark.asyncio
async def test_call_tool(client):
    client.process = AsyncMock()
    client.process.stdin.write = MagicMock()
    client.process.stdin.drain = AsyncMock()
    client._connected = True

    with patch.object(
        client, "_send_request", return_value={"content": "output"}
    ) as mock_send:
        result = await client.call_tool("tool1", {})
        assert result["content"] == "output"
        mock_send.assert_called_with("tools/call", {"name": "tool1", "arguments": {}})


@pytest.mark.asyncio
async def test_read_resource(client):
    client.process = AsyncMock()  # Needed for is_connected property
    client._connected = True
    with patch.object(
        client, "_send_request", return_value={"contents": [{"text": "data"}]}
    ):
        content = await client.read_resource("file:///test")
        assert content == "data"


@pytest.mark.asyncio
async def test_call_tool_not_connected(client):
    client._connected = False
    with pytest.raises(Exception, match="Not connected"):
        await client.call_tool("tool1", {})


class TestReconnect:
    @pytest.mark.asyncio
    async def test_cancel_reconnect_stops_task(self, server_config):
        client = MCPClient(server_config)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        client._reconnect_task = mock_task
        client._reconnect_attempts = 3

        client.cancel_reconnect()

        mock_task.cancel.assert_called_once()
        assert client._reconnect_task is None
        assert client._reconnect_attempts == 0

    @pytest.mark.asyncio
    async def test_cancel_reconnect_no_task(self, server_config):
        client = MCPClient(server_config)
        client._reconnect_task = None
        client._reconnect_attempts = 2

        client.cancel_reconnect()

        assert client._reconnect_attempts == 0

    @pytest.mark.asyncio
    async def test_manual_disconnect_sets_flag(self, server_config):
        client = MCPClient(server_config)
        client._connected = True
        client._manual_disconnect = False

        future = asyncio.Future()
        future.set_result(None)
        client._read_task = future

        await client.disconnect(manual=True)

        assert client._manual_disconnect is True

    @pytest.mark.asyncio
    async def test_non_manual_disconnect_preserves_flag(self, server_config):
        client = MCPClient(server_config)
        client._connected = True
        client._manual_disconnect = False

        future = asyncio.Future()
        future.set_result(None)
        client._read_task = future

        await client.disconnect(manual=False)

        assert client._manual_disconnect is False

    @pytest.mark.asyncio
    async def test_connect_resets_manual_disconnect_flag(self, server_config):
        client = MCPClient(server_config)
        client._manual_disconnect = True

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.stdin.write = MagicMock()
            mock_process.stdin.drain = AsyncMock()
            mock_exec.return_value = mock_process

            with patch.object(client, "_read_loop", new_callable=AsyncMock):
                with patch.object(client, "_send_request", return_value=True):
                    with patch.object(
                        client, "_discover_tools", new_callable=AsyncMock
                    ):
                        with patch.object(
                            client, "_discover_resources", new_callable=AsyncMock
                        ):
                            await client.connect()

        assert client._manual_disconnect is False

    @pytest.mark.asyncio
    async def test_reconnect_callbacks_called(self, server_config):
        attempt_callback = MagicMock()
        success_callback = MagicMock()
        failed_callback = MagicMock()

        client = MCPClient(
            server_config,
            on_reconnect_attempt=attempt_callback,
            on_reconnect_success=success_callback,
            on_reconnect_failed=failed_callback,
        )

        with patch.object(client, "disconnect", new_callable=AsyncMock):
            with patch.object(client, "connect", return_value=True):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await client._attempt_reconnect()

        attempt_callback.assert_called_once_with("test_server", 1, 1.0)
        success_callback.assert_called_once_with("test_server")
        failed_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconnect_failed_callback_after_max_attempts(self, server_config):
        failed_callback = MagicMock()

        client = MCPClient(
            server_config,
            on_reconnect_failed=failed_callback,
        )

        with patch.object(client, "disconnect", new_callable=AsyncMock):
            with patch.object(client, "connect", return_value=False):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await client._attempt_reconnect()

        failed_callback.assert_called_once_with("test_server", 5)

    @pytest.mark.asyncio
    async def test_reconnect_stops_on_manual_disconnect(self, server_config):
        attempt_callback = MagicMock()

        client = MCPClient(
            server_config,
            on_reconnect_attempt=attempt_callback,
        )

        async def set_manual_flag(_):
            client._manual_disconnect = True

        with patch("asyncio.sleep", side_effect=set_manual_flag):
            await client._attempt_reconnect()

        attempt_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self, server_config):
        client = MCPClient(server_config)
        sleep_delays = []

        async def capture_sleep(delay):
            sleep_delays.append(delay)
            if len(sleep_delays) >= 5:
                client._manual_disconnect = True

        with patch.object(client, "disconnect", new_callable=AsyncMock):
            with patch.object(client, "connect", return_value=False):
                with patch("asyncio.sleep", side_effect=capture_sleep):
                    await client._attempt_reconnect()

        assert sleep_delays == [1.0, 2.0, 4.0, 8.0, 16.0]
