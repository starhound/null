"""Unit tests for MCP client, config, and manager modules."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp.client import MCPClient, MCPResource, MCPTool
from mcp.config import MCPConfig, MCPServerConfig
from mcp.manager import MCPManager


# =============================================================================
# MCPServerConfig Tests
# =============================================================================


class TestMCPServerConfig:
    """Tests for MCPServerConfig dataclass."""

    def test_from_dict_basic(self):
        """Test creating config from dict with basic fields."""
        data = {"command": "npx", "args": ["-y", "mcp-server"], "enabled": True}
        config = MCPServerConfig.from_dict("test-server", data)

        assert config.name == "test-server"
        assert config.command == "npx"
        assert config.args == ["-y", "mcp-server"]
        assert config.enabled is True
        assert config.env == {}

    def test_from_dict_with_env(self):
        """Test creating config with environment variables."""
        data = {
            "command": "node",
            "args": ["server.js"],
            "env": {"API_KEY": "secret"},
            "enabled": False,
        }
        config = MCPServerConfig.from_dict("env-server", data)

        assert config.env == {"API_KEY": "secret"}
        assert config.enabled is False

    def test_from_dict_defaults(self):
        """Test that missing fields use defaults."""
        config = MCPServerConfig.from_dict("empty", {})

        assert config.command == ""
        assert config.args == []
        assert config.env == {}
        assert config.enabled is True

    def test_to_dict(self):
        """Test converting config back to dict."""
        config = MCPServerConfig(
            name="test",
            command="python",
            args=["-m", "server"],
            env={"KEY": "val"},
            enabled=True,
        )
        result = config.to_dict()

        assert result == {
            "command": "python",
            "args": ["-m", "server"],
            "env": {"KEY": "val"},
            "enabled": True,
        }


# =============================================================================
# MCPConfig Tests
# =============================================================================


class TestMCPConfig:
    """Tests for MCPConfig class."""

    def test_init_creates_config_file(self, mock_home):
        """Test that init creates config file if not exists."""
        config = MCPConfig()
        config_path = mock_home / ".null" / "mcp.json"

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert "mcpServers" in data

    def test_load_existing_config(self, mock_home):
        """Test loading existing configuration."""
        config_path = mock_home / ".null" / "mcp.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "brave": {
                            "command": "npx",
                            "args": ["-y", "brave"],
                            "enabled": True,
                        }
                    },
                    "profiles": {},
                    "activeProfile": None,
                }
            )
        )

        config = MCPConfig()

        assert "brave" in config.servers
        assert config.servers["brave"].command == "npx"

    def test_add_server(self, mock_home):
        """Test adding a new server."""
        config = MCPConfig()
        server = config.add_server("test", "node", ["server.js"], {"KEY": "val"})

        assert server.name == "test"
        assert "test" in config.servers

        # Verify saved to file
        data = json.loads((mock_home / ".null" / "mcp.json").read_text())
        assert "test" in data["mcpServers"]

    def test_remove_server(self, mock_home):
        """Test removing a server."""
        config = MCPConfig()
        config.add_server("removeme", "cmd")

        result = config.remove_server("removeme")

        assert result is True
        assert "removeme" not in config.servers

    def test_remove_nonexistent_server(self, mock_home):
        """Test removing a server that doesn't exist."""
        config = MCPConfig()
        result = config.remove_server("nonexistent")

        assert result is False

    def test_get_enabled_servers(self, mock_home):
        """Test getting only enabled servers."""
        config = MCPConfig()
        config.add_server("enabled", "cmd1")
        config.add_server("disabled", "cmd2")
        config.servers["disabled"].enabled = False
        config.save()

        enabled = config.get_enabled_servers()

        assert len(enabled) == 1
        assert enabled[0].name == "enabled"

    def test_toggle_server(self, mock_home):
        """Test toggling server enabled state."""
        config = MCPConfig()
        config.add_server("toggleme", "cmd")

        result = config.toggle_server("toggleme")

        assert result is False  # Was True, now False
        assert config.servers["toggleme"].enabled is False

    def test_toggle_nonexistent_server(self, mock_home):
        """Test toggling nonexistent server returns None."""
        config = MCPConfig()
        result = config.toggle_server("nonexistent")

        assert result is None

    def test_create_profile(self, mock_home):
        """Test creating a profile."""
        config = MCPConfig()
        config.add_server("server1", "cmd1")
        config.add_server("server2", "cmd2")

        config.create_profile("dev", ["server1", "server2"])

        assert "dev" in config.profiles
        assert config.profiles["dev"] == ["server1", "server2"]

    def test_create_profile_with_ai_config(self, mock_home):
        """Test creating a profile with AI configuration."""
        config = MCPConfig()
        config.add_server("server1", "cmd1")

        config.create_profile(
            "work", ["server1"], {"provider": "openai", "model": "gpt-4"}
        )

        assert config.profiles["work"]["servers"] == ["server1"]
        assert config.profiles["work"]["ai"]["provider"] == "openai"

    def test_set_active_profile(self, mock_home):
        """Test setting active profile."""
        config = MCPConfig()
        config.add_server("s1", "cmd")
        config.create_profile("test", ["s1"])

        config.set_active_profile("test")

        assert config.active_profile == "test"

    def test_set_invalid_profile_raises(self, mock_home):
        """Test setting invalid profile raises ValueError."""
        config = MCPConfig()

        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            config.set_active_profile("nonexistent")

    def test_delete_profile(self, mock_home):
        """Test deleting a profile."""
        config = MCPConfig()
        config.add_server("s1", "cmd")
        config.create_profile("deleteme", ["s1"])
        config.set_active_profile("deleteme")

        config.delete_profile("deleteme")

        assert "deleteme" not in config.profiles
        assert config.active_profile is None

    def test_get_active_ai_config(self, mock_home):
        """Test getting AI config from active profile."""
        config = MCPConfig()
        config.add_server("s1", "cmd")
        config.create_profile("ai_profile", ["s1"], {"provider": "anthropic"})
        config.set_active_profile("ai_profile")

        ai_config = config.get_active_ai_config()

        assert ai_config == {"provider": "anthropic"}

    def test_get_active_ai_config_no_profile(self, mock_home):
        """Test getting AI config when no profile active."""
        config = MCPConfig()
        result = config.get_active_ai_config()

        assert result is None


# =============================================================================
# MCPClient Tests
# =============================================================================


class TestMCPClient:
    """Tests for MCPClient class."""

    @pytest.fixture
    def server_config(self):
        """Create a test server config."""
        return MCPServerConfig(
            name="test-server",
            command="echo",
            args=["test"],
            env={},
            enabled=True,
        )

    @pytest.fixture
    def mock_process(self):
        """Create a mock subprocess."""
        process = MagicMock()
        process.stdin = MagicMock()
        process.stdin.write = MagicMock()
        process.stdin.drain = AsyncMock()
        process.stdout = MagicMock()
        process.stdout.readline = AsyncMock()
        process.stderr = MagicMock()
        process.terminate = MagicMock()
        process.kill = MagicMock()
        process.wait = AsyncMock()
        return process

    def test_init(self, server_config):
        """Test client initialization."""
        client = MCPClient(server_config)

        assert client.config == server_config
        assert client.process is None
        assert client.tools == []
        assert client.resources == []
        assert client.is_connected is False

    def test_is_connected_false_when_no_process(self, server_config):
        """Test is_connected is False when no process."""
        client = MCPClient(server_config)
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_starts_process(self, server_config):
        """Test that connect attempts to start subprocess."""
        client = MCPClient(server_config)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("echo not found")
            result = await client.connect()

        assert result is False
        mock_exec.assert_called_once()
        assert server_config.command in mock_exec.call_args[0]

    @pytest.mark.asyncio
    async def test_connect_failure(self, server_config):
        """Test connection failure."""
        client = MCPClient(server_config)

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=Exception("Connection failed"),
        ):
            result = await client.connect()

        assert result is False
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self, server_config, mock_process):
        """Test disconnection."""
        client = MCPClient(server_config)
        client.process = mock_process
        client._connected = True
        client._read_task = asyncio.create_task(asyncio.sleep(100))

        await client.disconnect()

        assert client.process is None
        assert client._connected is False
        assert client.tools == []

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, server_config):
        """Test calling tool when not connected raises exception."""
        client = MCPClient(server_config)

        with pytest.raises(Exception, match="Not connected"):
            await client.call_tool("test", {})

    @pytest.mark.asyncio
    async def test_call_tool_success(self, server_config, mock_process):
        """Test successful tool call."""
        client = MCPClient(server_config)
        client.process = mock_process
        client._connected = True

        tool_response = (
            json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"text": "result"}]}}
            ).encode()
            + b"\n"
        )

        call_count = 0

        async def mock_readline():
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return tool_response
            await asyncio.sleep(10)
            return b""

        mock_process.stdout.readline = mock_readline

        client._read_task = asyncio.create_task(client._read_loop())

        result = await client.call_tool("search", {"query": "test"})

        assert result == {"content": [{"text": "result"}]}

        client._read_task.cancel()
        try:
            await client._read_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_read_resource_not_connected(self, server_config):
        """Test reading resource when not connected raises exception."""
        client = MCPClient(server_config)

        with pytest.raises(Exception, match="Not connected"):
            await client.read_resource("file:///test")

    def test_cancel_reconnect(self, server_config):
        """Test canceling reconnection attempts."""
        client = MCPClient(server_config)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        client._reconnect_task = mock_task
        client._reconnect_attempts = 3

        client.cancel_reconnect()

        mock_task.cancel.assert_called_once()
        assert client._reconnect_task is None
        assert client._reconnect_attempts == 0


# =============================================================================
# MCPTool & MCPResource Tests
# =============================================================================


class TestMCPDataclasses:
    """Tests for MCP dataclasses."""

    def test_mcp_tool_creation(self):
        """Test MCPTool dataclass."""
        tool = MCPTool(
            name="search",
            description="Search the web",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            server_name="brave",
        )

        assert tool.name == "search"
        assert tool.description == "Search the web"
        assert tool.server_name == "brave"

    def test_mcp_resource_creation(self):
        """Test MCPResource dataclass."""
        resource = MCPResource(
            uri="file:///test.txt",
            name="test.txt",
            description="Test file",
            mime_type="text/plain",
            server_name="filesystem",
        )

        assert resource.uri == "file:///test.txt"
        assert resource.mime_type == "text/plain"


# =============================================================================
# MCPManager Tests
# =============================================================================


class TestMCPManager:
    """Tests for MCPManager class."""

    @pytest.fixture
    def mock_mcp_config(self, mock_home):
        """Create manager with mocked config."""
        manager = MCPManager()
        return manager

    def test_init(self, mock_mcp_config):
        """Test manager initialization."""
        assert mock_mcp_config.clients == {}
        assert mock_mcp_config._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_no_servers(self, mock_mcp_config):
        """Test initialization with no enabled servers."""
        await mock_mcp_config.initialize()

        assert mock_mcp_config._initialized is True
        assert mock_mcp_config.clients == {}

    @pytest.mark.asyncio
    async def test_initialize_with_servers(self, mock_home):
        """Test initialization connects to enabled servers."""
        # Add a server to config
        config_path = mock_home / ".null" / "mcp.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "test": {"command": "echo", "args": [], "enabled": True}
                    },
                    "profiles": {},
                    "activeProfile": None,
                }
            )
        )

        manager = MCPManager()

        with patch.object(
            manager, "connect_server", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = True
            await manager.initialize()

        mock_connect.assert_called_once_with("test")
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_connect_server_not_in_config(self, mock_mcp_config):
        """Test connecting to server not in config."""
        result = await mock_mcp_config.connect_server("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_connect_server_already_connected(self, mock_home):
        """Test connecting to already connected server."""
        manager = MCPManager()
        manager.config.add_server("test", "echo")

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
        mock_client.cancel_reconnect = MagicMock()
        manager.clients["test"] = mock_client

        await manager.disconnect_server("test")

        mock_client.cancel_reconnect.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert "test" not in manager.clients

    @pytest.mark.asyncio
    async def test_disconnect_all(self, mock_home):
        """Test disconnecting from all servers."""
        manager = MCPManager()

        mock_client1 = MagicMock()
        mock_client1.disconnect = AsyncMock()
        mock_client1.cancel_reconnect = MagicMock()
        mock_client2 = MagicMock()
        mock_client2.disconnect = AsyncMock()
        mock_client2.cancel_reconnect = MagicMock()

        manager.clients["server1"] = mock_client1
        manager.clients["server2"] = mock_client2
        manager._initialized = True

        await manager.disconnect_all()

        assert manager.clients == {}
        assert manager._initialized is False

    def test_get_all_tools(self, mock_home):
        """Test getting all tools from all clients."""
        manager = MCPManager()

        mock_client1 = MagicMock()
        mock_client1.tools = [
            MCPTool("tool1", "desc1", {}, "server1"),
            MCPTool("tool2", "desc2", {}, "server1"),
        ]
        mock_client2 = MagicMock()
        mock_client2.tools = [MCPTool("tool3", "desc3", {}, "server2")]

        manager.clients["server1"] = mock_client1
        manager.clients["server2"] = mock_client2

        tools = manager.get_all_tools()

        assert len(tools) == 3
        assert tools[0].name == "tool1"
        assert tools[2].name == "tool3"

    def test_get_all_resources(self, mock_home):
        """Test getting all resources from all clients."""
        manager = MCPManager()

        mock_client = MagicMock()
        mock_client.resources = [
            MCPResource("uri1", "name1", "desc1", "text/plain", "server1")
        ]
        manager.clients["server1"] = mock_client

        resources = manager.get_all_resources()

        assert len(resources) == 1
        assert resources[0].uri == "uri1"

    def test_get_tool_found(self, mock_home):
        """Test finding a tool by name."""
        manager = MCPManager()

        tool = MCPTool("search", "Search", {}, "brave")
        mock_client = MagicMock()
        mock_client.tools = [tool]
        manager.clients["brave"] = mock_client

        result = manager.get_tool("search")

        assert result == tool

    def test_get_tool_not_found(self, mock_home):
        """Test finding a tool that doesn't exist."""
        manager = MCPManager()

        result = manager.get_tool("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_home):
        """Test calling a tool successfully."""
        manager = MCPManager()

        tool = MCPTool("search", "Search", {}, "brave")
        mock_client = MagicMock()
        mock_client.tools = [tool]
        mock_client.is_connected = True
        mock_client.call_tool = AsyncMock(return_value={"result": "data"})
        manager.clients["brave"] = mock_client

        result = await manager.call_tool("search", {"query": "test"})

        assert result == {"result": "data"}
        mock_client.call_tool.assert_called_once_with("search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mock_home):
        """Test calling tool that doesn't exist raises exception."""
        manager = MCPManager()

        with pytest.raises(Exception, match="Tool not found"):
            await manager.call_tool("nonexistent", {})

    @pytest.mark.asyncio
    async def test_call_tool_server_not_connected(self, mock_home):
        """Test calling tool when server not connected raises exception."""
        manager = MCPManager()

        tool = MCPTool("search", "Search", {}, "brave")
        mock_client = MagicMock()
        mock_client.tools = [tool]
        mock_client.is_connected = False
        manager.clients["brave"] = mock_client

        with pytest.raises(Exception, match="Server not connected"):
            await manager.call_tool("search", {})

    @pytest.mark.asyncio
    async def test_read_resource_success(self, mock_home):
        """Test reading a resource successfully."""
        manager = MCPManager()

        resource = MCPResource("file:///test", "test", "desc", "text/plain", "fs")
        mock_client = MagicMock()
        mock_client.resources = [resource]
        mock_client.read_resource = AsyncMock(return_value="file content")
        manager.clients["fs"] = mock_client

        result = await manager.read_resource("file:///test")

        assert result == "file content"

    @pytest.mark.asyncio
    async def test_read_resource_not_found(self, mock_home):
        """Test reading resource that doesn't exist raises exception."""
        manager = MCPManager()

        with pytest.raises(Exception, match="Resource not found"):
            await manager.read_resource("file:///nonexistent")

    def test_get_tools_schema(self, mock_home):
        """Test getting tools schema for LLM."""
        manager = MCPManager()

        tool = MCPTool("search", "Search the web", {"type": "object"}, "brave")
        mock_client = MagicMock()
        mock_client.tools = [tool]
        manager.clients["brave"] = mock_client

        schema = manager.get_tools_schema()

        assert len(schema) == 1
        assert schema[0]["name"] == "search"
        assert schema[0]["description"] == "Search the web"
        assert schema[0]["input_schema"] == {"type": "object"}

    def test_get_status(self, mock_home):
        """Test getting status of all servers."""
        manager = MCPManager()
        manager.config.add_server("connected", "cmd1")
        manager.config.add_server("disconnected", "cmd2")

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.tools = [MCPTool("t1", "", {}, "connected")]
        mock_client.resources = []
        manager.clients["connected"] = mock_client

        status = manager.get_status()

        assert status["connected"]["connected"] is True
        assert status["connected"]["tools"] == 1
        assert status["disconnected"]["connected"] is False
        assert status["disconnected"]["tools"] == 0

    def test_add_server_via_manager(self, mock_home):
        """Test adding server through manager."""
        manager = MCPManager()

        server = manager.add_server("new", "node", ["server.js"], {"KEY": "val"})

        assert server.name == "new"
        assert "new" in manager.config.servers

    def test_remove_server_via_manager(self, mock_home):
        """Test removing server through manager."""
        manager = MCPManager()
        manager.config.add_server("removeme", "cmd")

        result = manager.remove_server("removeme")

        assert result is True
        assert "removeme" not in manager.config.servers

    def test_toggle_server_via_manager(self, mock_home):
        """Test toggling server through manager."""
        manager = MCPManager()
        manager.config.add_server("toggleme", "cmd")

        result = manager.toggle_server("toggleme")

        assert result is False  # Was True, now False

    def test_reload_config(self, mock_home):
        """Test reloading configuration."""
        manager = MCPManager()

        # Modify config file directly
        config_path = mock_home / ".null" / "mcp.json"
        data = json.loads(config_path.read_text())
        data["mcpServers"]["new_server"] = {"command": "test", "enabled": True}
        config_path.write_text(json.dumps(data))

        manager.reload_config()

        assert "new_server" in manager.config.servers

    @pytest.mark.asyncio
    async def test_reconnect_server(self, mock_home):
        """Test reconnecting to a server."""
        manager = MCPManager()
        manager.config.add_server("test", "echo")

        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        mock_client.cancel_reconnect = MagicMock()
        manager.clients["test"] = mock_client

        with patch.object(
            manager, "connect_server", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = True
            result = await manager.reconnect_server("test")

        assert result is True
        mock_client.disconnect.assert_called_once()
        mock_connect.assert_called_once_with("test")

    def test_reconnect_callbacks(self, mock_home):
        """Test that reconnect callbacks are passed to clients."""
        on_attempt = MagicMock()
        on_success = MagicMock()
        on_failed = MagicMock()

        manager = MCPManager(
            on_reconnect_attempt=on_attempt,
            on_reconnect_success=on_success,
            on_reconnect_failed=on_failed,
        )

        assert manager._on_reconnect_attempt == on_attempt
        assert manager._on_reconnect_success == on_success
        assert manager._on_reconnect_failed == on_failed
