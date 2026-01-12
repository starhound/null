"""Tests for commands/handler.py - SlashCommandHandler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.handler import CommandInfo, SlashCommandHandler


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.notify = MagicMock()
    return app


@pytest.fixture
def handler(mock_app):
    with patch.multiple(
        "commands.handler",
        CoreCommands=MagicMock(),
        AICommands=MagicMock(),
        RAGCommands=MagicMock(),
        SessionCommands=MagicMock(),
        ShareCommands=MagicMock(),
        MCPCommands=MagicMock(),
        ConfigCommands=MagicMock(),
        TodoCommands=MagicMock(),
    ):
        return SlashCommandHandler(mock_app)


class TestCommandInfo:
    def test_command_info_basic(self):
        info = CommandInfo(name="test", description="Test command")
        assert info.name == "test"
        assert info.description == "Test command"
        assert info.shortcut == ""
        assert info.subcommands == []

    def test_command_info_with_shortcut(self):
        info = CommandInfo(name="help", description="Show help", shortcut="F1")
        assert info.shortcut == "F1"

    def test_command_info_with_subcommands(self):
        info = CommandInfo(
            name="git",
            description="Git operations",
            subcommands=[
                ("status", "Show status"),
                ("diff", "Show diff"),
            ],
        )
        assert len(info.subcommands) == 2
        assert info.subcommands[0] == ("status", "Show status")


class TestSlashCommandHandlerInit:
    def test_handler_initializes_modules(self, mock_app):
        with patch.multiple(
            "commands.handler",
            CoreCommands=MagicMock(),
            AICommands=MagicMock(),
            RAGCommands=MagicMock(),
            SessionCommands=MagicMock(),
            ShareCommands=MagicMock(),
            MCPCommands=MagicMock(),
            ConfigCommands=MagicMock(),
            TodoCommands=MagicMock(),
        ):
            handler = SlashCommandHandler(mock_app)

        assert handler._core is not None
        assert handler._ai is not None
        assert handler._mcp is not None

    def test_handler_builds_command_registry(self, handler):
        assert "help" in handler._command_registry
        assert "status" in handler._command_registry
        assert "clear" in handler._command_registry
        assert "quit" in handler._command_registry

    def test_handler_creates_legacy_commands(self, handler):
        assert "help" in handler._commands
        assert callable(handler._commands["help"]) or callable(
            handler._commands["help"]
        )


class TestSlashCommandHandlerGetAllCommands:
    def test_get_all_commands_returns_list(self, handler):
        commands = handler.get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) > 0
        assert all(isinstance(c, CommandInfo) for c in commands)

    def test_get_all_commands_includes_core_commands(self, handler):
        commands = handler.get_all_commands()
        command_names = [c.name for c in commands]
        assert "help" in command_names
        assert "status" in command_names
        assert "clear" in command_names


class TestSlashCommandHandlerGetCommandInfo:
    def test_get_command_info_returns_info(self, handler):
        info = handler.get_command_info("help")
        assert info is not None
        assert info.name == "help"
        assert "help" in info.description.lower()

    def test_get_command_info_returns_none_for_unknown(self, handler):
        info = handler.get_command_info("nonexistent")
        assert info is None

    def test_get_command_info_includes_shortcut(self, handler):
        info = handler.get_command_info("help")
        assert info.shortcut == "F1"


class TestSlashCommandHandlerHandle:
    @pytest.mark.asyncio
    async def test_handle_calls_correct_handler(self, handler, mock_app):
        mock_handler = AsyncMock()
        handler._command_registry["help"] = (
            mock_handler,
            handler._command_registry["help"][1],
        )

        await handler.handle("/help")

        mock_handler.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_handle_passes_args(self, handler, mock_app):
        mock_handler = AsyncMock()
        handler._command_registry["git"] = (
            mock_handler,
            handler._command_registry["git"][1],
        )

        await handler.handle("/git status")

        mock_handler.assert_called_once_with(["status"])

    @pytest.mark.asyncio
    async def test_handle_multiple_args(self, handler, mock_app):
        mock_handler = AsyncMock()
        handler._command_registry["git"] = (
            mock_handler,
            handler._command_registry["git"][1],
        )

        await handler.handle("/git commit Initial commit message")

        mock_handler.assert_called_once_with(["commit", "Initial", "commit", "message"])

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, handler, mock_app):
        await handler.handle("/unknowncommand")

        mock_app.notify.assert_called_once()
        assert "Unknown command" in mock_app.notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_ai_commands(self, handler, mock_app):
        mock_handler = AsyncMock()
        handler._command_registry["provider"] = (
            mock_handler,
            handler._command_registry["provider"][1],
        )

        await handler.handle("/provider ollama")

        mock_handler.assert_called_once_with(["ollama"])

    @pytest.mark.asyncio
    async def test_handle_mcp_commands(self, handler, mock_app):
        mock_handler = AsyncMock()
        handler._command_registry["mcp"] = (
            mock_handler,
            handler._command_registry["mcp"][1],
        )

        await handler.handle("/mcp list")

        mock_handler.assert_called_once_with(["list"])

    @pytest.mark.asyncio
    async def test_handle_config_commands(self, handler, mock_app):
        mock_handler = AsyncMock()
        handler._command_registry["theme"] = (
            mock_handler,
            handler._command_registry["theme"][1],
        )

        await handler.handle("/theme dracula")

        mock_handler.assert_called_once_with(["dracula"])


class TestCommandRegistryCompleteness:
    def test_all_core_commands_registered(self, handler):
        core_commands = ["help", "status", "clear", "quit", "exit", "git", "reload"]
        for cmd in core_commands:
            assert cmd in handler._command_registry, f"Missing core command: {cmd}"

    def test_all_ai_commands_registered(self, handler):
        ai_commands = ["provider", "model", "ai", "agent", "context"]
        for cmd in ai_commands:
            assert cmd in handler._command_registry, f"Missing AI command: {cmd}"

    def test_all_ssh_commands_registered(self, handler):
        ssh_commands = ["ssh", "ssh-add", "ssh-list", "ssh-del"]
        for cmd in ssh_commands:
            assert cmd in handler._command_registry, f"Missing SSH command: {cmd}"

    def test_all_mcp_commands_registered(self, handler):
        mcp_commands = ["mcp", "tools"]
        for cmd in mcp_commands:
            assert cmd in handler._command_registry, f"Missing MCP command: {cmd}"

    def test_all_session_commands_registered(self, handler):
        session_commands = ["session", "export"]
        for cmd in session_commands:
            assert cmd in handler._command_registry, f"Missing session command: {cmd}"
