"""Tests for the help screen."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from screens.help import HelpScreen


class TestHelpScreen:
    def test_bindings_defined(self):
        screen = HelpScreen()
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    def test_compose_yields_container(self):
        screen = HelpScreen()
        widgets = list(screen.compose())
        assert len(widgets) == 1

    def test_button_pressed_close(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "close_btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once()

    def test_button_pressed_other_no_dismiss(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "other-button"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_not_called()

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss(result="test")
        screen.dismiss.assert_called_once_with("test")
