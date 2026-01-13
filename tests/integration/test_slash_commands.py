"""Integration tests for slash commands.

Tests actual behavior: argument routing, state changes, return values.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_branch_manager():
    """Mock BranchManager for branch command tests."""
    bm = MagicMock()
    bm.list_branches.return_value = [
        MagicMock(name="main"),
        MagicMock(name="feature-1"),
    ]
    bm.switch_branch.return_value = True
    bm.create_branch.return_value = MagicMock(name="new-branch")
    return bm


class TestClearCommand:
    """Tests for /clear command."""

    @pytest.mark.asyncio
    async def test_clear_clears_blocks(self, running_app):
        """Test /clear empties app.blocks list."""
        pilot, app = running_app

        # Add some fake blocks
        from models import BlockState, BlockType

        app.blocks = [
            BlockState(type=BlockType.COMMAND, content_input="ls"),
            BlockState(type=BlockType.AI_RESPONSE, content_input="test"),
        ]

        await app.command_handler.handle("/clear")
        await pilot.pause()

        assert app.blocks == []
        assert app.current_cli_block is None
        assert app.current_cli_widget is None


class TestMCPCommands:
    """Tests for /mcp commands - argument routing."""

    @pytest.mark.asyncio
    async def test_mcp_remove_existing_server(self, running_app):
        """Test /mcp remove routes server name correctly."""
        pilot, app = running_app

        app.mcp_manager.remove_server = MagicMock(return_value=True)

        await app.command_handler.handle("/mcp remove test-server")
        await pilot.pause()

        app.mcp_manager.remove_server.assert_called_with("test-server")

    @pytest.mark.asyncio
    async def test_mcp_remove_nonexistent_server(self, running_app):
        """Test /mcp remove with nonexistent server routes correctly."""
        pilot, app = running_app

        app.mcp_manager.remove_server = MagicMock(return_value=False)

        await app.command_handler.handle("/mcp remove nonexistent")
        await pilot.pause()

        app.mcp_manager.remove_server.assert_called_with("nonexistent")


class TestExportCommand:
    """Tests for /export command - format routing."""

    @pytest.mark.asyncio
    async def test_export_md_default(self, running_app):
        """Test /export defaults to markdown format."""
        pilot, app = running_app

        app._do_export = MagicMock()

        await app.command_handler.handle("/export")
        await pilot.pause()

        app._do_export.assert_called_with("md")

    @pytest.mark.asyncio
    async def test_export_md_explicit(self, running_app):
        """Test /export md exports to markdown."""
        pilot, app = running_app

        app._do_export = MagicMock()

        await app.command_handler.handle("/export md")
        await pilot.pause()

        app._do_export.assert_called_with("md")

    @pytest.mark.asyncio
    async def test_export_json(self, running_app):
        """Test /export json exports to JSON."""
        pilot, app = running_app

        app._do_export = MagicMock()

        await app.command_handler.handle("/export json")
        await pilot.pause()

        app._do_export.assert_called_with("json")

    @pytest.mark.asyncio
    async def test_export_markdown_alias(self, running_app):
        """Test /export markdown is alias for md."""
        pilot, app = running_app

        app._do_export = MagicMock()

        await app.command_handler.handle("/export markdown")
        await pilot.pause()

        app._do_export.assert_called_with("md")

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, running_app):
        """Test /export with invalid format does not call _do_export."""
        pilot, app = running_app

        app._do_export = MagicMock()

        await app.command_handler.handle("/export pdf")
        await pilot.pause()

        # Should not call _do_export for invalid format
        app._do_export.assert_not_called()


class TestBranchCommands:
    """Tests for /branch commands - argument routing."""

    @pytest.mark.asyncio
    async def test_branch_switch(self, running_app, mock_branch_manager):
        """Test /branch switch routes branch name correctly."""
        pilot, app = running_app
        app.branch_manager = mock_branch_manager

        await app.command_handler.handle("/branch switch feature-1")
        await pilot.pause()

        mock_branch_manager.switch_branch.assert_called_with("feature-1")

    @pytest.mark.asyncio
    async def test_branch_new(self, running_app, mock_branch_manager):
        """Test /branch new routes branch name correctly."""
        pilot, app = running_app
        app.branch_manager = mock_branch_manager

        await app.command_handler.handle("/branch new my-branch")
        await pilot.pause()

        mock_branch_manager.create_branch.assert_called_with("my-branch")


class TestQuitExitCommands:
    """Tests for /quit and /exit commands."""

    @pytest.mark.asyncio
    async def test_quit_exits_app(self, running_app):
        """Test /quit calls app.exit()."""
        pilot, app = running_app

        app.exit = MagicMock()

        await app.command_handler.handle("/quit")
        await pilot.pause()

        app.exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_exit_exits_app(self, running_app):
        """Test /exit calls app.exit()."""
        pilot, app = running_app

        app.exit = MagicMock()

        await app.command_handler.handle("/exit")
        await pilot.pause()

        app.exit.assert_called_once()


class TestCommandRegistry:
    """Tests for command registry functionality."""

    @pytest.mark.asyncio
    async def test_get_all_commands(self, running_app):
        """Test get_all_commands returns list of CommandInfo with attributes."""
        pilot, app = running_app

        commands = app.command_handler.get_all_commands()

        assert isinstance(commands, list)
        assert len(commands) > 0

        # Check first command has expected attributes
        cmd = commands[0]
        assert hasattr(cmd, "name")
        assert hasattr(cmd, "description")

    @pytest.mark.asyncio
    async def test_get_command_info_existing(self, running_app):
        """Test get_command_info returns info for existing command."""
        pilot, app = running_app

        info = app.command_handler.get_command_info("help")

        assert info is not None
        assert info.name == "help"

    @pytest.mark.asyncio
    async def test_get_command_info_nonexistent(self, running_app):
        """Test get_command_info returns None for nonexistent command."""
        pilot, app = running_app

        info = app.command_handler.get_command_info("nonexistent")

        assert info is None
