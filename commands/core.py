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
