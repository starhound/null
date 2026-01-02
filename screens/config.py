"""Settings configuration screen."""

from .base import (
    ModalScreen, ComposeResult, Binding, Container, Horizontal, Vertical,
    VerticalScroll, Label, Input, Button, Switch, Select, Static,
    TabbedContent, TabPane
)


class ConfigScreen(ModalScreen):
    """Settings configuration screen with tabbed sections."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self):
        super().__init__()
        from settings import get_settings
        self.settings = get_settings()
        self.controls = {}

    def compose(self) -> ComposeResult:
        with Container(id="config-outer"):
            with Static(id="config-header"):
                yield Label("Settings")

            with TabbedContent():
                with TabPane("Appearance", id="tab-appearance"):
                    with VerticalScroll(classes="settings-scroll"):
                        yield from self._appearance_settings()

                with TabPane("Editor", id="tab-editor"):
                    with VerticalScroll(classes="settings-scroll"):
                        yield from self._editor_settings()

                with TabPane("Terminal", id="tab-terminal"):
                    with VerticalScroll(classes="settings-scroll"):
                        yield from self._terminal_settings()

                with TabPane("AI", id="tab-ai"):
                    with VerticalScroll(classes="settings-scroll"):
                        yield from self._ai_settings()

            with Horizontal(id="config-footer"):
                yield Button("Save", id="save-btn")
                yield Button("Cancel", id="cancel-btn")
                yield Static("", classes="spacer")
                yield Button("Reset to Defaults", id="reset-btn")

    def _setting_row(
        self,
        key: str,
        label: str,
        hint: str,
        control
    ) -> ComposeResult:
        """Create a setting row with label, hint, and control."""
        with Horizontal(classes="setting-row"):
            with Vertical(classes="setting-info"):
                yield Label(label, classes="setting-label")
                yield Label(hint, classes="setting-hint")
            with Horizontal(classes="setting-control"):
                self.controls[key] = control
                yield control

    def _appearance_settings(self) -> ComposeResult:
        """Appearance tab settings."""
        from utils.terminal import get_terminal_info
        
        s = self.settings.appearance
        term_info = get_terminal_info()

        # Show detected terminal info
        yield Static("Terminal Detection", classes="settings-header")
        
        font_support = "✓ Supported" if term_info.supports_font_change else "✗ Not supported"
        with Horizontal(classes="setting-row terminal-info"):
            with Vertical(classes="setting-info"):
                yield Label(f"Detected: {term_info.name}", classes="setting-label")
                yield Label(f"Font control: {font_support}", classes="setting-hint")
            with Horizontal(classes="setting-control"):
                yield Static("")  # Placeholder for alignment

        yield Static("Theme", classes="settings-header")

        themes = [
            ("null-dark", "Null Dark"),
            ("null-warm", "Null Warm"),
            ("null-mono", "Null Mono"),
            ("null-light", "Null Light"),
            ("dracula", "Dracula"),
            ("nord", "Nord"),
            ("monokai", "Monokai"),
        ]
        yield from self._setting_row(
            "appearance.theme",
            "Theme",
            "Color theme for the interface",
            Select([(name, value) for value, name in themes], value=s.theme, id="theme")
        )

        # Font settings - show with info about terminal support
        yield Static("Font Settings", classes="settings-header")
        
        if not term_info.supports_font_change:
            yield Label(
                f"⚠ {term_info.name} does not support runtime font changes. "
                "Edit your terminal config directly.",
                classes="setting-warning"
            )

        fonts = [
            ("monospace", "Monospace (Default)"),
            ("Fira Code", "Fira Code"),
            ("JetBrains Mono", "JetBrains Mono"),
            ("Source Code Pro", "Source Code Pro"),
            ("Cascadia Code", "Cascadia Code"),
            ("IBM Plex Mono", "IBM Plex Mono"),
        ]
        yield from self._setting_row(
            "appearance.font_family",
            "Font Family",
            f"Terminal font {'(applied to terminal)' if term_info.supports_font_change else '(reference only)'}",
            Select([(name, value) for value, name in fonts], value=s.font_family, id="font_family")
        )

        yield from self._setting_row(
            "appearance.font_size",
            "Font Size",
            f"Font size in pixels {'(applied to terminal)' if term_info.supports_font_change else '(reference only)'}",
            Input(value=str(s.font_size), type="integer", id="font_size")
        )

        yield from self._setting_row(
            "appearance.line_height",
            "Line Height",
            "Line spacing multiplier (e.g., 1.4)",
            Input(value=str(s.line_height), type="number", id="line_height")
        )

        yield Static("Display Options", classes="settings-header")

        yield from self._setting_row(
            "appearance.show_timestamps",
            "Show Timestamps",
            "Display timestamps on blocks",
            Switch(value=s.show_timestamps, id="show_timestamps")
        )

        yield from self._setting_row(
            "appearance.show_line_numbers",
            "Show Line Numbers",
            "Display line numbers in code blocks",
            Switch(value=s.show_line_numbers, id="show_line_numbers")
        )

    def _editor_settings(self) -> ComposeResult:
        """Editor tab settings."""
        s = self.settings.editor

        yield from self._setting_row(
            "editor.tab_size",
            "Tab Size",
            "Number of spaces per tab",
            Input(value=str(s.tab_size), type="integer", id="tab_size")
        )

        yield from self._setting_row(
            "editor.word_wrap",
            "Word Wrap",
            "Wrap long lines in the editor",
            Switch(value=s.word_wrap, id="word_wrap")
        )

        yield from self._setting_row(
            "editor.auto_indent",
            "Auto Indent",
            "Automatically indent new lines",
            Switch(value=s.auto_indent, id="auto_indent")
        )

        yield from self._setting_row(
            "editor.vim_mode",
            "Vim Mode",
            "Enable vim-style keybindings",
            Switch(value=s.vim_mode, id="vim_mode")
        )

    def _terminal_settings(self) -> ComposeResult:
        """Terminal tab settings."""
        s = self.settings.terminal
        import os

        yield from self._setting_row(
            "terminal.shell",
            "Shell",
            f"Shell to use (empty = $SHELL: {os.environ.get('SHELL', '/bin/bash')})",
            Input(value=s.shell, placeholder=os.environ.get("SHELL", "/bin/bash"), id="shell")
        )

        yield from self._setting_row(
            "terminal.scrollback_lines",
            "Scrollback Lines",
            "Maximum lines to keep in history",
            Input(value=str(s.scrollback_lines), type="integer", id="scrollback_lines")
        )

        yield from self._setting_row(
            "terminal.auto_save_session",
            "Auto Save Session",
            "Automatically save session on changes",
            Switch(value=s.auto_save_session, id="auto_save_session")
        )

        yield from self._setting_row(
            "terminal.auto_save_interval",
            "Auto Save Interval",
            "Seconds between auto-saves",
            Input(value=str(s.auto_save_interval), type="integer", id="auto_save_interval")
        )

        yield from self._setting_row(
            "terminal.confirm_on_exit",
            "Confirm on Exit",
            "Ask for confirmation before quitting",
            Switch(value=s.confirm_on_exit, id="confirm_on_exit")
        )

        yield from self._setting_row(
            "terminal.clear_on_exit",
            "Clear on Exit",
            "Clear session when exiting",
            Switch(value=s.clear_on_exit, id="clear_on_exit")
        )

    def _ai_settings(self) -> ComposeResult:
        """AI tab settings."""
        from ai.factory import AIFactory

        s = self.settings.ai

        # Build provider list from factory metadata
        providers = []
        for key in AIFactory.list_providers():
            info = AIFactory.get_provider_info(key)
            providers.append((info.get("name", key), key))

        yield from self._setting_row(
            "ai.provider",
            "Default Provider",
            "Default AI provider to use",
            Select(providers, value=s.provider, id="ai_provider")
        )

        yield from self._setting_row(
            "ai.context_window",
            "Context Window",
            "Default context window size (tokens)",
            Input(value=str(s.context_window), type="integer", id="context_window")
        )

        yield from self._setting_row(
            "ai.max_tokens",
            "Max Response Tokens",
            "Maximum tokens in AI response",
            Input(value=str(s.max_tokens), type="integer", id="max_tokens")
        )

        yield from self._setting_row(
            "ai.temperature",
            "Temperature",
            "Creativity level (0.0 - 2.0)",
            Input(value=str(s.temperature), type="number", id="temperature")
        )

        yield from self._setting_row(
            "ai.stream_responses",
            "Stream Responses",
            "Show AI responses as they generate",
            Switch(value=s.stream_responses, id="stream_responses")
        )

        yield Static("Autocomplete Settings", classes="settings-header")

        yield from self._setting_row(
            "ai.autocomplete_enabled",
            "Enable Autocomplete",
            "AI-powered command suggestions",
            Switch(value=s.autocomplete_enabled, id="autocomplete_enabled")
        )

        # Autocomplete Provider override (optional)
        # Re-use providers list
        ac_providers = [("Default (Same as Chat)", "")] + providers
        yield from self._setting_row(
            "ai.autocomplete_provider",
            "Autocomplete Provider",
            "Provider for suggestions (empty = default)",
            Select(ac_providers, value=s.autocomplete_provider or "", id="autocomplete_provider")
        )

        yield from self._setting_row(
            "ai.autocomplete_model",
            "Autocomplete Model",
            "Model override (empty = default)",
            Input(value=s.autocomplete_model, id="autocomplete_model")
        )

    def _collect_values(self):
        """Collect all control values into settings structure."""
        from settings import Settings, AppearanceSettings, EditorSettings, TerminalSettings, AISettings

        def get_val(control):
            if control is None:
                return None
            if isinstance(control, Switch):
                return control.value
            elif isinstance(control, Select):
                return control.value
            elif isinstance(control, Input):
                val = control.value
                if control.type == "integer":
                    try:
                        return int(val)
                    except ValueError:
                        return 0
                elif control.type == "number":
                    try:
                        return float(val)
                    except ValueError:
                        return 0.0
                return val
            return None

        appearance = AppearanceSettings(
            theme=get_val(self.controls.get("appearance.theme")) or "null-dark",
            font_family=get_val(self.controls.get("appearance.font_family")) or "monospace",
            font_size=get_val(self.controls.get("appearance.font_size")) or 14,
            line_height=get_val(self.controls.get("appearance.line_height")) or 1.4,
            show_timestamps=get_val(self.controls.get("appearance.show_timestamps")) or False,
            show_line_numbers=get_val(self.controls.get("appearance.show_line_numbers")) or False,
        )

        editor = EditorSettings(
            tab_size=get_val(self.controls.get("editor.tab_size")) or 4,
            word_wrap=get_val(self.controls.get("editor.word_wrap")) or False,
            auto_indent=get_val(self.controls.get("editor.auto_indent")) or False,
            vim_mode=get_val(self.controls.get("editor.vim_mode")) or False,
        )

        terminal = TerminalSettings(
            shell=get_val(self.controls.get("terminal.shell")) or "",
            scrollback_lines=get_val(self.controls.get("terminal.scrollback_lines")) or 10000,
            auto_save_session=get_val(self.controls.get("terminal.auto_save_session")) or False,
            auto_save_interval=get_val(self.controls.get("terminal.auto_save_interval")) or 30,
            confirm_on_exit=get_val(self.controls.get("terminal.confirm_on_exit")) or False,
            clear_on_exit=get_val(self.controls.get("terminal.clear_on_exit")) or False,
        )

        ai = AISettings(
            provider=get_val(self.controls.get("ai.provider")) or "ollama",
            context_window=get_val(self.controls.get("ai.context_window")) or 4000,
            max_tokens=get_val(self.controls.get("ai.max_tokens")) or 2048,
            temperature=get_val(self.controls.get("ai.temperature")) or 0.7,
            stream_responses=get_val(self.controls.get("ai.stream_responses")) or False,
            autocomplete_enabled=get_val(self.controls.get("ai.autocomplete_enabled")) or False,
            autocomplete_provider=get_val(self.controls.get("ai.autocomplete_provider")) or "",
            autocomplete_model=get_val(self.controls.get("ai.autocomplete_model")) or "",
        )

        return Settings(
            appearance=appearance,
            editor=editor,
            terminal=terminal,
            ai=ai
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "reset-btn":
            self._reset_to_defaults()

    def action_save(self):
        """Save settings and close."""
        from settings import save_settings
        from config import Config

        new_settings = self._collect_values()
        save_settings(new_settings)

        # SYNC TO SQLITE (Config)
        # Ensure critical keys used by app logic are synced
        Config.set("theme", new_settings.appearance.theme)
        Config.set("ai.provider", new_settings.ai.provider)
        Config.set("ai.autocomplete.enabled", str(new_settings.ai.autocomplete_enabled))
        Config.set("ai.autocomplete.provider", new_settings.ai.autocomplete_provider)
        Config.set("ai.autocomplete.model", new_settings.ai.autocomplete_model)

        # Apply theme immediately
        try:
            self.app.theme = new_settings.appearance.theme
        except Exception:
            pass

        self.dismiss(new_settings)

    def action_cancel(self):
        """Cancel without saving."""
        self.dismiss(None)

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        from settings import Settings, save_settings

        default_settings = Settings()
        save_settings(default_settings)
        self.notify("Settings reset to defaults. Reopening...")
        self.dismiss(default_settings)
