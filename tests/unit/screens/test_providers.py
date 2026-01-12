"""Unit tests for screens/providers.py - ProvidersScreen and ProviderRow."""

from unittest.mock import MagicMock, patch

import pytest


class TestProviderRowInitialization:
    """Tests for ProviderRow widget initialization."""

    def test_provider_row_stores_provider_name(self):
        """ProviderRow should store the provider name."""
        from screens.providers import ProviderRow

        row = ProviderRow(
            "openai", {"name": "OpenAI"}, is_active=False, is_configured=False
        )
        assert row.provider_name == "openai"

    def test_provider_row_stores_info_dict(self):
        """ProviderRow should store provider info dictionary."""
        from screens.providers import ProviderRow

        info = {"name": "Anthropic", "description": "Claude models"}
        row = ProviderRow("anthropic", info, is_active=False, is_configured=False)
        assert row.info == info
        assert row.info.get("name") == "Anthropic"

    def test_provider_row_stores_active_state(self):
        """ProviderRow should store is_active flag."""
        from screens.providers import ProviderRow

        row_active = ProviderRow("openai", {}, is_active=True, is_configured=True)
        row_inactive = ProviderRow("openai", {}, is_active=False, is_configured=True)

        assert row_active.is_active is True
        assert row_inactive.is_active is False

    def test_provider_row_stores_configured_state(self):
        """ProviderRow should store is_configured flag."""
        from screens.providers import ProviderRow

        row_configured = ProviderRow("openai", {}, is_active=False, is_configured=True)
        row_unconfigured = ProviderRow(
            "openai", {}, is_active=False, is_configured=False
        )

        assert row_configured.is_configured is True
        assert row_unconfigured.is_configured is False

    def test_provider_row_has_class(self):
        """ProviderRow should have provider-row CSS class."""
        from screens.providers import ProviderRow

        row = ProviderRow("test", {}, is_active=False, is_configured=False)
        assert "provider-row" in row.classes

    def test_provider_row_is_focusable(self):
        """ProviderRow should be focusable for keyboard navigation."""
        from screens.providers import ProviderRow

        row = ProviderRow("test", {}, is_active=False, is_configured=False)
        assert row.can_focus is True


class TestProviderRowStates:
    """Tests for ProviderRow state combinations."""

    def test_active_provider_state(self):
        """Active provider should have is_active=True."""
        from screens.providers import ProviderRow

        row = ProviderRow(
            "ollama", {"name": "Ollama"}, is_active=True, is_configured=True
        )
        assert row.is_active is True
        assert row.is_configured is True

    def test_configured_but_not_active_state(self):
        """Configured but inactive provider state."""
        from screens.providers import ProviderRow

        row = ProviderRow(
            "openai", {"name": "OpenAI"}, is_active=False, is_configured=True
        )
        assert row.is_active is False
        assert row.is_configured is True

    def test_unconfigured_state(self):
        """Unconfigured provider state."""
        from screens.providers import ProviderRow

        row = ProviderRow(
            "azure", {"name": "Azure"}, is_active=False, is_configured=False
        )
        assert row.is_active is False
        assert row.is_configured is False


class TestProvidersScreenInitialization:
    """Tests for ProvidersScreen initialization."""

    @patch("screens.providers.Config")
    def test_screen_loads_active_provider(self, mock_config):
        """ProvidersScreen should load active provider from config."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = "anthropic"
        screen = ProvidersScreen()

        assert screen._active_provider == "anthropic"
        mock_config.get.assert_called_with("ai.provider")

    @patch("screens.providers.Config")
    def test_screen_handles_no_active_provider(self, mock_config):
        """ProvidersScreen should handle None active provider."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()

        assert screen._active_provider is None


class TestProvidersScreenBindings:
    """Tests for ProvidersScreen keyboard bindings."""

    @patch("screens.providers.Config")
    def test_has_escape_binding(self, mock_config):
        """ProvidersScreen should have escape binding to dismiss."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()

        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    @patch("screens.providers.Config")
    def test_has_navigation_bindings(self, mock_config):
        """ProvidersScreen should have up/down navigation bindings."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()

        binding_keys = [b.key for b in screen.BINDINGS]
        assert "up" in binding_keys
        assert "down" in binding_keys

    @patch("screens.providers.Config")
    def test_has_enter_binding_for_configure(self, mock_config):
        """ProvidersScreen should have enter binding to configure focused provider."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()

        binding_keys = [b.key for b in screen.BINDINGS]
        assert "enter" in binding_keys


class TestProvidersScreenIsProviderConfigured:
    """Tests for _is_provider_configured method."""

    @patch("screens.providers.Config")
    def test_cloud_provider_configured_with_api_key(self, mock_config):
        """Cloud provider is configured if API key is set."""
        from screens.providers import ProvidersScreen

        mock_config.get.side_effect = lambda key, default=None: {
            "ai.provider": "openai",
            "ai.openai.api_key": "sk-test-key",
        }.get(key, default)

        screen = ProvidersScreen()
        info = {"requires_api_key": True}

        assert screen._is_provider_configured("openai", info) is True

    @patch("screens.providers.Config")
    def test_cloud_provider_not_configured_without_api_key(self, mock_config):
        """Cloud provider is not configured if API key is missing."""
        from screens.providers import ProvidersScreen

        mock_config.get.side_effect = lambda key, default=None: {
            "ai.provider": None,
            "ai.openai.api_key": None,
        }.get(key, default)

        screen = ProvidersScreen()
        info = {"requires_api_key": True}

        assert screen._is_provider_configured("openai", info) is False

    @patch("screens.providers.Config")
    def test_cloud_provider_not_configured_with_empty_api_key(self, mock_config):
        """Cloud provider is not configured if API key is empty string."""
        from screens.providers import ProvidersScreen

        mock_config.get.side_effect = lambda key, default=None: {
            "ai.provider": None,
            "ai.anthropic.api_key": "",
        }.get(key, default)

        screen = ProvidersScreen()
        info = {"requires_api_key": True}

        assert screen._is_provider_configured("anthropic", info) is False

    @patch("screens.providers.Config")
    def test_local_provider_configured_with_endpoint(self, mock_config):
        """Local provider is configured if endpoint is set."""
        from screens.providers import ProvidersScreen

        mock_config.get.side_effect = lambda key, default=None: {
            "ai.provider": "ollama",
            "ai.ollama.endpoint": "http://localhost:11434",
        }.get(key, default)

        screen = ProvidersScreen()
        info = {"requires_endpoint": True, "requires_api_key": False}

        assert screen._is_provider_configured("ollama", info) is True

    @patch("screens.providers.Config")
    def test_local_provider_not_configured_without_endpoint(self, mock_config):
        """Local provider is not configured if endpoint is missing."""
        from screens.providers import ProvidersScreen

        mock_config.get.side_effect = lambda key, default=None: {
            "ai.provider": None,
            "ai.lm_studio.endpoint": None,
        }.get(key, default)

        screen = ProvidersScreen()
        info = {"requires_endpoint": True, "requires_api_key": False}

        assert screen._is_provider_configured("lm_studio", info) is False

    @patch("screens.providers.Config")
    def test_provider_with_no_requirements_not_configured(self, mock_config):
        """Provider without requirements returns False (must be explicitly configured)."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        info = {}

        assert screen._is_provider_configured("bedrock", info) is False


class TestProvidersScreenButtonHandling:
    """Tests for on_button_pressed event handling."""

    @patch("screens.providers.Config")
    def test_close_button_dismisses_with_none(self, mock_config):
        """Close button should dismiss screen with None result."""
        from textual.widgets import Button

        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        # Create a mock button event
        mock_button = MagicMock(spec=Button)
        mock_button.id = "close_btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with(None)

    @patch("screens.providers.Config")
    def test_configure_button_dismisses_with_configure_action(self, mock_config):
        """Configure button should dismiss with ('configure', provider_name)."""
        from textual.widgets import Button

        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock(spec=Button)
        mock_button.id = "config-openai"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with(("configure", "openai"))

    @patch("screens.providers.Config")
    @patch("config.SettingsManager")
    def test_activate_button_sets_provider_and_dismisses(
        self, mock_settings_manager, mock_config
    ):
        """Activate button should set provider and dismiss with ('activated', provider_name)."""
        from textual.widgets import Button

        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        mock_config.set = MagicMock()
        mock_sm_instance = MagicMock()
        mock_settings_manager.return_value = mock_sm_instance

        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock(spec=Button)
        mock_button.id = "activate-anthropic"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_config.set.assert_called_once_with("ai.provider", "anthropic")
        mock_sm_instance.set.assert_called_once_with("ai", "provider", "anthropic")
        screen.dismiss.assert_called_once_with(("activated", "anthropic"))

    @patch("screens.providers.Config")
    def test_unconfigure_button_removes_provider_config(self, mock_config):
        """Unconfigure button should remove provider config and dismiss."""
        from textual.widgets import Button

        from screens.providers import ProvidersScreen

        mock_storage = MagicMock()
        mock_config.get.return_value = None
        mock_config._get_storage.return_value = mock_storage

        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock(spec=Button)
        mock_button.id = "unconfigure-groq"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        mock_storage.delete_config_prefix.assert_called_once_with("ai.groq.")
        screen.dismiss.assert_called_once_with(("unconfigured", "groq"))

    @patch("screens.providers.Config")
    def test_button_with_none_id_is_ignored(self, mock_config):
        """Button with None id should not cause errors."""
        from textual.widgets import Button

        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock(spec=Button)
        mock_button.id = None
        mock_event = MagicMock()
        mock_event.button = mock_button

        # Should not raise
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_not_called()


class TestProvidersScreenUnconfigureProvider:
    """Tests for _unconfigure_provider method."""

    @patch("screens.providers.Config")
    def test_unconfigure_deletes_provider_config_prefix(self, mock_config):
        """_unconfigure_provider should delete all keys with provider prefix."""
        from screens.providers import ProvidersScreen

        mock_storage = MagicMock()
        mock_config.get.return_value = None
        mock_config._get_storage.return_value = mock_storage

        screen = ProvidersScreen()
        screen._unconfigure_provider("openai")

        mock_storage.delete_config_prefix.assert_called_once_with("ai.openai.")

    @patch("screens.providers.Config")
    def test_unconfigure_handles_different_providers(self, mock_config):
        """_unconfigure_provider should work with any provider name."""
        from screens.providers import ProvidersScreen

        mock_storage = MagicMock()
        mock_config.get.return_value = None
        mock_config._get_storage.return_value = mock_storage

        screen = ProvidersScreen()

        screen._unconfigure_provider("anthropic")
        mock_storage.delete_config_prefix.assert_called_with("ai.anthropic.")

        screen._unconfigure_provider("google")
        mock_storage.delete_config_prefix.assert_called_with("ai.google.")


class TestProvidersScreenActions:
    """Tests for ProvidersScreen action methods."""

    @patch("screens.providers.Config")
    def test_action_focus_prev_calls_focus_previous(self, mock_config):
        """action_focus_prev should call focus_previous."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.focus_previous = MagicMock()

        screen.action_focus_prev()

        screen.focus_previous.assert_called_once()

    @patch("screens.providers.Config")
    def test_action_focus_next_calls_focus_next_method(self, mock_config):
        """action_focus_next should call focus_next."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.focus_next = MagicMock()

        screen.action_focus_next()

        screen.focus_next.assert_called_once()

    @patch("screens.providers.Config")
    def test_action_configure_focused_with_provider_row(self, mock_config):
        """action_configure_focused should dismiss with configure action for focused ProviderRow."""
        from screens.providers import ProviderRow, ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        # Create a mock ProviderRow as focused element
        mock_row = MagicMock(spec=ProviderRow)
        mock_row.provider_name = "mistral"
        screen._focused = mock_row  # Set internal focused property

        # Override the focused property getter
        type(screen).focused = property(lambda self: self._focused)

        screen.action_configure_focused()

        screen.dismiss.assert_called_once_with(("configure", "mistral"))

    @patch("screens.providers.Config")
    def test_action_configure_focused_with_non_provider_row_does_nothing(
        self, mock_config
    ):
        """action_configure_focused should do nothing if focused element is not ProviderRow."""
        from textual.widgets import Button

        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        # Set focused to something other than ProviderRow
        screen._focused = MagicMock(spec=Button)
        type(screen).focused = property(lambda self: self._focused)

        screen.action_configure_focused()

        screen.dismiss.assert_not_called()

    @patch("screens.providers.Config")
    def test_action_configure_focused_with_none_focus_does_nothing(self, mock_config):
        """action_configure_focused should do nothing if nothing is focused."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        screen._focused = None
        type(screen).focused = property(lambda self: self._focused)

        screen.action_configure_focused()

        screen.dismiss.assert_not_called()


class TestProvidersScreenActionDismiss:
    """Tests for action_dismiss async method."""

    @patch("screens.providers.Config")
    @pytest.mark.asyncio
    async def test_action_dismiss_calls_dismiss_with_none(self, mock_config):
        """action_dismiss should call dismiss with None."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss()

        screen.dismiss.assert_called_once_with(None)

    @patch("screens.providers.Config")
    @pytest.mark.asyncio
    async def test_action_dismiss_ignores_result_parameter(self, mock_config):
        """action_dismiss should ignore the result parameter and always dismiss with None."""
        from screens.providers import ProvidersScreen

        mock_config.get.return_value = None
        screen = ProvidersScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result="some_value")

        screen.dismiss.assert_called_once_with(None)


class TestProviderRowInfoHandling:
    """Tests for ProviderRow handling of info dictionary."""

    def test_provider_row_handles_empty_info(self):
        """ProviderRow should handle empty info dict gracefully."""
        from screens.providers import ProviderRow

        row = ProviderRow("test", {}, is_active=False, is_configured=False)
        assert row.info == {}
        assert row.info.get("name", "fallback") == "fallback"

    def test_provider_row_handles_partial_info(self):
        """ProviderRow should handle info dict with missing keys."""
        from screens.providers import ProviderRow

        info = {"name": "TestProvider"}  # Missing description
        row = ProviderRow("test", info, is_active=False, is_configured=False)

        assert row.info.get("name") == "TestProvider"
        assert row.info.get("description", "") == ""

    def test_provider_row_with_full_info(self):
        """ProviderRow should store complete info dictionary."""
        from screens.providers import ProviderRow

        info = {
            "name": "OpenAI",
            "description": "GPT models",
            "requires_api_key": True,
            "requires_endpoint": False,
        }
        row = ProviderRow("openai", info, is_active=False, is_configured=True)

        assert row.info["name"] == "OpenAI"
        assert row.info["description"] == "GPT models"
        assert row.info["requires_api_key"] is True
        assert row.info["requires_endpoint"] is False
