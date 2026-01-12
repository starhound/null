"""Settings management for TUI/appearance options using JSON config file."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

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


@dataclass
class Settings:
    """Application settings container."""

    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)
    editor: EditorSettings = field(default_factory=EditorSettings)
    terminal: TerminalSettings = field(default_factory=TerminalSettings)
    ai: AISettings = field(default_factory=AISettings)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "appearance": asdict(self.appearance),
            "editor": asdict(self.editor),
            "terminal": asdict(self.terminal),
            "ai": asdict(self.ai),
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
