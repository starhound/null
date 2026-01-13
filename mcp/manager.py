"""MCP Manager - manages multiple MCP server connections."""

import asyncio
from collections.abc import Callable
from typing import Any

from .client import MCPClient, MCPResource, MCPTool
from .config import MCPConfig, MCPServerConfig
from .health_check import HealthStatus, MCPHealthChecker, ServerHealth
from .request_dedup import RequestDeduplicator


class MCPManager:
    """Manages multiple MCP server connections."""

    def __init__(
        self,
        on_reconnect_attempt: Callable[[str, int, float], None] | None = None,
        on_reconnect_success: Callable[[str], None] | None = None,
        on_reconnect_failed: Callable[[str, int], None] | None = None,
        dedup_enabled: bool = True,
        dedup_window: float = 1.0,
    ):
        self.config = MCPConfig()
        self.clients: dict[str, MCPClient] = {}
        self._initialized = False
        self.deduplicator = RequestDeduplicator(
            enabled=dedup_enabled, dedup_window=dedup_window
        )

        self._on_reconnect_attempt = on_reconnect_attempt
        self._on_reconnect_success = on_reconnect_success
        self._on_reconnect_failed = on_reconnect_failed

        self._health_checker: MCPHealthChecker | None = None
        self._on_health_change: (
            Callable[[str, HealthStatus, HealthStatus], None] | None
        ) = None

    @property
    def health_checker(self) -> MCPHealthChecker | None:
        return self._health_checker

    def set_health_change_callback(
        self, callback: Callable[[str, HealthStatus, HealthStatus], None] | None
    ):
        self._on_health_change = callback

    async def initialize(self):
        """Initialize and connect to all enabled MCP servers in parallel."""
        if self._initialized:
            return

        enabled_servers = self.config.get_enabled_servers()
        if not enabled_servers:
            self._initialized = True
            return

        # Connect to all servers concurrently
        tasks = []
        for server in enabled_servers:
            tasks.append(self.connect_server(server.name))

        await asyncio.gather(*tasks)
        self._initialized = True

    async def start_health_checks(self, check_interval: float = 30.0):
        if self._health_checker:
            await self._health_checker.stop()

        self._health_checker = MCPHealthChecker(
            manager=self,
            check_interval=check_interval,
            on_status_change=self._on_health_change,
        )
        await self._health_checker.start()

    async def stop_health_checks(self):
        if self._health_checker:
            await self._health_checker.stop()
            self._health_checker = None

    def get_server_health(self, name: str) -> ServerHealth | None:
        if self._health_checker:
            return self._health_checker.get_health(name)
        return None

    def get_all_server_health(self) -> dict[str, ServerHealth]:
        if self._health_checker:
            return self._health_checker.get_all_health()
        return {}

    async def connect_server(self, name: str) -> bool:
        """Connect to a specific server."""
        if name in self.clients:
            # Already connected
            return self.clients[name].is_connected

        if name not in self.config.servers:
            return False

        server_config = self.config.servers[name]
        if not server_config.enabled:
            return False

        client = MCPClient(
            server_config,
            on_reconnect_attempt=self._on_reconnect_attempt,
            on_reconnect_success=self._on_reconnect_success,
            on_reconnect_failed=self._on_reconnect_failed,
        )
        success = await client.connect()

        if success:
            self.clients[name] = client
            return True

        return False

    async def disconnect_server(self, name: str):
        """Disconnect from a specific server (cancels any pending reconnection)."""
        if name in self.clients:
            self.clients[name].cancel_reconnect()
            await self.clients[name].disconnect()
            del self.clients[name]

    async def disconnect_all(self):
        """Disconnect from all servers."""
        await self.stop_health_checks()
        for name in list(self.clients.keys()):
            await self.disconnect_server(name)
        self._initialized = False

    async def reconnect_server(self, name: str) -> bool:
        """Reconnect to a server."""
        await self.disconnect_server(name)
        return await self.connect_server(name)

    def get_all_tools(self) -> list[MCPTool]:
        """Get all available tools from all connected servers."""
        tools = []
        for client in self.clients.values():
            tools.extend(client.tools)
        return tools

    def get_all_resources(self) -> list[MCPResource]:
        """Get all available resources from all connected servers."""
        resources = []
        for client in self.clients.values():
            resources.extend(client.resources)
        return resources

    def get_tool(self, name: str) -> MCPTool | None:
        """Find a tool by name."""
        for client in self.clients.values():
            for tool in client.tools:
                if tool.name == name:
                    return tool
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool by name."""
        hit, cached_result = await self.deduplicator.get_cached(tool_name, arguments)
        if hit:
            return cached_result

        tool = self.get_tool(tool_name)
        if not tool:
            raise Exception(f"Tool not found: {tool_name}")

        client = self.clients.get(tool.server_name)
        if not client or not client.is_connected:
            raise Exception(f"Server not connected: {tool.server_name}")

        result = await client.call_tool(tool_name, arguments)
        await self.deduplicator.cache_result(tool_name, arguments, result)
        return result

    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI."""
        # Find the server that has this resource
        for client in self.clients.values():
            for resource in client.resources:
                if resource.uri == uri:
                    return await client.read_resource(uri)

        raise Exception(f"Resource not found: {uri}")

    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Get tool schemas in format suitable for LLM tool use."""
        tools = []
        for tool in self.get_all_tools():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
            )
        return tools

    def get_status(self) -> dict[str, Any]:
        """Get status of all configured servers."""
        status = {}
        for name, server in self.config.servers.items():
            client = self.clients.get(name)
            status[name] = {
                "enabled": server.enabled,
                "connected": client.is_connected if client else False,
                "tools": len(client.tools) if client else 0,
                "resources": len(client.resources) if client else 0,
                "command": server.command,
            }
        return status

    # Config management methods
    def add_server(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> MCPServerConfig:
        """Add a new MCP server."""
        return self.config.add_server(name, command, args, env)

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server."""
        # Disconnect first if connected
        if name in self.clients:
            # Store task reference to prevent garbage collection
            self._disconnect_task = asyncio.create_task(self.disconnect_server(name))
        return self.config.remove_server(name)

    def toggle_server(self, name: str) -> bool | None:
        """Toggle server enabled state."""
        return self.config.toggle_server(name)

    def reload_config(self):
        """Reload configuration from file."""
        self.config.load()
