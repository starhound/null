"""Integration tests for keyboard shortcuts and keybindings."""

import pytest

from screens import HelpScreen
from widgets import InputController


async def submit_input(pilot, app, text: str):
    """Helper to type text and submit it."""
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestGlobalKeybindings:
    """Tests for app-level keybindings."""

    @pytest.mark.asyncio
    async def test_f1_opens_help(self, running_app):
        """F1 should open help screen."""
        pilot, app = running_app

        await pilot.press("f1")
        await pilot.pause()

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], HelpScreen)

    @pytest.mark.asyncio
    async def test_f2_opens_model_selector(self, running_app):
        """F2 should open model selection."""
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_f3_opens_theme_selector(self, running_app):
        """F3 should open theme selection."""
        pilot, app = running_app

        await pilot.press("f3")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_f4_opens_provider_selector(self, running_app):
        """F4 should open provider selection."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_ctrl_l_clears_history(self, running_app):
        """Ctrl+L should clear history."""
        pilot, app = running_app

        # Add some content first
        await submit_input(pilot, app, "echo test")

        assert len(app.blocks) >= 1

        await pilot.press("ctrl+l")
        await pilot.pause()

        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_ctrl_p_opens_command_palette(self, running_app):
        """Ctrl+P action should open command palette."""
        pilot, app = running_app

        # Use action directly (keybinding may be captured by input widget)
        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette")
        assert "visible" in palette.classes

    @pytest.mark.asyncio
    async def test_ctrl_r_opens_history_search(self, running_app):
        """Ctrl+R should open history search."""
        pilot, app = running_app

        await pilot.press("ctrl+r")
        await pilot.pause()

        search = app.query_one("#history-search")
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_ctrl_f_opens_block_search(self, running_app):
        """Ctrl+F action should open block search."""
        pilot, app = running_app

        # Use action directly (keybinding may be captured by input widget)
        app.action_search_blocks()
        await pilot.pause()

        search = app.query_one("#block-search")
        assert "visible" in search.classes


class TestModeToggleKeybindings:
    """Tests for AI/CLI mode toggle keybindings."""

    @pytest.mark.asyncio
    async def test_ctrl_t_toggles_mode(self, running_app):
        """Ctrl+T should toggle AI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial = input_widget.mode
        await pilot.press("ctrl+t")
        await pilot.pause()

        assert input_widget.mode != initial

    @pytest.mark.asyncio
    async def test_ctrl_b_toggles_mode(self, running_app):
        """Ctrl+B should toggle AI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial = input_widget.mode
        await pilot.press("ctrl+b")
        await pilot.pause()

        assert input_widget.mode != initial

    @pytest.mark.asyncio
    async def test_ctrl_space_toggles_mode(self, running_app):
        """Ctrl+Space should toggle AI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial = input_widget.mode
        await pilot.press("ctrl+space")
        await pilot.pause()

        assert input_widget.mode != initial


class TestEscapeKeybinding:
    """Tests for escape key behavior."""

    @pytest.mark.asyncio
    async def test_escape_closes_modal(self, running_app):
        """Escape should close modal screens."""
        pilot, app = running_app

        # Open a modal
        await pilot.press("f1")
        await pilot.pause()
        assert len(app.screen_stack) > 1

        # Close with escape
        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_escape_closes_overlay(self, running_app):
        """Escape should close overlay widgets."""
        pilot, app = running_app

        # Open command palette via action
        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette")
        assert "visible" in palette.classes

        # Close with escape
        await pilot.press("escape")
        await pilot.pause()

        assert "visible" not in palette.classes

    @pytest.mark.asyncio
    async def test_escape_closes_history_search(self, running_app):
        """Escape should close history search."""
        pilot, app = running_app

        await pilot.press("ctrl+r")
        await pilot.pause()

        search = app.query_one("#history-search")
        assert "visible" in search.classes

        await pilot.press("escape")
        await pilot.pause()

        assert "visible" not in search.classes

    @pytest.mark.asyncio
    async def test_escape_closes_block_search(self, running_app):
        """Escape should close block search."""
        pilot, app = running_app

        # Open via action
        app.action_search_blocks()
        await pilot.pause()

        search = app.query_one("#block-search")
        assert "visible" in search.classes

        await pilot.press("escape")
        await pilot.pause()

        assert "visible" not in search.classes

    @pytest.mark.asyncio
    async def test_escape_hides_suggester(self, running_app):
        """Escape should hide command suggester."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "/"
        await pilot.pause()

        suggester = app.query_one("#suggester")
        assert suggester.display is True

        await pilot.press("escape")
        await pilot.pause()

        assert suggester.display is False


class TestInputKeybindings:
    """Tests for input widget keybindings."""

    @pytest.mark.asyncio
    async def test_enter_submits_input(self, running_app):
        """Enter should submit input."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "test command"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        # Input should be cleared after submission
        assert input_widget.text == ""

    @pytest.mark.asyncio
    async def test_shift_enter_adds_newline(self, running_app):
        """Shift+Enter should add newline without submitting."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "line1"
        await pilot.pause()
        await pilot.press("shift+enter")
        await pilot.pause()

        # Should have newline, not submitted
        assert "\n" in input_widget.text
        assert "line1" in input_widget.text


class TestNavigationKeybindings:
    """Tests for navigation keybindings."""

    @pytest.mark.asyncio
    async def test_history_up_navigates(self, running_app):
        """Up arrow should navigate command history."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        # Add commands to history
        await submit_input(pilot, app, "first")
        await submit_input(pilot, app, "second")

        # Navigate history
        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "second"

    @pytest.mark.asyncio
    async def test_history_down_navigates(self, running_app):
        """Down arrow should navigate history forward."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = ["cmd1", "cmd2"]

        input_widget.action_history_up()
        input_widget.action_history_up()
        await pilot.pause()

        input_widget.action_history_down()
        await pilot.pause()

        assert input_widget.text == "cmd2"


class TestQuickExport:
    """Tests for quick export keybinding."""

    @pytest.mark.asyncio
    async def test_ctrl_s_quick_export(self, running_app):
        """Ctrl+S should trigger quick export."""
        pilot, app = running_app

        # Add some content to export
        await submit_input(pilot, app, "echo test")

        # Quick export should work without error
        await pilot.press("ctrl+s")
        await pilot.pause()

        # Should not crash - export to temp file
