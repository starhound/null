import pytest
from unittest.mock import MagicMock

from screens.tools import ToolsScreen


class TestToolsScreen:
    def test_bindings_defined(self):
        screen = ToolsScreen()
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    def test_compose_yields_container(self):
        screen = ToolsScreen()
        widgets = list(screen.compose())
        assert len(widgets) == 1

    def test_button_pressed_dismisses(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_result(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss(result="test_result")
        screen.dismiss.assert_called_once_with("test_result")
