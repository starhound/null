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
    """Manages MCP configuration from ~/.null/mcp.json"""

    DEFAULT_CONFIG: ClassVar[dict[str, Any]] = {"mcpServers": {}}

    def __init__(self):
        self.config_path = Path.home() / ".null" / "mcp.json"
        self.servers: dict[str, MCPServerConfig] = {}
        self._ensure_config_exists()
        self.load()

    def _ensure_config_exists(self):
        """Create default config if it doesn't exist."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            self.config_path.write_text(
                json.dumps(self.DEFAULT_CONFIG, indent=2), encoding="utf-8"
            )

    def load(self):
        """Load configuration from file."""
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.servers = {}

            for name, server_data in data.get("mcpServers", {}).items():
                self.servers[name] = MCPServerConfig.from_dict(name, server_data)

        except Exception as e:
            print(f"Error loading MCP config: {e}")
            self.servers = {}

    def save(self):
        """Save configuration to file."""
        data = {
            "mcpServers": {
                name: server.to_dict() for name, server in self.servers.items()
            }
        }
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_server(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> MCPServerConfig:
        """Add a new MCP server configuration."""
        server = MCPServerConfig(
            name=name, command=command, args=args or [], env=env or {}, enabled=True
        )
        self.servers[name] = server
        self.save()
        return server

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server configuration."""
        if name in self.servers:
            del self.servers[name]
            self.save()
            return True
        return False

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        """Get list of enabled servers."""
        return [s for s in self.servers.values() if s.enabled]

    def toggle_server(self, name: str) -> bool | None:
        """Toggle server enabled state. Returns new state or None if not found."""
        if name in self.servers:
            self.servers[name].enabled = not self.servers[name].enabled
            self.save()
            return self.servers[name].enabled
        return None
