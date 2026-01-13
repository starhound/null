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
    DEFAULT_AGENT_LOOP_INTERVAL,
    DEFAULT_AGENT_MODE,
    DEFAULT_AI_ACTIVE_PROMPT,
    DEFAULT_AI_ENDPOINT,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    DEFAULT_CONTEXT_WINDOW,
    DEFAULT_EXECUTOR_CANCEL_GRACE_PERIOD,
    DEFAULT_EXECUTOR_POLL_INTERVAL,
    DEFAULT_EXECUTOR_YIELD_INTERVAL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MCP_HEALTH_CHECK_INTERVAL,
    DEFAULT_PROVIDER_MODEL_LOAD_DELAY,
    DEFAULT_RAG_BATCH_YIELD,
    DEFAULT_RAG_PROGRESS_INTERVAL,
    DEFAULT_RATE_LIMITER_BACKOFF,
    DEFAULT_SHELL,
    DEFAULT_SIDEBAR_UPDATE_INTERVAL,
    DEFAULT_SSH_RECONNECT_DELAY,
    DEFAULT_TEMPERATURE,
    DEFAULT_THEME,
)
from .keybindings import (
    DEFAULT_KEYBINDINGS,
    KEYBINDINGS_PATH,
    KeyBinding,
    KeybindingManager,
    KeyConflict,
    get_keybinding_manager,
    reload_keybindings,
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
    ValidationError,
    VoiceSettings,
    get_settings,
    save_settings,
)
from .storage import (
    APP_NAME,
    DB_PATH,
    HISTORY_LIMIT,
    KEYRING_SERVICE_NAME,
    SecurityManager,
    StorageManager,
)

from .timing import (
    TimingConfig,
    get_timing_config,
    reset_timing_config,
    set_timing_config,
)

__all__ = [
    "APP_NAME",
    "CONFIG_PATH",
    "DB_PATH",
    "DEFAULT_AGENT_LOOP_INTERVAL",
    "DEFAULT_AGENT_MODE",
    "DEFAULT_AI_ACTIVE_PROMPT",
    "DEFAULT_AI_ENDPOINT",
    "DEFAULT_AI_MODEL",
    "DEFAULT_AI_PROVIDER",
    "DEFAULT_CONTEXT_WINDOW",
    "DEFAULT_EXECUTOR_CANCEL_GRACE_PERIOD",
    "DEFAULT_EXECUTOR_POLL_INTERVAL",
    "DEFAULT_EXECUTOR_YIELD_INTERVAL",
    "DEFAULT_KEYBINDINGS",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MCP_HEALTH_CHECK_INTERVAL",
    "DEFAULT_PROVIDER_MODEL_LOAD_DELAY",
    "DEFAULT_RAG_BATCH_YIELD",
    "DEFAULT_RAG_PROGRESS_INTERVAL",
    "DEFAULT_RATE_LIMITER_BACKOFF",
    "DEFAULT_SHELL",
    "DEFAULT_SIDEBAR_UPDATE_INTERVAL",
    "DEFAULT_SSH_RECONNECT_DELAY",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_THEME",
    "HISTORY_LIMIT",
    "KEYBINDINGS_PATH",
    "KEYRING_SERVICE_NAME",
    "SENSITIVE_KEYS",
    "AISettings",
    "AppearanceSettings",
    "Config",
    "ConfigKeys",
    "EditorSettings",
    "KeyBinding",
    "KeybindingManager",
    "KeyConflict",
    "SecurityManager",
    "Settings",
    "SettingsManager",
    "StorageManager",
    "TerminalSettings",
    "TimingConfig",
    "ValidationError",
    "VoiceSettings",
    "get_keybinding_manager",
    "get_settings",
    "get_timing_config",
    "is_sensitive_key",
    "reload_keybindings",
    "reset_timing_config",
    "save_settings",
    "set_timing_config",
]
