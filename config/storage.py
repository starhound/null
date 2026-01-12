"""Storage management using SQLite with encryption for sensitive data."""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import keyring
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".null" / "null.db"
APP_NAME = "null-terminal"
KEYRING_SERVICE_NAME = "null-terminal-encryption-key"


class SecurityManager:
    """Manages encryption/decryption of sensitive configuration values."""

    def __init__(self):
        self._fernet: Fernet | None = None
        self._init_key()

    def _init_key(self):
        key = None
        use_keyring = True

        try:
            # Try to get key from keyring
            key = keyring.get_password(APP_NAME, KEYRING_SERVICE_NAME)
        except keyring.errors.KeyringError as e:
            logger.debug("Keyring not available: %s", e)
            use_keyring = False
        except Exception as e:
            logger.warning("Unexpected error accessing keyring: %s", e)
            use_keyring = False

        if not key:
            # Check for local key file first if keyring failed or return empty
            key_path = Path.home() / ".null" / ".key"
            if key_path.exists():
                key = key_path.read_text().strip()

            if not key:
                # Generate new key
                key = Fernet.generate_key().decode()

                # Try saving to keyring if it didn't fail earlier (e.g. key was just None)
                saved_to_keyring = False
                if use_keyring:
                    try:
                        keyring.set_password(APP_NAME, KEYRING_SERVICE_NAME, key)
                        saved_to_keyring = True
                    except keyring.errors.KeyringError as e:
                        logger.debug("Failed to save key to keyring: %s", e)
                    except Exception as e:
                        logger.warning("Unexpected error saving to keyring: %s", e)

                if not saved_to_keyring:
                    # Fallback: Store in a hidden file
                    key_path = Path.home() / ".null" / ".key"
                    key_path.parent.mkdir(parents=True, exist_ok=True)
                    key_path.write_text(key)
                    # Try to set permissions to read/write only by user
                    try:
                        os.chmod(key_path, 0o600)
                    except OSError as e:
                        logger.warning(
                            "Failed to set secure permissions on key file %s: %s",
                            key_path,
                            e,
                        )

        self._fernet = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        """Encrypt a string value."""
        if not data:
            return ""
        assert self._fernet is not None, "Fernet not initialized"
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt an encrypted token."""
        if not token:
            return ""
        assert self._fernet is not None, "Fernet not initialized"
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            logger.error(
                "Decryption failed: invalid token (possibly corrupted or wrong key)"
            )
            return "[Decryption Failed]"
        except Exception as e:
            logger.error("Unexpected decryption error: %s", e)
            return "[Decryption Failed]"


class StorageManager:
    """Manages SQLite database for configuration, history, and SSH hosts."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            self.db_path = DB_PATH
        else:
            self.db_path = db_path
        self.security = SecurityManager()
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        cursor = self.conn.cursor()

        # Config Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                is_sensitive BOOLEAN DEFAULT 0
            )
        """)

        # History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                exit_code INTEGER
            )
        """)

        # Interactions Table (for Recall/Semantic Search)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vector_id TEXT,
                type TEXT,
                input TEXT,
                output TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # SSH Hosts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ssh_hosts (
                alias TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                port INTEGER DEFAULT 22,
                username TEXT,
                key_path TEXT,
                encrypted_password TEXT,
                jump_host TEXT
            )
        """)

        # Migration: Add jump_host if missing
        try:
            cursor.execute("ALTER TABLE ssh_hosts ADD COLUMN jump_host TEXT")
        except sqlite3.OperationalError:
            # Column already exists - expected during normal operation
            pass
        except sqlite3.Error as e:
            logger.error("Database migration failed (add jump_host column): %s", e)
            raise

        self.conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value, decrypting if sensitive."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value, is_sensitive FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            val = row["value"]
            if row["is_sensitive"]:
                return self.security.decrypt(val)
            return val
        return default

    def set_config(self, key: str, value: str, is_sensitive: bool = False):
        """Set a configuration value, encrypting if sensitive."""
        cursor = self.conn.cursor()
        stored_val = value
        if is_sensitive:
            stored_val = self.security.encrypt(value)

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO config (key, value, is_sensitive)
                VALUES (?, ?, ?)
            """,
                (key, stored_val, is_sensitive),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to save config key '%s': %s", key, e)
            raise

    def delete_config(self, key: str):
        """Delete a config key from the database."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM config WHERE key = ?", (key,))
        self.conn.commit()

    def delete_config_prefix(self, prefix: str):
        """Delete all config keys starting with a prefix."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM config WHERE key LIKE ?", (f"{prefix}%",))
        self.conn.commit()

    def list_config(self) -> dict[str, str]:
        """List all configuration key-value pairs."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value, is_sensitive FROM config")
        result = {}
        for row in cursor.fetchall():
            key = row["key"]
            val = row["value"]
            if row["is_sensitive"]:
                val = self.security.decrypt(val)
            result[key] = val
        return result

    def add_history(self, command: str, exit_code: int = 0):
        """Add a command to history."""
        if not command.strip():
            return
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO history (command, exit_code) VALUES (?, ?)",
            (command, exit_code),
        )
        self.conn.commit()

    def get_last_history(self, limit: int = 50) -> list[str]:
        """Get recent command history."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT command FROM history ORDER BY id DESC LIMIT ?", (limit,))
        # Return reversed so latest is last in list (for easy up/cycling)
        return [row["command"] for row in cursor.fetchall()][::-1]

    def search_history(self, query: str, limit: int = 20) -> list[str]:
        """Search history for commands matching query."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT DISTINCT command FROM history WHERE command LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        return [row["command"] for row in cursor.fetchall()]

    # Session Management
    def _get_sessions_dir(self) -> Path:
        """Get sessions directory, create if needed."""
        sessions_dir = Path.home() / ".null" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

    def _get_current_session_file(self) -> Path:
        """Get path to current session file."""
        return self._get_sessions_dir() / "current.json"

    def save_session(self, blocks: list[Any], name: str | None = None) -> Path:
        """Save session to JSON file."""
        from models import BlockState

        sessions_dir = self._get_sessions_dir()

        if name:
            filename = f"session-{name}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"session-{timestamp}.json"

        data = {
            "saved_at": datetime.now().isoformat(),
            "blocks": [b.to_dict() if isinstance(b, BlockState) else b for b in blocks],
        }

        filepath = sessions_dir / filename
        try:
            filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.error("Failed to save session to %s: %s", filepath, e)
            raise

        try:
            self._get_current_session_file().write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except OSError as e:
            logger.warning("Failed to update current session file: %s", e)

        return filepath

    def save_current_session(self, blocks: list[Any]):
        """Quick save to current session (for auto-save)."""
        from models import BlockState

        if not blocks:
            return

        data = {
            "saved_at": datetime.now().isoformat(),
            "blocks": [b.to_dict() if isinstance(b, BlockState) else b for b in blocks],
        }

        try:
            self._get_current_session_file().write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except OSError as e:
            logger.error("Failed to auto-save current session: %s", e)

    def load_session(self, name: str | None = None) -> list[Any]:
        """Load session from JSON file."""
        from models import BlockState

        sessions_dir = self._get_sessions_dir()

        if name:
            filepath = sessions_dir / f"session-{name}.json"
        else:
            filepath = self._get_current_session_file()

        if not filepath.exists():
            return []

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            blocks = [BlockState.from_dict(b) for b in data.get("blocks", [])]
            return blocks
        except json.JSONDecodeError as e:
            logger.error("Failed to parse session file %s: %s", filepath, e)
            return []
        except OSError as e:
            logger.error("Failed to read session file %s: %s", filepath, e)
            return []
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Invalid session data in %s: %s", filepath, e)
            return []

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        sessions = []
        sessions_dir = self._get_sessions_dir()

        for f in sorted(sessions_dir.glob("session-*.json"), reverse=True):
            if f.name == "current.json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                name = f.stem.replace("session-", "")
                sessions.append(
                    {
                        "name": name,
                        "saved_at": data.get("saved_at", ""),
                        "block_count": len(data.get("blocks", [])),
                        "path": str(f),
                    }
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Skipping corrupted session file %s: %s", f, e)

        return sessions

    def clear_current_session(self):
        """Delete current session file."""
        current = self._get_current_session_file()
        if current.exists():
            current.unlink()

    # SSH Management
    def add_ssh_host(
        self,
        alias: str,
        hostname: str,
        port: int = 22,
        username: str | None = None,
        key_path: str | None = None,
        password: str | None = None,
        jump_host: str | None = None,
    ):
        """Add or update an SSH host config."""
        cursor = self.conn.cursor()

        enc_pass = None
        if password:
            enc_pass = self.security.encrypt(password)

        cursor.execute(
            """
            INSERT OR REPLACE INTO ssh_hosts (alias, hostname, port, username, key_path, encrypted_password, jump_host)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (alias, hostname, port, username, key_path, enc_pass, jump_host),
        )
        self.conn.commit()

    def get_ssh_host(self, alias: str) -> dict[str, Any] | None:
        """Get host config by alias."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ssh_hosts WHERE alias = ?", (alias,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data["encrypted_password"]:
                data["password"] = self.security.decrypt(data["encrypted_password"])
            else:
                data["password"] = None
            return data
        return None

    def list_ssh_hosts(self) -> list[dict[str, Any]]:
        """List all SSH hosts."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT alias, hostname, port, username, jump_host FROM ssh_hosts ORDER BY alias"
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_ssh_host(self, alias: str):
        """Delete an SSH host."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM ssh_hosts WHERE alias = ?", (alias,))
        self.conn.commit()

    def add_interaction(
        self,
        type: str,
        input_text: str,
        output_text: str,
        vector_id: str | None = None,
        metadata: str | None = None,
    ) -> int | None:
        """Add an interaction (command/AI response) to history."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO interactions (type, input, output, vector_id, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (type, input_text, output_text, vector_id, metadata),
        )
        self.conn.commit()
        return cursor.lastrowid

    def search_interactions(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search interactions by input content."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM interactions WHERE input LIKE ? OR output LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close the database connection."""
        self.conn.close()
