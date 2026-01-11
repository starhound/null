import json
from pathlib import Path

import pytest

from mcp.config import MCPConfig, MCPServerConfig


class TestMCPServerConfig:
    def test_default_values(self):
        config = MCPServerConfig(name="test", command="npx")
        assert config.name == "test"
        assert config.command == "npx"
        assert config.args == []
        assert config.env == {}
        assert config.enabled is True

    def test_from_dict(self):
        data = {
            "command": "uvx",
            "args": ["mcp-server-test"],
            "env": {"API_KEY": "secret"},
            "enabled": False,
        }
        config = MCPServerConfig.from_dict("my-server", data)
        assert config.name == "my-server"
        assert config.command == "uvx"
        assert config.args == ["mcp-server-test"]
        assert config.env == {"API_KEY": "secret"}
        assert config.enabled is False

    def test_from_dict_defaults(self):
        config = MCPServerConfig.from_dict("minimal", {})
        assert config.name == "minimal"
        assert config.command == ""
        assert config.args == []
        assert config.env == {}
        assert config.enabled is True

    def test_to_dict(self):
        config = MCPServerConfig(
            name="test",
            command="npx",
            args=["-y", "@test/server"],
            env={"TOKEN": "abc"},
            enabled=True,
        )
        result = config.to_dict()
        assert result == {
            "command": "npx",
            "args": ["-y", "@test/server"],
            "env": {"TOKEN": "abc"},
            "enabled": True,
        }
        assert "name" not in result


class TestMCPConfig:
    @pytest.fixture
    def mock_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        (tmp_path / ".null").mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_init_creates_config_file(self, mock_home):
        config = MCPConfig()
        assert config.config_path.exists()
        assert config.servers == {}
        assert config.profiles == {}
        assert config.active_profile is None

    def test_init_loads_existing_config(self, mock_home):
        config_path = mock_home / ".null" / "mcp.json"
        config_data = {
            "mcpServers": {
                "test-server": {
                    "command": "npx",
                    "args": ["-y", "@test/mcp"],
                    "env": {},
                    "enabled": True,
                }
            },
            "profiles": {"dev": ["test-server"]},
            "activeProfile": "dev",
        }
        config_path.write_text(json.dumps(config_data))
        config = MCPConfig()
        assert "test-server" in config.servers
        assert config.servers["test-server"].command == "npx"
        assert config.profiles == {"dev": ["test-server"]}
        assert config.active_profile == "dev"

    def test_save(self, mock_home):
        config = MCPConfig()
        config.servers["new-server"] = MCPServerConfig(
            name="new-server", command="uvx", args=["test"]
        )
        config.save()
        saved_data = json.loads(config.config_path.read_text())
        assert "new-server" in saved_data["mcpServers"]
        assert saved_data["mcpServers"]["new-server"]["command"] == "uvx"

    def test_add_server(self, mock_home):
        config = MCPConfig()
        server = config.add_server(
            name="brave-search",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={"BRAVE_API_KEY": "test"},
        )
        assert server.name == "brave-search"
        assert "brave-search" in config.servers
        saved_data = json.loads(config.config_path.read_text())
        assert "brave-search" in saved_data["mcpServers"]

    def test_remove_server(self, mock_home):
        config = MCPConfig()
        config.add_server("to-remove", "npx", ["-y", "test"])
        assert "to-remove" in config.servers
        result = config.remove_server("to-remove")
        assert result is True
        assert "to-remove" not in config.servers

    def test_remove_server_not_found(self, mock_home):
        config = MCPConfig()
        result = config.remove_server("nonexistent")
        assert result is False

    def test_remove_server_cleans_profiles_list(self, mock_home):
        config = MCPConfig()
        config.add_server("server1", "npx", [])
        config.create_profile("test-profile", ["server1"])
        config.remove_server("server1")
        assert "server1" not in config.profiles["test-profile"]

    def test_remove_server_cleans_profiles_dict(self, mock_home):
        config = MCPConfig()
        config.add_server("server1", "npx", [])
        config.profiles["complex-profile"] = {"servers": ["server1"], "ai": {}}
        config.save()
        config.remove_server("server1")
        assert "server1" not in config.profiles["complex-profile"]["servers"]

    def test_get_enabled_servers_no_profile(self, mock_home):
        config = MCPConfig()
        config.add_server("enabled", "npx", [])
        disabled = config.add_server("disabled", "npx", [])
        disabled.enabled = False
        config.save()
        enabled_servers = config.get_enabled_servers()
        names = [s.name for s in enabled_servers]
        assert "enabled" in names
        assert "disabled" not in names

    def test_get_enabled_servers_with_list_profile(self, mock_home):
        config = MCPConfig()
        config.add_server("server1", "npx", [])
        config.add_server("server2", "npx", [])
        config.create_profile("my-profile", ["server1"])
        config.set_active_profile("my-profile")
        enabled = config.get_enabled_servers()
        names = [s.name for s in enabled]
        assert "server1" in names
        assert "server2" not in names

    def test_get_enabled_servers_with_dict_profile(self, mock_home):
        config = MCPConfig()
        config.add_server("server1", "npx", [])
        config.add_server("server2", "npx", [])
        config.profiles["dict-profile"] = {"servers": ["server2"], "ai": {}}
        config.save()
        config.set_active_profile("dict-profile")
        enabled = config.get_enabled_servers()
        names = [s.name for s in enabled]
        assert "server2" in names
        assert "server1" not in names

    def test_set_active_profile(self, mock_home):
        config = MCPConfig()
        config.profiles["test"] = []
        config.save()
        config.set_active_profile("test")
        assert config.active_profile == "test"

    def test_set_active_profile_none(self, mock_home):
        config = MCPConfig()
        config.profiles["test"] = []
        config.active_profile = "test"
        config.save()
        config.set_active_profile(None)
        assert config.active_profile is None

    def test_set_active_profile_not_found(self, mock_home):
        config = MCPConfig()
        with pytest.raises(ValueError, match="not found"):
            config.set_active_profile("nonexistent")

    def test_create_profile_list(self, mock_home):
        config = MCPConfig()
        config.add_server("server1", "npx", [])
        config.add_server("server2", "npx", [])
        config.create_profile("new-profile", ["server1", "server2"])
        assert "new-profile" in config.profiles
        assert config.profiles["new-profile"] == ["server1", "server2"]

    def test_create_profile_with_ai_config(self, mock_home):
        config = MCPConfig()
        config.add_server("server1", "npx", [])
        config.create_profile(
            "ai-profile",
            ["server1"],
            ai_config={"provider": "openai", "model": "gpt-4"},
        )
        assert config.profiles["ai-profile"]["servers"] == ["server1"]
        assert config.profiles["ai-profile"]["ai"]["provider"] == "openai"

    def test_create_profile_filters_invalid_servers(self, mock_home):
        config = MCPConfig()
        config.add_server("valid", "npx", [])
        config.create_profile("filtered", ["valid", "invalid"])
        assert config.profiles["filtered"] == ["valid"]

    def test_delete_profile(self, mock_home):
        config = MCPConfig()
        config.profiles["to-delete"] = []
        config.save()
        config.delete_profile("to-delete")
        assert "to-delete" not in config.profiles

    def test_delete_active_profile_clears_active(self, mock_home):
        config = MCPConfig()
        config.profiles["active"] = []
        config.active_profile = "active"
        config.save()
        config.delete_profile("active")
        assert config.active_profile is None

    def test_get_active_ai_config_no_profile(self, mock_home):
        config = MCPConfig()
        result = config.get_active_ai_config()
        assert result is None

    def test_get_active_ai_config_list_profile(self, mock_home):
        config = MCPConfig()
        config.profiles["list-profile"] = []
        config.active_profile = "list-profile"
        result = config.get_active_ai_config()
        assert result is None

    def test_get_active_ai_config_dict_profile(self, mock_home):
        config = MCPConfig()
        config.profiles["ai-profile"] = {
            "servers": [],
            "ai": {"provider": "anthropic", "model": "claude-3"},
        }
        config.active_profile = "ai-profile"
        result = config.get_active_ai_config()
        assert result == {"provider": "anthropic", "model": "claude-3"}

    def test_toggle_server_enables(self, mock_home):
        config = MCPConfig()
        server = config.add_server("toggle-test", "npx", [])
        server.enabled = False
        config.save()
        result = config.toggle_server("toggle-test")
        assert result is True
        assert config.servers["toggle-test"].enabled is True

    def test_toggle_server_disables(self, mock_home):
        config = MCPConfig()
        config.add_server("toggle-test", "npx", [])
        result = config.toggle_server("toggle-test")
        assert result is False
        assert config.servers["toggle-test"].enabled is False

    def test_toggle_server_not_found(self, mock_home):
        config = MCPConfig()
        result = config.toggle_server("nonexistent")
        assert result is None
