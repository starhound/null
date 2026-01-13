"""Integration tests for configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.ai import Config
from config.defaults import (
    DEFAULT_AI_ACTIVE_PROMPT,
    DEFAULT_AI_ENDPOINT,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    DEFAULT_SHELL,
    DEFAULT_THEME,
)
from config.keys import SENSITIVE_KEYS, ConfigKeys, is_sensitive_key
from config.storage import SecurityManager, StorageManager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Isolate tests from real home directory."""
    null_dir = tmp_path / ".null"
    null_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def isolated_storage(isolated_home, monkeypatch):
    """Create isolated StorageManager with temp database."""
    import config.storage as storage_module

    temp_db_path = isolated_home / ".null" / "null.db"
    monkeypatch.setattr(storage_module, "DB_PATH", temp_db_path)

    storage = StorageManager()
    yield storage
    storage.close()


@pytest.fixture
def isolated_config(isolated_storage):
    """Provide Config facade with isolated storage."""
    return Config


@pytest.fixture
def in_memory_storage(isolated_home):
    """Create an in-memory storage manager."""
    storage = StorageManager(db_path=Path(":memory:"))
    yield storage
    storage.close()


# ============================================================================
# AISettings Loading/Saving Tests
# ============================================================================


class TestAISettingsLoadSave:
    """Test AISettings (Config) loading and saving."""

    def test_load_all_defaults(self, isolated_config):
        """Test loading configuration returns defaults when empty."""
        config = isolated_config.load_all()

        assert config["theme"] == DEFAULT_THEME
        assert config["shell"] == DEFAULT_SHELL
        assert config["ai"]["provider"] == DEFAULT_AI_PROVIDER
        assert config["ai"]["model"] == DEFAULT_AI_MODEL
        assert config["ai"]["endpoint"] == DEFAULT_AI_ENDPOINT
        assert config["ai"]["active_prompt"] == DEFAULT_AI_ACTIVE_PROMPT

    def test_set_and_get_basic_config(self, isolated_config):
        """Test setting and getting basic configuration values."""
        isolated_config.set("theme", "monokai")
        isolated_config.set("shell", "/bin/zsh")

        assert isolated_config.get("theme") == "monokai"
        assert isolated_config.get("shell") == "/bin/zsh"

    def test_set_and_get_ai_provider(self, isolated_config):
        """Test setting AI provider configuration."""
        isolated_config.set("ai.provider", "openai")
        isolated_config.set("ai.openai.model", "gpt-4")
        isolated_config.set("ai.openai.endpoint", "https://api.openai.com/v1")

        config = isolated_config.load_all()
        assert config["ai"]["provider"] == "openai"
        assert config["ai"]["model"] == "gpt-4"
        assert config["ai"]["endpoint"] == "https://api.openai.com/v1"

    def test_update_key_with_path(self, isolated_config):
        """Test update_key with path notation."""
        isolated_config.update_key(["ai", "provider"], "anthropic")
        assert isolated_config.get("ai.provider") == "anthropic"

    def test_get_nonexistent_key_returns_default(self, isolated_config):
        """Test getting nonexistent key returns default."""
        result = isolated_config.get("nonexistent.key", "default_value")
        assert result == "default_value"

    def test_agent_mode_boolean_conversion(self, isolated_config):
        """Test agent mode string to boolean conversion."""
        isolated_config.set("ai.agent_mode", "true")
        config = isolated_config.load_all()
        assert config["ai"]["agent_mode"] is True

        isolated_config.set("ai.agent_mode", "false")
        config = isolated_config.load_all()
        assert config["ai"]["agent_mode"] is False

        isolated_config.set("ai.agent_mode", "1")
        config = isolated_config.load_all()
        assert config["ai"]["agent_mode"] is True

    def test_agent_max_iterations(self, isolated_config):
        """Test agent_max_iterations integer conversion."""
        isolated_config.set("ai.agent_max_iterations", "25")
        config = isolated_config.load_all()
        assert config["ai"]["agent_max_iterations"] == 25

    def test_embedding_provider_config(self, isolated_config):
        """Test embedding provider configuration."""
        isolated_config.set("ai.embedding_provider", "ollama")
        isolated_config.set("ai.embedding.ollama.model", "nomic-embed-text")
        isolated_config.set("ai.embedding.ollama.endpoint", "http://localhost:11434")

        config = isolated_config.load_all()
        assert config["ai"]["embedding_provider"] == "ollama"
        assert config["ai"]["embedding_model"] == "nomic-embed-text"
        assert config["ai"]["embedding_endpoint"] == "http://localhost:11434"


# ============================================================================
# Storage (SQLite) Operations Tests
# ============================================================================


class TestStorageOperations:
    """Test StorageManager SQLite operations."""

    def test_config_crud_operations(self, isolated_storage):
        """Test config CRUD operations."""
        # Create
        isolated_storage.set_config("test.key", "test_value")
        assert isolated_storage.get_config("test.key") == "test_value"

        # Update
        isolated_storage.set_config("test.key", "updated_value")
        assert isolated_storage.get_config("test.key") == "updated_value"

        # Delete
        isolated_storage.delete_config("test.key")
        assert isolated_storage.get_config("test.key") is None

    def test_delete_config_prefix(self, isolated_storage):
        """Test deleting config keys by prefix."""
        isolated_storage.set_config("prefix.key1", "value1")
        isolated_storage.set_config("prefix.key2", "value2")
        isolated_storage.set_config("other.key", "value3")

        isolated_storage.delete_config_prefix("prefix.")

        assert isolated_storage.get_config("prefix.key1") is None
        assert isolated_storage.get_config("prefix.key2") is None
        assert isolated_storage.get_config("other.key") == "value3"

    def test_list_config(self, isolated_storage):
        """Test listing all configuration."""
        isolated_storage.set_config("key1", "value1")
        isolated_storage.set_config("key2", "value2")

        config_list = isolated_storage.list_config()
        assert config_list["key1"] == "value1"
        assert config_list["key2"] == "value2"

    def test_history_operations(self, isolated_storage):
        """Test command history operations."""
        isolated_storage.add_history("ls -la", exit_code=0)
        isolated_storage.add_history("cd /tmp", exit_code=0)
        isolated_storage.add_history("git status", exit_code=1)

        history = isolated_storage.get_last_history(limit=10)
        assert len(history) == 3
        assert "ls -la" in history
        assert "git status" in history

    def test_history_search(self, isolated_storage):
        """Test history search functionality."""
        isolated_storage.add_history("git status")
        isolated_storage.add_history("git commit -m 'test'")
        isolated_storage.add_history("ls -la")

        results = isolated_storage.search_history("git")
        assert len(results) == 2
        assert all("git" in cmd for cmd in results)

    def test_empty_history_not_added(self, isolated_storage):
        """Test empty commands are not added to history."""
        isolated_storage.add_history("")
        isolated_storage.add_history("   ")

        history = isolated_storage.get_last_history()
        assert len(history) == 0

    def test_ssh_host_crud(self, isolated_storage):
        """Test SSH host CRUD operations."""
        # Add
        isolated_storage.add_ssh_host(
            alias="myserver",
            hostname="192.168.1.100",
            port=22,
            username="admin",
            key_path="/home/user/.ssh/id_rsa",
        )

        # Get
        host = isolated_storage.get_ssh_host("myserver")
        assert host is not None
        assert host["hostname"] == "192.168.1.100"
        assert host["username"] == "admin"

        # List
        hosts = isolated_storage.list_ssh_hosts()
        assert len(hosts) == 1

        # Delete
        isolated_storage.delete_ssh_host("myserver")
        assert isolated_storage.get_ssh_host("myserver") is None

    def test_ssh_host_with_password(self, isolated_storage):
        """Test SSH host with encrypted password."""
        isolated_storage.add_ssh_host(
            alias="secure_server",
            hostname="10.0.0.1",
            password="secret123",
        )

        host = isolated_storage.get_ssh_host("secure_server")
        assert host["password"] == "secret123"

    def test_ssh_host_with_jump_host(self, isolated_storage):
        """Test SSH host with jump host configuration."""
        isolated_storage.add_ssh_host(
            alias="internal",
            hostname="10.0.0.50",
            jump_host="bastion.example.com",
        )

        host = isolated_storage.get_ssh_host("internal")
        assert host["jump_host"] == "bastion.example.com"

    def test_interactions_crud(self, isolated_storage):
        """Test interaction storage operations."""
        # Add
        row_id = isolated_storage.add_interaction(
            type="command",
            input_text="ls -la",
            output_text="file1.txt\nfile2.txt",
            metadata='{"cwd": "/home/user"}',
        )
        assert row_id is not None

        # Search
        results = isolated_storage.search_interactions("ls")
        assert len(results) == 1
        assert results[0]["input"] == "ls -la"

    def test_in_memory_storage(self, in_memory_storage):
        """Test in-memory storage mode."""
        in_memory_storage.set_config("test", "value")
        assert in_memory_storage.get_config("test") == "value"


# ============================================================================
# Encryption Tests
# ============================================================================


class TestEncryption:
    """Test encryption of sensitive data."""

    def test_security_manager_encrypt_decrypt(self, isolated_home):
        """Test basic encryption and decryption."""
        security = SecurityManager()

        plaintext = "my_secret_api_key_12345"
        encrypted = security.encrypt(plaintext)

        # Encrypted should be different from plaintext
        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)

        # Decryption should return original
        decrypted = security.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, isolated_home):
        """Test encrypting empty string returns empty."""
        security = SecurityManager()
        assert security.encrypt("") == ""
        assert security.decrypt("") == ""

    def test_sensitive_config_encrypted_in_storage(self, isolated_storage):
        """Test sensitive config values are encrypted in database."""
        api_key = "sk-test-api-key-1234567890"

        isolated_storage.set_config("ai.openai.api_key", api_key, is_sensitive=True)

        # Query raw database to verify encryption
        cursor = isolated_storage.conn.cursor()
        cursor.execute(
            "SELECT value, is_sensitive FROM config WHERE key = ?",
            ("ai.openai.api_key",),
        )
        row = cursor.fetchone()

        # Value in DB should be encrypted (not plaintext)
        assert row["value"] != api_key
        assert row["is_sensitive"] == 1

        # But get_config should decrypt
        result = isolated_storage.get_config("ai.openai.api_key")
        assert result == api_key

    def test_config_facade_auto_encrypts_sensitive_keys(self, isolated_config):
        """Test Config.set auto-encrypts sensitive keys."""
        isolated_config.set("ai.anthropic.api_key", "sk-ant-test-key")

        # Verify it can be retrieved correctly
        assert isolated_config.get("ai.anthropic.api_key") == "sk-ant-test-key"

    def test_invalid_token_decryption(self, isolated_home):
        """Test decryption of invalid token returns error message."""
        security = SecurityManager()
        result = security.decrypt("invalid_encrypted_token")
        assert result == "[Decryption Failed]"

    def test_key_persistence_via_file(self, isolated_home):
        """Test encryption key persists via file fallback."""
        # First SecurityManager creates key
        with patch("keyring.get_password", side_effect=Exception("No keyring")):
            with patch("keyring.set_password", side_effect=Exception("No keyring")):
                sm1 = SecurityManager()
                encrypted = sm1.encrypt("test_data")

        # Key file should exist
        key_file = isolated_home / ".null" / ".key"
        assert key_file.exists()

        # Second SecurityManager should use same key
        with patch("keyring.get_password", side_effect=Exception("No keyring")):
            sm2 = SecurityManager()
            decrypted = sm2.decrypt(encrypted)

        assert decrypted == "test_data"


# ============================================================================
# Default Configuration Tests
# ============================================================================


class TestDefaultConfiguration:
    """Test default configuration values."""

    def test_default_shell_from_env(self, monkeypatch):
        """Test default shell from environment."""
        monkeypatch.setenv("SHELL", "/bin/fish")

        # Re-import to get updated default
        import importlib

        import config.defaults as defaults_module

        importlib.reload(defaults_module)

        assert defaults_module.DEFAULT_SHELL == "/bin/fish"


# ============================================================================
# Configuration Migration Tests
# ============================================================================


class TestConfigurationMigration:
    """Test configuration migration scenarios."""

    def test_schema_migration_jump_host_column(self, isolated_home):
        """Test migration adds jump_host column if missing."""
        import sqlite3

        db_path = isolated_home / ".null" / "null.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create old schema without jump_host
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE ssh_hosts (
                alias TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                port INTEGER DEFAULT 22,
                username TEXT,
                key_path TEXT,
                encrypted_password TEXT
            )
        """)
        conn.commit()
        conn.close()

        # StorageManager should migrate schema
        storage = StorageManager(db_path=db_path)

        # Verify jump_host column exists
        cursor = storage.conn.cursor()
        cursor.execute("PRAGMA table_info(ssh_hosts)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "jump_host" in columns

        storage.close()

    def test_config_overwrite_existing(self, isolated_storage):
        """Test config values can be overwritten."""
        isolated_storage.set_config("test.key", "original")
        assert isolated_storage.get_config("test.key") == "original"

        isolated_storage.set_config("test.key", "updated")
        assert isolated_storage.get_config("test.key") == "updated"

    def test_sensitive_to_non_sensitive_update(self, isolated_storage):
        """Test updating sensitive value preserves sensitivity flag."""
        isolated_storage.set_config("secret", "value1", is_sensitive=True)
        isolated_storage.set_config("secret", "value2", is_sensitive=True)

        cursor = isolated_storage.conn.cursor()
        cursor.execute("SELECT is_sensitive FROM config WHERE key = ?", ("secret",))
        row = cursor.fetchone()
        assert row["is_sensitive"] == 1


# ============================================================================
# Environment Variable Handling Tests
# ============================================================================


class TestEnvironmentVariableHandling:
    """Test environment variable handling in configuration."""

    def test_shell_from_environment(self, monkeypatch, isolated_config):
        """Test shell default comes from environment."""
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")

        # When no shell is configured, should use env default
        # Note: This tests the defaults module behavior
        import importlib

        import config.defaults

        importlib.reload(config.defaults)
        assert config.defaults.DEFAULT_SHELL == "/usr/bin/zsh"

    def test_shell_override_environment(self, isolated_config):
        """Test configured shell overrides environment default."""
        isolated_config.set("shell", "/bin/bash")
        assert isolated_config.get("shell") == "/bin/bash"


# ============================================================================
# Sensitive Key Detection Tests
# ============================================================================


class TestSensitiveKeyDetection:
    """Test sensitive key detection logic."""

    def test_known_sensitive_keys(self):
        """Test known sensitive keys are detected."""
        for key in SENSITIVE_KEYS:
            assert is_sensitive_key(key), f"{key} should be sensitive"

    def test_api_key_suffix_pattern(self):
        """Test any key ending in .api_key is sensitive."""
        assert is_sensitive_key("ai.custom_provider.api_key")
        assert is_sensitive_key("some.nested.api_key")

    def test_secret_key_suffix_pattern(self):
        """Test any key ending in .secret_key is sensitive."""
        assert is_sensitive_key("ai.bedrock.secret_key")
        assert is_sensitive_key("custom.secret_key")

    def test_non_sensitive_keys(self):
        """Test regular keys are not marked sensitive."""
        assert not is_sensitive_key("theme")
        assert not is_sensitive_key("shell")
        assert not is_sensitive_key("ai.provider")
        assert not is_sensitive_key("ai.openai.model")

    def test_config_keys_helper_methods(self):
        """Test ConfigKeys helper methods."""
        assert ConfigKeys.ai_model("openai") == "ai.openai.model"
        assert ConfigKeys.ai_api_key("openai") == "ai.openai.api_key"
        assert ConfigKeys.ai_endpoint("ollama") == "ai.ollama.endpoint"
        assert ConfigKeys.ai_region("bedrock") == "ai.bedrock.region"


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Test session save/load functionality."""

    def test_save_and_load_session(self, isolated_storage, sample_block_state):
        """Test saving and loading a session."""
        blocks = [sample_block_state]

        filepath = isolated_storage.save_session(blocks, name="test_session")
        assert filepath.exists()

        loaded = isolated_storage.load_session(name="test_session")
        assert len(loaded) == 1
        assert loaded[0].content_input == sample_block_state.content_input

    def test_list_sessions(self, isolated_storage, sample_block_state):
        """Test listing saved sessions."""
        isolated_storage.save_session([sample_block_state], name="session1")
        isolated_storage.save_session([sample_block_state], name="session2")

        sessions = isolated_storage.list_sessions()
        names = [s["name"] for s in sessions]
        assert "session1" in names
        assert "session2" in names

    def test_current_session_autosave(self, isolated_storage, sample_block_state):
        """Test auto-save to current session."""
        isolated_storage.save_current_session([sample_block_state])

        loaded = isolated_storage.load_session()  # Loads current
        assert len(loaded) == 1

    def test_clear_current_session(self, isolated_storage, sample_block_state):
        """Test clearing current session."""
        isolated_storage.save_current_session([sample_block_state])
        isolated_storage.clear_current_session()

        loaded = isolated_storage.load_session()
        assert len(loaded) == 0

    def test_load_nonexistent_session(self, isolated_storage):
        """Test loading nonexistent session returns empty list."""
        loaded = isolated_storage.load_session(name="does_not_exist")
        assert loaded == []


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""

    def test_unicode_config_values(self, isolated_storage):
        """Test unicode values in configuration."""
        isolated_storage.set_config("greeting", "Hello, 世界! 🌍")
        assert isolated_storage.get_config("greeting") == "Hello, 世界! 🌍"

    def test_very_long_config_value(self, isolated_storage):
        """Test very long configuration values."""
        long_value = "x" * 10000
        isolated_storage.set_config("long.key", long_value)
        assert isolated_storage.get_config("long.key") == long_value

    def test_special_characters_in_key(self, isolated_storage):
        """Test special characters in config keys."""
        isolated_storage.set_config("key.with-dashes_and.dots", "value")
        assert isolated_storage.get_config("key.with-dashes_and.dots") == "value"

    def test_concurrent_access_same_db(self, isolated_home):
        """Test concurrent access to same database."""
        import config.storage as storage_module

        db_path = isolated_home / ".null" / "null.db"
        storage_module.DB_PATH = db_path

        storage1 = StorageManager(db_path=db_path)
        storage2 = StorageManager(db_path=db_path)

        storage1.set_config("key1", "value1")
        storage2.set_config("key2", "value2")

        assert storage1.get_config("key2") == "value2"
        assert storage2.get_config("key1") == "value1"

        storage1.close()
        storage2.close()

    def test_db_directory_creation(self, tmp_path):
        """Test database directory is created if missing."""
        nested_path = tmp_path / "deep" / "nested" / "path" / "null.db"
        storage = StorageManager(db_path=nested_path)

        assert nested_path.parent.exists()
        storage.set_config("test", "value")
        assert storage.get_config("test") == "value"

        storage.close()
