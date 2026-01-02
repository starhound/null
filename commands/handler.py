"""Main command handler that routes to command modules."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from .core import CoreCommands
from .ai import AICommands
from .session import SessionCommands
from .mcp import MCPCommands
from .config import ConfigCommands


class SlashCommandHandler:
    """Routes and executes slash commands."""

    def __init__(self, app: "NullApp"):
        self.app = app

        # Initialize command modules
        self._core = CoreCommands(app)
        self._ai = AICommands(app)
        self._session = SessionCommands(app)
        self._mcp = MCPCommands(app)
        self._config = ConfigCommands(app)

        # Build command routing table
        self._commands = {
            # Core commands
            "help": self._core.cmd_help,
            "status": self._core.cmd_status,
            "clear": self._core.cmd_clear,
            "quit": self._core.cmd_quit,
            "exit": self._core.cmd_exit,

            # AI commands
            "provider": self._ai.cmd_provider,
            "model": self._ai.cmd_model,
            "prompts": self._ai.cmd_prompts,
            "ai": self._ai.cmd_ai,
            "chat": self._ai.cmd_chat,
            "compact": self._ai.cmd_compact,

            # Session commands
            "session": self._session.cmd_session,
            "export": self._session.cmd_export,

            # MCP commands
            "mcp": self._mcp.cmd_mcp,

            # Config commands
            "config": self._config.cmd_config,
            "settings": self._config.cmd_settings,
            "theme": self._config.cmd_theme,
        }

    async def handle(self, text: str):
        """Route and execute a slash command."""
        parts = text.split()
        command = parts[0][1:]  # strip /
        args = parts[1:]

        handler = self._commands.get(command)
        if handler:
            await handler(args)
        else:
            self.app.notify(f"Unknown command: {command}", severity="warning")
