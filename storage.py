import sqlite3
import os
import secrets
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DB_PATH = Path.home() / ".null" / "null.db"
APP_NAME = "null-terminal"
KEYRING_SERVICE_NAME = "null-terminal-encryption-key"

class SecurityManager:
    def __init__(self):
        self._fernet: Optional[Fernet] = None
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
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
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
        
        self.conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value, is_sensitive FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            val = row['value']
            if row['is_sensitive']:
                return self.security.decrypt(val)
            return val
        return default

    def set_config(self, key: str, value: str, is_sensitive: bool = False):
        cursor = self.conn.cursor()
        stored_val = value
        if is_sensitive:
            stored_val = self.security.encrypt(value)
            
        cursor.execute("""
            INSERT OR REPLACE INTO config (key, value, is_sensitive)
            VALUES (?, ?, ?)
        """, (key, stored_val, is_sensitive))
        self.conn.commit()

    def add_history(self, command: str, exit_code: int = 0):
        if not command.strip():
            return
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO history (command, exit_code) VALUES (?, ?)", (command, exit_code))
        self.conn.commit()

    def get_last_history(self, limit: int = 50) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT command FROM history ORDER BY id DESC LIMIT ?", (limit,))
        # Return reversed so latest is last in list (for easy up/cycling)
        return [row['command'] for row in cursor.fetchall()][::-1]

    def close(self):
        self.conn.close()
