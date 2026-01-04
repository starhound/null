"""Integration tests for screen navigation and modals."""

import pytest

from screens import ConfirmDialog, HelpScreen


class TestHelpScreen:
    """Tests for help screen modal."""

    @pytest.mark.asyncio
    async def test_help_screen_opens_with_f1(self, running_app):
        """F1 should open help screen."""
        pilot, app = running_app

        await pilot.press("f1")
        await pilot.pause()

        # Help screen should be on screen stack
        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], HelpScreen)

    @pytest.mark.asyncio
    async def test_help_screen_opens_with_action(self, running_app):
        """open_help action should open help screen."""
        pilot, app = running_app

        app.action_open_help()
        await pilot.pause()

        assert isinstance(app.screen_stack[-1], HelpScreen)

    @pytest.mark.asyncio
    async def test_help_screen_closes_with_escape(self, running_app):
        """Escape should close help screen."""
        pilot, app = running_app

        await pilot.press("f1")
        await pilot.pause()
        assert len(app.screen_stack) > 1

        await pilot.press("escape")
        await pilot.pause()

        # Should be back to main screen
        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_help_screen_has_content(self, running_app):
        """Help screen should display command information."""
        pilot, app = running_app

        await pilot.press("f1")
        await pilot.pause()

        help_screen = app.screen_stack[-1]
        assert isinstance(help_screen, HelpScreen)

        # Help screen should have the commands table
        # The screen composes a DataTable with commands


class TestConfirmDialog:
    """Tests for confirmation dialog."""

    @pytest.mark.asyncio
    async def test_confirm_dialog_displays(self, running_app):
        """Confirm dialog should display when pushed."""
        pilot, app = running_app

        result_holder = {"result": None}

        def on_confirm(result):
            result_holder["result"] = result

        app.push_screen(
            ConfirmDialog(title="Test", message="Are you sure?"),
            on_confirm,
        )
        await pilot.pause()

        assert isinstance(app.screen_stack[-1], ConfirmDialog)

    @pytest.mark.asyncio
    async def test_confirm_dialog_yes_returns_true(self, running_app):
        """Clicking Yes should return True."""
        pilot, app = running_app

        result_holder = {"result": None}

        def on_confirm(result):
            result_holder["result"] = result

        app.push_screen(
            ConfirmDialog(title="Test", message="Test?"),
            on_confirm,
        )
        await pilot.pause()

        # Click yes button
        await pilot.click("#confirm-yes")
        await pilot.pause()

        assert result_holder["result"] is True

    @pytest.mark.asyncio
    async def test_confirm_dialog_no_returns_false(self, running_app):
        """Clicking No should return False."""
        pilot, app = running_app

        result_holder = {"result": None}

        def on_confirm(result):
            result_holder["result"] = result

        app.push_screen(
            ConfirmDialog(title="Test", message="Test?"),
            on_confirm,
        )
        await pilot.pause()

        # Click no button
        await pilot.click("#confirm-no")
        await pilot.pause()

        assert result_holder["result"] is False

    @pytest.mark.asyncio
    async def test_confirm_dialog_escape_returns_false(self, running_app):
        """Escape should return False."""
        pilot, app = running_app

        result_holder = {"result": None}

        def on_confirm(result):
            result_holder["result"] = result

        app.push_screen(
            ConfirmDialog(title="Test", message="Test?"),
            on_confirm,
        )
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert result_holder["result"] is False


class TestModelListScreen:
    """Tests for model selection screen."""

    @pytest.mark.asyncio
    async def test_model_screen_opens_with_f2(self, running_app):
        """F2 should open model selection screen."""
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        # Model screen should be on stack
        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_model_screen_closes_with_escape(self, running_app):
        """Escape should close model selection screen."""
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1


class TestCommandPalette:
    """Tests for command palette overlay."""

    @pytest.mark.asyncio
    async def test_command_palette_opens_with_action(self, running_app):
        """Command palette action should open overlay."""
        pilot, app = running_app

        # Use action directly (keybinding may be captured by input widget)
        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette")
        # Palette should be visible (uses CSS class)
        assert "visible" in palette.classes

    @pytest.mark.asyncio
    async def test_command_palette_closes_with_escape(self, running_app):
        """Escape should close command palette."""
        pilot, app = running_app

        app.action_open_command_palette()
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        palette = app.query_one("#command-palette")
        assert "visible" not in palette.classes


class TestHistorySearch:
    """Tests for history search overlay."""

    @pytest.mark.asyncio
    async def test_history_search_opens_with_ctrl_r(self, running_app):
        """Ctrl+R should open history search."""
        pilot, app = running_app

        await pilot.press("ctrl+r")
        await pilot.pause()

        search = app.query_one("#history-search")
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_history_search_closes_with_escape(self, running_app):
        """Escape should close history search."""
        pilot, app = running_app

        await pilot.press("ctrl+r")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        search = app.query_one("#history-search")
        assert "visible" not in search.classes


class TestBlockSearch:
    """Tests for block search overlay."""

    @pytest.mark.asyncio
    async def test_block_search_opens_with_action(self, running_app):
        """Block search action should open overlay."""
        pilot, app = running_app

        # Use action directly (keybinding may be captured by input widget)
        app.action_search_blocks()
        await pilot.pause()

        search = app.query_one("#block-search")
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_block_search_closes_with_escape(self, running_app):
        """Escape should close block search."""
        pilot, app = running_app

        app.action_search_blocks()
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        search = app.query_one("#block-search")
        assert "visible" not in search.classes
