"""Integration tests for HelpScreen."""

import pytest
from textual.widgets import Button, DataTable, Label

from app import NullApp
from screens.help import HelpScreen


@pytest.fixture
async def help_app(mock_home):
    """Fixture that launches NullApp and pushes HelpScreen."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await app.push_screen(HelpScreen())
        await pilot.pause()
        yield app, pilot


class TestHelpScreenIntegration:
    """Integration tests for the HelpScreen modal."""

    @pytest.mark.asyncio
    async def test_help_content_rendered(self, help_app):
        """Test that help content is rendered with title label."""
        app, pilot = help_app
        label = app.screen.query_one(Label)
        assert "Help" in str(label.render())

    @pytest.mark.asyncio
    async def test_keybindings_shown_in_table(self, help_app):
        """Test that keybindings are shown in the DataTable."""
        app, pilot = help_app
        table = app.screen.query_one(DataTable)
        assert len(table.columns) == 3
        assert table.row_count > 0

    @pytest.mark.asyncio
    async def test_table_contains_expected_commands(self, help_app):
        """Test that expected commands appear in the help table."""
        app, pilot = help_app
        table = app.screen.query_one(DataTable)
        assert table.row_count >= 10

    @pytest.mark.asyncio
    async def test_dismiss_via_escape(self, help_app):
        """Test that the screen can be dismissed with Escape key."""
        app, pilot = help_app
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)

    @pytest.mark.asyncio
    async def test_dismiss_via_close_button(self, help_app):
        """Test that the screen can be dismissed via close button."""
        app, pilot = help_app
        assert isinstance(app.screen, HelpScreen)
        await pilot.click("#close_btn")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)
