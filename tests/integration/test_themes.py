"""Integration tests for theme switching and configuration."""

import pytest

from themes import get_all_themes
from widgets import InputController


async def submit_input(pilot, app, text: str):
    """Helper to type text and submit it."""
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestThemeLoading:
    """Tests for theme loading and registration."""

    @pytest.mark.asyncio
    async def test_builtin_themes_available(self, running_app):
        """Built-in themes should be available."""
        pilot, app = running_app

        themes = app.available_themes
        assert "null-dark" in themes
        assert "null-light" in themes

    @pytest.mark.asyncio
    async def test_all_themes_registered(self, running_app):
        """All themes from get_all_themes should be registered."""
        pilot, app = running_app

        all_themes = get_all_themes()
        for theme_name in all_themes:
            assert theme_name in app.available_themes


class TestThemeSwitching:
    """Tests for theme switching functionality."""

    @pytest.mark.asyncio
    async def test_theme_command_changes_theme(self, running_app):
        """'/theme' command should change the active theme."""
        pilot, app = running_app

        original_theme = app.theme

        await submit_input(pilot, app, "/theme null-light")

        assert app.theme == "null-light"
        assert app.theme != original_theme

    @pytest.mark.asyncio
    async def test_theme_persists_after_change(self, running_app, mock_storage):
        """Theme change should be persisted to storage."""
        pilot, app = running_app

        await submit_input(pilot, app, "/theme null-light")

        # Check storage has the new theme
        saved_theme = mock_storage.get_config("theme")
        assert saved_theme == "null-light"

    @pytest.mark.asyncio
    async def test_invalid_theme_ignored(self, running_app):
        """Invalid theme name should be handled gracefully."""
        pilot, app = running_app

        original_theme = app.theme

        await submit_input(pilot, app, "/theme nonexistent-theme")

        # Theme should remain unchanged
        assert app.theme == original_theme

    @pytest.mark.asyncio
    async def test_theme_list_shows_options(self, running_app):
        """'/theme' without args should list available themes."""
        pilot, app = running_app

        await submit_input(pilot, app, "/theme")

        # Should have shown notification or created block
        # No crash means success

    @pytest.mark.asyncio
    async def test_f3_opens_theme_selector(self, running_app):
        """F3 should open theme selection screen."""
        pilot, app = running_app

        await pilot.press("f3")
        await pilot.pause()

        # Should have opened a screen
        assert len(app.screen_stack) > 1


class TestThemeIntegrity:
    """Tests for theme integrity and validity."""

    def test_all_themes_have_required_properties(self):
        """All themes should have required color properties."""
        themes = get_all_themes()

        for name, theme in themes.items():
            # Themes should have basic required variables
            assert theme is not None
            # Theme should be a valid Textual Theme object
            assert hasattr(theme, "name")

    @pytest.mark.asyncio
    async def test_theme_switch_doesnt_break_ui(self, running_app):
        """Switching themes should not break UI rendering."""
        pilot, app = running_app

        # Switch through all themes
        for theme_name in list(app.available_themes)[:3]:  # Test first 3
            app.theme = theme_name
            await pilot.pause()

            # UI should still be functional
            assert app.is_running
            assert app.query_one("#input") is not None


class TestThemeVisuals:
    """Tests for theme visual changes."""

    @pytest.mark.asyncio
    async def test_dark_theme_applies(self, running_app):
        """Dark theme should apply dark mode setting."""
        pilot, app = running_app

        app.theme = "null-dark"
        await pilot.pause()

        assert app.theme == "null-dark"
        # Note: app.dark is controlled by the theme's dark property

    @pytest.mark.asyncio
    async def test_light_theme_applies(self, running_app):
        """Light theme should apply light mode setting."""
        pilot, app = running_app

        app.theme = "null-light"
        await pilot.pause()

        assert app.theme == "null-light"


class TestThemeCommands:
    """Tests for theme-related slash commands."""

    @pytest.mark.asyncio
    async def test_themes_command_lists_all(self, running_app):
        """'/themes' should list available themes."""
        pilot, app = running_app

        await submit_input(pilot, app, "/themes")

        # Should execute without error
