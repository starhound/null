"""Integration tests for MCP (Model Context Protocol) system."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.client import MCPClient, MCPResource, MCPTool
from mcp.config import MCPConfig, MCPServerConfig
from mcp.manager import MCPManager


class TestMCPManagerInitialization:
    """Test MCPManager initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_manager_initializes_empty(self, mock_home):
        """Test manager initializes with no servers."""
        manager = MCPManager()
        assert manager._initialized is False
        assert manager.clients == {}

        await manager.initialize()
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_manager_initializes_only_once(self, mock_home):
        """Test manager doesn't reinitialize if already initialized."""
        manager = MCPManager()
        await manager.initialize()
        manager._initialized = True

        # Should not reinitialize
        with patch.object(manager, "connect_server") as mock_connect:
            await manager.initialize()
            mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_manager_connects_enabled_servers(self, mock_home):
        """Test manager connects to all enabled servers on init."""
        # Setup config with servers
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "echo",
                    "args": ["hello"],
                    "enabled": True,
                }
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        manager = MCPManager()

        with patch.object(manager, "connect_server", new_callable=AsyncMock) as mock:
            mock.return_value = True
            await manager.initialize()
            mock.assert_called_once_with("test-server")


class TestMCPServerConnection:
    """Test connecting to MCP servers."""

    @pytest.mark.asyncio
    async def test_connect_server_not_in_config(self, mock_home):
        """Test connecting to non-existent server fails."""
        manager = MCPManager()
        result = await manager.connect_server("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_disabled_server(self, mock_home):
        """Test connecting to disabled server fails."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "disabled-server": {
                    "command": "echo",
                    "args": [],
                    "enabled": False,
                }
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        manager = MCPManager()
        result = await manager.connect_server("disabled-server")
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_already_connected_server(self, mock_home):
        """Test connecting to already connected server returns existing state."""
        manager = MCPManager()

        mock_client = MagicMock()
        mock_client.is_connected = True
        manager.clients["test"] = mock_client

        result = await manager.connect_server("test")
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_server(self, mock_home):
        """Test disconnecting from a server."""
        manager = MCPManager()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        manager.clients["test"] = mock_client

        await manager.disconnect_server("test")

        mock_client.disconnect.assert_called_once()
        assert "test" not in manager.clients

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_server(self, mock_home):
        """Test disconnecting from non-existent server is safe."""
        manager = MCPManager()
        # Should not raise
        await manager.disconnect_server("nonexistent")

    @pytest.mark.asyncio
    async def test_disconnect_all_servers(self, mock_home):
        """Test disconnecting from all servers."""
        manager = MCPManager()
        manager._initialized = True

        mock_client1 = MagicMock()
        mock_client1.disconnect = AsyncMock()
        mock_client2 = MagicMock()
        mock_client2.disconnect = AsyncMock()

        manager.clients["server1"] = mock_client1
        manager.clients["server2"] = mock_client2

        await manager.disconnect_all()

        assert manager.clients == {}
        assert manager._initialized is False
        mock_client1.disconnect.assert_called_once()
        mock_client2.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_server(self, mock_home):
        """Test reconnecting to a server."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "echo",
                    "args": [],
                    "enabled": True,
                }
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        manager = MCPManager()

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        manager.clients["test-server"] = mock_client

        with patch.object(MCPClient, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            result = await manager.reconnect_server("test-server")

        mock_client.disconnect.assert_called_once()


class TestMCPToolDiscovery:
    """Test discovering tools from MCP servers."""

    def test_get_all_tools_empty(self, mock_home):
        """Test getting tools when no servers connected."""
        manager = MCPManager()
        tools = manager.get_all_tools()
        assert tools == []

    def test_get_all_tools_aggregates(self, mock_home):
        """Test tools are aggregated from all servers."""
        manager = MCPManager()

        tool1 = MCPTool(
            name="tool1",
            description="Tool 1",
            input_schema={},
            server_name="server1",
        )
        tool2 = MCPTool(
            name="tool2",
            description="Tool 2",
            input_schema={},
            server_name="server2",
        )

        mock_client1 = MagicMock()
        mock_client1.tools = [tool1]
        mock_client2 = MagicMock()
        mock_client2.tools = [tool2]

        manager.clients["server1"] = mock_client1
        manager.clients["server2"] = mock_client2

        tools = manager.get_all_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools

    def test_get_tool_by_name(self, mock_home):
        """Test finding a specific tool by name."""
        manager = MCPManager()

        tool = MCPTool(
            name="search",
            description="Search tool",
            input_schema={"type": "object"},
            server_name="server1",
        )

        mock_client = MagicMock()
        mock_client.tools = [tool]
        manager.clients["server1"] = mock_client

        found = manager.get_tool("search")
        assert found == tool

        not_found = manager.get_tool("nonexistent")
        assert not_found is None

    def test_get_tools_schema(self, mock_home):
        """Test getting tool schemas for LLM."""
        manager = MCPManager()

        tool = MCPTool(
            name="read_file",
            description="Read a file",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            server_name="fs-server",
        )

        mock_client = MagicMock()
        mock_client.tools = [tool]
        manager.clients["fs-server"] = mock_client

        schemas = manager.get_tools_schema()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "read_file"
        assert schemas[0]["description"] == "Read a file"
        assert "input_schema" in schemas[0]


class TestMCPToolCalling:
    """Test calling MCP tools."""

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_home):
        """Test calling a tool successfully."""
        manager = MCPManager()

        tool = MCPTool(
            name="test_tool",
            description="Test",
            input_schema={},
            server_name="test-server",
        )

        mock_client = MagicMock()
        mock_client.tools = [tool]
        mock_client.is_connected = True
        mock_client.call_tool = AsyncMock(return_value={"result": "success"})

        manager.clients["test-server"] = mock_client

        result = await manager.call_tool("test_tool", {"arg": "value"})
        assert result == {"result": "success"}
        mock_client.call_tool.assert_called_once_with("test_tool", {"arg": "value"})

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mock_home):
        """Test calling non-existent tool raises exception."""
        manager = MCPManager()

        with pytest.raises(Exception) as exc_info:
            await manager.call_tool("nonexistent", {})

        assert "Tool not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_server_disconnected(self, mock_home):
        """Test calling tool when server disconnected raises exception."""
        manager = MCPManager()

        tool = MCPTool(
            name="test_tool",
            description="Test",
            input_schema={},
            server_name="disconnected-server",
        )

        mock_client = MagicMock()
        mock_client.tools = [tool]
        mock_client.is_connected = False

        manager.clients["disconnected-server"] = mock_client

        with pytest.raises(Exception) as exc_info:
            await manager.call_tool("test_tool", {})

        assert "Server not connected" in str(exc_info.value)


class TestMCPServerDisconnection:
    """Test handling server disconnection scenarios."""

    @pytest.mark.asyncio
    async def test_server_tools_cleared_on_disconnect(self, mock_home):
        """Test server tools are cleared when disconnected."""
        manager = MCPManager()

        tool = MCPTool(
            name="tool1",
            description="Tool 1",
            input_schema={},
            server_name="server1",
        )

        mock_client = MagicMock()
        mock_client.tools = [tool]
        mock_client.disconnect = AsyncMock()
        manager.clients["server1"] = mock_client

        # Verify tool exists
        assert manager.get_tool("tool1") is not None

        # Disconnect
        await manager.disconnect_server("server1")

        # Tool should no longer be found
        assert manager.get_tool("tool1") is None

    @pytest.mark.asyncio
    async def test_get_status_reflects_connection_state(self, mock_home):
        """Test get_status shows correct connection state."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "connected-server": {
                    "command": "echo",
                    "args": [],
                    "enabled": True,
                },
                "disconnected-server": {
                    "command": "echo",
                    "args": [],
                    "enabled": True,
                },
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        manager = MCPManager()

        mock_connected = MagicMock()
        mock_connected.is_connected = True
        mock_connected.tools = [MagicMock()]
        mock_connected.resources = []
        manager.clients["connected-server"] = mock_connected

        status = manager.get_status()

        assert status["connected-server"]["connected"] is True
        assert status["connected-server"]["tools"] == 1
        assert status["disconnected-server"]["connected"] is False
        assert status["disconnected-server"]["tools"] == 0


class TestMCPConfigLoading:
    """Test MCP configuration loading and saving."""

    def test_config_creates_default_file(self, mock_home):
        """Test config creates default file if not exists."""
        config_path = mock_home / ".null" / "mcp.json"
        assert not config_path.exists()

        config = MCPConfig()

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert "mcpServers" in data

    def test_config_loads_existing_servers(self, mock_home):
        """Test config loads existing server configurations."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "brave-search": {
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-server-brave"],
                    "env": {"BRAVE_API_KEY": "test-key"},
                    "enabled": True,
                }
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig()

        assert "brave-search" in config.servers
        server = config.servers["brave-search"]
        assert server.command == "npx"
        assert server.args == ["-y", "@anthropic/mcp-server-brave"]
        assert server.env == {"BRAVE_API_KEY": "test-key"}
        assert server.enabled is True

    def test_config_add_server(self, mock_home):
        """Test adding a new server to config."""
        config = MCPConfig()

        server = config.add_server(
            name="new-server",
            command="npx",
            args=["-y", "some-package"],
            env={"API_KEY": "secret"},
        )

        assert server.name == "new-server"
        assert "new-server" in config.servers

        # Verify persisted
        data = json.loads(config.config_path.read_text())
        assert "new-server" in data["mcpServers"]

    def test_config_remove_server(self, mock_home):
        """Test removing a server from config."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "to-remove": {
                    "command": "echo",
                    "args": [],
                    "enabled": True,
                }
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig()
        result = config.remove_server("to-remove")

        assert result is True
        assert "to-remove" not in config.servers

    def test_config_remove_nonexistent_server(self, mock_home):
        """Test removing non-existent server returns False."""
        config = MCPConfig()
        result = config.remove_server("nonexistent")
        assert result is False

    def test_config_toggle_server(self, mock_home):
        """Test toggling server enabled state."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "toggle-test": {
                    "command": "echo",
                    "args": [],
                    "enabled": True,
                }
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig()

        # Toggle off
        result = config.toggle_server("toggle-test")
        assert result is False
        assert config.servers["toggle-test"].enabled is False

        # Toggle on
        result = config.toggle_server("toggle-test")
        assert result is True
        assert config.servers["toggle-test"].enabled is True

    def test_config_toggle_nonexistent_server(self, mock_home):
        """Test toggling non-existent server returns None."""
        config = MCPConfig()
        result = config.toggle_server("nonexistent")
        assert result is None

    def test_config_get_enabled_servers(self, mock_home):
        """Test getting only enabled servers."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "enabled1": {"command": "echo", "args": [], "enabled": True},
                "disabled1": {"command": "echo", "args": [], "enabled": False},
                "enabled2": {"command": "echo", "args": [], "enabled": True},
            },
            "profiles": {},
            "activeProfile": None,
        }
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig()
        enabled = config.get_enabled_servers()

        assert len(enabled) == 2
        names = [s.name for s in enabled]
        assert "enabled1" in names
        assert "enabled2" in names
        assert "disabled1" not in names

    def test_config_reload(self, mock_home):
        """Test reloading config from file."""
        config = MCPConfig()
        config.add_server("initial", "echo", [])

        # Modify file directly
        data = json.loads(config.config_path.read_text())
        data["mcpServers"]["added-externally"] = {
            "command": "external",
            "args": [],
            "enabled": True,
        }
        config.config_path.write_text(json.dumps(data))

        # Reload
        config.load()

        assert "added-externally" in config.servers


class TestMCPConfigProfiles:
    """Test MCP profile management."""

    def test_create_profile(self, mock_home):
        """Test creating a profile."""
        config = MCPConfig()
        config.add_server("server1", "echo", [])
        config.add_server("server2", "echo", [])

        config.create_profile("dev", ["server1"])

        assert "dev" in config.profiles
        assert config.profiles["dev"] == ["server1"]

    def test_create_profile_with_ai_config(self, mock_home):
        """Test creating a profile with AI configuration."""
        config = MCPConfig()
        config.add_server("server1", "echo", [])

        config.create_profile(
            "work",
            ["server1"],
            ai_config={"provider": "openai", "model": "gpt-4"},
        )

        assert "work" in config.profiles
        assert config.profiles["work"]["servers"] == ["server1"]
        assert config.profiles["work"]["ai"]["provider"] == "openai"

    def test_set_active_profile(self, mock_home):
        """Test setting active profile."""
        config = MCPConfig()
        config.add_server("server1", "echo", [])
        config.create_profile("test", ["server1"])

        config.set_active_profile("test")
        assert config.active_profile == "test"

    def test_set_invalid_profile(self, mock_home):
        """Test setting non-existent profile raises error."""
        config = MCPConfig()

        with pytest.raises(ValueError) as exc_info:
            config.set_active_profile("nonexistent")

        assert "not found" in str(exc_info.value)

    def test_get_enabled_servers_with_profile(self, mock_home):
        """Test enabled servers filtered by active profile."""
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "server1": {"command": "echo", "args": [], "enabled": True},
                "server2": {"command": "echo", "args": [], "enabled": True},
                "server3": {"command": "echo", "args": [], "enabled": True},
            },
            "profiles": {"limited": ["server1", "server3"]},
            "activeProfile": "limited",
        }
        config_path.write_text(json.dumps(config_data))

        config = MCPConfig()
        enabled = config.get_enabled_servers()

        names = [s.name for s in enabled]
        assert "server1" in names
        assert "server3" in names
        assert "server2" not in names

    def test_delete_profile(self, mock_home):
        """Test deleting a profile."""
        config = MCPConfig()
        config.add_server("server1", "echo", [])
        config.create_profile("to-delete", ["server1"])
        config.set_active_profile("to-delete")

        config.delete_profile("to-delete")

        assert "to-delete" not in config.profiles
        assert config.active_profile is None


class TestMCPResources:
    """Test MCP resource handling."""

    def test_get_all_resources(self, mock_home):
        """Test getting all resources from servers."""
        manager = MCPManager()

        resource = MCPResource(
            uri="file:///path/to/resource",
            name="Test Resource",
            description="A test resource",
            mime_type="text/plain",
            server_name="fs-server",
        )

        mock_client = MagicMock()
        mock_client.resources = [resource]
        manager.clients["fs-server"] = mock_client

        resources = manager.get_all_resources()
        assert len(resources) == 1
        assert resources[0].uri == "file:///path/to/resource"

    @pytest.mark.asyncio
    async def test_read_resource(self, mock_home):
        """Test reading a resource."""
        manager = MCPManager()

        resource = MCPResource(
            uri="file:///test.txt",
            name="test.txt",
            description="Test file",
            mime_type="text/plain",
            server_name="fs-server",
        )

        mock_client = MagicMock()
        mock_client.resources = [resource]
        mock_client.read_resource = AsyncMock(return_value="file contents")
        manager.clients["fs-server"] = mock_client

        content = await manager.read_resource("file:///test.txt")
        assert content == "file contents"

    @pytest.mark.asyncio
    async def test_read_resource_not_found(self, mock_home):
        """Test reading non-existent resource raises exception."""
        manager = MCPManager()

        with pytest.raises(Exception) as exc_info:
            await manager.read_resource("file:///nonexistent")

        assert "Resource not found" in str(exc_info.value)


class TestMCPManagerConfigMethods:
    """Test MCPManager config management methods."""

    def test_add_server_via_manager(self, mock_home):
        """Test adding server through manager."""
        manager = MCPManager()

        server = manager.add_server(
            name="new-server",
            command="npx",
            args=["-y", "package"],
            env={"KEY": "value"},
        )

        assert server.name == "new-server"
        assert "new-server" in manager.config.servers

    def test_remove_server_via_manager(self, mock_home):
        """Test removing server through manager."""
        manager = MCPManager()
        manager.add_server("to-remove", "echo", [])

        result = manager.remove_server("to-remove")

        assert result is True
        assert "to-remove" not in manager.config.servers

    def test_toggle_server_via_manager(self, mock_home):
        """Test toggling server through manager."""
        manager = MCPManager()
        manager.add_server("toggle-test", "echo", [])

        result = manager.toggle_server("toggle-test")

        assert result is False
        assert manager.config.servers["toggle-test"].enabled is False

    def test_reload_config_via_manager(self, mock_home):
        """Test reloading config through manager."""
        manager = MCPManager()

        # Modify config file
        data = json.loads(manager.config.config_path.read_text())
        data["mcpServers"]["external"] = {
            "command": "external",
            "args": [],
            "enabled": True,
        }
        manager.config.config_path.write_text(json.dumps(data))

        manager.reload_config()

        assert "external" in manager.config.servers
