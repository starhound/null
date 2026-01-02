from storage import StorageManager
import os

# Keys that should be encrypted
SENSITIVE_KEYS = {
    "ai.openai.api_key", "ai.azure.api_key", "ai.xai.api_key", 
    "ai.bedrock.secret_key", "ai.lm_studio.api_key"
}

class Config:
    @staticmethod
    def _get_storage():
        return StorageManager()

    @staticmethod
    def load_all():
        # Helper to load common config into a dict for easy access
        sm = Config._get_storage()
        provider = sm.get_config("ai.provider", "ollama")
        return {
            "theme": sm.get_config("theme", "monokai"),
            "shell": sm.get_config("shell", os.environ.get("SHELL", "bash")),
            "ai": {
                "provider": provider,
                # Dynamic load based on active provider
                "model": sm.get_config(f"ai.{provider}.model", "llama3"),
                "endpoint": sm.get_config(f"ai.{provider}.endpoint", "http://localhost:11434"),
                "api_key": sm.get_config(f"ai.{provider}.api_key", ""),
                "region": sm.get_config(f"ai.{provider}.region", ""),
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


