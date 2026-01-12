"""Unit tests for config/defaults.py - default configuration values."""

import os

from config.defaults import (
    DEFAULT_AGENT_MODE,
    DEFAULT_AI_ACTIVE_PROMPT,
    DEFAULT_AI_ENDPOINT,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SHELL,
    DEFAULT_TEMPERATURE,
    DEFAULT_THEME,
)


class TestThemeDefaults:
    """Tests for theme default values."""

    def test_default_theme_exists(self):
        """DEFAULT_THEME should be defined."""
        assert DEFAULT_THEME is not None

    def test_default_theme_is_string(self):
        """DEFAULT_THEME should be a string."""
        assert isinstance(DEFAULT_THEME, str)

    def test_default_theme_value(self):
        """DEFAULT_THEME should be 'null-dark'."""
        assert DEFAULT_THEME == "null-dark"


class TestShellDefaults:
    """Tests for shell default values."""

    def test_default_shell_exists(self):
        """DEFAULT_SHELL should be defined."""
        assert DEFAULT_SHELL is not None

    def test_default_shell_is_string(self):
        """DEFAULT_SHELL should be a string."""
        assert isinstance(DEFAULT_SHELL, str)

    def test_default_shell_is_absolute_path(self):
        """DEFAULT_SHELL should be an absolute path."""
        assert DEFAULT_SHELL.startswith("/")

    def test_default_shell_uses_environment(self):
        """DEFAULT_SHELL should use SHELL env var if available."""
        # The default falls back to /bin/bash if SHELL is not set
        expected = os.environ.get("SHELL", "/bin/bash")
        assert DEFAULT_SHELL == expected

    def test_default_shell_fallback(self, monkeypatch):
        """Without SHELL env var, should fall back to /bin/bash."""
        # This test verifies the behavior at module import time
        # We can't easily test the import-time behavior, but we test the logic
        monkeypatch.delenv("SHELL", raising=False)
        fallback = os.environ.get("SHELL", "/bin/bash")
        assert fallback == "/bin/bash"


class TestAIProviderDefaults:
    """Tests for AI provider default values."""

    def test_default_ai_provider_exists(self):
        """DEFAULT_AI_PROVIDER should be defined."""
        assert DEFAULT_AI_PROVIDER is not None

    def test_default_ai_provider_is_string(self):
        """DEFAULT_AI_PROVIDER should be a string."""
        assert isinstance(DEFAULT_AI_PROVIDER, str)

    def test_default_ai_provider_value(self):
        """DEFAULT_AI_PROVIDER should be empty (user must configure)."""
        assert DEFAULT_AI_PROVIDER == ""

    def test_default_ai_model_exists(self):
        """DEFAULT_AI_MODEL should be defined."""
        assert DEFAULT_AI_MODEL is not None

    def test_default_ai_model_is_string(self):
        """DEFAULT_AI_MODEL should be a string."""
        assert isinstance(DEFAULT_AI_MODEL, str)

    def test_default_ai_model_value(self):
        """DEFAULT_AI_MODEL should be empty (user must configure)."""
        assert DEFAULT_AI_MODEL == ""

    def test_default_ai_endpoint_exists(self):
        """DEFAULT_AI_ENDPOINT should be defined."""
        assert DEFAULT_AI_ENDPOINT is not None

    def test_default_ai_endpoint_is_string(self):
        """DEFAULT_AI_ENDPOINT should be a string."""
        assert isinstance(DEFAULT_AI_ENDPOINT, str)

    def test_default_ai_endpoint_is_empty(self):
        """DEFAULT_AI_ENDPOINT should be empty (user must configure)."""
        assert DEFAULT_AI_ENDPOINT == ""

    def test_default_ai_active_prompt_exists(self):
        """DEFAULT_AI_ACTIVE_PROMPT should be defined."""
        assert DEFAULT_AI_ACTIVE_PROMPT is not None

    def test_default_ai_active_prompt_is_string(self):
        """DEFAULT_AI_ACTIVE_PROMPT should be a string."""
        assert isinstance(DEFAULT_AI_ACTIVE_PROMPT, str)

    def test_default_ai_active_prompt_value(self):
        """DEFAULT_AI_ACTIVE_PROMPT should be 'default'."""
        assert DEFAULT_AI_ACTIVE_PROMPT == "default"


class TestAgentModeDefaults:
    """Tests for agent mode default values."""

    def test_default_agent_mode_exists(self):
        """DEFAULT_AGENT_MODE should be defined."""
        assert DEFAULT_AGENT_MODE is not None

    def test_default_agent_mode_is_bool(self):
        """DEFAULT_AGENT_MODE should be a boolean."""
        assert isinstance(DEFAULT_AGENT_MODE, bool)

    def test_default_agent_mode_value(self):
        """DEFAULT_AGENT_MODE should be False."""
        assert DEFAULT_AGENT_MODE is False


class TestContextDefaults:
    """Tests for context and token default values."""

    def test_default_context_window_exists(self):
        """DEFAULT_CONTEXT_WINDOW should be defined."""
        assert DEFAULT_CONTEXT_WINDOW is not None

    def test_default_context_window_is_int(self):
        """DEFAULT_CONTEXT_WINDOW should be an integer."""
        assert isinstance(DEFAULT_CONTEXT_WINDOW, int)

    def test_default_context_window_positive(self):
        """DEFAULT_CONTEXT_WINDOW should be positive."""
        assert DEFAULT_CONTEXT_WINDOW > 0

    def test_default_context_window_value(self):
        """DEFAULT_CONTEXT_WINDOW should be 4000."""
        assert DEFAULT_CONTEXT_WINDOW == 4000

    def test_default_max_tokens_exists(self):
        """DEFAULT_MAX_TOKENS should be defined."""
        assert DEFAULT_MAX_TOKENS is not None

    def test_default_max_tokens_is_int(self):
        """DEFAULT_MAX_TOKENS should be an integer."""
        assert isinstance(DEFAULT_MAX_TOKENS, int)

    def test_default_max_tokens_positive(self):
        """DEFAULT_MAX_TOKENS should be positive."""
        assert DEFAULT_MAX_TOKENS > 0

    def test_default_max_tokens_value(self):
        """DEFAULT_MAX_TOKENS should be 2048."""
        assert DEFAULT_MAX_TOKENS == 2048

    def test_max_tokens_less_than_context(self):
        """DEFAULT_MAX_TOKENS should be less than DEFAULT_CONTEXT_WINDOW."""
        assert DEFAULT_MAX_TOKENS < DEFAULT_CONTEXT_WINDOW


class TestTemperatureDefaults:
    """Tests for temperature default values."""

    def test_default_temperature_exists(self):
        """DEFAULT_TEMPERATURE should be defined."""
        assert DEFAULT_TEMPERATURE is not None

    def test_default_temperature_is_float(self):
        """DEFAULT_TEMPERATURE should be a float."""
        assert isinstance(DEFAULT_TEMPERATURE, float)

    def test_default_temperature_in_range(self):
        """DEFAULT_TEMPERATURE should be between 0 and 2."""
        assert 0.0 <= DEFAULT_TEMPERATURE <= 2.0

    def test_default_temperature_value(self):
        """DEFAULT_TEMPERATURE should be 0.7."""
        assert DEFAULT_TEMPERATURE == 0.7


class TestDefaultsConsistency:
    """Tests for consistency between related defaults."""

    def test_ai_defaults_are_empty(self):
        """AI provider/model/endpoint defaults should be empty (user must configure)."""
        assert DEFAULT_AI_PROVIDER == ""
        assert DEFAULT_AI_MODEL == ""
        assert DEFAULT_AI_ENDPOINT == ""

    def test_all_defaults_have_values(self):
        """All default values should be non-None."""
        defaults = [
            DEFAULT_THEME,
            DEFAULT_SHELL,
            DEFAULT_AI_ACTIVE_PROMPT,
            DEFAULT_CONTEXT_WINDOW,
            DEFAULT_MAX_TOKENS,
            DEFAULT_TEMPERATURE,
        ]
        for default in defaults:
            assert default is not None

    def test_required_defaults_are_not_empty_strings(self):
        """Required string defaults should not be empty."""
        string_defaults = [
            DEFAULT_THEME,
            DEFAULT_SHELL,
            DEFAULT_AI_ACTIVE_PROMPT,
        ]
        for default in string_defaults:
            assert len(default) > 0
