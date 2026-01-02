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

        provider = self.app.config.get("ai", {}).get("provider", "none")
        model = self.app.config.get("ai", {}).get("model", "none")
        persona = self.app.config.get("ai", {}).get("active_prompt", "default")
        blocks_count = len(self.app.blocks)

        context_str = ContextManager.get_context(self.app.blocks)
        context_chars = len(context_str)
        context_tokens = context_chars // 4

        status_bar = self.app.query_one("#status-bar", StatusBar)
        provider_status = status_bar.provider_status

        lines = [
            f"  Provider:      {provider} ({provider_status})",
            f"  Model:         {model}",
            f"  Persona:       {persona}",
            f"  Blocks:        {blocks_count}",
            f"  Context:       ~{context_tokens} tokens ({context_chars} chars)",
        ]
        await self.show_output("/status", "\n".join(lines))

    async def cmd_clear(self, args: list[str]):
        """Clear history and context."""
        self.app.blocks = []
        self.app.current_cli_block = None
        self.app.current_cli_widget = None
        history = self.app.query_one("#history", HistoryViewport)
        await history.remove_children()
        self.app._update_status_bar()
        self.notify("History and context cleared")

    async def cmd_quit(self, args: list[str]):
        """Quit the application."""
        self.app.exit()

    async def cmd_exit(self, args: list[str]):
        """Exit the application (alias)."""
        self.app.exit()
