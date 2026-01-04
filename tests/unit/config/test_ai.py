"""Unit tests for config/ai.py - Config class for AI/LLM settings."""

import pytest
from unittest.mock import MagicMock, patch

from config.ai import Config
from config.defaults import (
    DEFAULT_AI_ACTIVE_PROMPT,
    DEFAULT_AI_ENDPOINT,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    DEFAULT_SHELL,
    DEFAULT_THEME,
)


class TestConfigGet:
    """Tests for Config.get() method."""

    def test_get_existing_key(self, mock_config, mock_storage):
        """get() should return stored value."""
        mock_storage.set_config("test.key", "test_value")
        result = mock_config.get("test.key")
        assert result == "test_value"

    def test_get_nonexistent_with_default(self, mock_config):
        """get() should return default for missing key."""
        result = mock_config.get("nonexistent.key", default="fallback")
        assert result == "fallback"

    def test_get_nonexistent_without_default(self, mock_config):
        """get() without default should return None for missing key."""
        result = mock_config.get("nonexistent.key")
        assert result is None

    def test_get_sensitive_key_decrypted(self, mock_config, mock_storage):
        """get() should return decrypted value for sensitive keys."""
        mock_storage.set_config("ai.openai.api_key", "sk-secret123", is_sensitive=True)
        result = mock_config.get("ai.openai.api_key")
        assert result == "sk-secret123"

    def test_get_various_value_types(self, mock_config, mock_storage):
        """get() should handle various string values."""
        test_cases = [
            ("key.string", "simple"),
            ("key.empty", ""),
            ("key.spaces", "value with spaces"),
            ("key.special", "!@#$%^&*()"),
            ("key.unicode", "\u00e9\u00e8\u00ea"),
            ("key.number_str", "12345"),
            ("key.bool_str", "true"),
        ]
        for key, value in test_cases:
            mock_storage.set_config(key, value)
            assert mock_config.get(key) == value


class TestConfigSet:
    """Tests for Config.set() method."""

    def test_set_basic_value(self, mock_config, mock_storage):
        """set() should store basic value."""
        mock_config.set("test.key", "test_value")
        result = mock_storage.get_config("test.key")
        assert result == "test_value"

    def test_set_overwrites_existing(self, mock_config, mock_storage):
        """set() should overwrite existing value."""
        mock_config.set("test.key", "value1")
        mock_config.set("test.key", "value2")
        result = mock_config.get("test.key")
        assert result == "value2"

    def test_set_sensitive_key_encrypted(self, mock_config, mock_storage):
        """set() should encrypt sensitive keys automatically."""
        mock_config.set("ai.openai.api_key", "sk-secret")

        # Verify it's marked as sensitive in database
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT is_sensitive, value FROM config WHERE key = ?",
            ("ai.openai.api_key",),
        )
        row = cursor.fetchone()
        assert row["is_sensitive"] == 1
        # Value should be encrypted (different from original)
        assert row["value"] != "sk-secret"

        # But get should return decrypted
        assert mock_config.get("ai.openai.api_key") == "sk-secret"

    def test_set_non_sensitive_key_not_encrypted(self, mock_config, mock_storage):
        """set() should not encrypt non-sensitive keys."""
        mock_config.set("ai.provider", "openai")

        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT is_sensitive, value FROM config WHERE key = ?",
            ("ai.provider",),
        )
        row = cursor.fetchone()
        assert row["is_sensitive"] == 0
        assert row["value"] == "openai"

    def test_set_pattern_matched_sensitive_key(self, mock_config, mock_storage):
        """set() should encrypt keys matching sensitive patterns."""
        # Keys ending with .api_key should be sensitive
        mock_config.set("ai.custom_provider.api_key", "my-key")

        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT is_sensitive FROM config WHERE key = ?",
            ("ai.custom_provider.api_key",),
        )
        row = cursor.fetchone()
        assert row["is_sensitive"] == 1


class TestConfigUpdateKey:
    """Tests for Config.update_key() method."""

    def test_update_key_simple_path(self, mock_config, mock_storage):
        """update_key() should work with simple path."""
        mock_config.update_key(["theme"], "light")
        result = mock_config.get("theme")
        assert result == "light"

    def test_update_key_nested_path(self, mock_config, mock_storage):
        """update_key() should join path segments with dots."""
        mock_config.update_key(["ai", "openai", "model"], "gpt-4")
        result = mock_config.get("ai.openai.model")
        assert result == "gpt-4"

    def test_update_key_single_element_path(self, mock_config, mock_storage):
        """update_key() should handle single element path."""
        mock_config.update_key(["shell"], "/bin/zsh")
        result = mock_config.get("shell")
        assert result == "/bin/zsh"

    def test_update_key_sensitive_path(self, mock_config, mock_storage):
        """update_key() should handle sensitive key paths."""
        mock_config.update_key(["ai", "anthropic", "api_key"], "sk-ant-xxx")

        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT is_sensitive FROM config WHERE key = ?",
            ("ai.anthropic.api_key",),
        )
        row = cursor.fetchone()
        assert row["is_sensitive"] == 1


class TestConfigLoadAll:
    """Tests for Config.load_all() method."""

    def test_load_all_returns_dict(self, mock_config):
        """load_all() should return a dictionary."""
        result = mock_config.load_all()
        assert isinstance(result, dict)

    def test_load_all_contains_expected_keys(self, mock_config):
        """load_all() should contain theme, shell, and ai keys."""
        result = mock_config.load_all()
        assert "theme" in result
        assert "shell" in result
        assert "ai" in result

    def test_load_all_ai_structure(self, mock_config):
        """load_all() ai section should have expected structure."""
        result = mock_config.load_all()
        ai = result["ai"]

        assert "provider" in ai
        assert "model" in ai
        assert "endpoint" in ai
        assert "api_key" in ai
        assert "region" in ai
        assert "agent_mode" in ai
        assert "active_prompt" in ai

    def test_load_all_uses_defaults(self, temp_dir, monkeypatch):
        """load_all() should use defaults when no config exists."""
        # Use completely fresh temp directory with no prior data
        from pathlib import Path
        import config.storage as storage_module

        null_dir = temp_dir / ".null"
        null_dir.mkdir(parents=True, exist_ok=True)

        # Patch both Path.home() and the module-level DB_PATH
        monkeypatch.setattr(Path, "home", lambda: temp_dir)
        monkeypatch.setattr(storage_module, "DB_PATH", temp_dir / ".null" / "null.db")

        from config.storage import StorageManager
        from config import Config

        storage = StorageManager()
        try:
            result = Config.load_all()

            assert result["theme"] == DEFAULT_THEME
            assert result["shell"] == DEFAULT_SHELL
            assert result["ai"]["provider"] == DEFAULT_AI_PROVIDER
            assert result["ai"]["model"] == DEFAULT_AI_MODEL
            assert result["ai"]["endpoint"] == DEFAULT_AI_ENDPOINT
            assert result["ai"]["active_prompt"] == DEFAULT_AI_ACTIVE_PROMPT
        finally:
            storage.close()

    def test_load_all_respects_stored_values(self, mock_config, mock_storage):
        """load_all() should use stored values when available."""
        mock_storage.set_config("theme", "custom-theme")
        mock_storage.set_config("shell", "/bin/zsh")
        mock_storage.set_config("ai.provider", "openai")

        result = mock_config.load_all()

        assert result["theme"] == "custom-theme"
        assert result["shell"] == "/bin/zsh"
        assert result["ai"]["provider"] == "openai"

    def test_load_all_dynamic_provider_settings(self, mock_config, mock_storage):
        """load_all() should load settings based on active provider."""
        # Set OpenAI as provider
        mock_storage.set_config("ai.provider", "openai")
        mock_storage.set_config("ai.openai.model", "gpt-4")
        mock_storage.set_config("ai.openai.endpoint", "https://api.openai.com")
        mock_storage.set_config("ai.openai.api_key", "sk-xxx", is_sensitive=True)

        result = mock_config.load_all()

        assert result["ai"]["provider"] == "openai"
        assert result["ai"]["model"] == "gpt-4"
        assert result["ai"]["endpoint"] == "https://api.openai.com"
        assert result["ai"]["api_key"] == "sk-xxx"

    def test_load_all_agent_mode_parsing(self, mock_config, mock_storage):
        """load_all() should parse agent_mode as boolean."""
        # Test various truthy values
        for truthy in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            mock_storage.set_config("ai.agent_mode", truthy)
            result = mock_config.load_all()
            assert result["ai"]["agent_mode"] is True, f"Failed for: {truthy}"

        # Test various falsy values
        for falsy in ["false", "False", "0", "no", "", "anything"]:
            mock_storage.set_config("ai.agent_mode", falsy)
            result = mock_config.load_all()
            assert result["ai"]["agent_mode"] is False, f"Failed for: {falsy}"

    def test_load_all_agent_mode_default(self, mock_config):
        """load_all() should default agent_mode to False."""
        result = mock_config.load_all()
        assert result["ai"]["agent_mode"] is False

    def test_load_all_missing_provider_settings(self, temp_dir, monkeypatch):
        """load_all() should use defaults for missing provider-specific settings."""
        # Use completely fresh temp directory to avoid pollution from other tests
        from pathlib import Path
        import config.storage as storage_module

        null_dir = temp_dir / ".null"
        null_dir.mkdir(parents=True, exist_ok=True)

        # Patch both Path.home() and the module-level DB_PATH
        monkeypatch.setattr(Path, "home", lambda: temp_dir)
        monkeypatch.setattr(storage_module, "DB_PATH", temp_dir / ".null" / "null.db")

        from config.storage import StorageManager
        from config import Config

        storage = StorageManager()
        try:
            storage.set_config("ai.provider", "custom_provider")

            result = Config.load_all()

            # Should fall back to defaults when provider-specific settings missing
            assert result["ai"]["provider"] == "custom_provider"
            assert result["ai"]["model"] == DEFAULT_AI_MODEL
            assert result["ai"]["endpoint"] == DEFAULT_AI_ENDPOINT
            assert result["ai"]["api_key"] == ""
            assert result["ai"]["region"] == ""
        finally:
            storage.close()


class TestConfigGetStorage:
    """Tests for Config._get_storage() internal method."""

    def test_get_storage_returns_storage_manager(self, mock_home):
        """_get_storage() should return StorageManager instance."""
        from config.storage import StorageManager

        storage = Config._get_storage()
        assert isinstance(storage, StorageManager)
        storage.close()

    def test_get_storage_creates_new_instance(self, mock_home):
        """_get_storage() should create new instance each call."""
        storage1 = Config._get_storage()
        storage2 = Config._get_storage()
        # They should be different instances
        assert storage1 is not storage2
        storage1.close()
        storage2.close()


class TestConfigIntegration:
    """Integration tests for Config class."""

    def test_set_and_load_all_roundtrip(self, mock_config, mock_storage):
        """Values set via set() should appear in load_all()."""
        mock_config.set("theme", "roundtrip-theme")
        mock_config.set("ai.provider", "anthropic")
        mock_config.set("ai.anthropic.model", "claude-3")

        result = mock_config.load_all()

        assert result["theme"] == "roundtrip-theme"
        assert result["ai"]["provider"] == "anthropic"
        assert result["ai"]["model"] == "claude-3"

    def test_update_key_and_get_roundtrip(self, mock_config, mock_storage):
        """Values set via update_key() should be retrievable via get()."""
        mock_config.update_key(["ai", "groq", "endpoint"], "https://api.groq.com")
        result = mock_config.get("ai.groq.endpoint")
        assert result == "https://api.groq.com"

    def test_multiple_providers_isolation(self, mock_config, mock_storage):
        """Settings for different providers should be isolated."""
        # Set up multiple providers
        mock_config.set("ai.openai.api_key", "openai-key")
        mock_config.set("ai.anthropic.api_key", "anthropic-key")
        mock_config.set("ai.openai.model", "gpt-4")
        mock_config.set("ai.anthropic.model", "claude-3")

        # Each should be independently accessible
        assert mock_config.get("ai.openai.api_key") == "openai-key"
        assert mock_config.get("ai.anthropic.api_key") == "anthropic-key"
        assert mock_config.get("ai.openai.model") == "gpt-4"
        assert mock_config.get("ai.anthropic.model") == "claude-3"

        # load_all should use active provider
        mock_config.set("ai.provider", "openai")
        result = mock_config.load_all()
        assert result["ai"]["api_key"] == "openai-key"
        assert result["ai"]["model"] == "gpt-4"

        mock_config.set("ai.provider", "anthropic")
        result = mock_config.load_all()
        assert result["ai"]["api_key"] == "anthropic-key"
        assert result["ai"]["model"] == "claude-3"
