"""Configuration package for Null Terminal.

This package consolidates all configuration handling:
- ai.py: AI/LLM configuration (provider, model, API keys)
- settings.py: TUI settings (appearance, editor, terminal)
- storage.py: SQLite database and encryption
- keys.py: Sensitive key definitions
- defaults.py: Default configuration values
"""

from .ai import Config
from .defaults import (
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
from .keys import SENSITIVE_KEYS, ConfigKeys, is_sensitive_key
from .settings import (
    CONFIG_PATH,
    AISettings,
    AppearanceSettings,
    EditorSettings,
    Settings,
    SettingsManager,
    TerminalSettings,
    get_settings,
    save_settings,
)
from .storage import (
    APP_NAME,
    DB_PATH,
    KEYRING_SERVICE_NAME,
    SecurityManager,
    StorageManager,
)

__all__ = [
    "APP_NAME",
    # Settings
    "CONFIG_PATH",
    # Storage
    "DB_PATH",
    "DEFAULT_AGENT_MODE",
    "DEFAULT_AI_ACTIVE_PROMPT",
    "DEFAULT_AI_ENDPOINT",
    "DEFAULT_AI_MODEL",
    "DEFAULT_AI_PROVIDER",
    "DEFAULT_CONTEXT_WINDOW",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_SHELL",
    "DEFAULT_TEMPERATURE",
    # Defaults
    "DEFAULT_THEME",
    "KEYRING_SERVICE_NAME",
    # Keys
    "SENSITIVE_KEYS",
    "AISettings",
    "AppearanceSettings",
    # AI Configuration
    "Config",
    "ConfigKeys",
    "EditorSettings",
    "SecurityManager",
    "Settings",
    "SettingsManager",
    "StorageManager",
    "TerminalSettings",
    "get_settings",
    "is_sensitive_key",
    "save_settings",
]
