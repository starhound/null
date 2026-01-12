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
        _pilot, app = running_app
        # If we get here, app mounted successfully
        assert app.is_running

    @pytest.mark.asyncio
    async def test_app_has_required_widgets(self, running_app):
        """App should have all required core widgets."""
        _pilot, app = running_app

        # Core widgets should exist
        assert app.query_one("#app-header", AppHeader) is not None
        assert app.query_one("#history", HistoryViewport) is not None
        assert app.query_one("#input", InputController) is not None
        assert app.query_one("#status-bar", StatusBar) is not None
        assert app.query_one(Footer) is not None

    @pytest.mark.asyncio
    async def test_app_has_optional_widgets(self, running_app):
        """App should have optional overlay widgets (hidden by default)."""
        _pilot, app = running_app

        # These should exist but may be hidden
        assert app.query_one("#suggester", CommandSuggester)
        assert app.query_one("#command-palette", CommandPalette)

    @pytest.mark.asyncio
    async def test_input_container_structure(self, running_app):
        """Input container should have prompt and input widget."""
        _pilot, app = running_app

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
        _pilot, app = running_app
        assert app.theme is not None

    @pytest.mark.asyncio
    async def test_default_theme_is_null_dark(self, running_app):
        """Default theme should be null-dark when no saved theme."""
        _pilot, app = running_app
        # With fresh temp storage, theme should default to null-dark
        assert app.theme == "null-dark"

    @pytest.mark.asyncio
    async def test_available_themes_registered(self, running_app):
        """Custom themes should be registered."""
        _pilot, app = running_app
        # Should have at least null-dark and null-light
        themes = app.available_themes
        assert "null-dark" in themes


class TestAppState:
    """Tests for app state management."""

    @pytest.mark.asyncio
    async def test_app_has_blocks_list(self, running_app):
        """App should have empty blocks list on fresh start."""
        _pilot, app = running_app
        assert isinstance(app.blocks, list)

    @pytest.mark.asyncio
    async def test_app_has_process_manager(self, running_app):
        """App should have process manager initialized."""
        _pilot, app = running_app
        assert app.process_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_handlers(self, running_app):
        """App should have all handlers initialized."""
        _pilot, app = running_app
        assert app.command_handler is not None
        assert app.execution_handler is not None
        assert app.input_handler is not None

    @pytest.mark.asyncio
    async def test_app_not_busy_initially(self, running_app):
        """App should not be busy on startup."""
        _pilot, app = running_app
        assert not app.is_busy()


class TestAppRendering:
    """Tests for basic rendering."""

    @pytest.mark.asyncio
    async def test_header_renders(self, running_app):
        """App header should render."""
        _pilot, app = running_app
        header = app.query_one("#app-header", AppHeader)
        # Header should be visible
        assert header.display is True

    @pytest.mark.asyncio
    async def test_status_bar_renders(self, running_app):
        """Status bar should render."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        assert status.display is True

    @pytest.mark.asyncio
    async def test_history_viewport_renders(self, running_app):
        """History viewport should render and be empty initially."""
        _pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)
        assert history.display is True


class TestAppModes:
    """Tests for CLI/AI mode functionality."""

    @pytest.mark.asyncio
    async def test_app_starts_in_cli_mode(self, running_app):
        """App should start in CLI mode by default."""
        _pilot, app = running_app
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


class TestStatusBar:
    """Tests for status bar widget behavior."""

    @pytest.mark.asyncio
    async def test_status_bar_has_mode_indicator(self, running_app):
        """Status bar should have mode indicator."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        mode_indicator = status.query_one("#mode-indicator", Label)
        assert mode_indicator is not None

    @pytest.mark.asyncio
    async def test_status_bar_has_provider_indicator(self, running_app):
        """Status bar should have provider indicator."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        provider_indicator = status.query_one("#provider-indicator", Label)
        assert provider_indicator is not None

    @pytest.mark.asyncio
    async def test_status_bar_has_context_indicator(self, running_app):
        """Status bar should have context indicator."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        context_indicator = status.query_one("#context-indicator", Label)
        assert context_indicator is not None

    @pytest.mark.asyncio
    async def test_status_bar_mode_updates_on_toggle(self, running_app):
        """Status bar mode should update when AI mode is toggled."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        initial_mode = status.mode
        assert initial_mode == "CLI"

        app.action_toggle_ai_mode()
        await pilot.pause()

        assert status.mode == "AI"

    @pytest.mark.asyncio
    async def test_status_bar_has_git_indicator(self, running_app):
        """Status bar should have git branch indicator."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        git_indicator = status.query_one("#git-indicator", Label)
        assert git_indicator is not None

    @pytest.mark.asyncio
    async def test_status_bar_has_mcp_indicator(self, running_app):
        """Status bar should have MCP tools indicator."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        mcp_indicator = status.query_one("#mcp-indicator", Label)
        assert mcp_indicator is not None

    @pytest.mark.asyncio
    async def test_status_bar_has_process_indicator(self, running_app):
        """Status bar should have process count indicator."""
        _pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)
        process_indicator = status.query_one("#process-indicator", Label)
        assert process_indicator is not None


class TestSidebar:
    """Tests for sidebar toggle and display."""

    @pytest.mark.asyncio
    async def test_sidebar_initially_hidden(self, running_app):
        """Sidebar should be hidden by default."""
        _pilot, app = running_app
        sidebar = app.query_one("#sidebar")
        assert sidebar.display is False

    @pytest.mark.asyncio
    async def test_sidebar_toggles_with_action(self, running_app):
        """toggle_file_tree action should show/hide sidebar."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar")

        assert sidebar.display is False

        app.action_toggle_file_tree()
        await pilot.pause()

        assert sidebar.display is True

    @pytest.mark.asyncio
    async def test_sidebar_toggles_back(self, running_app):
        """Toggling sidebar twice should hide it again."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar")

        app.action_toggle_file_tree()
        await pilot.pause()
        assert sidebar.display is True

        app.action_toggle_file_tree()
        await pilot.pause()
        assert sidebar.display is False

    @pytest.mark.asyncio
    async def test_sidebar_has_directory_tree(self, running_app):
        """Sidebar should contain directory tree when visible."""
        pilot, app = running_app
        from textual.widgets import DirectoryTree

        app.action_toggle_file_tree()
        await pilot.pause()

        sidebar = app.query_one("#sidebar")
        tree = sidebar.query_one(DirectoryTree)
        assert tree is not None


class TestAppHeader:
    """Tests for app header widget."""

    @pytest.mark.asyncio
    async def test_header_has_title(self, running_app):
        """App header should display title."""
        _pilot, app = running_app
        header = app.query_one("#app-header", AppHeader)
        title_label = header.query_one(".header-title", Label)
        assert title_label is not None

    @pytest.mark.asyncio
    async def test_header_has_left_section(self, running_app):
        """App header should have left section with icon/provider."""
        _pilot, app = running_app
        header = app.query_one("#app-header", AppHeader)
        left_label = header.query_one(".header-left", Label)
        assert left_label is not None

    @pytest.mark.asyncio
    async def test_header_has_clock(self, running_app):
        """App header should display clock."""
        _pilot, app = running_app
        header = app.query_one("#app-header", AppHeader)
        clock_label = header.query_one("#header-clock", Label)
        assert clock_label is not None
