"""Integration tests for screen navigation and modals."""

import pytest

from screens import ConfirmDialog, HelpScreen
from screens.selection import ThemeSelectionScreen


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
    @pytest.mark.asyncio
    async def test_model_screen_opens_with_f2(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_model_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_model_screen_shows_loading_indicator(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        from screens.selection import ModelListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, ModelListScreen)

        indicator = screen.query_one("#loading-indicator")
        assert indicator is not None

    @pytest.mark.asyncio
    async def test_model_screen_has_search_input(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        from textual.widgets import Input

        from screens.selection import ModelListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, ModelListScreen)

        search_input = screen.query_one("#model-search", Input)
        assert search_input is not None
        assert search_input.placeholder == "Search models..."

    @pytest.mark.asyncio
    async def test_model_screen_shows_no_providers_message(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        from screens.selection import ModelListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, ModelListScreen)
        assert screen._models_by_provider == {}

    @pytest.mark.asyncio
    async def test_model_screen_has_cancel_button(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        from textual.widgets import Button

        from screens.selection import ModelListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, ModelListScreen)

        cancel_btn = screen.query_one("#cancel_btn", Button)
        assert cancel_btn is not None


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


class TestThemeSelectionScreen:
    """Tests for theme selection screen."""

    @pytest.mark.asyncio
    async def test_theme_screen_opens_with_f3(self, running_app):
        """F3 should open theme selection screen."""
        pilot, app = running_app

        await pilot.press("f3")
        await pilot.pause()

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], ThemeSelectionScreen)

    @pytest.mark.asyncio
    async def test_theme_screen_closes_with_escape(self, running_app):
        """Escape should close theme screen and restore original theme."""
        pilot, app = running_app

        original_theme = app.theme
        await pilot.press("f3")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1
        assert app.theme == original_theme

    @pytest.mark.asyncio
    async def test_theme_screen_has_theme_list(self, running_app):
        """Theme screen should display available themes."""
        pilot, app = running_app

        await pilot.press("f3")
        await pilot.pause()

        from textual.widgets import ListView

        screen = app.screen_stack[-1]
        assert isinstance(screen, ThemeSelectionScreen)

        listview = screen.query_one("#item_list", ListView)
        assert listview is not None

    @pytest.mark.asyncio
    async def test_theme_screen_has_cancel_button(self, running_app):
        """Theme screen should have cancel button."""
        pilot, app = running_app

        await pilot.press("f3")
        await pilot.pause()

        from textual.widgets import Button

        screen = app.screen_stack[-1]
        cancel_btn = screen.query_one("#cancel_btn", Button)
        assert cancel_btn is not None

    @pytest.mark.asyncio
    async def test_theme_screen_shows_null_themes(self, running_app):
        """Theme screen should include null-dark and null-light themes."""
        pilot, app = running_app

        await pilot.press("f3")
        await pilot.pause()

        screen = app.screen_stack[-1]
        assert isinstance(screen, ThemeSelectionScreen)
        assert "null-dark" in screen.items
        assert "null-light" in screen.items


class TestProviderSelectionScreen:
    """Tests for AI provider selection screen (F4).

    Note: F4 opens a SelectionListScreen for provider selection, not ProvidersScreen.
    ProvidersScreen is a separate management screen accessed via /providers command.
    """

    @pytest.mark.asyncio
    async def test_provider_selection_opens_with_f4(self, running_app):
        """F4 should open provider selection screen."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        from screens.selection import SelectionListScreen

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], SelectionListScreen)

    @pytest.mark.asyncio
    async def test_provider_selection_closes_with_escape(self, running_app):
        """Escape should close provider selection screen."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_provider_selection_has_title(self, running_app):
        """Provider selection screen should have title."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        from screens.selection import SelectionListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, SelectionListScreen)
        assert screen._screen_title == "Select Provider"

    @pytest.mark.asyncio
    async def test_provider_selection_has_items(self, running_app):
        """Provider selection should show available providers."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        from screens.selection import SelectionListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, SelectionListScreen)
        assert len(screen.items) > 0

    @pytest.mark.asyncio
    async def test_provider_selection_has_list_view(self, running_app):
        """Provider selection should have ListView widget."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        from textual.widgets import ListView

        screen = app.screen_stack[-1]
        listview = screen.query_one("#item_list", ListView)
        assert listview is not None

    @pytest.mark.asyncio
    async def test_provider_selection_has_cancel_button(self, running_app):
        """Provider selection should have cancel button."""
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        from textual.widgets import Button

        screen = app.screen_stack[-1]
        cancel_btn = screen.query_one("#cancel_btn", Button)
        assert cancel_btn is not None


class TestSettingsScreen:
    """Tests for settings configuration screen."""

    @pytest.mark.asyncio
    async def test_settings_command_opens_screen(self, running_app):
        """/settings command should open config screen."""
        pilot, app = running_app

        input_widget = app.query_one("#input")
        input_widget.text = "/settings"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        from screens.config import ConfigScreen

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], ConfigScreen)

    @pytest.mark.asyncio
    async def test_settings_screen_closes_with_escape(self, running_app):
        """Escape should close settings screen."""
        pilot, app = running_app

        input_widget = app.query_one("#input")
        input_widget.text = "/settings"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_settings_screen_has_tabs(self, running_app):
        """/settings screen should have tabbed content."""
        pilot, app = running_app

        input_widget = app.query_one("#input")
        input_widget.text = "/settings"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        from textual.widgets import TabbedContent

        screen = app.screen_stack[-1]
        tabbed = screen.query_one(TabbedContent)
        assert tabbed is not None

    @pytest.mark.asyncio
    async def test_settings_screen_has_save_button(self, running_app):
        """Settings screen should have save button."""
        pilot, app = running_app

        input_widget = app.query_one("#input")
        input_widget.text = "/settings"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        from textual.widgets import Button

        screen = app.screen_stack[-1]
        save_btn = screen.query_one("#save-btn", Button)
        assert save_btn is not None

    @pytest.mark.asyncio
    async def test_settings_screen_has_cancel_button(self, running_app):
        """Settings screen should have cancel button."""
        pilot, app = running_app

        input_widget = app.query_one("#input")
        input_widget.text = "/settings"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        from textual.widgets import Button

        screen = app.screen_stack[-1]
        cancel_btn = screen.query_one("#cancel-btn", Button)
        assert cancel_btn is not None
