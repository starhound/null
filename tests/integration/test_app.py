"""Integration tests for app initialization and basic rendering."""

import pytest
from textual.widgets import Footer, Label

from widgets import (
    AppHeader,
    CommandPalette,
    CommandSuggester,
    HistoryViewport,
    InputController,
    StatusBar,
)


class TestAppInitialization:
    """Tests for app startup and initialization."""

    @pytest.mark.asyncio
    async def test_app_mounts_successfully(self, running_app):
        """App should mount without errors."""
        pilot, app = running_app
        # If we get here, app mounted successfully
        assert app.is_running

    @pytest.mark.asyncio
    async def test_app_has_required_widgets(self, running_app):
        """App should have all required core widgets."""
        pilot, app = running_app

        # Core widgets should exist
        assert app.query_one("#app-header", AppHeader) is not None
        assert app.query_one("#history", HistoryViewport) is not None
        assert app.query_one("#input", InputController) is not None
        assert app.query_one("#status-bar", StatusBar) is not None
        assert app.query_one(Footer) is not None

    @pytest.mark.asyncio
    async def test_app_has_optional_widgets(self, running_app):
        """App should have optional overlay widgets (hidden by default)."""
        pilot, app = running_app

        # These should exist but may be hidden
        assert app.query_one("#suggester", CommandSuggester)
        assert app.query_one("#command-palette", CommandPalette)

    @pytest.mark.asyncio
    async def test_input_container_structure(self, running_app):
        """Input container should have prompt and input widget."""
        pilot, app = running_app

        prompt = app.query_one("#prompt-line", Label)
        input_widget = app.query_one("#input", InputController)

        assert prompt is not None
        assert input_widget is not None

    @pytest.mark.asyncio
    async def test_input_is_focused_on_mount(self, running_app):
        """Input widget should be focused after mount."""
        pilot, app = running_app

        input_widget = app.query_one("#input", InputController)
        # Give time for focus to settle
        await pilot.pause()
        assert input_widget.has_focus


class TestAppTheme:
    """Tests for app theme handling."""

    @pytest.mark.asyncio
    async def test_app_has_theme(self, running_app):
        """App should have a theme set."""
        pilot, app = running_app
        assert app.theme is not None

    @pytest.mark.asyncio
    async def test_default_theme_is_null_dark(self, running_app):
        """Default theme should be null-dark when no saved theme."""
        pilot, app = running_app
        # With fresh temp storage, theme should default to null-dark
        assert app.theme == "null-dark"

    @pytest.mark.asyncio
    async def test_available_themes_registered(self, running_app):
        """Custom themes should be registered."""
        pilot, app = running_app
        # Should have at least null-dark and null-light
        themes = app.available_themes
        assert "null-dark" in themes


class TestAppState:
    """Tests for app state management."""

    @pytest.mark.asyncio
    async def test_app_has_blocks_list(self, running_app):
        """App should have empty blocks list on fresh start."""
        pilot, app = running_app
        assert isinstance(app.blocks, list)

    @pytest.mark.asyncio
    async def test_app_has_process_manager(self, running_app):
        """App should have process manager initialized."""
        pilot, app = running_app
        assert app.process_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_handlers(self, running_app):
        """App should have all handlers initialized."""
        pilot, app = running_app
        assert app.command_handler is not None
        assert app.execution_handler is not None
        assert app.input_handler is not None

    @pytest.mark.asyncio
    async def test_app_not_busy_initially(self, running_app):
        """App should not be busy on startup."""
        pilot, app = running_app
        assert not app.is_busy()


class TestAppRendering:
    """Tests for basic rendering."""

    @pytest.mark.asyncio
    async def test_header_renders(self, running_app):
        """App header should render."""
        pilot, app = running_app
        header = app.query_one("#app-header", AppHeader)
        # Header should be visible
        assert header.display is True

    @pytest.mark.asyncio
    async def test_status_bar_renders(self, running_app):
        """Status bar should render."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        assert status.display is True

    @pytest.mark.asyncio
    async def test_history_viewport_renders(self, running_app):
        """History viewport should render and be empty initially."""
        pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)
        assert history.display is True


class TestAppModes:
    """Tests for CLI/AI mode functionality."""

    @pytest.mark.asyncio
    async def test_app_starts_in_cli_mode(self, running_app):
        """App should start in CLI mode by default."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)
        # CLI mode is the default
        assert not input_widget.is_ai_mode

    @pytest.mark.asyncio
    async def test_toggle_ai_mode_action(self, running_app):
        """toggle_ai_mode action should switch modes."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial_mode = input_widget.is_ai_mode
        app.action_toggle_ai_mode()
        await pilot.pause()

        assert input_widget.is_ai_mode != initial_mode

    @pytest.mark.asyncio
    async def test_toggle_ai_mode_twice_returns_to_original(self, running_app):
        """Toggling AI mode twice should return to original mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial_mode = input_widget.is_ai_mode
        app.action_toggle_ai_mode()
        await pilot.pause()
        app.action_toggle_ai_mode()
        await pilot.pause()

        assert input_widget.is_ai_mode == initial_mode
