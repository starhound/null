"""AI/LLM configuration management."""

from .defaults import (
    DEFAULT_AI_ACTIVE_PROMPT,
    DEFAULT_AI_ENDPOINT,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    DEFAULT_SHELL,
    DEFAULT_THEME,
)
from .keys import is_sensitive_key
from .storage import StorageManager


class Config:
    """Main configuration class for AI/LLM settings.

    Provides static methods for getting and setting configuration values
    stored in SQLite database with encryption for sensitive keys.
    """

    @staticmethod
    def _get_storage() -> StorageManager:
        """Get the storage manager instance."""
        return StorageManager()

    @staticmethod
    def load_all() -> dict:
        """Load common config into a dict for easy access.

        Returns a dictionary with theme, shell, and ai settings.
        Note: Prompts are now managed by the prompts module, not here.
        """
        sm = Config._get_storage()
        provider = sm.get_config("ai.provider", DEFAULT_AI_PROVIDER)
        agent_mode_str = sm.get_config("ai.agent_mode", "false")
        agent_mode = agent_mode_str.lower() in ("true", "1", "yes")

        agent_max_iterations = int(sm.get_config("ai.agent_max_iterations", "10"))
        agent_approval_mode = sm.get_config("ai.agent_approval_mode", "auto")
        agent_thinking_visible_str = sm.get_config("ai.agent_thinking_visible", "true")
        agent_thinking_visible = agent_thinking_visible_str.lower() in (
            "true",
            "1",
            "yes",
        )

        embedding_provider = sm.get_config("ai.embedding_provider", "ollama")
        embedding_model = sm.get_config(
            f"ai.embedding.{embedding_provider}.model", "nomic-embed-text"
        )
        embedding_endpoint = sm.get_config(
            f"ai.embedding.{embedding_provider}.endpoint", "http://localhost:11434"
        )

        return {
            "theme": sm.get_config("theme", DEFAULT_THEME),
            "shell": sm.get_config("shell", DEFAULT_SHELL),
            "ai": {
                "provider": provider,
                "model": sm.get_config(f"ai.{provider}.model", DEFAULT_AI_MODEL),
                "endpoint": sm.get_config(
                    f"ai.{provider}.endpoint", DEFAULT_AI_ENDPOINT
                ),
                "api_key": sm.get_config(f"ai.{provider}.api_key", ""),
                "region": sm.get_config(f"ai.{provider}.region", ""),
                "agent_mode": agent_mode,
                "agent_max_iterations": agent_max_iterations,
                "agent_approval_mode": agent_approval_mode,
                "agent_thinking_visible": agent_thinking_visible,
                "embedding_provider": embedding_provider,
                "embedding_model": embedding_model,
                "embedding_endpoint": embedding_endpoint,
                "active_prompt": sm.get_config(
                    "ai.active_prompt", DEFAULT_AI_ACTIVE_PROMPT
                ),
            },
        }

    @staticmethod
    def get(key: str, default=None):
        """Get a configuration value.

        Args:
            key: The configuration key (e.g., "ai.provider", "theme").
            default: Default value if key not found.

        Returns:
            The configuration value, or default if not found.
        """
        sm = Config._get_storage()
        return sm.get_config(key, default)

    @staticmethod
    def set(key: str, value: str):
        """Set a configuration value.

        Args:
            key: The configuration key.
            value: The value to set.

        Sensitive keys (API keys, secrets) are automatically encrypted.
        """
        sm = Config._get_storage()
        sm.set_config(key, value, is_sensitive=is_sensitive_key(key))

    @staticmethod
    def update_key(key_path: list[str], value):
        """Update a specific config key using path notation.

        Args:
            key_path: List of path segments, e.g., ["ai", "model"].
            value: The value to set.
        """
        key_str = ".".join(key_path)
        Config.set(key_str, value)
