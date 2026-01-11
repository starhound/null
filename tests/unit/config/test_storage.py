"""Unit tests for config/storage.py - StorageManager and SecurityManager classes."""

import sqlite3

import pytest
from cryptography.fernet import Fernet

from config.storage import (
    APP_NAME,
    DB_PATH,
    KEYRING_SERVICE_NAME,
    SecurityManager,
    StorageManager,
)


class TestSecurityManager:
    """Tests for SecurityManager encryption/decryption."""

    @pytest.fixture
    def security_manager(self, mock_home):
        """Create a SecurityManager with mocked home directory."""
        return SecurityManager()

    def test_init_creates_fernet(self, security_manager):
        """SecurityManager should initialize with a Fernet instance."""
        assert security_manager._fernet is not None
        assert isinstance(security_manager._fernet, Fernet)

    def test_encrypt_returns_string(self, security_manager):
        """encrypt() should return a string."""
        result = security_manager.encrypt("test data")
        assert isinstance(result, str)

    def test_encrypt_produces_different_output(self, security_manager):
        """encrypt() should produce encrypted output different from input."""
        plaintext = "my secret data"
        encrypted = security_manager.encrypt(plaintext)
        assert encrypted != plaintext

    def test_decrypt_reverses_encryption(self, security_manager):
        """decrypt() should reverse encryption."""
        original = "my secret password"
        encrypted = security_manager.encrypt(original)
        decrypted = security_manager.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self, security_manager):
        """encrypt() with empty string should return empty string."""
        result = security_manager.encrypt("")
        assert result == ""

    def test_decrypt_empty_string(self, security_manager):
        """decrypt() with empty string should return empty string."""
        result = security_manager.decrypt("")
        assert result == ""

    def test_decrypt_invalid_token(self, security_manager):
        """decrypt() with invalid token should return failure message."""
        result = security_manager.decrypt("invalid-token")
        assert result == "[Decryption Failed]"

    def test_encrypt_various_characters(self, security_manager):
        """encrypt/decrypt should handle various character types."""
        test_strings = [
            "simple text",
            "with numbers 12345",
            "special !@#$%^&*()",
            "unicode: \u00e9\u00e8\u00ea\u00eb",
            "emoji: hello",
            "newlines\nand\ttabs",
            "very long " * 100,
        ]
        for original in test_strings:
            encrypted = security_manager.encrypt(original)
            decrypted = security_manager.decrypt(encrypted)
            assert decrypted == original, f"Failed for: {original[:50]}"

    def test_key_persistence(self, mock_home):
        """SecurityManager should create persistent key file when keyring unavailable."""
        # First manager creates key
        sm1 = SecurityManager()
        encrypted = sm1.encrypt("test data")

        # Second manager should use same key
        sm2 = SecurityManager()
        decrypted = sm2.decrypt(encrypted)
        assert decrypted == "test data"

    def test_key_file_permissions(self, mock_home):
        """Key file should have restricted permissions."""
        SecurityManager()
        key_path = mock_home / ".null" / ".key"
        if key_path.exists():
            # Check file exists and has proper permissions (0o600)
            mode = key_path.stat().st_mode & 0o777
            assert mode == 0o600


class TestStorageManagerInit:
    """Tests for StorageManager initialization."""

    def test_creates_db_directory(self, mock_home):
        """StorageManager should create .null directory."""
        StorageManager()
        null_dir = mock_home / ".null"
        assert null_dir.exists()
        assert null_dir.is_dir()

    def test_creates_database_file(self, mock_home):
        """StorageManager should create database file."""
        sm = StorageManager()
        assert sm.db_path.exists()
        sm.close()

    def test_creates_config_table(self, mock_storage):
        """Database should have config table."""
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='config'"
        )
        assert cursor.fetchone() is not None

    def test_creates_history_table(self, mock_storage):
        """Database should have history table."""
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='history'"
        )
        assert cursor.fetchone() is not None

    def test_creates_ssh_hosts_table(self, mock_storage):
        """Database should have ssh_hosts table."""
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ssh_hosts'"
        )
        assert cursor.fetchone() is not None

    def test_config_table_schema(self, mock_storage):
        """Config table should have expected columns."""
        cursor = mock_storage.conn.cursor()
        cursor.execute("PRAGMA table_info(config)")
        columns = {row["name"] for row in cursor.fetchall()}
        assert "key" in columns
        assert "value" in columns
        assert "is_sensitive" in columns


class TestStorageManagerConfig:
    """Tests for StorageManager configuration CRUD operations."""

    def test_get_config_default(self, mock_storage):
        """get_config() should return default for missing key."""
        result = mock_storage.get_config("nonexistent", "default_value")
        assert result == "default_value"

    def test_get_config_none_default(self, mock_storage):
        """get_config() should return None by default for missing key."""
        result = mock_storage.get_config("nonexistent")
        assert result is None

    def test_set_and_get_config(self, mock_storage):
        """set_config() followed by get_config() should work."""
        mock_storage.set_config("test.key", "test_value")
        result = mock_storage.get_config("test.key")
        assert result == "test_value"

    def test_set_config_overwrite(self, mock_storage):
        """set_config() should overwrite existing values."""
        mock_storage.set_config("test.key", "value1")
        mock_storage.set_config("test.key", "value2")
        result = mock_storage.get_config("test.key")
        assert result == "value2"

    def test_set_config_sensitive(self, mock_storage):
        """set_config() with sensitive=True should encrypt value."""
        mock_storage.set_config("api.key", "secret123", is_sensitive=True)

        # Value in database should be encrypted
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT value, is_sensitive FROM config WHERE key = ?", ("api.key",)
        )
        row = cursor.fetchone()
        assert row["is_sensitive"] == 1
        assert row["value"] != "secret123"  # Should be encrypted

        # get_config should return decrypted value
        result = mock_storage.get_config("api.key")
        assert result == "secret123"

    def test_delete_config(self, mock_storage):
        """delete_config() should remove key."""
        mock_storage.set_config("test.key", "value")
        mock_storage.delete_config("test.key")
        result = mock_storage.get_config("test.key")
        assert result is None

    def test_delete_config_nonexistent(self, mock_storage):
        """delete_config() on nonexistent key should not raise."""
        mock_storage.delete_config("nonexistent.key")  # Should not raise

    def test_delete_config_prefix(self, mock_storage):
        """delete_config_prefix() should remove all matching keys."""
        mock_storage.set_config("ai.openai.model", "gpt-4")
        mock_storage.set_config("ai.openai.key", "sk-123")
        mock_storage.set_config("ai.anthropic.model", "claude")
        mock_storage.set_config("theme", "dark")

        mock_storage.delete_config_prefix("ai.openai.")

        assert mock_storage.get_config("ai.openai.model") is None
        assert mock_storage.get_config("ai.openai.key") is None
        assert mock_storage.get_config("ai.anthropic.model") == "claude"
        assert mock_storage.get_config("theme") == "dark"

    def test_config_with_special_characters(self, mock_storage):
        """Config should handle special characters in values."""
        special_values = [
            "value with spaces",
            "value\nwith\nnewlines",
            "value\twith\ttabs",
            "unicode: \u00e9\u00e8\u00ea",
            "quotes: 'single' and \"double\"",
            "backslash: \\path\\to\\file",
        ]
        for i, value in enumerate(special_values):
            key = f"test.special.{i}"
            mock_storage.set_config(key, value)
            assert mock_storage.get_config(key) == value


class TestStorageManagerHistory:
    """Tests for StorageManager history operations."""

    def test_add_history(self, mock_storage):
        """add_history() should add command to history."""
        mock_storage.add_history("ls -la")
        history = mock_storage.get_last_history(10)
        assert "ls -la" in history

    def test_add_history_empty_ignored(self, mock_storage):
        """add_history() with empty command should be ignored."""
        # Get current history count
        initial_count = len(mock_storage.get_last_history(1000))

        mock_storage.add_history("")
        mock_storage.add_history("   ")

        # Count should not have increased
        final_count = len(mock_storage.get_last_history(1000))
        assert final_count == initial_count

    def test_add_history_with_exit_code(self, mock_storage):
        """add_history() should store exit code."""
        mock_storage.add_history("failing command", exit_code=1)
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT exit_code FROM history WHERE command = ?", ("failing command",)
        )
        row = cursor.fetchone()
        assert row["exit_code"] == 1

    def test_get_last_history_limit(self, mock_storage):
        """get_last_history() should respect limit."""
        for i in range(10):
            mock_storage.add_history(f"command {i}")

        history = mock_storage.get_last_history(5)
        assert len(history) == 5

    def test_get_last_history_order(self, mock_storage):
        """get_last_history() should return commands with latest last."""
        # Use unique command names to avoid confusion with other test data
        mock_storage.add_history("order_test_first")
        mock_storage.add_history("order_test_second")
        mock_storage.add_history("order_test_third")

        history = mock_storage.get_last_history(1000)
        # Filter to only our test commands
        test_history = [h for h in history if h.startswith("order_test_")]

        assert test_history[-1] == "order_test_third"
        assert test_history[0] == "order_test_first"

    def test_search_history(self, mock_storage):
        """search_history() should find matching commands."""
        # Use unique prefix to avoid conflicts with other test data
        mock_storage.add_history("searchtest_git status")
        mock_storage.add_history("searchtest_git commit -m 'test'")
        mock_storage.add_history("searchtest_ls -la")
        mock_storage.add_history("searchtest_git push")

        results = mock_storage.search_history("searchtest_git")
        assert len(results) == 3
        assert all("searchtest_git" in cmd for cmd in results)

    def test_search_history_limit(self, mock_storage):
        """search_history() should respect limit."""
        for i in range(20):
            mock_storage.add_history(f"git command {i}")

        results = mock_storage.search_history("git", limit=5)
        assert len(results) == 5

    def test_search_history_no_match(self, mock_storage):
        """search_history() should return empty list for no matches."""
        mock_storage.add_history("git status")
        results = mock_storage.search_history("docker")
        assert results == []


class TestStorageManagerSSH:
    """Tests for StorageManager SSH host operations."""

    def test_add_ssh_host_basic(self, mock_storage):
        """add_ssh_host() should add a basic host."""
        mock_storage.add_ssh_host("myserver", "example.com")
        host = mock_storage.get_ssh_host("myserver")

        assert host is not None
        assert host["alias"] == "myserver"
        assert host["hostname"] == "example.com"
        assert host["port"] == 22

    def test_add_ssh_host_full(self, mock_storage):
        """add_ssh_host() should handle all parameters."""
        mock_storage.add_ssh_host(
            alias="prodserver",
            hostname="prod.example.com",
            port=2222,
            username="admin",
            key_path="/home/user/.ssh/id_rsa",
            password="secret",
            jump_host="bastion",
        )

        host = mock_storage.get_ssh_host("prodserver")
        assert host["hostname"] == "prod.example.com"
        assert host["port"] == 2222
        assert host["username"] == "admin"
        assert host["key_path"] == "/home/user/.ssh/id_rsa"
        assert host["password"] == "secret"
        assert host["jump_host"] == "bastion"

    def test_add_ssh_host_password_encrypted(self, mock_storage):
        """add_ssh_host() should encrypt password."""
        mock_storage.add_ssh_host("server", "host.com", password="mysecret")

        # Check raw database value is encrypted
        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT encrypted_password FROM ssh_hosts WHERE alias = ?", ("server",)
        )
        row = cursor.fetchone()
        assert row["encrypted_password"] != "mysecret"

        # get_ssh_host should return decrypted password
        host = mock_storage.get_ssh_host("server")
        assert host["password"] == "mysecret"

    def test_add_ssh_host_update(self, mock_storage):
        """add_ssh_host() should update existing host."""
        mock_storage.add_ssh_host("server", "old.example.com")
        mock_storage.add_ssh_host("server", "new.example.com", port=3333)

        host = mock_storage.get_ssh_host("server")
        assert host["hostname"] == "new.example.com"
        assert host["port"] == 3333

    def test_get_ssh_host_nonexistent(self, mock_storage):
        """get_ssh_host() should return None for missing host."""
        result = mock_storage.get_ssh_host("nonexistent")
        assert result is None

    def test_list_ssh_hosts(self, mock_storage):
        """list_ssh_hosts() should return all hosts."""
        # Use unique prefixed names to avoid conflicts with other tests
        mock_storage.add_ssh_host("list_test_server1", "host1.com")
        mock_storage.add_ssh_host("list_test_server2", "host2.com", username="user2")
        mock_storage.add_ssh_host("list_test_aserver", "host3.com")

        hosts = mock_storage.list_ssh_hosts()
        # Filter to only our test hosts
        test_hosts = [h for h in hosts if h["alias"].startswith("list_test_")]

        assert len(test_hosts) == 3
        # Should be sorted by alias
        aliases = [h["alias"] for h in test_hosts]
        assert aliases == sorted(aliases)

    def test_list_ssh_hosts_returns_list(self, mock_storage):
        """list_ssh_hosts() should return a list type."""
        hosts = mock_storage.list_ssh_hosts()
        assert isinstance(hosts, list)

    def test_delete_ssh_host(self, mock_storage):
        """delete_ssh_host() should remove host."""
        mock_storage.add_ssh_host("server", "host.com")
        mock_storage.delete_ssh_host("server")

        result = mock_storage.get_ssh_host("server")
        assert result is None

    def test_delete_ssh_host_nonexistent(self, mock_storage):
        """delete_ssh_host() on nonexistent host should not raise."""
        mock_storage.delete_ssh_host("nonexistent")  # Should not raise


class TestStorageManagerSession:
    """Tests for StorageManager session operations."""

    def test_get_sessions_dir_creates_directory(self, mock_storage, mock_home):
        """_get_sessions_dir() should create sessions directory."""
        sessions_dir = mock_storage._get_sessions_dir()
        assert sessions_dir.exists()
        assert sessions_dir.is_dir()

    def test_save_and_load_session(self, mock_storage):
        """save_session() and load_session() should work together."""
        from models import BlockState, BlockType

        blocks = [
            BlockState(
                type=BlockType.COMMAND, content_input="ls", content_output="file1"
            ),
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="hello",
                content_output="Hi there!",
            ),
        ]

        mock_storage.save_session(blocks, name="test")
        loaded = mock_storage.load_session(name="test")

        assert len(loaded) == 2
        assert loaded[0].content_input == "ls"
        assert loaded[1].content_output == "Hi there!"

    def test_save_current_session(self, mock_storage):
        """save_current_session() should save to current.json."""
        from models import BlockState, BlockType

        blocks = [BlockState(type=BlockType.COMMAND, content_input="pwd")]

        mock_storage.save_current_session(blocks)
        current_file = mock_storage._get_current_session_file()
        assert current_file.exists()

    def test_save_current_session_empty_blocks(self, mock_storage):
        """save_current_session() with empty blocks should do nothing."""
        mock_storage.save_current_session([])
        current_file = mock_storage._get_current_session_file()
        assert not current_file.exists()

    def test_load_session_nonexistent(self, mock_storage):
        """load_session() for nonexistent session should return empty list."""
        result = mock_storage.load_session(name="nonexistent")
        assert result == []

    def test_list_sessions(self, mock_storage):
        """list_sessions() should return session info."""
        from models import BlockState, BlockType

        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]

        mock_storage.save_session(blocks, name="session1")
        mock_storage.save_session(blocks, name="session2")

        sessions = mock_storage.list_sessions()
        names = [s["name"] for s in sessions]
        assert "session1" in names
        assert "session2" in names

    def test_clear_current_session(self, mock_storage):
        """clear_current_session() should delete current.json."""
        from models import BlockState, BlockType

        blocks = [BlockState(type=BlockType.COMMAND, content_input="ls")]
        mock_storage.save_current_session(blocks)

        mock_storage.clear_current_session()
        current_file = mock_storage._get_current_session_file()
        assert not current_file.exists()

    def test_clear_current_session_nonexistent(self, mock_storage):
        """clear_current_session() on nonexistent file should not raise."""
        mock_storage.clear_current_session()  # Should not raise


class TestStorageManagerClose:
    """Tests for StorageManager cleanup."""

    def test_close_connection(self, mock_home):
        """close() should close database connection."""
        sm = StorageManager()
        sm.close()

        # Attempting to use connection should raise
        with pytest.raises(sqlite3.ProgrammingError):
            sm.conn.execute("SELECT 1")


class TestStorageConstants:
    """Tests for module-level constants."""

    def test_db_path_in_home(self):
        """DB_PATH should be in user's .null directory."""
        assert ".null" in str(DB_PATH)
        assert "null.db" in str(DB_PATH)

    def test_app_name_defined(self):
        """APP_NAME should be defined."""
        assert APP_NAME == "null-terminal"

    def test_keyring_service_name_defined(self):
        """KEYRING_SERVICE_NAME should be defined."""
        assert KEYRING_SERVICE_NAME == "null-terminal-encryption-key"
