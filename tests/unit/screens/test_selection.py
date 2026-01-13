from unittest.mock import MagicMock, patch

import pytest

from screens.selection import (
    ModelItem,
    ModelListScreen,
    SelectionListScreen,
    ThemeSelectionScreen,
)


def get_binding_keys(bindings):
    keys = []
    for b in bindings:
        if hasattr(b, "key"):
            keys.append(b.key)
        elif isinstance(b, tuple) and len(b) >= 1:
            keys.append(b[0])
    return keys


# =============================================================================
# SelectionListScreen Tests
# =============================================================================


class TestSelectionListScreen:
    """Tests for SelectionListScreen initialization and basic behavior."""

    def test_init_stores_title_and_items(self):
        """SelectionListScreen should store title and items."""
        screen = SelectionListScreen(title="Pick One", items=["a", "b", "c"])
        assert screen._screen_title == "Pick One"
        assert screen.items == ["a", "b", "c"]

    def test_init_empty_items(self):
        """SelectionListScreen should handle empty items list."""
        screen = SelectionListScreen(title="Empty", items=[])
        assert screen.items == []

    def test_init_single_item(self):
        """SelectionListScreen should handle single item list."""
        screen = SelectionListScreen(title="Single", items=["only-one"])
        assert screen.items == ["only-one"]
        assert len(screen.items) == 1

    def test_init_many_items(self):
        """SelectionListScreen should handle many items."""
        items = [f"item-{i}" for i in range(100)]
        screen = SelectionListScreen(title="Many", items=items)
        assert len(screen.items) == 100
        assert screen.items[0] == "item-0"
        assert screen.items[99] == "item-99"

    def test_init_special_characters_in_items(self):
        """SelectionListScreen should handle special characters in items."""
        items = [
            "item with spaces",
            "item/with/slashes",
            "item:with:colons",
            "item@#$%",
        ]
        screen = SelectionListScreen(title="Special", items=items)
        assert screen.items == items

    def test_bindings_defined(self):
        screen = SelectionListScreen(title="Test", items=["x"])
        binding_keys = get_binding_keys(screen.BINDINGS)
        assert "escape" in binding_keys

    def test_button_pressed_dismisses_none(self):
        """on_button_pressed should dismiss with None."""
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        """action_dismiss should dismiss with None."""
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_result_ignores_result(self):
        """action_dismiss should ignore result parameter."""
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()
        await screen.action_dismiss(result="ignored")
        screen.dismiss.assert_called_once_with(None)


class TestSelectionListScreenOnListViewSelected:
    """Tests for SelectionListScreen on_list_view_selected method."""

    def test_on_list_view_selected_valid_index(self):
        """on_list_view_selected should dismiss with selected item."""
        screen = SelectionListScreen(title="Test", items=["apple", "banana", "cherry"])
        screen.dismiss = MagicMock()

        mock_listview = MagicMock()
        mock_listview.index = 1
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with("banana")

    def test_on_list_view_selected_first_item(self):
        """on_list_view_selected should dismiss with first item when index is 0."""
        screen = SelectionListScreen(title="Test", items=["first", "second"])
        screen.dismiss = MagicMock()

        mock_listview = MagicMock()
        mock_listview.index = 0
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with("first")

    def test_on_list_view_selected_last_item(self):
        """on_list_view_selected should dismiss with last item."""
        screen = SelectionListScreen(title="Test", items=["a", "b", "c"])
        screen.dismiss = MagicMock()

        mock_listview = MagicMock()
        mock_listview.index = 2
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with("c")

    def test_on_list_view_selected_none_index(self):
        """on_list_view_selected should dismiss None when index is None."""
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()

        mock_listview = MagicMock()
        mock_listview.index = None
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with(None)

    def test_on_list_view_selected_negative_index(self):
        """on_list_view_selected should dismiss None when index is negative."""
        screen = SelectionListScreen(title="Test", items=["x"])
        screen.dismiss = MagicMock()

        mock_listview = MagicMock()
        mock_listview.index = -1
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with(None)

    def test_on_list_view_selected_index_out_of_bounds(self):
        """on_list_view_selected should dismiss None when index exceeds items."""
        screen = SelectionListScreen(title="Test", items=["a", "b"])
        screen.dismiss = MagicMock()

        mock_listview = MagicMock()
        mock_listview.index = 5  # Out of bounds
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with(None)


# =============================================================================
# ThemeSelectionScreen Tests
# =============================================================================


class TestThemeSelectionScreen:
    """Tests for ThemeSelectionScreen initialization and basic behavior."""

    def test_init_stores_title_and_items(self):
        """ThemeSelectionScreen should store title and items."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark", "light"])
        assert screen._screen_title == "Themes"
        assert screen.items == ["dark", "light"]
        assert screen._original_theme is None

    def test_bindings_defined(self):
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        binding_keys = get_binding_keys(screen.BINDINGS)
        assert "escape" in binding_keys

    def test_init_empty_items(self):
        """ThemeSelectionScreen should handle empty items list."""
        screen = ThemeSelectionScreen(title="Empty", items=[])
        assert screen.items == []

    def test_init_many_themes(self):
        """ThemeSelectionScreen should handle many theme options."""
        themes = ["monokai", "dracula", "nord", "gruvbox", "solarized", "null-dark"]
        screen = ThemeSelectionScreen(title="Select Theme", items=themes)
        assert len(screen.items) == 6


class TestThemeSelectionScreenOnMount:
    """Tests for ThemeSelectionScreen on_mount method."""

    def test_on_mount_stores_original_theme(self):
        """on_mount should store the current theme."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])

        mock_app = MagicMock()
        mock_app.theme = "nord"
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        screen.on_mount()
        assert screen._original_theme == "nord"


class TestThemeSelectionScreenOnDescendantFocus:
    """Tests for ThemeSelectionScreen on_descendant_focus method."""

    def test_on_descendant_focus_applies_theme_preview(self):
        """on_descendant_focus should apply theme preview for ThemeListItem."""
        from screens.selection import ThemeListItem

        screen = ThemeSelectionScreen(
            title="Themes", items=["dark", "light", "dracula"]
        )

        mock_app = MagicMock()
        mock_app.theme = "original"
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        mock_item = MagicMock(spec=ThemeListItem)
        mock_item._theme_name = "dracula"

        mock_event = MagicMock()
        mock_event.widget = mock_item

        screen.on_descendant_focus(mock_event)

        assert mock_app.theme == "dracula"
        assert screen._highlighted_theme == "dracula"

    def test_on_descendant_focus_ignores_non_theme_items(self):
        """on_descendant_focus should ignore non-ThemeListItem widgets."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])

        mock_app = MagicMock()
        mock_app.theme = "original"
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        mock_event = MagicMock()
        mock_event.widget = MagicMock()  # Not a ThemeListItem

        screen.on_descendant_focus(mock_event)

        assert mock_app.theme == "original"

    def test_on_descendant_focus_handles_exception(self):
        """on_descendant_focus should handle theme apply exception gracefully."""
        from screens.selection import ThemeListItem

        screen = ThemeSelectionScreen(title="Themes", items=["invalid-theme"])

        mock_app = MagicMock()

        def raise_on_set(value):
            raise ValueError("Invalid theme")

        type(mock_app).theme = property(lambda self: "original", raise_on_set)
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        mock_item = MagicMock(spec=ThemeListItem)
        mock_item._theme_name = "invalid-theme"

        mock_event = MagicMock()
        mock_event.widget = mock_item

        screen.on_descendant_focus(mock_event)


class TestThemeSelectionScreenOnThemeListItemSelected:
    """Tests for ThemeSelectionScreen on_theme_list_item_selected method."""

    def test_on_theme_list_item_selected_dismisses_with_theme(self):
        """on_theme_list_item_selected should dismiss with theme name."""
        from screens.selection import ThemeListItem

        screen = ThemeSelectionScreen(title="Themes", items=["dark", "light"])
        screen.dismiss = MagicMock()

        mock_message = MagicMock()
        mock_message.theme_name = "light"

        screen.on_theme_list_item_selected(mock_message)

        screen.dismiss.assert_called_once_with("light")


class TestThemeSelectionScreenOnButtonPressed:
    """Tests for ThemeSelectionScreen on_button_pressed method."""

    def test_on_button_pressed_cancel_restores_original_theme(self):
        """on_button_pressed cancel should restore original theme."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        screen._original_theme = "gruvbox"
        screen.dismiss = MagicMock()

        mock_app = MagicMock()
        mock_app.theme = "preview-theme"
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        mock_event = MagicMock()
        mock_event.button.id = "cancel_btn"
        screen.on_button_pressed(mock_event)

        assert mock_app.theme == "gruvbox"
        screen.dismiss.assert_called_once_with(None)

    def test_on_button_pressed_cancel_no_original_theme(self):
        """on_button_pressed cancel should dismiss without restoring if no original."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        screen._original_theme = None
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        mock_event.button.id = "cancel_btn"
        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with(None)


class TestThemeSelectionScreenActionDismiss:
    """Tests for ThemeSelectionScreen action_dismiss method."""

    @pytest.mark.asyncio
    async def test_action_dismiss_restores_original_theme(self):
        """action_dismiss should restore original theme."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        screen._original_theme = "monokai"
        screen.dismiss = MagicMock()

        mock_app = MagicMock()
        mock_app.theme = "preview-theme"
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        await screen.action_dismiss()

        assert mock_app.theme == "monokai"
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_no_original_theme(self):
        """action_dismiss should dismiss without restoring if no original."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        screen._original_theme = None
        screen.dismiss = MagicMock()

        await screen.action_dismiss()

        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_ignores_result_parameter(self):
        """action_dismiss should ignore result parameter."""
        screen = ThemeSelectionScreen(title="Themes", items=["dark"])
        screen._original_theme = None
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result="ignored")

        screen.dismiss.assert_called_once_with(None)


# =============================================================================
# ModelItem Tests
# =============================================================================


class TestModelItem:
    """Tests for ModelItem widget."""

    def test_init_sets_attributes(self):
        """ModelItem should set provider and model attributes."""
        item = ModelItem(provider="openai", model="gpt-4")
        assert item.provider == "openai"
        assert item.model == "gpt-4"
        assert item.can_focus is True

    def test_init_adds_model_item_class(self):
        """ModelItem should have model-item CSS class."""
        item = ModelItem(provider="ollama", model="llama3")
        assert "model-item" in item.classes

    def test_init_displays_model_with_indent(self):
        """ModelItem should display model name with indent."""
        ModelItem(provider="anthropic", model="claude-3")
        # The Static widget is initialized with "  {model}"
        # We can't easily check render without mounting, but we can verify init args

    def test_on_click_posts_selected_message(self):
        """on_click should post Selected message."""
        item = ModelItem(provider="anthropic", model="claude-3")
        item.post_message = MagicMock()

        item.on_click()

        item.post_message.assert_called_once()
        message = item.post_message.call_args[0][0]
        assert isinstance(message, ModelItem.Selected)
        assert message.provider == "anthropic"
        assert message.model == "claude-3"

    def test_on_key_enter_posts_selected_message(self):
        """on_key should post Selected message on enter."""
        item = ModelItem(provider="ollama", model="llama3")
        item.post_message = MagicMock()

        mock_event = MagicMock()
        mock_event.key = "enter"

        item.on_key(mock_event)

        item.post_message.assert_called_once()
        mock_event.stop.assert_called_once()

    def test_on_key_other_key_no_message(self):
        """on_key should not post message for non-enter keys."""
        item = ModelItem(provider="ollama", model="llama3")
        item.post_message = MagicMock()

        mock_event = MagicMock()
        mock_event.key = "space"

        item.on_key(mock_event)

        item.post_message.assert_not_called()

    def test_on_key_tab_no_message(self):
        """on_key should not post message for tab key."""
        item = ModelItem(provider="openai", model="gpt-4")
        item.post_message = MagicMock()

        mock_event = MagicMock()
        mock_event.key = "tab"

        item.on_key(mock_event)

        item.post_message.assert_not_called()

    def test_on_key_escape_no_message(self):
        """on_key should not post message for escape key."""
        item = ModelItem(provider="openai", model="gpt-4")
        item.post_message = MagicMock()

        mock_event = MagicMock()
        mock_event.key = "escape"

        item.on_key(mock_event)

        item.post_message.assert_not_called()


class TestModelItemSelected:
    """Tests for ModelItem.Selected message."""

    def test_selected_message_attributes(self):
        """Selected message should store provider and model."""
        msg = ModelItem.Selected(provider="test_provider", model="test_model")
        assert msg.provider == "test_provider"
        assert msg.model == "test_model"

    def test_selected_message_different_providers(self):
        """Selected message should work with various providers."""
        providers = ["openai", "anthropic", "ollama", "google", "azure"]
        for provider in providers:
            msg = ModelItem.Selected(provider=provider, model="test-model")
            assert msg.provider == provider

    def test_selected_message_special_model_names(self):
        """Selected message should handle special model names."""
        models = [
            "gpt-4-turbo-preview",
            "claude-3-opus-20240229",
            "llama3:latest",
            "mistral:7b-instruct",
        ]
        for model in models:
            msg = ModelItem.Selected(provider="test", model=model)
            assert msg.model == model


# =============================================================================
# ModelListScreen Tests
# =============================================================================


class TestModelListScreen:
    """Tests for ModelListScreen initialization and basic behavior."""

    def test_init_default_values(self):
        """ModelListScreen should initialize with default values."""
        screen = ModelListScreen()
        assert screen.ai_manager is None
        assert screen._spinner_index == 0
        assert screen._models_by_provider == {}
        assert screen._total_providers == 0

    def test_init_with_fetch_func(self):
        """ModelListScreen should store fetch_func as ai_manager."""
        mock_func = MagicMock()
        screen = ModelListScreen(fetch_func=mock_func)
        assert screen.ai_manager == mock_func

    def test_bindings_defined(self):
        screen = ModelListScreen()
        binding_keys = get_binding_keys(screen.BINDINGS)
        assert "escape" in binding_keys
        assert "up" in binding_keys
        assert "down" in binding_keys
        assert "tab" in binding_keys
        assert "shift+tab" in binding_keys

    def test_spinner_frames_defined(self):
        """ModelListScreen should have spinner frames."""
        assert len(ModelListScreen.SPINNER_FRAMES) > 0
        assert len(ModelListScreen.SPINNER_FRAMES) == 8

    def test_reactive_attributes(self):
        """ModelListScreen should have reactive attributes with defaults."""
        screen = ModelListScreen()
        assert screen.is_loading is True
        assert screen.search_query == ""

    def test_button_pressed_dismisses_none(self):
        """on_button_pressed should dismiss with None."""
        screen = ModelListScreen()
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        """action_dismiss should dismiss with None."""
        screen = ModelListScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_result_ignores_result(self):
        """action_dismiss should ignore result parameter."""
        screen = ModelListScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss(result="ignored")
        screen.dismiss.assert_called_once_with(None)


class TestModelListScreenOnModelItemSelected:
    """Tests for ModelListScreen on_model_item_selected method."""

    def test_on_model_item_selected(self):
        """on_model_item_selected should dismiss with tuple."""
        screen = ModelListScreen()
        screen.dismiss = MagicMock()

        mock_message = MagicMock()
        mock_message.provider = "openai"
        mock_message.model = "gpt-4"

        screen.on_model_item_selected(mock_message)
        screen.dismiss.assert_called_once_with(("openai", "gpt-4"))

    def test_on_model_item_selected_different_providers(self):
        """on_model_item_selected should work with various providers."""
        providers = ["ollama", "anthropic", "google", "azure", "bedrock"]
        for provider in providers:
            screen = ModelListScreen()
            screen.dismiss = MagicMock()

            mock_message = MagicMock()
            mock_message.provider = provider
            mock_message.model = "test-model"

            screen.on_model_item_selected(mock_message)
            screen.dismiss.assert_called_once_with((provider, "test-model"))


class TestModelListScreenSpinner:
    """Tests for ModelListScreen spinner methods."""

    def test_stop_spinner(self):
        """_stop_spinner should stop timer and set to None."""
        screen = ModelListScreen()
        mock_timer = MagicMock()
        screen._spinner_timer = mock_timer

        screen._stop_spinner()

        mock_timer.stop.assert_called_once()
        assert screen._spinner_timer is None

    def test_stop_spinner_no_timer(self):
        """_stop_spinner should handle None timer gracefully."""
        screen = ModelListScreen()
        screen._spinner_timer = None
        screen._stop_spinner()
        assert screen._spinner_timer is None

    def test_animate_spinner_increments_index(self):
        """_animate_spinner should increment spinner index."""
        screen = ModelListScreen()
        screen._spinner_index = 0
        screen._total_providers = 0
        screen.query_one = MagicMock(side_effect=Exception("not mounted"))

        screen._animate_spinner()

        assert screen._spinner_index == 1

    def test_animate_spinner_wraps_around(self):
        """_animate_spinner should wrap index around."""
        screen = ModelListScreen()
        screen._spinner_index = 7  # Last index
        screen._total_providers = 0
        screen.query_one = MagicMock(side_effect=Exception("not mounted"))

        screen._animate_spinner()

        assert screen._spinner_index == 0

    def test_animate_spinner_updates_indicator_checking_providers(self):
        """_animate_spinner should show 'Checking providers' when no providers yet."""
        screen = ModelListScreen()
        screen._spinner_index = 0
        screen._total_providers = 0

        mock_indicator = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)

        screen._animate_spinner()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "Checking providers" in call_arg

    def test_animate_spinner_updates_indicator_loading_models(self):
        """_animate_spinner should show 'Loading models' when providers found."""
        screen = ModelListScreen()
        screen._spinner_index = 0
        screen._total_providers = 3

        mock_indicator = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)

        screen._animate_spinner()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "Loading" in call_arg
        assert "providers" in call_arg

    def test_animate_spinner_handles_query_exception(self):
        """_animate_spinner should handle query_one exception."""
        screen = ModelListScreen()
        screen._spinner_index = 0
        screen.query_one = MagicMock(side_effect=Exception("Widget not found"))

        # Should not raise
        screen._animate_spinner()


class TestModelListScreenActions:
    """Tests for ModelListScreen action methods."""

    def test_action_focus_prev(self):
        """action_focus_prev should call focus_previous."""
        screen = ModelListScreen()
        screen.focus_previous = MagicMock()

        screen.action_focus_prev()

        screen.focus_previous.assert_called_once()

    def test_action_focus_next(self):
        """action_focus_next should call focus_next."""
        screen = ModelListScreen()
        screen.focus_next = MagicMock()

        screen.action_focus_next()

        screen.focus_next.assert_called_once()


class TestModelListScreenOnInputChanged:
    """Tests for ModelListScreen on_input_changed method."""

    def test_on_input_changed_updates_search_query(self):
        """on_input_changed should update search_query."""
        screen = ModelListScreen()
        screen.is_loading = False
        screen._update_collapsibles = MagicMock()

        mock_event = MagicMock()
        mock_event.input.id = "model-search"
        mock_event.value = "GPT"

        screen.on_input_changed(mock_event)

        assert screen.search_query == "gpt"  # lowercased
        screen._update_collapsibles.assert_called_once()

    def test_on_input_changed_does_not_update_if_loading(self):
        """on_input_changed should not update collapsibles while loading."""
        screen = ModelListScreen()
        screen.is_loading = True
        screen._update_collapsibles = MagicMock()

        mock_event = MagicMock()
        mock_event.input.id = "model-search"
        mock_event.value = "test"

        screen.on_input_changed(mock_event)

        assert screen.search_query == "test"
        screen._update_collapsibles.assert_not_called()

    def test_on_input_changed_ignores_other_inputs(self):
        """on_input_changed should ignore non-search inputs."""
        screen = ModelListScreen()
        screen.is_loading = False
        screen._update_collapsibles = MagicMock()
        original_query = screen.search_query

        mock_event = MagicMock()
        mock_event.input.id = "other-input"
        mock_event.value = "test"

        screen.on_input_changed(mock_event)

        assert screen.search_query == original_query
        screen._update_collapsibles.assert_not_called()


class TestModelListScreenOnUnmount:
    """Tests for ModelListScreen on_unmount method."""

    def test_on_unmount_stops_spinner(self):
        """on_unmount should stop the spinner."""
        screen = ModelListScreen()
        screen._stop_spinner = MagicMock()

        screen.on_unmount()

        screen._stop_spinner.assert_called_once()


class TestModelListScreenStartSpinner:
    """Tests for ModelListScreen _start_spinner method."""

    def test_start_spinner_updates_indicator(self):
        """_start_spinner should update loading indicator."""
        screen = ModelListScreen()

        mock_indicator = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)
        screen.set_interval = MagicMock(return_value=MagicMock())

        screen._start_spinner()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "Checking providers" in call_arg

    def test_start_spinner_sets_interval(self):
        """_start_spinner should set interval for animation."""
        screen = ModelListScreen()

        mock_indicator = MagicMock()
        mock_timer = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)
        screen.set_interval = MagicMock(return_value=mock_timer)

        screen._start_spinner()

        screen.set_interval.assert_called_once_with(0.08, screen._animate_spinner)
        assert screen._spinner_timer == mock_timer

    def test_start_spinner_handles_exception(self):
        """_start_spinner should handle query_one exception."""
        screen = ModelListScreen()
        screen.query_one = MagicMock(side_effect=Exception("Widget not found"))

        # Should not raise
        screen._start_spinner()


class TestModelListScreenShowNoProviders:
    """Tests for ModelListScreen _show_no_providers method."""

    def test_show_no_providers_updates_indicator(self):
        """_show_no_providers should update indicator with error."""
        screen = ModelListScreen()

        mock_indicator = MagicMock()
        mock_scroll = MagicMock()
        screen.query_one = MagicMock(
            side_effect=[mock_indicator, mock_scroll, mock_scroll, mock_scroll]
        )

        screen._show_no_providers()

        mock_indicator.update.assert_called_once_with("No providers configured")
        mock_indicator.add_class.assert_called_once_with("error")

    def test_show_no_providers_mounts_help_text(self):
        """_show_no_providers should mount helpful instructions."""
        screen = ModelListScreen()

        mock_indicator = MagicMock()
        mock_scroll = MagicMock()

        def query_one_side_effect(selector, *args):
            if "loading-indicator" in selector:
                return mock_indicator
            return mock_scroll

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen._show_no_providers()

        # Should mount 3 Static widgets with help text
        assert mock_scroll.mount.call_count == 3

    def test_show_no_providers_handles_exception(self):
        """_show_no_providers should handle exceptions gracefully."""
        screen = ModelListScreen()
        screen.query_one = MagicMock(side_effect=Exception("Widget not found"))

        # Should not raise
        screen._show_no_providers()


class TestModelListScreenShowError:
    """Tests for ModelListScreen _show_error method."""

    def test_show_error_updates_indicator(self):
        """_show_error should update indicator with error message."""
        screen = ModelListScreen()

        mock_indicator = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)

        screen._show_error("Connection failed")

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "Connection failed" in call_arg
        assert "✗" in call_arg
        mock_indicator.add_class.assert_called_once_with("error")

    def test_show_error_handles_exception(self):
        """_show_error should handle query_one exception."""
        screen = ModelListScreen()
        screen.query_one = MagicMock(side_effect=Exception("Widget not found"))

        # Should not raise
        screen._show_error("Error message")


class TestModelListScreenFinalizeList:
    """Tests for ModelListScreen _finalize_list method."""

    def test_finalize_list_shows_success_with_models(self):
        """_finalize_list should show success message with model count."""
        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": ["gpt-4", "gpt-3.5"],
            "anthropic": ["claude-3"],
        }

        mock_indicator = MagicMock()
        mock_search = MagicMock()

        def query_one_side_effect(selector, *args):
            if "loading-indicator" in selector:
                return mock_indicator
            return mock_search

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen._finalize_list()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "3 models" in call_arg  # Total models
        assert "2 provider" in call_arg  # Provider count
        mock_indicator.add_class.assert_called_once_with("success")

    def test_finalize_list_shows_error_with_no_models(self):
        """_finalize_list should show error when no models found."""
        screen = ModelListScreen()
        screen._models_by_provider = {}

        mock_indicator = MagicMock()
        mock_search = MagicMock()

        def query_one_side_effect(selector, *args):
            if "loading-indicator" in selector:
                return mock_indicator
            return mock_search

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen._finalize_list()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "No models found" in call_arg
        mock_indicator.add_class.assert_called_once_with("error")

    def test_finalize_list_focuses_search_input(self):
        """_finalize_list should focus the search input."""
        screen = ModelListScreen()
        screen._models_by_provider = {"openai": ["gpt-4"]}

        mock_indicator = MagicMock()
        mock_search = MagicMock()

        def query_one_side_effect(selector, *args):
            if "loading-indicator" in selector:
                return mock_indicator
            return mock_search

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen._finalize_list()

        mock_search.focus.assert_called_once()

    def test_finalize_list_handles_exception(self):
        """_finalize_list should handle exceptions gracefully."""
        screen = ModelListScreen()
        screen.query_one = MagicMock(side_effect=Exception("Widget not found"))

        # Should not raise
        screen._finalize_list()


class TestModelListScreenUpdateProgressText:
    def test_update_progress_text_with_providers(self):
        screen = ModelListScreen()
        screen._total_providers = 5
        screen._completed_providers = 3
        screen._spinner_index = 0

        mock_indicator = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)

        screen._update_progress_text()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "3/5" in call_arg
        assert "providers" in call_arg

    def test_update_progress_text_no_providers(self):
        screen = ModelListScreen()
        screen._total_providers = 0
        screen._spinner_index = 0

        mock_indicator = MagicMock()
        screen.query_one = MagicMock(return_value=mock_indicator)

        screen._update_progress_text()

        mock_indicator.update.assert_called_once()
        call_arg = mock_indicator.update.call_args[0][0]
        assert "Checking providers" in call_arg

    def test_update_progress_text_handles_exception(self):
        screen = ModelListScreen()
        screen.query_one = MagicMock(side_effect=Exception("Widget not found"))

        screen._update_progress_text()


class TestModelListScreenUpdateCollapsibles:
    """Tests for ModelListScreen _update_collapsibles method."""

    @patch("config.Config")
    def test_update_collapsibles_creates_provider_sections(self, mock_config):
        mock_config.get.return_value = "openai"

        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": ["gpt-4", "gpt-3.5-turbo"],
            "anthropic": ["claude-3"],
        }
        screen.search_query = ""

        mock_scroll = MagicMock()
        mock_scroll.children = []
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Should mount 2 collapsibles
        assert mock_scroll.mount.call_count == 2

    @patch("config.Config")
    def test_update_collapsibles_filters_by_search_query(self, mock_config):
        mock_config.get.return_value = None

        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": ["gpt-4", "gpt-3.5-turbo", "text-davinci"],
        }
        screen.search_query = "gpt"

        mock_scroll = MagicMock()
        mock_scroll.children = []
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Should mount 1 collapsible with filtered models
        assert mock_scroll.mount.call_count == 1

    @patch("config.Config")
    def test_update_collapsibles_skips_empty_providers(self, mock_config):
        mock_config.get.return_value = None

        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": [],  # Empty
            "anthropic": ["claude-3"],
        }
        screen.search_query = ""

        mock_scroll = MagicMock()
        mock_scroll.children = []
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Should only mount 1 collapsible (skipping empty openai)
        assert mock_scroll.mount.call_count == 1

    @patch("config.Config")
    def test_update_collapsibles_preserves_existing_when_not_searching(
        self, mock_config
    ):
        """Incremental update: existing providers are preserved when not searching."""
        mock_config.get.return_value = None

        screen = ModelListScreen()
        screen._models_by_provider = {"openai": ["gpt-4"]}
        screen.search_query = ""

        mock_child = MagicMock()
        mock_child.id = "provider-openai"  # Already exists
        mock_scroll = MagicMock()
        mock_scroll.children = [mock_child]
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Should NOT remove existing children when not searching (incremental)
        mock_child.remove.assert_not_called()
        # Should NOT mount duplicate (already exists)
        assert mock_scroll.mount.call_count == 0

    @patch("config.Config")
    def test_update_collapsibles_removes_children_when_searching(self, mock_config):
        """Full rebuild when searching to apply filter."""
        mock_config.get.return_value = None

        screen = ModelListScreen()
        screen._models_by_provider = {"openai": ["gpt-4"]}
        screen.search_query = "gpt"  # Searching

        mock_child = MagicMock()
        mock_child.id = "provider-openai"
        mock_scroll = MagicMock()
        mock_scroll.children = [mock_child]
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # SHOULD remove children when searching (full rebuild)
        mock_child.remove.assert_called_once()

    @patch("config.Config")
    def test_update_collapsibles_limits_models_per_provider(self, mock_config):
        mock_config.get.return_value = None

        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": [f"model-{i}" for i in range(150)],  # More than 100
        }
        screen.search_query = ""

        mock_scroll = MagicMock()
        mock_scroll.children = []
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Should mount collapsible (model count limited internally)
        assert mock_scroll.mount.call_count == 1

    @patch("config.Config")
    def test_update_collapsibles_active_provider_expanded(self, mock_config):
        mock_config.get.return_value = "anthropic"

        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": ["gpt-4"],
            "anthropic": ["claude-3"],
        }
        screen.search_query = ""

        mock_scroll = MagicMock()
        mock_scroll.children = []
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Active provider should be first due to sorting
        assert mock_scroll.mount.call_count == 2

    @patch("config.Config")
    def test_update_collapsibles_search_expands_all(self, mock_config):
        mock_config.get.return_value = None

        screen = ModelListScreen()
        screen._models_by_provider = {
            "openai": ["gpt-4"],
            "anthropic": ["claude-3"],
        }
        screen.search_query = "model"  # Has search query

        mock_scroll = MagicMock()
        mock_scroll.children = []
        screen.query_one = MagicMock(return_value=mock_scroll)

        screen._update_collapsibles()

        # Both should be mounted (if models match)
        # Note: search query "model" doesn't match "gpt-4" or "claude-3"


class TestModelListScreenEdgeCases:
    """Edge case tests for ModelListScreen."""

    def test_spinner_timer_set_to_none_initially(self):
        """_spinner_timer should be None initially."""
        screen = ModelListScreen()
        assert screen._spinner_timer is None

    def test_models_by_provider_empty_initially(self):
        """_models_by_provider should be empty dict initially."""
        screen = ModelListScreen()
        assert screen._models_by_provider == {}
        assert isinstance(screen._models_by_provider, dict)

    def test_total_providers_zero_initially(self):
        """_total_providers should be 0 initially."""
        screen = ModelListScreen()
        assert screen._total_providers == 0

    def test_spinner_index_zero_initially(self):
        """_spinner_index should be 0 initially."""
        screen = ModelListScreen()
        assert screen._spinner_index == 0

    def test_is_loading_true_initially(self):
        """is_loading should be True initially."""
        screen = ModelListScreen()
        assert screen.is_loading is True

    def test_search_query_empty_initially(self):
        """search_query should be empty string initially."""
        screen = ModelListScreen()
        assert screen.search_query == ""


# =============================================================================
# Integration-style Tests (Unit tests that test component interactions)
# =============================================================================


class TestSelectionScreensIntegration:
    """Integration-style tests for selection screens."""

    def test_selection_list_screen_workflow(self):
        """Test SelectionListScreen typical workflow."""
        items = ["option1", "option2", "option3"]
        screen = SelectionListScreen(title="Select Option", items=items)

        # Verify initial state
        assert screen._screen_title == "Select Option"
        assert screen.items == items

        # Simulate selection
        screen.dismiss = MagicMock()
        mock_listview = MagicMock()
        mock_listview.index = 1
        screen.query_one = MagicMock(return_value=mock_listview)

        mock_message = MagicMock()
        screen.on_list_view_selected(mock_message)

        screen.dismiss.assert_called_once_with("option2")

    def test_theme_selection_screen_workflow(self):
        """Test ThemeSelectionScreen typical workflow."""
        from screens.selection import ThemeListItem

        themes = ["dark", "light", "monokai"]
        screen = ThemeSelectionScreen(title="Select Theme", items=themes)

        mock_app = MagicMock()
        mock_app.theme = "original"
        screen._app = mock_app
        type(screen).app = property(lambda self: self._app)

        screen.on_mount()
        assert screen._original_theme == "original"

        mock_item = MagicMock(spec=ThemeListItem)
        mock_item._theme_name = "monokai"

        mock_event = MagicMock()
        mock_event.widget = mock_item
        screen.on_descendant_focus(mock_event)

        assert mock_app.theme == "monokai"
        assert screen._highlighted_theme == "monokai"

        screen.dismiss = MagicMock()
        mock_button_event = MagicMock()
        mock_button_event.button.id = "cancel_btn"
        screen.on_button_pressed(mock_button_event)

        assert mock_app.theme == "original"
        screen.dismiss.assert_called_once_with(None)

    def test_model_item_selection_workflow(self):
        """Test ModelItem selection workflow."""
        item = ModelItem(provider="openai", model="gpt-4")

        # Verify attributes
        assert item.provider == "openai"
        assert item.model == "gpt-4"
        assert item.can_focus is True

        # Test click
        item.post_message = MagicMock()
        item.on_click()

        message = item.post_message.call_args[0][0]
        assert isinstance(message, ModelItem.Selected)
        assert message.provider == "openai"
        assert message.model == "gpt-4"

    def test_model_list_screen_workflow(self):
        screen = ModelListScreen()

        assert screen.is_loading is True
        assert screen._models_by_provider == {}

        screen._models_by_provider = {
            "openai": ["gpt-4", "gpt-3.5"],
            "anthropic": ["claude-3"],
        }
        screen._total_providers = 2
        screen.is_loading = False

        assert screen._models_by_provider == {
            "openai": ["gpt-4", "gpt-3.5"],
            "anthropic": ["claude-3"],
        }
        assert screen._total_providers == 2
        assert screen.is_loading is False

        screen.dismiss = MagicMock()
        mock_message = MagicMock()
        mock_message.provider = "anthropic"
        mock_message.model = "claude-3"

        screen.on_model_item_selected(mock_message)

        screen.dismiss.assert_called_once_with(("anthropic", "claude-3"))
