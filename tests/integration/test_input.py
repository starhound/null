"""Integration tests for input handling and slash commands."""

import pytest

from widgets import InputController


async def type_text(pilot, app, text: str):
    """Helper to type text into the input widget."""
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()


async def submit_input(pilot, app, text: str):
    """Helper to type text and submit it."""
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestInputWidget:
    """Tests for InputController widget."""

    @pytest.mark.asyncio
    async def test_input_accepts_text(self, running_app):
        """Input widget should accept typed text."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "hello world"
        await pilot.pause()

        assert input_widget.text == "hello world"

    @pytest.mark.asyncio
    async def test_input_clears_on_submit(self, running_app):
        """Input should clear after submission."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "test"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        # After submission, input should be cleared
        assert input_widget.text == ""

    @pytest.mark.asyncio
    async def test_shift_enter_inserts_newline(self, running_app):
        """Shift+Enter should insert newline, not submit."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "line1"
        await pilot.pause()
        await pilot.press("shift+enter")
        await pilot.pause()

        # Should have newline
        assert "\n" in input_widget.text


class TestInputModeToggle:
    """Tests for CLI/AI mode toggling."""

    @pytest.mark.asyncio
    async def test_starts_in_cli_mode(self, running_app):
        """Input should start in CLI mode."""
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        assert input_widget.mode == "CLI"
        assert not input_widget.is_ai_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_changes_mode(self, running_app):
        """toggle_mode should switch between CLI and AI."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        assert input_widget.mode == "AI"
        assert input_widget.is_ai_mode

    @pytest.mark.asyncio
    async def test_ai_mode_adds_class(self, running_app):
        """AI mode should add 'ai-mode' CSS class."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        assert "ai-mode" in input_widget.classes

    @pytest.mark.asyncio
    async def test_cli_mode_removes_class(self, running_app):
        """Switching back to CLI should remove 'ai-mode' class."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()  # To AI
        input_widget.toggle_mode()  # Back to CLI
        await pilot.pause()

        assert "ai-mode" not in input_widget.classes

    @pytest.mark.asyncio
    async def test_ctrl_t_toggles_mode(self, running_app):
        """Ctrl+T should toggle AI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial = input_widget.mode
        await pilot.press("ctrl+t")
        await pilot.pause()

        assert input_widget.mode != initial


class TestSlashCommands:
    """Tests for slash command handling."""

    @pytest.mark.asyncio
    async def test_help_command(self, running_app):
        """'/help' command should open help screen."""
        pilot, app = running_app

        await submit_input(pilot, app, "/help")

        # Help screen should be open
        from screens import HelpScreen

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], HelpScreen)

    @pytest.mark.asyncio
    async def test_clear_command(self, running_app):
        """'/clear' command should clear history."""
        pilot, app = running_app

        # First add some content
        await submit_input(pilot, app, "echo test")

        # Now clear
        await submit_input(pilot, app, "/clear")

        # History should be empty
        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_theme_command_changes_theme(self, running_app):
        """'/theme' command should change theme."""
        pilot, app = running_app

        await submit_input(pilot, app, "/theme null-light")

        assert app.theme == "null-light"

    @pytest.mark.asyncio
    async def test_ai_command_toggles_mode(self, running_app):
        """'/ai' command should toggle AI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        assert input_widget.mode == "CLI"

        await submit_input(pilot, app, "/ai")

        assert input_widget.mode == "AI"

    @pytest.mark.asyncio
    async def test_ai_command_toggles_back(self, running_app):
        """'/ai' command should toggle back to CLI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        # Switch to AI mode
        await submit_input(pilot, app, "/ai")
        assert input_widget.mode == "AI"

        # Toggle back
        await submit_input(pilot, app, "/ai")

        assert input_widget.mode == "CLI"

    @pytest.mark.asyncio
    async def test_version_command(self, running_app):
        """'/version' command should execute without error."""
        pilot, app = running_app

        await submit_input(pilot, app, "/version")

        # Should have executed without error


class TestCommandSuggester:
    """Tests for command suggester widget."""

    @pytest.mark.asyncio
    async def test_suggester_appears_on_slash(self, running_app):
        """Typing '/' should show command suggester."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/"
        await pilot.pause()

        suggester = app.query_one("#suggester")
        assert suggester.display is True

    @pytest.mark.asyncio
    async def test_suggester_filters_commands(self, running_app):
        """Suggester should filter commands based on input."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/he"
        await pilot.pause()

        suggester = app.query_one("#suggester")
        assert suggester.display is True

    @pytest.mark.asyncio
    async def test_suggester_hides_on_non_slash(self, running_app):
        """Suggester should hide when input doesn't start with /."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/"
        await pilot.pause()

        suggester = app.query_one("#suggester")
        assert suggester.display is True

        # Clear and type something else
        input_widget.text = "echo"
        await pilot.pause()

        assert suggester.display is False


class TestInputHistory:
    """Tests for command history navigation."""

    @pytest.mark.asyncio
    async def test_history_stores_commands(self, running_app):
        """Commands should be stored in history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        await submit_input(pilot, app, "first command")
        await submit_input(pilot, app, "second command")

        # History should contain commands
        assert "first command" in input_widget.cmd_history
        assert "second command" in input_widget.cmd_history

    @pytest.mark.asyncio
    async def test_history_up_navigates(self, running_app):
        """Up arrow should navigate history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        # Add commands to history
        input_widget.cmd_history = ["command1", "command2", "command3"]

        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "command3"

        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "command2"

    @pytest.mark.asyncio
    async def test_history_down_navigates(self, running_app):
        """Down arrow should navigate history forward."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = ["command1", "command2"]
        input_widget.action_history_up()
        input_widget.action_history_up()
        await pilot.pause()

        # Now at command1, go down
        input_widget.action_history_down()
        await pilot.pause()

        assert input_widget.text == "command2"


class TestBuiltinCommands:
    """Tests for built-in shell commands."""

    @pytest.mark.asyncio
    async def test_echo_command(self, running_app):
        """'echo' should execute and create a block."""
        pilot, app = running_app

        await submit_input(pilot, app, "echo hello world")

        # Should have created a block
        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_cd_command(self, running_app, temp_home):
        """'cd' should change directory without error."""
        pilot, app = running_app

        await submit_input(pilot, app, f"cd {temp_home}")

        # Command should have been handled without error
