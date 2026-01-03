import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import keyring
from cryptography.fernet import Fernet

DB_PATH = Path.home() / ".null" / "null.db"
APP_NAME = "null-terminal"
KEYRING_SERVICE_NAME = "null-terminal-encryption-key"


class SecurityManager:
    def __init__(self):
        self._fernet: Fernet | None = None
        self._init_key()

    def _init_key(self):
        key = None
        use_keyring = True

        try:
            # Try to get key from keyring
            key = keyring.get_password(APP_NAME, KEYRING_SERVICE_NAME)
        except Exception:
            # NoKeyringError or other backend issues
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
                    except Exception:
                        pass

                if not saved_to_keyring:
                    # Fallback: Store in a hidden file
                    key_path = Path.home() / ".null" / ".key"
                    key_path.parent.mkdir(parents=True, exist_ok=True)
                    key_path.write_text(key)
                    # Try to set permissions to read/write only by user
                    try:
                        os.chmod(key_path, 0o600)
                    except Exception:
                        pass

        self._fernet = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        assert self._fernet is not None, "Fernet not initialized"
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        assert self._fernet is not None, "Fernet not initialized"
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except Exception:
            return "[Decryption Failed]"


class StorageManager:
    def __init__(self):
        self.db_path = DB_PATH
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
        except Exception:
            # Column likely exists
            pass

        self.conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
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
        cursor = self.conn.cursor()
        stored_val = value
        if is_sensitive:
            stored_val = self.security.encrypt(value)

        cursor.execute(
            """
            INSERT OR REPLACE INTO config (key, value, is_sensitive)
            VALUES (?, ?, ?)
        """,
            (key, stored_val, is_sensitive),
        )
        self.conn.commit()

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

    def add_history(self, command: str, exit_code: int = 0):
        if not command.strip():
            return
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO history (command, exit_code) VALUES (?, ?)",
            (command, exit_code),
        )
        self.conn.commit()

    def get_last_history(self, limit: int = 50) -> list[str]:
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
        import json

        from models import BlockState

        sessions_dir = self._get_sessions_dir()

        if name:
            filename = f"session-{name}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"session-{timestamp}.json"

        # Serialize blocks
        data = {
            "saved_at": datetime.now().isoformat(),
            "blocks": [b.to_dict() if isinstance(b, BlockState) else b for b in blocks],
        }

        filepath = sessions_dir / filename
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Also save as current
        self._get_current_session_file().write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

        return filepath

    def save_current_session(self, blocks: list[Any]):
        """Quick save to current session (for auto-save)."""
        import json

        from models import BlockState

        if not blocks:
            return

        data = {
            "saved_at": datetime.now().isoformat(),
            "blocks": [b.to_dict() if isinstance(b, BlockState) else b for b in blocks],
        }

        self._get_current_session_file().write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def load_session(self, name: str | None = None) -> list[Any]:
        """Load session from JSON file."""
        import json

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
        except Exception:
            return []

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        sessions = []
        sessions_dir = self._get_sessions_dir()

        for f in sorted(sessions_dir.glob("session-*.json"), reverse=True):
            if f.name == "current.json":
                continue
            try:
                import json

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
            except Exception:
                pass

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

    def close(self):
        self.conn.close()
