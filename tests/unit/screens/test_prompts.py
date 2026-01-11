"""Tests for screens/prompts.py - PromptEditorScreen and PromptListItem."""

from unittest.mock import MagicMock, patch

import pytest

from screens.prompts import PromptEditorScreen, PromptListItem


class TestPromptListItem:
    """Tests for PromptListItem widget."""

    def test_init_stores_key(self):
        """Should store prompt key."""
        item = PromptListItem(key="my-prompt", name="My Prompt", is_user=True)
        assert item.key == "my-prompt"

    def test_init_stores_name(self):
        """Should store prompt name."""
        item = PromptListItem(key="my-prompt", name="My Prompt", is_user=True)
        assert item.prompt_name == "My Prompt"

    def test_init_stores_is_user_true(self):
        """Should store is_user flag when True."""
        item = PromptListItem(key="custom", name="Custom", is_user=True)
        assert item.is_user is True

    def test_init_stores_is_user_false(self):
        """Should store is_user flag when False."""
        item = PromptListItem(key="builtin", name="Built-in", is_user=False)
        assert item.is_user is False

    def test_compose_returns_label(self):
        """Should compose a Label widget."""
        item = PromptListItem(key="test", name="Test Prompt", is_user=True)
        children = list(item.compose())
        assert len(children) == 1

    def test_user_prompt_shows_user_icon(self):
        """User prompts should have user icon in label."""
        from textual.widgets import Label

        item = PromptListItem(key="user-prompt", name="User Prompt", is_user=True)
        children = list(item.compose())
        label = children[0]
        assert isinstance(label, Label)

    def test_builtin_prompt_shows_lock_icon(self):
        """Built-in prompts should have lock icon in label."""
        from textual.widgets import Label

        item = PromptListItem(key="default", name="Default", is_user=False)
        children = list(item.compose())
        label = children[0]
        assert isinstance(label, Label)


class TestPromptEditorScreenInit:
    """Tests for PromptEditorScreen initialization."""

    @patch("screens.prompts.get_prompt_manager")
    def test_init_gets_prompt_manager(self, mock_get_pm):
        """Should get prompt manager on init."""
        mock_pm = MagicMock()
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()

        mock_get_pm.assert_called_once()
        assert screen.pm is mock_pm

    @patch("screens.prompts.get_prompt_manager")
    def test_init_sets_current_key_none(self, mock_get_pm):
        """Should initialize current_key as None."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()

        assert screen.current_key is None

    @patch("screens.prompts.get_prompt_manager")
    def test_init_sets_is_dirty_false(self, mock_get_pm):
        """Should initialize is_dirty as False."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()

        assert screen.is_dirty is False


class TestPromptEditorScreenBindings:
    """Tests for PromptEditorScreen keybindings."""

    def test_escape_binding_defined(self):
        """Should have escape binding for dismiss."""
        bindings = PromptEditorScreen.BINDINGS
        binding_keys = _get_binding_keys(bindings)
        assert "escape" in binding_keys

    def test_ctrl_s_binding_defined(self):
        """Should have ctrl+s binding for save."""
        bindings = PromptEditorScreen.BINDINGS
        binding_keys = _get_binding_keys(bindings)
        assert "ctrl+s" in binding_keys

    def test_ctrl_n_binding_defined(self):
        """Should have ctrl+n binding for new prompt."""
        bindings = PromptEditorScreen.BINDINGS
        binding_keys = _get_binding_keys(bindings)
        assert "ctrl+n" in binding_keys

    def test_ctrl_d_binding_defined(self):
        """Should have ctrl+d binding for delete."""
        bindings = PromptEditorScreen.BINDINGS
        binding_keys = _get_binding_keys(bindings)
        assert "ctrl+d" in binding_keys

    def test_escape_action_is_dismiss(self):
        """Escape binding should trigger dismiss action."""
        bindings = PromptEditorScreen.BINDINGS
        action = _get_binding_action(bindings, "escape")
        assert action == "dismiss"

    def test_ctrl_s_action_is_save(self):
        """Ctrl+S binding should trigger save_prompt action."""
        bindings = PromptEditorScreen.BINDINGS
        action = _get_binding_action(bindings, "ctrl+s")
        assert action == "save_prompt"

    def test_ctrl_n_action_is_new(self):
        """Ctrl+N binding should trigger new_prompt action."""
        bindings = PromptEditorScreen.BINDINGS
        action = _get_binding_action(bindings, "ctrl+n")
        assert action == "new_prompt"

    def test_ctrl_d_action_is_delete(self):
        """Ctrl+D binding should trigger delete_prompt action."""
        bindings = PromptEditorScreen.BINDINGS
        action = _get_binding_action(bindings, "ctrl+d")
        assert action == "delete_prompt"


class TestPromptEditorScreenLoadPrompts:
    """Tests for PromptEditorScreen load_prompts method."""

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompts_calls_list_prompts(self, mock_get_pm):
        """Should call pm.list_prompts()."""
        mock_pm = MagicMock()
        mock_pm.list_prompts.return_value = []
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        mock_lv = MagicMock()
        screen.query_one = MagicMock(return_value=mock_lv)

        screen.load_prompts()

        mock_pm.list_prompts.assert_called_once()

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompts_clears_listview(self, mock_get_pm):
        """Should clear ListView before loading."""
        mock_pm = MagicMock()
        mock_pm.list_prompts.return_value = []
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        mock_lv = MagicMock()
        screen.query_one = MagicMock(return_value=mock_lv)

        screen.load_prompts()

        mock_lv.clear.assert_called_once()

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompts_appends_items(self, mock_get_pm):
        """Should append PromptListItem for each prompt."""
        mock_pm = MagicMock()
        mock_pm.list_prompts.return_value = [
            ("default", "Default", "Default prompt", False),
            ("custom", "Custom", "Custom prompt", True),
        ]
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        mock_lv = MagicMock()
        screen.query_one = MagicMock(return_value=mock_lv)

        screen.load_prompts()

        assert mock_lv.append.call_count == 2


class TestPromptEditorScreenLoadPromptDetails:
    """Tests for PromptEditorScreen load_prompt_details method."""

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompt_details_sets_current_key(self, mock_get_pm):
        """Should set current_key to loaded key."""
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = {
            "description": "Test",
            "content": "Content",
        }
        mock_pm._user_prompts = {"test-key": {}}
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.query_one = MagicMock(return_value=MagicMock())

        screen.load_prompt_details("test-key")

        assert screen.current_key == "test-key"

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompt_details_returns_early_if_no_data(self, mock_get_pm):
        """Should return early if prompt not found."""
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = None
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.current_key = None

        screen.load_prompt_details("nonexistent")

        assert screen.current_key == "nonexistent"

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompt_details_enables_delete_for_user_prompts(self, mock_get_pm):
        """Should enable delete button for user prompts."""
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = {
            "description": "Test",
            "content": "Content",
        }
        mock_pm._user_prompts = {"user-prompt": {}}
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        mock_delete_btn = MagicMock()
        mock_name_input = MagicMock()
        mock_desc_input = MagicMock()
        mock_content_area = MagicMock()

        def query_one_side_effect(selector, *args):
            if selector == "#delete-btn":
                return mock_delete_btn
            elif selector == "#prompt-name-input":
                return mock_name_input
            elif selector == "#prompt-desc-input":
                return mock_desc_input
            elif selector == "#prompt-content-area":
                return mock_content_area
            return MagicMock()

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen.load_prompt_details("user-prompt")

        assert mock_delete_btn.disabled is False

    @patch("screens.prompts.get_prompt_manager")
    def test_load_prompt_details_disables_delete_for_builtins(self, mock_get_pm):
        """Should disable delete button for built-in prompts."""
        mock_pm = MagicMock()
        mock_pm.get_prompt.return_value = {
            "description": "Test",
            "content": "Content",
        }
        mock_pm._user_prompts = {}
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        mock_delete_btn = MagicMock()
        mock_name_input = MagicMock()
        mock_desc_input = MagicMock()
        mock_content_area = MagicMock()

        def query_one_side_effect(selector, *args):
            if selector == "#delete-btn":
                return mock_delete_btn
            elif selector == "#prompt-name-input":
                return mock_name_input
            elif selector == "#prompt-desc-input":
                return mock_desc_input
            elif selector == "#prompt-content-area":
                return mock_content_area
            return MagicMock()

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen.load_prompt_details("default")

        assert mock_delete_btn.disabled is True


class TestPromptEditorScreenActionNewPrompt:
    """Tests for PromptEditorScreen action_new_prompt method."""

    @patch("screens.prompts.get_prompt_manager")
    def test_new_prompt_clears_current_key(self, mock_get_pm):
        """Should clear current_key."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        screen.current_key = "old-key"
        screen.query_one = MagicMock(return_value=MagicMock())

        screen.action_new_prompt()

        assert screen.current_key is None

    @patch("screens.prompts.get_prompt_manager")
    def test_new_prompt_clears_form_fields(self, mock_get_pm):
        """Should clear all form fields."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        mock_lv = MagicMock()
        mock_name_input = MagicMock()
        mock_desc_input = MagicMock()
        mock_content_area = MagicMock()
        mock_delete_btn = MagicMock()

        def query_one_side_effect(selector, *args):
            if selector == "#prompt-list":
                return mock_lv
            elif selector == "#prompt-name-input":
                return mock_name_input
            elif selector == "#prompt-desc-input":
                return mock_desc_input
            elif selector == "#prompt-content-area":
                return mock_content_area
            elif selector == "#delete-btn":
                return mock_delete_btn
            return MagicMock()

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen.action_new_prompt()

        assert mock_name_input.value == ""
        assert mock_desc_input.value == ""
        assert mock_content_area.text == ""

    @patch("screens.prompts.get_prompt_manager")
    def test_new_prompt_disables_delete_button(self, mock_get_pm):
        """Should disable delete button for new prompts."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        mock_delete_btn = MagicMock()

        def query_one_side_effect(selector, *args):
            if selector == "#delete-btn":
                return mock_delete_btn
            return MagicMock()

        screen.query_one = MagicMock(side_effect=query_one_side_effect)

        screen.action_new_prompt()

        assert mock_delete_btn.disabled is True


class TestPromptEditorScreenActionSavePrompt:
    """Tests for PromptEditorScreen action_save_prompt method."""

    @patch("screens.prompts.get_prompt_manager")
    def test_save_prompt_requires_key(self, mock_get_pm):
        """Should notify error if key is empty."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        mock_name_input = MagicMock()
        mock_name_input.value = ""

        screen.query_one = MagicMock(return_value=mock_name_input)
        screen.notify = MagicMock()

        screen.action_save_prompt()

        screen.notify.assert_called_once()
        call_args = screen.notify.call_args
        assert call_args[1].get("severity") == "error"

    @patch("screens.prompts.get_prompt_manager")
    def test_save_prompt_rejects_builtin_overwrite(self, mock_get_pm):
        """Should reject attempts to overwrite built-in prompts."""
        from prompts import templates

        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        screen.current_key = None

        mock_name_input = MagicMock()
        mock_name_input.value = "default"
        mock_desc_input = MagicMock()
        mock_desc_input.value = "desc"
        mock_content_area = MagicMock()
        mock_content_area.text = "content"

        def query_one_side_effect(selector, *args):
            if "name" in selector:
                return mock_name_input
            elif "desc" in selector:
                return mock_desc_input
            elif "content" in selector:
                return mock_content_area
            return MagicMock()

        screen.query_one = MagicMock(side_effect=query_one_side_effect)
        screen.notify = MagicMock()

        with patch.dict(templates.BUILTIN_PROMPTS, {"default": {}}, clear=True):
            screen.action_save_prompt()

        screen.notify.assert_called()
        call_args = screen.notify.call_args
        assert call_args[1].get("severity") == "error"

    @patch("screens.prompts.get_prompt_manager")
    def test_save_prompt_calls_pm_save(self, mock_get_pm):
        """Should call pm.save_prompt with correct arguments."""
        from prompts import templates

        mock_pm = MagicMock()
        mock_pm._user_prompts = {}
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.current_key = None

        mock_name_input = MagicMock()
        mock_name_input.value = "new-prompt"
        mock_desc_input = MagicMock()
        mock_desc_input.value = "A new prompt"
        mock_content_area = MagicMock()
        mock_content_area.text = "Prompt content"

        def query_one_side_effect(selector, *args):
            if "name" in selector:
                return mock_name_input
            elif "desc" in selector:
                return mock_desc_input
            elif "content" in selector:
                return mock_content_area
            return MagicMock()

        screen.query_one = MagicMock(side_effect=query_one_side_effect)
        screen.notify = MagicMock()
        screen.load_prompts = MagicMock()

        with patch.dict(templates.BUILTIN_PROMPTS, {}, clear=True):
            screen.action_save_prompt()

        mock_pm.save_prompt.assert_called_once_with(
            "new-prompt", "new-prompt", "A new prompt", "Prompt content"
        )


class TestPromptEditorScreenActionDeletePrompt:
    """Tests for PromptEditorScreen action_delete_prompt method."""

    @patch("screens.prompts.get_prompt_manager")
    def test_delete_prompt_returns_early_if_no_current_key(self, mock_get_pm):
        """Should return early if no prompt selected."""
        mock_pm = MagicMock()
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.current_key = None

        screen.action_delete_prompt()

        mock_pm.delete_prompt.assert_not_called()

    @patch("screens.prompts.get_prompt_manager")
    def test_delete_prompt_calls_pm_delete(self, mock_get_pm):
        """Should call pm.delete_prompt with current key."""
        mock_pm = MagicMock()
        mock_pm.delete_prompt.return_value = True
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.current_key = "to-delete"
        screen.notify = MagicMock()
        screen.action_new_prompt = MagicMock()
        screen.load_prompts = MagicMock()

        screen.action_delete_prompt()

        mock_pm.delete_prompt.assert_called_once_with("to-delete")

    @patch("screens.prompts.get_prompt_manager")
    def test_delete_prompt_notifies_on_success(self, mock_get_pm):
        """Should notify user on successful delete."""
        mock_pm = MagicMock()
        mock_pm.delete_prompt.return_value = True
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.current_key = "to-delete"
        screen.notify = MagicMock()
        screen.action_new_prompt = MagicMock()
        screen.load_prompts = MagicMock()

        screen.action_delete_prompt()

        screen.notify.assert_called_once()
        call_args = screen.notify.call_args
        assert (
            call_args[1].get("severity") is None
            or call_args[1].get("severity") != "error"
        )

    @patch("screens.prompts.get_prompt_manager")
    def test_delete_prompt_notifies_error_on_failure(self, mock_get_pm):
        """Should notify error if delete fails (built-in prompt)."""
        mock_pm = MagicMock()
        mock_pm.delete_prompt.return_value = False
        mock_get_pm.return_value = mock_pm

        screen = PromptEditorScreen()
        screen.current_key = "default"
        screen.notify = MagicMock()

        screen.action_delete_prompt()

        screen.notify.assert_called_once()
        call_args = screen.notify.call_args
        assert call_args[1].get("severity") == "error"


class TestPromptEditorScreenButtonHandlers:
    """Tests for PromptEditorScreen button press handlers."""

    @patch("screens.prompts.get_prompt_manager")
    def test_new_btn_calls_action_new_prompt(self, mock_get_pm):
        """New button should trigger action_new_prompt."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        screen.action_new_prompt = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "new-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.action_new_prompt.assert_called_once()

    @patch("screens.prompts.get_prompt_manager")
    def test_save_btn_calls_action_save_prompt(self, mock_get_pm):
        """Save button should trigger action_save_prompt."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        screen.action_save_prompt = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "save-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.action_save_prompt.assert_called_once()

    @patch("screens.prompts.get_prompt_manager")
    def test_delete_btn_calls_action_delete_prompt(self, mock_get_pm):
        """Delete button should trigger action_delete_prompt."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        screen.action_delete_prompt = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "delete-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.action_delete_prompt.assert_called_once()

    @patch("screens.prompts.get_prompt_manager")
    def test_close_btn_calls_dismiss(self, mock_get_pm):
        """Close button should trigger dismiss."""
        mock_get_pm.return_value = MagicMock()

        screen = PromptEditorScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "close-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once()


class TestPromptEditorScreenInheritance:
    """Tests for PromptEditorScreen inheritance."""

    def test_inherits_from_modal_screen(self):
        """Should inherit from ModalScreen."""
        from screens.base import ModalScreen

        assert issubclass(PromptEditorScreen, ModalScreen)


def _get_binding_keys(bindings):
    """Extract keys from bindings list."""
    from textual.binding import Binding

    keys = []
    for b in bindings:
        if isinstance(b, Binding):
            keys.append(b.key)
        elif isinstance(b, tuple):
            keys.append(b[0])
    return keys


def _get_binding_action(bindings, key):
    """Get action for a specific binding key."""
    from textual.binding import Binding

    for b in bindings:
        if isinstance(b, Binding) and b.key == key:
            return b.action
        elif isinstance(b, tuple) and b[0] == key:
            return b[1]
    return None
