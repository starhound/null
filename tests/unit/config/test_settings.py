"""Unit tests for config/settings.py - Settings dataclasses and SettingsManager."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from config.settings import (
    CONFIG_PATH,
    AISettings,
    AppearanceSettings,
    EditorSettings,
    Settings,
    SettingsManager,
    TerminalSettings,
    get_settings,
    save_settings,
)


class TestAppearanceSettings:
    """Tests for AppearanceSettings dataclass."""

    def test_default_values(self):
        """AppearanceSettings should have expected defaults."""
        settings = AppearanceSettings()
        assert settings.theme == "null-dark"
        assert settings.font_family == "monospace"
        assert settings.font_size == 14
        assert settings.line_height == 1.4
        assert settings.show_timestamps is True
        assert settings.show_line_numbers is True

    def test_custom_values(self):
        """AppearanceSettings should accept custom values."""
        settings = AppearanceSettings(
            theme="light",
            font_family="Fira Code",
            font_size=16,
            line_height=1.6,
            show_timestamps=False,
            show_line_numbers=False,
        )
        assert settings.theme == "light"
        assert settings.font_family == "Fira Code"
        assert settings.font_size == 16
        assert settings.line_height == 1.6
        assert settings.show_timestamps is False
        assert settings.show_line_numbers is False

    def test_can_convert_to_dict(self):
        """AppearanceSettings should be convertible to dict."""
        settings = AppearanceSettings()
        d = asdict(settings)
        assert isinstance(d, dict)
        assert "theme" in d
        assert "font_family" in d


class TestEditorSettings:
    """Tests for EditorSettings dataclass."""

    def test_default_values(self):
        """EditorSettings should have expected defaults."""
        settings = EditorSettings()
        assert settings.tab_size == 4
        assert settings.word_wrap is True
        assert settings.auto_indent is True
        assert settings.vim_mode is False

    def test_custom_values(self):
        """EditorSettings should accept custom values."""
        settings = EditorSettings(
            tab_size=2,
            word_wrap=False,
            auto_indent=False,
            vim_mode=True,
        )
        assert settings.tab_size == 2
        assert settings.word_wrap is False
        assert settings.auto_indent is False
        assert settings.vim_mode is True


class TestTerminalSettings:
    """Tests for TerminalSettings dataclass."""

    def test_default_shell_from_env(self):
        """TerminalSettings shell should default to SHELL env var."""
        settings = TerminalSettings()
        expected = os.environ.get("SHELL", "/bin/bash")
        assert settings.shell == expected

    def test_default_values(self):
        """TerminalSettings should have expected defaults."""
        settings = TerminalSettings()
        assert settings.scrollback_lines == 10000
        assert settings.clear_on_exit is False
        assert settings.confirm_on_exit is True
        assert settings.auto_save_session is True
        assert settings.auto_save_interval == 30
        assert settings.cursor_style == "block"
        assert settings.cursor_blink is True
        assert settings.bold_is_bright is True

    def test_env_derived_values(self):
        """TerminalSettings should read environment values."""
        settings = TerminalSettings()
        assert settings.term_type == os.environ.get("TERM", "xterm-256color")
        assert settings.colorterm == os.environ.get("COLORTERM", "truecolor")
        assert settings.lang == os.environ.get("LANG", "en_US.UTF-8")

    def test_custom_values(self):
        """TerminalSettings should accept custom values."""
        settings = TerminalSettings(
            shell="/bin/zsh",
            scrollback_lines=5000,
            cursor_style="beam",
            cursor_blink=False,
        )
        assert settings.shell == "/bin/zsh"
        assert settings.scrollback_lines == 5000
        assert settings.cursor_style == "beam"
        assert settings.cursor_blink is False


class TestAISettings:
    """Tests for AISettings dataclass."""

    def test_default_values(self):
        """AISettings should have expected defaults."""
        settings = AISettings()
        assert settings.provider == "ollama"
        assert settings.default_model == ""
        assert settings.active_prompt == "default"
        assert settings.context_window == 4000
        assert settings.max_tokens == 2048
        assert settings.temperature == 0.7
        assert settings.stream_responses is True
        assert settings.autocomplete_enabled is False
        assert settings.autocomplete_provider == ""
        assert settings.autocomplete_model == ""

    def test_custom_values(self):
        """AISettings should accept custom values."""
        settings = AISettings(
            provider="openai",
            default_model="gpt-4",
            temperature=0.5,
            max_tokens=4096,
            autocomplete_enabled=True,
        )
        assert settings.provider == "openai"
        assert settings.default_model == "gpt-4"
        assert settings.temperature == 0.5
        assert settings.max_tokens == 4096
        assert settings.autocomplete_enabled is True


class TestSettings:
    """Tests for Settings container dataclass."""

    def test_default_initialization(self):
        """Settings should initialize with default sub-settings."""
        settings = Settings()
        assert isinstance(settings.appearance, AppearanceSettings)
        assert isinstance(settings.editor, EditorSettings)
        assert isinstance(settings.terminal, TerminalSettings)
        assert isinstance(settings.ai, AISettings)

    def test_custom_sub_settings(self):
        """Settings should accept custom sub-settings."""
        appearance = AppearanceSettings(theme="light")
        settings = Settings(appearance=appearance)
        assert settings.appearance.theme == "light"

    def test_to_dict(self):
        """to_dict() should return nested dictionary."""
        settings = Settings()
        d = settings.to_dict()

        assert isinstance(d, dict)
        assert "appearance" in d
        assert "editor" in d
        assert "terminal" in d
        assert "ai" in d

        assert d["appearance"]["theme"] == "null-dark"
        assert d["editor"]["tab_size"] == 4
        assert d["ai"]["provider"] == "ollama"

    def test_from_dict_with_all_sections(self):
        """from_dict() should restore settings from dict."""
        data = {
            "appearance": {"theme": "light", "font_size": 16},
            "editor": {"tab_size": 2, "vim_mode": True},
            "terminal": {"scrollback_lines": 5000},
            "ai": {"provider": "openai", "temperature": 0.3},
        }

        settings = Settings.from_dict(data)
        assert settings.appearance.theme == "light"
        assert settings.appearance.font_size == 16
        assert settings.editor.tab_size == 2
        assert settings.editor.vim_mode is True
        assert settings.terminal.scrollback_lines == 5000
        assert settings.ai.provider == "openai"
        assert settings.ai.temperature == 0.3

    def test_from_dict_partial(self):
        """from_dict() should handle partial data with defaults."""
        data = {"appearance": {"theme": "custom"}}

        settings = Settings.from_dict(data)
        assert settings.appearance.theme == "custom"
        # Other appearance settings should be defaults
        assert settings.appearance.font_size == 14
        # Other sections should be defaults
        assert settings.editor.tab_size == 4
        assert settings.ai.provider == "ollama"

    def test_from_dict_empty(self):
        """from_dict() with empty dict should return defaults."""
        settings = Settings.from_dict({})
        assert settings.appearance.theme == "null-dark"
        assert settings.editor.tab_size == 4

    def test_from_dict_unknown_keys_ignored(self):
        """from_dict() should ignore unknown keys."""
        data = {
            "appearance": {"theme": "test", "unknown_key": "value"},
            "unknown_section": {"key": "value"},
        }

        settings = Settings.from_dict(data)
        assert settings.appearance.theme == "test"
        # Should not raise, unknown keys silently ignored

    def test_roundtrip(self):
        """to_dict() and from_dict() should roundtrip."""
        original = Settings()
        original.appearance.theme = "custom"
        original.editor.vim_mode = True
        original.ai.temperature = 0.5

        data = original.to_dict()
        restored = Settings.from_dict(data)

        assert restored.appearance.theme == original.appearance.theme
        assert restored.editor.vim_mode == original.editor.vim_mode
        assert restored.ai.temperature == original.ai.temperature


class TestSettingsManager:
    """Tests for SettingsManager class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset SettingsManager singleton between tests."""
        SettingsManager._instance = None
        SettingsManager._settings = None
        yield
        SettingsManager._instance = None
        SettingsManager._settings = None

    @pytest.fixture
    def mock_config_path(self, mock_home):
        """Mock CONFIG_PATH to use temp directory."""
        config_path = mock_home / ".null" / "config.json"
        with patch("config.settings.CONFIG_PATH", config_path):
            yield config_path

    def test_singleton_pattern(self, mock_config_path):
        """SettingsManager should be a singleton."""
        sm1 = SettingsManager()
        sm2 = SettingsManager()
        assert sm1 is sm2

    def test_load_creates_default_on_first_run(self, mock_config_path):
        """load() should create default settings if config doesn't exist."""
        assert not mock_config_path.exists()

        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()
            settings = sm.settings

        assert settings is not None
        assert settings.appearance.theme == "null-dark"

    def test_load_reads_existing_config(self, mock_config_path):
        """load() should read existing config file."""
        mock_config_path.parent.mkdir(parents=True, exist_ok=True)
        mock_config_path.write_text(
            json.dumps({"appearance": {"theme": "custom-theme"}}),
            encoding="utf-8",
        )

        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()

        assert sm.settings.appearance.theme == "custom-theme"

    def test_load_handles_invalid_json(self, mock_config_path):
        """load() should return defaults on invalid JSON."""
        mock_config_path.parent.mkdir(parents=True, exist_ok=True)
        mock_config_path.write_text("invalid json {{{", encoding="utf-8")

        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()

        # Should return defaults instead of crashing
        assert sm.settings.appearance.theme == "null-dark"

    def test_save_writes_config(self, mock_config_path):
        """save() should write settings to config file."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()
            sm.settings.appearance.theme = "saved-theme"
            sm.save()

        # Read back from file
        data = json.loads(mock_config_path.read_text(encoding="utf-8"))
        assert data["appearance"]["theme"] == "saved-theme"

    def test_save_creates_parent_directory(self, mock_home):
        """save() should create parent directory if needed."""
        config_path = mock_home / ".null" / "subdir" / "config.json"

        with patch("config.settings.CONFIG_PATH", config_path):
            sm = SettingsManager()
            sm.save()

        assert config_path.parent.exists()

    def test_get_method(self, mock_config_path):
        """get() should retrieve specific setting."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()
            sm.settings.appearance.font_size = 20

        result = sm.get("appearance", "font_size")
        assert result == 20

    def test_get_with_default(self, mock_config_path):
        """get() should return default for missing key."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()

        result = sm.get("appearance", "nonexistent", default="fallback")
        assert result == "fallback"

    def test_get_invalid_section(self, mock_config_path):
        """get() should return default for invalid section."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()

        result = sm.get("invalid_section", "key", default="fallback")
        assert result == "fallback"

    def test_set_method(self, mock_config_path):
        """set() should update and save setting."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()
            sm.set("appearance", "theme", "new-theme")

        assert sm.settings.appearance.theme == "new-theme"
        # Should be persisted
        data = json.loads(mock_config_path.read_text(encoding="utf-8"))
        assert data["appearance"]["theme"] == "new-theme"

    def test_set_invalid_key_ignored(self, mock_config_path):
        """set() with invalid key should not raise."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()
            sm.set("appearance", "nonexistent_key", "value")  # Should not raise

    def test_reload_method(self, mock_config_path):
        """reload() should re-read settings from disk."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()
            sm.settings.appearance.theme = "modified"

            # Write different value directly to file
            mock_config_path.write_text(
                json.dumps({"appearance": {"theme": "from-disk"}}),
                encoding="utf-8",
            )

            sm.reload()

        assert sm.settings.appearance.theme == "from-disk"

    def test_settings_property(self, mock_config_path):
        """settings property should return Settings instance."""
        with patch("config.settings.CONFIG_PATH", mock_config_path):
            sm = SettingsManager()

        assert isinstance(sm.settings, Settings)


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset SettingsManager singleton between tests."""
        SettingsManager._instance = None
        SettingsManager._settings = None
        yield
        SettingsManager._instance = None
        SettingsManager._settings = None

    def test_get_settings(self, mock_home):
        """get_settings() should return Settings instance."""
        config_path = mock_home / ".null" / "config.json"
        with patch("config.settings.CONFIG_PATH", config_path):
            settings = get_settings()

        assert isinstance(settings, Settings)

    def test_save_settings(self, mock_home):
        """save_settings() should save settings to disk."""
        config_path = mock_home / ".null" / "config.json"

        with patch("config.settings.CONFIG_PATH", config_path):
            settings = Settings()
            settings.appearance.theme = "saved-via-function"
            save_settings(settings)

        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["appearance"]["theme"] == "saved-via-function"


class TestConfigPath:
    """Tests for CONFIG_PATH constant."""

    def test_config_path_in_home(self):
        """CONFIG_PATH should be in user's .null directory."""
        assert ".null" in str(CONFIG_PATH)
        assert "config.json" in str(CONFIG_PATH)

    def test_config_path_is_path_object(self):
        """CONFIG_PATH should be a Path object."""
        assert isinstance(CONFIG_PATH, Path)
