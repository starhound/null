"""Main command handler that routes to command modules."""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Tuple, Callable, List
from dataclasses import dataclass

if TYPE_CHECKING:
    from app import NullApp

from .core import CoreCommands
from .ai import AICommands
from .session import SessionCommands
from .mcp import MCPCommands
from .config import ConfigCommands


@dataclass
class CommandInfo:
    """Information about a slash command."""
    name: str
    description: str
    shortcut: str = ""
    subcommands: List[Tuple[str, str]] = None  # [(subcommand, description), ...]

    def __post_init__(self):
        if self.subcommands is None:
            self.subcommands = []


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

        # Build command routing table with descriptions
        self._command_registry: Dict[str, Tuple[Callable, CommandInfo]] = {
            # Core commands
            "help": (self._core.cmd_help, CommandInfo("help", "Show help screen", "F1")),
            "status": (self._core.cmd_status, CommandInfo("status", "Show current status")),
            "clear": (self._core.cmd_clear, CommandInfo("clear", "Clear history and context", "Ctrl+L")),
            "quit": (self._core.cmd_quit, CommandInfo("quit", "Exit application", "Ctrl+C")),
            "exit": (self._core.cmd_exit, CommandInfo("exit", "Exit application")),

            # AI commands
            "provider": (self._ai.cmd_provider, CommandInfo("provider", "Select AI provider", "F4")),
            "model": (self._ai.cmd_model, CommandInfo("model", "Select AI model", "F2")),
            "prompts": (self._ai.cmd_prompts, CommandInfo("prompts", "Manage system prompts")),
            "ai": (self._ai.cmd_ai, CommandInfo("ai", "Toggle AI mode", "Ctrl+Space")),
            "chat": (self._ai.cmd_chat, CommandInfo("chat", "Toggle AI mode")),
            "agent": (self._ai.cmd_agent, CommandInfo("agent", "Toggle agent mode (auto tool execution)")),
            "compact": (self._ai.cmd_compact, CommandInfo("compact", "Summarize context to save tokens")),

            # Session commands
            "session": (self._session.cmd_session, CommandInfo(
                "session", "Manage sessions",
                subcommands=[
                    ("save [name]", "Save current session"),
                    ("load <name>", "Load a saved session"),
                    ("list", "List saved sessions"),
                    ("new", "Start new session"),
                    ("delete <name>", "Delete a session"),
                ]
            )),
            "export": (self._session.cmd_export, CommandInfo(
                "export", "Export conversation", "Ctrl+S",
                subcommands=[
                    ("md", "Export to Markdown"),
                    ("json", "Export to JSON"),
                    ("txt", "Export to plain text"),
                ]
            )),

            # MCP commands
            "mcp": (self._mcp.cmd_mcp, CommandInfo(
                "mcp", "Manage MCP servers",
                subcommands=[
                    ("list", "List configured MCP servers"),
                    ("add", "Add a new MCP server"),
                    ("remove <name>", "Remove an MCP server"),
                    ("tools", "Show available MCP tools"),
                    ("connect <name>", "Connect to a server"),
                ]
            )),

            # Config commands
            "config": (self._config.cmd_config, CommandInfo("config", "Open settings")),
            "settings": (self._config.cmd_settings, CommandInfo("settings", "Open settings")),
            "theme": (self._config.cmd_theme, CommandInfo("theme", "Change UI theme", "F3")),
        }

        # Legacy _commands dict for backward compatibility
        self._commands = {k: v[0] for k, v in self._command_registry.items()}

    def get_all_commands(self) -> List[CommandInfo]:
        """Get list of all available commands with their info."""
        return [info for _, info in self._command_registry.values()]

    def get_command_info(self, name: str) -> CommandInfo | None:
        """Get info for a specific command."""
        entry = self._command_registry.get(name)
        return entry[1] if entry else None

    async def handle(self, text: str):
        """Route and execute a slash command."""
        parts = text.split()
        command = parts[0][1:]  # strip /
        args = parts[1:]

        entry = self._command_registry.get(command)
        if entry:
            handler = entry[0]
            await handler(args)
        else:
            self.app.notify(f"Unknown command: {command}", severity="warning")
