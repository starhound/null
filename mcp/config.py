"""MCP configuration management."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "MCPServerConfig":
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            enabled=data.get("enabled", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "enabled": self.enabled,
        }


class MCPConfig:
    DEFAULT_CONFIG: ClassVar[dict[str, Any]] = {
        "mcpServers": {},
        "profiles": {},
        "activeProfile": None,
    }

    def __init__(self):
        self.config_path = Path.home() / ".null" / "mcp.json"
        self.servers: dict[str, MCPServerConfig] = {}
        self.profiles: dict[str, Any] = {}
        self.active_profile: str | None = None
        self._ensure_config_exists()
        self.load()

    def _ensure_config_exists(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            self.config_path.write_text(
                json.dumps(self.DEFAULT_CONFIG, indent=2), encoding="utf-8"
            )

    def load(self):
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.servers = {}
            self.profiles = data.get("profiles", {})
            self.active_profile = data.get("activeProfile")

            for name, server_data in data.get("mcpServers", {}).items():
                self.servers[name] = MCPServerConfig.from_dict(name, server_data)

        except Exception as e:
            print(f"Error loading MCP config: {e}")
            self.servers = {}
            self.profiles = {}
            self.active_profile = None

    def save(self):
        data = {
            "mcpServers": {
                name: server.to_dict() for name, server in self.servers.items()
            },
            "profiles": self.profiles,
            "activeProfile": self.active_profile,
        }
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_server(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> MCPServerConfig:
        server = MCPServerConfig(
            name=name, command=command, args=args or [], env=env or {}, enabled=True
        )
        self.servers[name] = server
        self.save()
        return server

    def remove_server(self, name: str) -> bool:
        if name in self.servers:
            del self.servers[name]
            for profile in self.profiles.values():
                if isinstance(profile, list):
                    if name in profile:
                        profile.remove(name)
                elif isinstance(profile, dict) and "servers" in profile:
                    if name in profile["servers"]:
                        profile["servers"].remove(name)
            self.save()
            return True
        return False

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        if self.active_profile and self.active_profile in self.profiles:
            profile_data = self.profiles[self.active_profile]
            if isinstance(profile_data, list):
                profile_servers = set(profile_data)
            else:
                profile_servers = set(profile_data.get("servers", []))

            return [
                s
                for s in self.servers.values()
                if s.enabled and s.name in profile_servers
            ]

        return [s for s in self.servers.values() if s.enabled]

    def set_active_profile(self, profile_name: str | None):
        if profile_name and profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' not found")
        self.active_profile = profile_name
        self.save()

    def create_profile(
        self, name: str, servers: list[str], ai_config: dict[str, str] | None = None
    ):
        valid_servers = [s for s in servers if s in self.servers]
        if ai_config:
            self.profiles[name] = {"servers": valid_servers, "ai": ai_config}
        else:
            self.profiles[name] = valid_servers
        self.save()

    def delete_profile(self, name: str):
        if name in self.profiles:
            del self.profiles[name]
            if self.active_profile == name:
                self.active_profile = None
            self.save()

    def get_active_ai_config(self) -> dict[str, str] | None:
        if not self.active_profile or self.active_profile not in self.profiles:
            return None

        profile_data = self.profiles[self.active_profile]
        if isinstance(profile_data, dict) and "ai" in profile_data:
            return profile_data["ai"]
        return None

    def toggle_server(self, name: str) -> bool | None:
        """Toggle server enabled state. Returns new state or None if not found."""
        if name in self.servers:
            self.servers[name].enabled = not self.servers[name].enabled
            self.save()
            return self.servers[name].enabled
        return None
