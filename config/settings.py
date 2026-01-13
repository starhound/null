"""Settings management for TUI/appearance options using JSON config file."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


class ValidationError(Exception):
    """Configuration validation error with field-specific messages.

    Attributes:
        errors: Dictionary mapping field names to error messages.
    """

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        messages = [f"{field}: {msg}" for field, msg in errors.items()]
        super().__init__("; ".join(messages))

    def __str__(self) -> str:
        return ", ".join(f"{k}: {v}" for k, v in self.errors.items())


CONFIG_PATH = Path.home() / ".null" / "config.json"


@dataclass
class AppearanceSettings:
    """UI appearance settings."""

    theme: str = "null-dark"
    font_family: str = "monospace"
    font_size: int = 14
    line_height: float = 1.4
    show_timestamps: bool = True
    show_line_numbers: bool = True


@dataclass
class EditorSettings:
    """Editor/input settings."""

    tab_size: int = 4
    word_wrap: bool = True
    auto_indent: bool = True
    vim_mode: bool = False


@dataclass
class TerminalSettings:
    """Terminal behavior settings."""

    # Existing fields with env defaults
    shell: str = field(default_factory=lambda: os.environ.get("SHELL", "/bin/bash"))
    scrollback_lines: int = 10000
    max_history_blocks: int = 100
    clear_on_exit: bool = False
    confirm_on_exit: bool = True
    auto_save_session: bool = True
    auto_save_interval: int = 30  # seconds

    # New settings
    cursor_style: str = "block"  # block, beam, underline
    cursor_blink: bool = True
    bold_is_bright: bool = True

    # Environment-derived (read-only hints)
    term_type: str = field(
        default_factory=lambda: os.environ.get("TERM", "xterm-256color")
    )
    colorterm: str = field(
        default_factory=lambda: os.environ.get("COLORTERM", "truecolor")
    )
    lang: str = field(default_factory=lambda: os.environ.get("LANG", "en_US.UTF-8"))


MODEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._:/-]+$")


@dataclass
class AISettings:
    """AI provider settings."""

    provider: str = ""
    default_model: str = ""
    active_prompt: str = "default"
    context_window: int = 4000
    max_tokens: int = 2048
    temperature: float = 0.7
    stream_responses: bool = True
    autocomplete_enabled: bool = False
    autocomplete_provider: str = ""
    autocomplete_model: str = ""
    embedding_provider: str = ""
    embedding_model: str = ""
    embedding_endpoint: str = ""
    use_rag: bool = False
    rag_top_k: int = 3
    custom_template_variables: dict[str, str] = field(default_factory=dict)

    def validate(self, api_key: str = "") -> dict[str, str]:
        """Validate settings. Returns errors dict, raises ValidationError if invalid."""
        errors: dict[str, str] = {}

        if not (0.0 <= self.temperature <= 2.0):
            errors["temperature"] = "Must be between 0.0 and 2.0"

        if self.max_tokens <= 0:
            errors["max_tokens"] = "Must be a positive integer"

        if self.context_window <= 0:
            errors["context_window"] = "Must be a positive integer"

        cloud_providers = {
            "openai",
            "anthropic",
            "google",
            "azure",
            "bedrock",
            "groq",
            "mistral",
            "deepseek",
            "together",
            "openrouter",
        }
        if self.provider and self.provider.lower() in cloud_providers:
            if not api_key or not api_key.strip():
                errors["api_key"] = f"Required for {self.provider}"

        if self.default_model and not MODEL_NAME_PATTERN.match(self.default_model):
            errors["model"] = "Invalid characters in model name"

        if self.autocomplete_model and not MODEL_NAME_PATTERN.match(
            self.autocomplete_model
        ):
            errors["autocomplete_model"] = "Invalid characters in model name"

        if self.embedding_model and not MODEL_NAME_PATTERN.match(self.embedding_model):
            errors["embedding_model"] = "Invalid characters in model name"

        if errors:
            raise ValidationError(errors)

        return errors


@dataclass
class VoiceSettings:
    """Voice input settings."""

    enabled: bool = False
    hotkey: str = "ctrl+m"
    stt_provider: str = "openai"
    stt_model: str = "whisper-1"
    language: str = "en"
    push_to_talk: bool = True


@dataclass
class SecuritySettings:
    """Security and encryption settings."""

    encrypt_sessions: bool = True
    session_encryption_key_rotation: bool = False
    command_allowlist_mode: bool = False
    blocked_command_patterns: list[str] = field(default_factory=list)


@dataclass
class Settings:
    """Application settings container."""

    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    editor: EditorSettings = field(default_factory=EditorSettings)
    terminal: TerminalSettings = field(default_factory=TerminalSettings)
    ai: AISettings = field(default_factory=AISettings)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "appearance": asdict(self.appearance),
            "editor": asdict(self.editor),
            "terminal": asdict(self.terminal),
            "ai": asdict(self.ai),
            "voice": asdict(self.voice),
            "security": asdict(self.security),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create Settings from dictionary."""
        settings = cls()

        if "appearance" in data:
            for key, value in data["appearance"].items():
                if hasattr(settings.appearance, key):
                    setattr(settings.appearance, key, value)

        if "editor" in data:
            for key, value in data["editor"].items():
                if hasattr(settings.editor, key):
                    setattr(settings.editor, key, value)

        if "terminal" in data:
            for key, value in data["terminal"].items():
                if hasattr(settings.terminal, key):
                    setattr(settings.terminal, key, value)

        if "ai" in data:
            for key, value in data["ai"].items():
                if hasattr(settings.ai, key):
                    setattr(settings.ai, key, value)

        if "voice" in data:
            for key, value in data["voice"].items():
                if hasattr(settings.voice, key):
                    setattr(settings.voice, key, value)

        if "security" in data:
            for key, value in data["security"].items():
                if hasattr(settings.security, key):
                    setattr(settings.security, key, value)

        return settings


class SettingsManager:
    """Manages loading and saving settings from JSON config file."""

    _instance: Optional["SettingsManager"] = None
    _settings: Settings | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._settings is None:
            self._settings = self.load()

    @property
    def settings(self) -> Settings:
        """Get current settings."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings

    def load(self) -> Settings:
        """Load settings from config file."""
        if not CONFIG_PATH.exists():
            # First run - create settings with terminal defaults
            settings = self._create_with_terminal_defaults()
            self.save(settings)
            return settings

        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return Settings.from_dict(data)
        except Exception:
            try:
                if CONFIG_PATH.exists():
                    backup_path = CONFIG_PATH.with_suffix(".json.bak")
                    CONFIG_PATH.rename(backup_path)
            except Exception:
                pass
            return Settings()

    def _create_with_terminal_defaults(self) -> Settings:
        """Create settings initialized with host terminal's current config.

        On first run, we read the terminal's config file to get the user's
        current font and cursor settings as our defaults.
        """
        settings = Settings()

        try:
            from utils.terminal import load_terminal_defaults

            term_config = load_terminal_defaults()
            if term_config:
                # Use terminal's font settings as our defaults
                if term_config.font_family:
                    settings.appearance.font_family = term_config.font_family
                if term_config.font_size > 0:
                    settings.appearance.font_size = int(term_config.font_size)

                # Use terminal's cursor settings
                if term_config.cursor_style:
                    settings.terminal.cursor_style = term_config.cursor_style
                if term_config.cursor_blink is not None:
                    settings.terminal.cursor_blink = term_config.cursor_blink
        except Exception:
            pass  # Use defaults if terminal config reading fails

        return settings

    def save(self, settings: Settings | None = None) -> None:
        """Save settings to config file."""
        if settings is None:
            settings = self._settings
        if settings is None:
            return

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(settings.to_dict(), indent=2), encoding="utf-8"
        )
        self._settings = settings

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        section_obj = getattr(self.settings, section, None)
        if section_obj is None:
            return default
        return getattr(section_obj, key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a specific setting value and save."""
        section_obj = getattr(self.settings, section, None)
        if section_obj is not None and hasattr(section_obj, key):
            setattr(section_obj, key, value)
            self.save()

    def reload(self) -> Settings:
        """Reload settings from disk."""
        self._settings = self.load()
        return self._settings


def get_settings() -> Settings:
    """Get the current settings instance."""
    return SettingsManager().settings


def save_settings(settings: Settings | None = None) -> None:
    """Save settings to disk."""
    SettingsManager().save(settings)
