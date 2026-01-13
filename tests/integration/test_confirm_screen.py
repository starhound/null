"""Integration tests for ConfirmDialog screen."""

import pytest

from app import NullApp
from screens.confirm import ConfirmDialog


@pytest.fixture
async def confirm_app(temp_home, mock_storage, mock_ai_components):
    """Create app with ConfirmDialog pushed."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        screen = ConfirmDialog(title="Confirm Delete", message="Delete file?")
        app.push_screen(screen)
        await pilot.pause()
        yield app, pilot, screen


class TestConfirmDialogIntegration:
    """Integration tests for ConfirmDialog."""

    @pytest.mark.asyncio
    async def test_confirm_displays_message(self, confirm_app):
        """Test that ConfirmDialog displays with the correct message."""
        app, pilot, screen = confirm_app
        assert isinstance(app.screen, ConfirmDialog)

        message_label = screen.query_one("#confirm-message")
        assert "Delete file?" in str(message_label.content)

    @pytest.mark.asyncio
    async def test_confirm_displays_title(self, confirm_app):
        """Test that ConfirmDialog displays with the correct title."""
        app, pilot, screen = confirm_app

        title_static = screen.query_one("#confirm-title")
        assert "Confirm Delete" in str(title_static.content)

    @pytest.mark.asyncio
    async def test_yes_button_returns_true(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Yes button returns True."""
        app = NullApp()
        result = None

        def capture_result(value: bool) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ConfirmDialog(message="Delete file?")
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            yes_button = screen.query_one("#confirm-yes")
            await pilot.click(yes_button)
            await pilot.pause()

        assert result is True

    @pytest.mark.asyncio
    async def test_no_button_returns_false(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking No button returns False."""
        app = NullApp()
        result = None

        def capture_result(value: bool) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ConfirmDialog(message="Delete file?")
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            no_button = screen.query_one("#confirm-no")
            await pilot.click(no_button)
            await pilot.pause()

        assert result is False

    @pytest.mark.asyncio
    async def test_enter_key_confirms(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that Enter key returns True (confirm action)."""
        app = NullApp()
        result = None

        def capture_result(value: bool) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ConfirmDialog(message="Delete file?")
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            # Press Enter to confirm
            await pilot.press("enter")
            await pilot.pause()

        assert result is True

    @pytest.mark.asyncio
    async def test_escape_key_cancels(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that Escape key returns False (cancel action)."""
        app = NullApp()
        result = None

        def capture_result(value: bool) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = ConfirmDialog(message="Delete file?")
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            # Press Escape to cancel
            await pilot.press("escape")
            await pilot.pause()

        assert result is False

    @pytest.mark.asyncio
    async def test_yes_button_focused_on_mount(self, confirm_app):
        """Test that Yes button is focused when dialog opens."""
        app, pilot, screen = confirm_app

        yes_button = screen.query_one("#confirm-yes")
        assert yes_button.has_focus
