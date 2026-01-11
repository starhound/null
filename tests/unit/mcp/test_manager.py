from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.config import MCPServerConfig
from mcp.manager import MCPManager


@pytest.fixture
def mock_config():
    with patch("mcp.manager.MCPConfig") as MockConfig:
        config_instance = MockConfig.return_value
        config_instance.servers = {}
        config_instance.get_enabled_servers.return_value = []
        yield config_instance


@pytest.fixture
def manager(mock_config):
    return MCPManager()


@pytest.mark.asyncio
async def test_initialize_empty(manager, mock_config):
    await manager.initialize()
    assert manager._initialized
    assert len(manager.clients) == 0


@pytest.mark.asyncio
async def test_initialize_with_servers(manager, mock_config):
    server = MCPServerConfig(name="test", command="echo", enabled=True)
    mock_config.get_enabled_servers.return_value = [server]
    mock_config.servers = {"test": server}

    with patch("mcp.manager.MCPClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.connect = AsyncMock(return_value=True)

        await manager.initialize()

        assert "test" in manager.clients
        client_instance.connect.assert_called_once()


@pytest.mark.asyncio
async def test_connect_server_success(manager, mock_config):
    server = MCPServerConfig(name="test", command="echo", enabled=True)
    mock_config.servers = {"test": server}

    with patch("mcp.manager.MCPClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.connect = AsyncMock(return_value=True)

        result = await manager.connect_server("test")

        assert result is True
        assert "test" in manager.clients


@pytest.mark.asyncio
async def test_connect_server_failure(manager, mock_config):
    server = MCPServerConfig(name="test", command="echo", enabled=True)
    mock_config.servers = {"test": server}

    with patch("mcp.manager.MCPClient") as MockClient:
        client_instance = MockClient.return_value
        client_instance.connect = AsyncMock(return_value=False)

        result = await manager.connect_server("test")

        assert result is False
        assert "test" not in manager.clients


@pytest.mark.asyncio
async def test_disconnect_server(manager):
    client_mock = MagicMock()
    client_mock.disconnect = AsyncMock()
    manager.clients["test"] = client_mock

    await manager.disconnect_server("test")

    assert "test" not in manager.clients
    client_mock.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_call_tool(manager):
    client_mock = MagicMock()
    client_mock.is_connected = True
    client_mock.call_tool = AsyncMock(return_value="result")

    tool_mock = MagicMock()
    tool_mock.name = "my_tool"
    tool_mock.server_name = "test_server"
    client_mock.tools = [tool_mock]

    manager.clients["test_server"] = client_mock

    result = await manager.call_tool("my_tool", {"arg": "val"})

    assert result == "result"
    client_mock.call_tool.assert_called_with("my_tool", {"arg": "val"})


@pytest.mark.asyncio
async def test_call_tool_not_found(manager):
    with pytest.raises(Exception, match="Tool not found"):
        await manager.call_tool("missing", {})
