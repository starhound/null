import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from mcp.client import MCPClient, MCPTool
from mcp.config import MCPServerConfig
import asyncio


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
