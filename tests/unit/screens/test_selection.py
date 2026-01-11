import pytest
from unittest.mock import MagicMock, patch

from screens.selection import (
    SelectionListScreen,
    ThemeSelectionScreen,
    ModelItem,
    ModelListScreen,
)


class TestSelectionListScreen:
    def test_init_stores_title_and_items(self):
        screen = SelectionListScreen(title="Pick One", items=["a", "b", "c"])
        assert screen._screen_title == "Pick One"
        assert screen.items == ["a", "b", "c"]

    def test_init_empty_items(self):
        screen = SelectionListScreen(title="Empty", items=[])
        assert screen.items == []

    def test_bindings_defined(self):
        screen = SelectionListScreen(title="Test", items=["x"])
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    def test_button_pressed_dismisses_none(self):
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)


class TestThemeSelectionScreen:
    def test_init_stores_title_and_items(self):
        screen = ThemeSelectionScreen(title="Themes", items=["dark", "light"])
        assert screen._screen_title == "Themes"
        assert screen.items == ["dark", "light"]
        assert screen._original_theme is None

    def test_bindings_defined(self):
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys


class TestModelItem:
    def test_init_sets_attributes(self):
        item = ModelItem(provider="openai", model="gpt-4")
        assert item.provider == "openai"
        assert item.model == "gpt-4"
        assert item.can_focus is True

    def test_on_click_posts_selected_message(self):
        item = ModelItem(provider="anthropic", model="claude-3")
        item.post_message = MagicMock()

        item.on_click()

        item.post_message.assert_called_once()
        message = item.post_message.call_args[0][0]
        assert isinstance(message, ModelItem.Selected)
        assert message.provider == "anthropic"
        assert message.model == "claude-3"

    def test_on_key_enter_posts_selected_message(self):
        item = ModelItem(provider="ollama", model="llama3")
        item.post_message = MagicMock()

        mock_event = MagicMock()
        mock_event.key = "enter"

        item.on_key(mock_event)

        item.post_message.assert_called_once()
        mock_event.stop.assert_called_once()

    def test_on_key_other_key_no_message(self):
        item = ModelItem(provider="ollama", model="llama3")
        item.post_message = MagicMock()

        mock_event = MagicMock()
        mock_event.key = "space"

        item.on_key(mock_event)

        item.post_message.assert_not_called()


class TestModelItemSelected:
    def test_selected_message_attributes(self):
        msg = ModelItem.Selected(provider="test_provider", model="test_model")
        assert msg.provider == "test_provider"
        assert msg.model == "test_model"


class TestModelListScreen:
    def test_init_default_values(self):
        screen = ModelListScreen()
        assert screen.ai_manager is None
        assert screen._spinner_index == 0
        assert screen._models_by_provider == {}
        assert screen._total_providers == 0

    def test_init_with_fetch_func(self):
        mock_func = MagicMock()
        screen = ModelListScreen(fetch_func=mock_func)
        assert screen.ai_manager == mock_func

    def test_bindings_defined(self):
        screen = ModelListScreen()
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys
        assert "up" in binding_keys
        assert "down" in binding_keys
        assert "tab" in binding_keys
        assert "shift+tab" in binding_keys

    def test_spinner_frames_defined(self):
        assert len(ModelListScreen.SPINNER_FRAMES) > 0

    def test_reactive_attributes(self):
        screen = ModelListScreen()
        assert screen.is_loading is True
        assert screen.search_query == ""

    def test_button_pressed_dismisses_none(self):
        screen = ModelListScreen()
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        screen = ModelListScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)

    def test_on_model_item_selected(self):
        screen = ModelListScreen()
        screen.dismiss = MagicMock()

        mock_message = MagicMock()
        mock_message.provider = "openai"
        mock_message.model = "gpt-4"

        screen.on_model_item_selected(mock_message)
        screen.dismiss.assert_called_once_with(("openai", "gpt-4"))

    def test_stop_spinner(self):
        screen = ModelListScreen()
        mock_timer = MagicMock()
        screen._spinner_timer = mock_timer

        screen._stop_spinner()

        mock_timer.stop.assert_called_once()
        assert screen._spinner_timer is None

    def test_stop_spinner_no_timer(self):
        screen = ModelListScreen()
        screen._spinner_timer = None
        screen._stop_spinner()
        assert screen._spinner_timer is None
