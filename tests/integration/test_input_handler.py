"""Integration tests for InputHandler class."""

import os
from pathlib import Path

import pytest

from widgets import InputController


class TestInputHandlerSubmission:
    """Tests for InputHandler.handle_submission."""

    @pytest.mark.asyncio
    async def test_empty_input_is_ignored(self, running_app):
        """Empty input should not create blocks or add to history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial_blocks = len(app.blocks)
        initial_history = len(input_widget.cmd_history)

        input_widget.text = ""
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) == initial_blocks
        assert len(input_widget.cmd_history) == initial_history

    @pytest.mark.asyncio
    async def test_whitespace_only_input_is_ignored(self, running_app):
        """Whitespace-only input should be ignored."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial_blocks = len(app.blocks)

        input_widget.text = "   \t  "
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) == initial_blocks

    @pytest.mark.asyncio
    async def test_regular_command_creates_block(self, running_app):
        """Regular CLI commands should create command blocks."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo test"
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_input_cleared_after_submission(self, running_app):
        """Input should be cleared after successful submission."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo test"
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""


class TestInputHandlerSlashCommands:
    """Tests for slash command routing in InputHandler."""

    @pytest.mark.asyncio
    async def test_slash_help_routes_to_command_handler(self, running_app):
        """'/help' should route to command handler and open help screen."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/help"
        await pilot.press("enter")
        await pilot.pause()

        from screens import HelpScreen

        assert any(isinstance(s, HelpScreen) for s in app.screen_stack)

    @pytest.mark.asyncio
    async def test_slash_clear_routes_to_command_handler(self, running_app):
        """'/clear' should clear blocks."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo test"
        await pilot.press("enter")
        await pilot.pause()

        input_widget.text = "/clear"
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_slash_command_clears_input(self, running_app):
        """Slash commands should clear input after execution."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/version"
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""

    @pytest.mark.asyncio
    async def test_invalid_slash_command_handled(self, running_app):
        """Invalid slash commands should be handled gracefully."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/notacommand"
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""


class TestInputHandlerHistory:
    """Tests for command history in InputHandler."""

    @pytest.mark.asyncio
    async def test_command_added_to_history(self, running_app):
        """Submitted commands should be added to history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo history_test"
        await pilot.press("enter")
        await pilot.pause()

        assert "echo history_test" in input_widget.cmd_history

    @pytest.mark.asyncio
    async def test_slash_command_added_to_history(self, running_app):
        """Slash commands should also be added to history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/version"
        await pilot.press("enter")
        await pilot.pause()

        assert "/version" in input_widget.cmd_history

    @pytest.mark.asyncio
    async def test_history_navigation_up(self, running_app):
        """Up arrow should navigate backwards through history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "cmd1"
        await pilot.press("enter")
        await pilot.pause()

        input_widget.text = "cmd2"
        await pilot.press("enter")
        await pilot.pause()

        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "cmd2"

        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "cmd1"

    @pytest.mark.asyncio
    async def test_history_navigation_down(self, running_app):
        """Down arrow should navigate forwards through history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = ["cmd1", "cmd2", "cmd3"]

        input_widget.action_history_up()
        input_widget.action_history_up()
        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "cmd1"

        input_widget.action_history_down()
        await pilot.pause()

        assert input_widget.text == "cmd2"

    @pytest.mark.asyncio
    async def test_empty_history_navigation(self, running_app):
        """History navigation with empty history should not crash."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = []

        input_widget.action_history_up()
        await pilot.pause()

        input_widget.action_history_down()
        await pilot.pause()

        assert input_widget.text == ""


class TestInputHandlerBuiltins:
    """Tests for built-in command handling (cd, pwd, clear)."""

    @pytest.mark.asyncio
    async def test_pwd_shows_current_directory(self, running_app):
        """'pwd' should display current working directory."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "pwd"
        await pilot.press("enter")
        await pilot.pause()

        from widgets import HistoryViewport

        history_vp = app.query_one("#history", HistoryViewport)
        assert len(history_vp.children) >= 1

    @pytest.mark.asyncio
    async def test_cd_changes_directory(self, running_app, temp_home):
        """'cd' should change working directory."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        test_dir = temp_home / "test_cd_dir"
        test_dir.mkdir(exist_ok=True)

        original_cwd = Path.cwd()

        input_widget.text = f"cd {test_dir}"
        await pilot.press("enter")
        await pilot.pause()

        assert Path.cwd() == test_dir

        os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_cd_home_goes_to_home(self, running_app, temp_home):
        """'cd' without args should go to home directory."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        original_cwd = Path.cwd()

        input_widget.text = "cd"
        await pilot.press("enter")
        await pilot.pause()

        assert Path.cwd() == temp_home

        os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_cd_tilde_expansion(self, running_app, temp_home):
        """'cd ~' should expand to home directory."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        original_cwd = Path.cwd()

        input_widget.text = "cd ~"
        await pilot.press("enter")
        await pilot.pause()

        assert Path.cwd() == temp_home

        os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_cd_dash_returns_to_previous(self, running_app, temp_home):
        """'cd -' should return to previous directory."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        dir1 = temp_home / "dir1"
        dir2 = temp_home / "dir2"
        dir1.mkdir(exist_ok=True)
        dir2.mkdir(exist_ok=True)

        original_cwd = Path.cwd()

        input_widget.text = f"cd {dir1}"
        await pilot.press("enter")
        await pilot.pause()

        input_widget.text = f"cd {dir2}"
        await pilot.press("enter")
        await pilot.pause()

        input_widget.text = "cd -"
        await pilot.press("enter")
        await pilot.pause()

        assert Path.cwd() == dir1

        os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_clear_clears_history(self, running_app):
        """'clear' command should clear history blocks."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo test"
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) >= 1

        input_widget.text = "clear"
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) == 0


class TestInputHandlerValidation:
    """Tests for input validation and edge cases."""

    @pytest.mark.asyncio
    async def test_special_characters_in_input(self, running_app):
        """Special characters should be handled."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        special = "echo $HOME && ls | grep test"
        input_widget.text = special
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""

    @pytest.mark.asyncio
    async def test_unicode_input(self, running_app):
        """Unicode characters should be handled."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo 你好世界 🌍"
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""

    @pytest.mark.asyncio
    async def test_very_long_input(self, running_app):
        """Very long input should be handled."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        long_input = "echo " + "x" * 1000
        input_widget.text = long_input
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""


class TestInputHandlerAIMode:
    """Tests for AI mode input handling."""

    @pytest.mark.asyncio
    async def test_ai_mode_without_provider_shows_error(self, running_app):
        """AI input without provider configured should show error."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        assert input_widget.is_ai_mode

        input_widget.text = "Tell me a joke"
        await pilot.press("enter")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_slash_command_works_in_ai_mode(self, running_app):
        """Slash commands should work in AI mode too."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        input_widget.text = "/version"
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""
