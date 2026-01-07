"""Core commands: help, status, clear, quit."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from widgets import HistoryViewport, StatusBar

from .base import CommandMixin


class CoreCommands(CommandMixin):
    """Core application commands."""

    def __init__(self, app: NullApp):
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
        total_tokens = (
            status_bar.session_input_tokens + status_bar.session_output_tokens
        )
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

        from screens.ssh import SSHScreen
        from utils.ssh_client import SSHSession

        # Resolve jump host if configured
        tunnel_session = None
        jump_alias = host_config.get("jump_host")

        if jump_alias:
            jump_config = self.app.storage.get_ssh_host(jump_alias)
            if not jump_config:
                self.notify(
                    f"Jump host alias not found: {jump_alias}", severity="error"
                )
                return

            tunnel_session = SSHSession(
                hostname=jump_config["hostname"],
                port=jump_config["port"],
                username=jump_config["username"],
                password=jump_config["password"],
                key_path=jump_config["key_path"],
            )

        session = SSHSession(
            hostname=host_config["hostname"],
            port=host_config["port"],
            username=host_config["username"],
            password=host_config["password"],
            key_path=host_config["key_path"],
            tunnel=tunnel_session,
        )

        self.app.push_screen(SSHScreen(session, alias))

    async def cmd_ssh_add(self, args: list[str]):
        """Add SSH host: /ssh-add [alias host user port key] or interactive form."""
        if not args:
            # Show interactive form
            from screens.ssh_add import SSHAddScreen

            self.app.push_screen(SSHAddScreen())
            return

        if len(args) < 3:
            self.notify(
                "Usage: /ssh-add <alias> <host> <user> [port] [key_path]",
                severity="error",
            )
            return

        alias = args[0]
        hostname = args[1]
        username = args[2]
        port = int(args[3]) if len(args) > 3 else 22
        key_path = args[4] if len(args) > 4 else None

        self.app.storage.add_ssh_host(alias, hostname, port, username, key_path)
        self.notify(f"Added SSH host: {alias}")

    async def cmd_ssh_list(self, args: list[str]):
        """List saved SSH hosts."""
        hosts = self.app.storage.list_ssh_hosts()
        if not hosts:
            self.notify("No SSH hosts saved.")
            return

        lines = ["SSH Hosts:", "----------"]
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

    async def cmd_nullify(self, args: list[str]):
        """Open a new terminal tab/window with the Null Terminal profile.

        Usage:
            /nullify        - Open new tab with Null Terminal profile
            /nullify window - Open new window with Null Terminal profile
        """
        from utils.terminal import (
            TerminalType,
            activate_null_profile,
            get_terminal_info,
        )

        info = get_terminal_info()

        if info.type != TerminalType.WINDOWS_TERMINAL:
            self.notify(
                f"{info.name} doesn't require profile activation",
                severity="warning",
            )
            return

        new_window = "window" in args or "-w" in args

        if activate_null_profile(new_window=new_window):
            action = "window" if new_window else "tab"
            self.notify(f"Opening new {action} with Null Terminal profile...")
        else:
            self.notify("Failed to activate Null Terminal profile", severity="error")

    async def cmd_reload(self, args: list[str]):
        try:
            from themes import get_all_themes

            for theme in get_all_themes().values():
                self.app.register_theme(theme)

            self.app.mcp_manager.reload_config()
            await self.app.mcp_manager.initialize()

            self.notify("Configuration reloaded")
        except Exception as e:
            self.notify(f"Reload failed: {e}", severity="error")

    async def cmd_git(self, args: list[str]):
        from utils.git import get_git_status

        status = await get_git_status()

        if not status.is_repo:
            self.notify("Not a git repository", severity="warning")
            return

        lines = [
            f"  Branch: {status.branch}",
            f"  Dirty:  {'Yes' if status.is_dirty else 'No'}",
        ]
        await self.show_output("/git status", "\n".join(lines))
