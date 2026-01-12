"""Unit tests for commands/config.py - ConfigCommands class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.config import ConfigCommands


class TestConfigCommandsInit:
    """Tests for ConfigCommands initialization."""

    def test_init_stores_app_reference(self):
        """ConfigCommands should store app reference."""
        mock_app = MagicMock()
        commands = ConfigCommands(mock_app)
        assert commands.app is mock_app


class TestCmdConfig:
    """Tests for cmd_config method."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock app with required attributes."""
        app = MagicMock()
        app.available_themes = ["null-dark", "dracula", "nord"]
        app.theme = "null-dark"
        app.notify = MagicMock()
        app._update_status_bar = MagicMock()
        app.push_screen = MagicMock()
        return app

    @pytest.fixture
    def config_commands(self, mock_app):
        """Create ConfigCommands instance with mock app."""
        return ConfigCommands(mock_app)

    @pytest.mark.asyncio
    async def test_cmd_config_pushes_screen(self, config_commands, mock_app):
        """cmd_config should push ConfigScreen."""
        with patch("screens.ConfigScreen") as MockConfigScreen:
            mock_screen = MagicMock()
            MockConfigScreen.return_value = mock_screen

            await config_commands.cmd_config([])

            mock_app.push_screen.assert_called_once()
            args, _kwargs = mock_app.push_screen.call_args
            assert args[0] is mock_screen

    @pytest.mark.asyncio
    async def test_cmd_config_callback_applies_theme(self, config_commands, mock_app):
        """Callback should apply theme when valid."""
        with patch("commands.config.Config") as MockConfig:
            with patch("screens.ConfigScreen"):
                with patch.object(config_commands, "notify"):
                    await config_commands.cmd_config([])

                    args, _kwargs = mock_app.push_screen.call_args
                    callback = args[1]

                    result = MagicMock()
                    result.appearance.theme = "dracula"
                    result.ai.provider = "openai"

                    callback(result)

                    assert mock_app.theme == "dracula"
                    MockConfig.set.assert_any_call("theme", "dracula")

    @pytest.mark.asyncio
    async def test_cmd_config_callback_skips_invalid_theme(
        self, config_commands, mock_app
    ):
        """Callback should not apply unknown theme."""
        with patch("screens.ConfigScreen"):
            with patch.object(config_commands, "notify"):
                await config_commands.cmd_config([])

                args, _kwargs = mock_app.push_screen.call_args
                callback = args[1]

                result = MagicMock()
                result.appearance.theme = "unknown-theme"
                result.ai.provider = "openai"

                with patch("config.Config"):
                    callback(result)

                    assert mock_app.theme == "null-dark"

    @pytest.mark.asyncio
    async def test_cmd_config_callback_syncs_ai_provider(
        self, config_commands, mock_app
    ):
        """Callback should sync AI provider to SQLite config."""
        with patch("commands.config.Config") as MockConfig:
            with patch("screens.ConfigScreen"):
                with patch.object(config_commands, "notify"):
                    await config_commands.cmd_config([])

                    args, _kwargs = mock_app.push_screen.call_args
                    callback = args[1]

                    result = MagicMock()
                    result.appearance.theme = "null-dark"
                    result.ai.provider = "anthropic"

                    callback(result)

                    MockConfig.set.assert_any_call("ai.provider", "anthropic")

    @pytest.mark.asyncio
    async def test_cmd_config_callback_notifies_on_save(
        self, config_commands, mock_app
    ):
        """Callback should notify user on successful save."""
        with patch("screens.ConfigScreen"):
            await config_commands.cmd_config([])

            args, _kwargs = mock_app.push_screen.call_args
            callback = args[1]

            result = MagicMock()
            result.appearance.theme = "null-dark"
            result.ai.provider = "ollama"

            with patch("config.Config"):
                callback(result)

                mock_app.notify.assert_called()
                call_args = mock_app.notify.call_args
                assert call_args[0][0] == "Settings saved"

    @pytest.mark.asyncio
    async def test_cmd_config_callback_updates_status_bar(
        self, config_commands, mock_app
    ):
        """Callback should update status bar after saving."""
        with patch("screens.ConfigScreen"):
            with patch.object(config_commands, "notify"):
                await config_commands.cmd_config([])

                args, _kwargs = mock_app.push_screen.call_args
                callback = args[1]

                result = MagicMock()
                result.appearance.theme = "null-dark"
                result.ai.provider = "ollama"

                with patch("config.Config"):
                    callback(result)

                    mock_app._update_status_bar.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_config_callback_handles_none_result(
        self, config_commands, mock_app
    ):
        """Callback should handle None result (cancelled)."""
        with patch("screens.ConfigScreen"):
            await config_commands.cmd_config([])

            args, _kwargs = mock_app.push_screen.call_args
            callback = args[1]

            callback(None)

            mock_app.notify.assert_not_called()
            mock_app._update_status_bar.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_config_callback_handles_empty_theme(
        self, config_commands, mock_app
    ):
        """Callback should handle empty/None theme gracefully."""
        with patch("screens.ConfigScreen"):
            await config_commands.cmd_config([])

            args, _kwargs = mock_app.push_screen.call_args
            callback = args[1]

            result = MagicMock()
            result.appearance.theme = None
            result.ai.provider = "ollama"

            with patch("config.Config"):
                callback(result)

                mock_app.notify.assert_called()
                call_args = mock_app.notify.call_args
                assert call_args[0][0] == "Settings saved"


class TestCmdSettings:
    """Tests for cmd_settings method (alias)."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock app."""
        app = MagicMock()
        app.available_themes = ["null-dark"]
        app.push_screen = MagicMock()
        return app

    @pytest.fixture
    def config_commands(self, mock_app):
        """Create ConfigCommands instance."""
        return ConfigCommands(mock_app)

    @pytest.mark.asyncio
    async def test_cmd_settings_calls_cmd_config(self, config_commands):
        """cmd_settings should call cmd_config."""
        with patch.object(
            config_commands, "cmd_config", new_callable=AsyncMock
        ) as mock_cmd_config:
            await config_commands.cmd_settings(["arg1", "arg2"])
            mock_cmd_config.assert_called_once_with(["arg1", "arg2"])

    @pytest.mark.asyncio
    async def test_cmd_settings_empty_args(self, config_commands):
        """cmd_settings should work with empty args."""
        with patch.object(
            config_commands, "cmd_config", new_callable=AsyncMock
        ) as mock_cmd_config:
            await config_commands.cmd_settings([])
            mock_cmd_config.assert_called_once_with([])


class TestCmdTheme:
    """Tests for cmd_theme method."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock app with theme support."""
        app = MagicMock()
        app.available_themes = ["null-dark", "dracula", "nord", "monokai"]
        app.theme = "null-dark"
        app.action_select_theme = MagicMock()
        app.notify = MagicMock()
        return app

    @pytest.fixture
    def config_commands(self, mock_app):
        """Create ConfigCommands instance."""
        return ConfigCommands(mock_app)

    @pytest.mark.asyncio
    async def test_cmd_theme_no_args_opens_selector(self, config_commands, mock_app):
        """cmd_theme without args should open theme selector."""
        await config_commands.cmd_theme([])
        mock_app.action_select_theme.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_theme_valid_theme_applies(self, config_commands, mock_app):
        """cmd_theme with valid theme should apply it."""
        with patch("commands.config.Config") as MockConfig:
            await config_commands.cmd_theme(["dracula"])

            MockConfig.update_key.assert_called_once_with(["theme"], "dracula")
            assert mock_app.theme == "dracula"

    @pytest.mark.asyncio
    async def test_cmd_theme_valid_theme_notifies(self, config_commands, mock_app):
        """cmd_theme should notify on successful theme change."""
        with patch("commands.config.Config"):
            await config_commands.cmd_theme(["nord"])

            mock_app.notify.assert_called_once()
            call_args = mock_app.notify.call_args
            assert call_args[0][0] == "Theme set to nord"

    @pytest.mark.asyncio
    async def test_cmd_theme_invalid_theme_shows_error(self, config_commands, mock_app):
        """cmd_theme with unknown theme should show error."""
        with patch("commands.config.Config") as MockConfig:
            await config_commands.cmd_theme(["unknown-theme"])

            # Should not update config
            MockConfig.update_key.assert_not_called()
            # Should not change app theme
            assert mock_app.theme == "null-dark"
            # Should show error
            mock_app.notify.assert_called_once_with(
                "Unknown theme: unknown-theme", severity="error"
            )

    @pytest.mark.asyncio
    async def test_cmd_theme_multiple_args_uses_first(self, config_commands, mock_app):
        """cmd_theme with multiple args should use first."""
        with patch("commands.config.Config"):
            await config_commands.cmd_theme(["monokai", "extra", "args"])

            assert mock_app.theme == "monokai"
            mock_app.notify.assert_called_once()
            call_args = mock_app.notify.call_args
            assert call_args[0][0] == "Theme set to monokai"

    @pytest.mark.asyncio
    async def test_cmd_theme_case_sensitive(self, config_commands, mock_app):
        """cmd_theme should be case-sensitive."""
        with patch("commands.config.Config") as MockConfig:
            # "Dracula" (uppercase D) should not match "dracula"
            await config_commands.cmd_theme(["Dracula"])

            MockConfig.update_key.assert_not_called()
            mock_app.notify.assert_called_with(
                "Unknown theme: Dracula", severity="error"
            )


class TestCommandMixinIntegration:
    """Tests for CommandMixin integration."""

    def test_inherits_command_mixin(self):
        """ConfigCommands should inherit from CommandMixin."""
        from commands.base import CommandMixin

        assert issubclass(ConfigCommands, CommandMixin)

    def test_has_notify_method(self):
        """ConfigCommands should have notify method from mixin."""
        mock_app = MagicMock()
        commands = ConfigCommands(mock_app)
        assert hasattr(commands, "notify")

    def test_notify_delegates_to_app(self):
        """notify should delegate to app.notify."""
        mock_app = MagicMock()
        commands = ConfigCommands(mock_app)

        commands.notify("test message", severity="warning")

        mock_app.notify.assert_called_once()
        args, kwargs = mock_app.notify.call_args
        assert args[0] == "test message"
        assert kwargs["severity"] == "warning"
