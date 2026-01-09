"""MCP server management commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from .base import CommandMixin


class MCPCommands(CommandMixin):
    """MCP server management commands."""

    def __init__(self, app: NullApp):
        self.app = app

    async def cmd_mcp(self, args: list[str]):
        """MCP server management."""
        if not args:
            args = ["list"]

        subcommand = args[0]

        if subcommand == "list":
            await self._mcp_list()
        elif subcommand == "catalog":
            await self._mcp_catalog()
        elif subcommand == "tools":
            await self._mcp_tools()
        elif subcommand == "resources":
            await self._mcp_resources()
        elif subcommand == "read" and len(args) >= 2:
            await self._mcp_read(args[1])
        elif subcommand == "add":
            await self._mcp_add()
        elif subcommand == "edit" and len(args) >= 2:
            await self._mcp_edit(args[1])
        elif subcommand == "remove" and len(args) >= 2:
            self._mcp_remove(args[1])
        elif subcommand == "enable" and len(args) >= 2:
            await self._mcp_enable(args[1])
        elif subcommand == "disable" and len(args) >= 2:
            await self._mcp_disable(args[1])
        elif subcommand == "reconnect":
            await self._mcp_reconnect(args[1] if len(args) >= 2 else None)
        else:
            self.notify(
                "Usage: /mcp [list|catalog|tools|add|edit|remove|enable|disable|reconnect]",
                severity="warning",
            )

    async def _mcp_list(self):
        status = self.app.mcp_manager.get_status()
        if not status:
            self.notify(
                "No MCP servers configured. Use /mcp catalog or /mcp add",
                severity="warning",
            )
            return

        lines = []
        for name, info in status.items():
            state = (
                "connected"
                if info["connected"]
                else ("disabled" if not info["enabled"] else "disconnected")
            )
            tools = info["tools"]
            lines.append(f"  {name:20} {state:12} {tools} tools")
        await self.show_output("/mcp list", "\n".join(lines))

    async def _mcp_catalog(self):
        from screens import MCPCatalogScreen

        installed_servers = set(self.app.mcp_manager.config.servers.keys())

        def on_catalog_result(result):
            if not result:
                return

            action = result.get("action")

            if action == "custom":
                self.app.run_worker(self._mcp_add())
            elif action == "install":
                entry = result.get("entry")
                if entry:
                    self._install_from_catalog(entry)

        self.app.push_screen(MCPCatalogScreen(installed_servers), on_catalog_result)

    def _install_from_catalog(self, entry):
        from mcp.catalog import CatalogEntry
        from screens import MCPServerConfigScreen

        if not isinstance(entry, CatalogEntry):
            return

        prefilled = {
            "command": entry.command,
            "args": entry.args,
            "env": {k: "" for k in entry.env_keys},
        }

        def on_config_result(result):
            if result:
                name = result["name"]
                self.app.mcp_manager.add_server(
                    name, result["command"], result["args"], result["env"]
                )
                self.notify(f"Added MCP server: {name}")
                self.app.run_worker(self.app._connect_new_mcp_server(name))

        self.app.push_screen(
            MCPServerConfigScreen(entry.name, prefilled), on_config_result
        )

    async def _mcp_tools(self):
        """List available MCP tools."""
        tools = self.app.mcp_manager.get_all_tools()
        if not tools:
            self.notify("No MCP tools available", severity="warning")
            return

        lines = []
        for tool in tools:
            desc_text = (
                tool.description[:40] + "..."
                if len(tool.description) > 40
                else tool.description
            )
            lines.append(f"  {tool.name:25} {tool.server_name:15} {desc_text}")
        await self.show_output("/mcp tools", "\n".join(lines))

    async def _mcp_resources(self):
        resources = self.app.mcp_manager.get_all_resources()
        if not resources:
            self.notify("No MCP resources available", severity="warning")
            return

        lines = []
        for res in resources:
            lines.append(f"  {res.name:30} {res.uri}")
            if res.description:
                lines.append(f"    {res.description}")

        await self.show_output("/mcp resources", "\n".join(lines))

    async def _mcp_read(self, uri: str):
        try:
            content = await self.app.mcp_manager.read_resource(uri)
            await self.show_output(f"/mcp read {uri}", content)
        except Exception as e:
            self.notify(f"Error reading resource: {e}", severity="error")

    async def _mcp_add(self):
        """Add a new MCP server."""
        from screens import MCPServerConfigScreen

        def on_server_added(result):
            if result:
                name = result["name"]
                self.app.mcp_manager.add_server(
                    name, result["command"], result["args"], result["env"]
                )
                self.notify(f"Added MCP server: {name}")
                self.app.run_worker(self.app._connect_new_mcp_server(name))

        self.app.push_screen(MCPServerConfigScreen(), on_server_added)

    async def _mcp_edit(self, name: str):
        """Edit an MCP server."""
        if name not in self.app.mcp_manager.config.servers:
            self.notify(f"Server not found: {name}", severity="error")
            return

        from screens import MCPServerConfigScreen

        server = self.app.mcp_manager.config.servers[name]
        current = {"command": server.command, "args": server.args, "env": server.env}

        def on_server_edited(result):
            if result:
                server.command = result["command"]
                server.args = result["args"]
                server.env = result["env"]
                self.app.mcp_manager.config.save()
                self.notify(f"Updated MCP server: {name}")
                self.app.run_worker(self.app.mcp_manager.reconnect_server(name))

        self.app.push_screen(MCPServerConfigScreen(name, current), on_server_edited)

    def _mcp_remove(self, name: str):
        """Remove an MCP server."""
        if self.app.mcp_manager.remove_server(name):
            self.notify(f"Removed MCP server: {name}")
        else:
            self.notify(f"Server not found: {name}", severity="error")

    async def _mcp_enable(self, name: str):
        """Enable an MCP server."""
        if name in self.app.mcp_manager.config.servers:
            self.app.mcp_manager.config.servers[name].enabled = True
            self.app.mcp_manager.config.save()
            await self.app.mcp_manager.connect_server(name)
            self.notify(f"Enabled MCP server: {name}")
        else:
            self.notify(f"Server not found: {name}", severity="error")

    async def _mcp_disable(self, name: str):
        """Disable an MCP server."""
        if name in self.app.mcp_manager.config.servers:
            self.app.mcp_manager.config.servers[name].enabled = False
            self.app.mcp_manager.config.save()
            await self.app.mcp_manager.disconnect_server(name)
            self.notify(f"Disabled MCP server: {name}")
        else:
            self.notify(f"Server not found: {name}", severity="error")

    async def _mcp_reconnect(self, name: str | None):
        """Reconnect MCP server(s)."""
        if name:
            if await self.app.mcp_manager.reconnect_server(name):
                self.notify(f"Reconnected: {name}")
            else:
                self.notify(f"Failed to reconnect: {name}", severity="error")
        else:
            await self.app.mcp_manager.disconnect_all()
            await self.app.mcp_manager.initialize()
            tools = self.app.mcp_manager.get_all_tools()
            self.notify(f"Reconnected all servers ({len(tools)} tools)")

    async def cmd_tools_ui(self, args: list[str]):
        """Open MCP Tools UI."""
        from screens import ToolsScreen

        self.app.push_screen(ToolsScreen())
