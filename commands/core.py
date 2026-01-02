"""Core commands: help, status, clear, quit."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from .base import CommandMixin
from widgets import HistoryViewport, StatusBar


class CoreCommands(CommandMixin):
    """Core application commands."""

    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_help(self, args: list[str]):
        """Show help screen."""
        from screens import HelpScreen
        self.app.push_screen(HelpScreen())

    async def cmd_status(self, args: list[str]):
        """Show current status."""
        from context import ContextManager

        provider_name = self.app.config.get("ai", {}).get("provider", "none")
        
        # Get model from actual provider instance (most accurate)
        if self.app.ai_provider and self.app.ai_provider.model:
            model = self.app.ai_provider.model
        else:
            # Fallback to config
            from config import Config
            model = Config.get(f"ai.{provider_name}.model") or "none"
        
        persona = self.app.config.get("ai", {}).get("active_prompt", "default")
        blocks_count = len(self.app.blocks)

        context_str = ContextManager.get_context(self.app.blocks)
        context_chars = len(context_str)
        context_tokens = context_chars // 4

        status_bar = self.app.query_one("#status-bar", StatusBar)
        provider_status = status_bar.provider_status

        # Token usage info
        total_tokens = status_bar.session_input_tokens + status_bar.session_output_tokens
        session_cost = status_bar.session_cost

        lines = [
            f"  Provider:      {provider_name} ({provider_status})",
            f"  Model:         {model}",
            f"  Persona:       {persona}",
            f"  Blocks:        {blocks_count}",
            f"  Context:       ~{context_tokens} tokens ({context_chars} chars)",
            f"  Session Tokens: {total_tokens:,} ({status_bar.session_input_tokens:,} in / {status_bar.session_output_tokens:,} out)",
            f"  Session Cost:   ${session_cost:.4f}",
        ]
        await self.show_output("/status", "\n".join(lines))

    async def cmd_clear(self, args: list[str]):
        """Clear history and context."""
        self.app.blocks = []
        self.app.current_cli_block = None
        self.app.current_cli_widget = None
        history = self.app.query_one("#history", HistoryViewport)
        await history.remove_children()

        # Reset token usage in status bar
        status_bar = self.app.query_one("#status-bar", StatusBar)
        status_bar.reset_token_usage()

        self.app._update_status_bar()
        self.notify("History and context cleared")

    async def cmd_quit(self, args: list[str]):
        """Quit the application."""
        self.app.exit()

    async def cmd_exit(self, args: list[str]):
        """Exit the application (alias)."""
        self.app.exit()

    async def cmd_ssh(self, args: list[str]):
        """Connect to an SSH host: /ssh <alias>"""
        if not args:
            self.notify("Usage: /ssh <alias>", severity="error")
            return

        alias = args[0]
        host_config = self.app.storage.get_ssh_host(alias)
        
        if not host_config:
            self.notify(f"Unknown host alias: {alias}", severity="error")
            return

        from utils.ssh_client import SSHSession
        from screens.ssh import SSHScreen
        
        session = SSHSession(
            hostname=host_config['hostname'],
            port=host_config['port'],
            username=host_config['username'],
            password=host_config['password'],
            key_path=host_config['key_path']
        )
        
        self.app.push_screen(SSHScreen(session, alias))

    async def cmd_ssh_add(self, args: list[str]):
        """Add SSH host: /ssh-add <alias> <host> <user> [port]"""
        if len(args) < 3:
            self.notify("Usage: /ssh-add <alias> <host> <user> [port] [key_path]", severity="error")
            return

        alias = args[0]
        hostname = args[1]
        username = args[2]
        port = int(args[3]) if len(args) > 3 else 22
        key_path = args[4] if len(args) > 4 else None
        
        # Password usually requires secure prompt, for now we add without password 
        # or rely on key. User can use config command later to set password if we implement it.
        # OR we could accept password as arg but that's insecure in history.
        # Prefer key auth.
        
        self.app.storage.add_ssh_host(alias, hostname, port, username, key_path)
        self.notify(f"Added SSH host: {alias}")

    async def cmd_ssh_list(self, args: list[str]):
        """List saved SSH hosts."""
        hosts = self.app.storage.list_ssh_hosts()
        if not hosts:
            self.notify("No SSH hosts saved.")
            return

        lines = [f"SSH Hosts:", "----------"]
        for h in hosts:
            lines.append(f"{h['alias']}: {h['username']}@{h['hostname']}:{h['port']}")
            
        await self.show_output("/ssh-list", "\n".join(lines))

    async def cmd_ssh_del(self, args: list[str]):
        """Delete SSH host: /ssh-del <alias>"""
        if not args:
            self.notify("Usage: /ssh-del <alias>", severity="error")
            return
            
        alias = args[0]
        self.app.storage.delete_ssh_host(alias)
        self.notify(f"Deleted SSH host: {alias}")
