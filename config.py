from storage import StorageManager
import os

# Keys that should be encrypted
SENSITIVE_KEYS = {"ai.api_key", "ai.secret_key"}

class Config:
    @staticmethod
    def _get_storage():
        return StorageManager()

    @staticmethod
    def load_all():
        # Helper to load common config into a dict for easy access
        # In a full db implementation, we might cache this or query on demand.
        # For now, let's just query specific keys we use often.
        sm = Config._get_storage()
        return {
            "theme": sm.get_config("theme", "monokai"),
            "shell": sm.get_config("shell", os.environ.get("SHELL", "bash")),
            "ai": {
                "provider": sm.get_config("ai.provider", "ollama"),
                "model": sm.get_config("ai.model", "llama3"),
                "endpoint": sm.get_config("ai.endpoint", "http://localhost:11434"),
                "api_key": sm.get_config("ai.api_key", ""),
            }
        }

    @staticmethod
    def get(key: str, default=None):
        sm = Config._get_storage()
        return sm.get_config(key, default)

    @staticmethod
    def set(key: str, value: str):
        sm = Config._get_storage()
        is_sensitive = key in SENSITIVE_KEYS
        sm.set_config(key, value, is_sensitive=is_sensitive)

    @staticmethod
    def update_key(key_path: list[str], value):
        """Update a specific config key. key_path e.g. ['ai', 'model'] -> key='ai.model'"""
        key_str = ".".join(key_path)
        Config.set(key_str, value)


