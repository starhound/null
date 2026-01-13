"""Integration tests for DisclaimerScreen."""

import pytest

from app import NullApp
from screens.disclaimer import DISCLAIMER_TEXT, DisclaimerScreen


@pytest.fixture
async def disclaimer_app(temp_home, mock_storage, mock_ai_components):
    """Create app with DisclaimerScreen pushed."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        screen = DisclaimerScreen()
        app.push_screen(screen)
        await pilot.pause()
        yield app, pilot, screen


class TestDisclaimerScreenIntegration:
    """Integration tests for DisclaimerScreen."""

    @pytest.mark.asyncio
    async def test_disclaimer_title_shown(self, disclaimer_app):
        """Test that disclaimer title is displayed."""
        app, pilot, screen = disclaimer_app

        title_static = screen.query_one("#disclaimer-title")
        assert "AI USAGE DISCLAIMER" in str(title_static.content)

    @pytest.mark.asyncio
    async def test_disclaimer_text_shown(self, disclaimer_app):
        """Test that disclaimer text content is displayed."""
        app, pilot, screen = disclaimer_app

        message_static = screen.query_one("#disclaimer-message")
        content = str(message_static.content)
        assert "AI models can produce incorrect" in content
        assert "You are responsible for reviewing" in content

    @pytest.mark.asyncio
    async def test_accept_button_dismisses_with_true(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Test that clicking Accept button dismisses with True."""
        app = NullApp()
        result = None

        def capture_result(value: bool) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = DisclaimerScreen()
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            accept_button = screen.query_one("#confirm-yes")
            await pilot.click(accept_button)
            await pilot.pause()

        assert result is True

    @pytest.mark.asyncio
    async def test_enter_key_accepts(self, temp_home, mock_storage, mock_ai_components):
        """Test that Enter key accepts the disclaimer."""
        app = NullApp()
        result = None

        def capture_result(value: bool) -> None:
            nonlocal result
            result = value

        async with app.run_test(size=(120, 50)) as pilot:
            screen = DisclaimerScreen()
            app.push_screen(screen, callback=capture_result)
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

        assert result is True
