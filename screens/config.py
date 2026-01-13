"""Settings configuration screen."""

from typing import Any, ClassVar

from textual.binding import BindingType

from textual import on

from textual.css.query import NoMatches

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    Input,
    Label,
    ModalScreen,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    Vertical,
    VerticalScroll,
)

FIELD_TO_INPUT_ID: dict[str, str] = {
    "temperature": "temperature",
    "max_tokens": "max_tokens",
    "context_window": "context_window",
    "model": "autocomplete_model",
    "autocomplete_model": "autocomplete_model",
    "embedding_model": "embedding_model",
}


class ConfigScreen(ModalScreen):
    """Settings configuration screen with tabbed sections."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self):
        super().__init__()
        from config import Config, get_settings

        self.settings = get_settings()
        self.controls = {}

        # Sync ai.provider from SQLite (source of truth) to JSON settings
        # This ensures model selection changes are reflected in config screen
        sqlite_provider = Config.get("ai.provider")
        if sqlite_provider and sqlite_provider != self.settings.ai.provider:
            self.settings.ai.provider = sqlite_provider

    def on_mount(self) -> None:
        self.query_one("#theme", Select).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_save()

    @on(Input.Changed, "#temperature")
    def validate_temperature(self, event: Input.Changed) -> None:
        """Validate temperature is a float between 0.0 and 2.0."""
        try:
            val = float(event.value)
            if 0.0 <= val <= 2.0:
                event.input.remove_class("input-invalid")
            else:
                event.input.add_class("input-invalid")
        except ValueError:
            event.input.add_class("input-invalid")

    @on(Input.Changed, "#max_tokens")
    def validate_max_tokens(self, event: Input.Changed) -> None:
        """Validate max_tokens is a positive integer."""
        try:
            val = int(event.value)
            if val > 0:
                event.input.remove_class("input-invalid")
            else:
                event.input.add_class("input-invalid")
        except ValueError:
            event.input.add_class("input-invalid")

    @on(Switch.Changed)
    def update_switch_labels(self, event: Switch.Changed) -> None:
        label_id = f"{event.switch.id}_label"
        try:
            label = self.query_one(f"#{label_id}", Static)
            label.update("On" if event.value else "Off")
        except NoMatches:
            pass

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

                with TabPane("Voice", id="tab-voice"):
                    with VerticalScroll(classes="settings-scroll"):
                        yield from self._voice_settings()

                with TabPane("Keys", id="tab-keys"):
                    with VerticalScroll(classes="settings-scroll"):
                        yield from self._keybinding_settings()

            with Horizontal(id="config-footer"):
                yield Button("Save", id="save-btn")
                yield Button("Cancel", id="cancel-btn")
                yield Static("", classes="spacer")
                yield Button("Reset to Defaults", id="reset-btn")

    def _setting_row(self, key: str, label: str, hint: str, control) -> ComposeResult:
        """Create a setting row with label, hint, and control."""
        with Horizontal(classes="setting-row"):
            with Vertical(classes="setting-info"):
                yield Label(label, classes="setting-label")
                yield Label(hint, classes="setting-hint")
            with Horizontal(classes="setting-control"):
                self.controls[key] = control
                yield control
                # Add text label for Switch widgets (accessibility)
                if isinstance(control, Switch):
                    label_text = "On" if control.value else "Off"
                    yield Static(
                        label_text, id=f"{control.id}_label", classes="switch-label"
                    )

    def _appearance_settings(self) -> ComposeResult:
        """Appearance tab settings."""
        from utils.terminal import get_terminal_info

        s = self.settings.appearance
        term_info = get_terminal_info()

        # Show detected terminal info
        yield Static("Terminal Detection", classes="settings-header")

        font_support = (
            "✓ Supported" if term_info.supports_font_change else "✗ Not supported"
        )
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
            Select(
                [(name, value) for value, name in themes], value=s.theme, id="theme"
            ),
        )

        yield Static("Font Settings", classes="settings-header")

        # Show terminal capability info
        if not term_info.supports_font_change:
            yield Label(
                f"⚠ {term_info.name} requires manual font configuration.",
                classes="setting-warning",
            )

        fonts = [
            ("monospace", "Monospace (Default)"),
            ("Fira Code", "Fira Code"),
            ("JetBrains Mono", "JetBrains Mono"),
            ("Cascadia Code", "Cascadia Code"),
            ("Source Code Pro", "Source Code Pro"),
        ]
        yield from self._setting_row(
            "appearance.font_family",
            "Font Family",
            "Preferred terminal font",
            Select(
                [(name, value) for value, name in fonts],
                value=s.font_family,
                id="font_family",
            ),
        )

        yield from self._setting_row(
            "appearance.font_size",
            "Font Size",
            "Font size in pixels",
            Input(value=str(s.font_size), type="integer", id="font_size"),
        )

        yield Static("Display Options", classes="settings-header")

        yield from self._setting_row(
            "appearance.show_timestamps",
            "Show Timestamps",
            "Display timestamps on blocks",
            Switch(value=s.show_timestamps, id="show_timestamps"),
        )

        yield from self._setting_row(
            "appearance.show_line_numbers",
            "Show Line Numbers",
            "Display line numbers in code blocks",
            Switch(value=s.show_line_numbers, id="show_line_numbers"),
        )

    def _editor_settings(self) -> ComposeResult:
        """Editor tab settings."""
        s = self.settings.editor

        yield from self._setting_row(
            "editor.tab_size",
            "Tab Size",
            "Number of spaces per tab",
            Input(value=str(s.tab_size), type="integer", id="tab_size"),
        )

        yield from self._setting_row(
            "editor.word_wrap",
            "Word Wrap",
            "Wrap long lines in the editor",
            Switch(value=s.word_wrap, id="word_wrap"),
        )

        yield from self._setting_row(
            "editor.auto_indent",
            "Auto Indent",
            "Automatically indent new lines",
            Switch(value=s.auto_indent, id="auto_indent"),
        )

        yield from self._setting_row(
            "editor.vim_mode",
            "Vim Mode",
            "Enable vim-style keybindings",
            Switch(value=s.vim_mode, id="vim_mode"),
        )

    def _terminal_settings(self) -> ComposeResult:
        """Terminal tab settings."""
        s = self.settings.terminal
        import os

        yield from self._setting_row(
            "terminal.shell",
            "Shell",
            f"Shell to use (empty = $SHELL: {os.environ.get('SHELL', '/bin/bash')})",
            Input(
                value=s.shell,
                placeholder=os.environ.get("SHELL", "/bin/bash"),
                id="shell",
            ),
        )

        yield from self._setting_row(
            "terminal.scrollback_lines",
            "Scrollback Lines",
            "Maximum lines to keep in history",
            Input(value=str(s.scrollback_lines), type="integer", id="scrollback_lines"),
        )

        yield from self._setting_row(
            "terminal.auto_save_session",
            "Auto Save Session",
            "Automatically save session on changes",
            Switch(value=s.auto_save_session, id="auto_save_session"),
        )

        yield from self._setting_row(
            "terminal.auto_save_interval",
            "Auto Save Interval",
            "Seconds between auto-saves",
            Input(
                value=str(s.auto_save_interval), type="integer", id="auto_save_interval"
            ),
        )

        yield from self._setting_row(
            "terminal.confirm_on_exit",
            "Confirm on Exit",
            "Ask for confirmation before quitting",
            Switch(value=s.confirm_on_exit, id="confirm_on_exit"),
        )

        yield from self._setting_row(
            "terminal.clear_on_exit",
            "Clear on Exit",
            "Clear session when exiting",
            Switch(value=s.clear_on_exit, id="clear_on_exit"),
        )

        yield Static("Cursor Settings", classes="settings-header")

        yield from self._setting_row(
            "terminal.cursor_style",
            "Cursor Style",
            "Cursor appearance in input",
            Select(
                [("Block", "block"), ("Beam", "beam"), ("Underline", "underline")],
                value=s.cursor_style,
                id="cursor_style",
            ),
        )

        yield from self._setting_row(
            "terminal.cursor_blink",
            "Cursor Blink",
            "Enable cursor blinking in input",
            Switch(value=s.cursor_blink, id="cursor_blink"),
        )

        yield from self._setting_row(
            "terminal.bold_is_bright",
            "Bold is Bright",
            "Render bold text as bright colors",
            Switch(value=s.bold_is_bright, id="bold_is_bright"),
        )

    def _ai_settings(self) -> ComposeResult:
        """AI tab settings."""
        from ai.factory import AIFactory

        s = self.settings.ai

        providers = [("Not configured", "")]
        for key in AIFactory.list_providers():
            info = AIFactory.get_provider_info(key)
            providers.append((info.get("name", key), key))

        provider_value = s.provider if s.provider else ""

        yield from self._setting_row(
            "ai.provider",
            "Default Provider",
            "Default AI provider to use",
            Select(providers, value=provider_value, id="ai_provider"),
        )

        yield from self._setting_row(
            "ai.context_window",
            "Context Window",
            "Default context window size (tokens)",
            Input(value=str(s.context_window), type="integer", id="context_window"),
        )

        yield from self._setting_row(
            "ai.max_tokens",
            "Max Response Tokens",
            "Maximum tokens in AI response",
            Input(value=str(s.max_tokens), type="integer", id="max_tokens"),
        )

        yield from self._setting_row(
            "ai.temperature",
            "Temperature",
            "Creativity level (0.0 - 2.0)",
            Input(value=str(s.temperature), type="number", id="temperature"),
        )

        yield from self._setting_row(
            "ai.stream_responses",
            "Stream Responses",
            "Show AI responses as they generate",
            Switch(value=s.stream_responses, id="stream_responses"),
        )

        yield Static("Autocomplete Settings", classes="settings-header")

        yield from self._setting_row(
            "ai.autocomplete_enabled",
            "Enable Autocomplete",
            "AI-powered command suggestions",
            Switch(value=s.autocomplete_enabled, id="autocomplete_enabled"),
        )

        # Autocomplete Provider override (optional)
        # Re-use providers list
        ac_providers = [("Default (Same as Chat)", ""), *providers]
        yield from self._setting_row(
            "ai.autocomplete_provider",
            "Autocomplete Provider",
            "Provider for suggestions (empty = default)",
            Select(
                ac_providers,
                value=s.autocomplete_provider or "",
                id="autocomplete_provider",
            ),
        )

        yield from self._setting_row(
            "ai.autocomplete_model",
            "Autocomplete Model",
            "Model override (empty = default)",
            Input(value=s.autocomplete_model, id="autocomplete_model"),
        )

        yield Static("Embedding Settings", classes="settings-header")

        embedding_provider_value = s.embedding_provider if s.embedding_provider else ""

        yield from self._setting_row(
            "ai.embedding_provider",
            "Embedding Provider",
            "Provider for semantic search embeddings",
            Select(providers, value=embedding_provider_value, id="embedding_provider"),
        )

        yield from self._setting_row(
            "ai.embedding_model",
            "Embedding Model",
            "Model name (e.g. nomic-embed-text)",
            Input(value=s.embedding_model, id="embedding_model"),
        )

        yield from self._setting_row(
            "ai.embedding_endpoint",
            "Embedding Endpoint",
            "API endpoint (e.g. http://localhost:11434)",
            Input(value=s.embedding_endpoint, id="embedding_endpoint"),
        )

    def _voice_settings(self) -> ComposeResult:
        s = self.settings.voice

        yield from self._setting_row(
            "voice.enabled",
            "Enable Voice Input",
            "Allow voice-to-text input",
            Switch(value=s.enabled, id="voice_enabled"),
        )

        yield from self._setting_row(
            "voice.hotkey",
            "Hotkey",
            "Press Ctrl+M to start/stop recording",
            Label(s.hotkey, id="voice_hotkey"),
        )

        stt_providers = [
            ("OpenAI Whisper", "openai"),
        ]
        yield from self._setting_row(
            "voice.stt_provider",
            "Transcription Service",
            "Service that converts speech to text",
            Select(stt_providers, value=s.stt_provider, id="stt_provider"),
        )

        yield from self._setting_row(
            "voice.stt_model",
            "Model",
            "Use 'whisper-1' for OpenAI (default)",
            Input(value=s.stt_model or "", placeholder="whisper-1", id="stt_model"),
        )

        yield from self._setting_row(
            "voice.language",
            "Language",
            "Two-letter code: en, es, fr, de, ja, zh, etc.",
            Input(value=s.language or "", placeholder="en", id="voice_language"),
        )

        yield from self._setting_row(
            "voice.push_to_talk",
            "Push to Talk",
            "Hold hotkey to record, release to stop",
            Switch(value=s.push_to_talk, id="push_to_talk"),
        )

    def _keybinding_settings(self) -> ComposeResult:
        from config import get_keybinding_manager

        self._kb_manager = get_keybinding_manager()
        conflicts = self._kb_manager.detect_all_conflicts()

        if conflicts:
            yield Static("⚠ Conflicts Detected", classes="settings-header warning")
            for conflict in conflicts:
                yield Label(conflict.description, classes="setting-warning")

        yield Static("Global Shortcuts", classes="settings-header")
        yield from self._keybinding_context_rows("app")

        yield Static("Input Shortcuts", classes="settings-header")
        yield from self._keybinding_context_rows("input")

        yield Static("Block Shortcuts", classes="settings-header")
        yield from self._keybinding_context_rows("block")

        with Horizontal(classes="setting-row"):
            yield Button("Reset All Keys", id="reset-keys-btn", variant="warning")

    def _keybinding_context_rows(self, context: str) -> ComposeResult:
        bindings = self._kb_manager.get_bindings_by_context(context)
        for binding in bindings:
            is_modified = self._kb_manager.is_modified(binding.id)
            default_key = self._kb_manager.get_default_key(binding.id)
            hint = (
                f"Default: {self._kb_manager.format_key_display(default_key)}"
                if default_key
                else ""
            )
            if is_modified:
                hint = f"⚡ Modified | {hint}"

            input_widget = Input(
                value=binding.key,
                id=f"kb_{binding.id}",
                classes="keybinding-input" + (" modified" if is_modified else ""),
            )
            yield from self._setting_row(
                f"keybinding.{binding.id}",
                binding.description,
                hint,
                input_widget,
            )

    @on(Input.Changed, ".keybinding-input")
    def validate_keybinding(self, event: Input.Changed) -> None:
        from config import KeybindingManager

        key = event.value
        is_valid, error = KeybindingManager.validate_key(key)
        if is_valid:
            event.input.remove_class("input-invalid")
        else:
            event.input.add_class("input-invalid")

    def _collect_values(self):
        """Collect all control values into settings structure."""
        from config import (
            AISettings,
            AppearanceSettings,
            EditorSettings,
            Settings,
            TerminalSettings,
            VoiceSettings,
        )

        def get_val(control: Any) -> Any:
            if control is None:
                return None

            val = getattr(control, "value", None)

            if val.__class__.__name__ == "NoSelection":
                return None

            if isinstance(control, Input):
                if control.type == "integer":
                    try:
                        return max(1, int(str(val)))
                    except (ValueError, TypeError):
                        return 1
                elif control.type == "number":
                    try:
                        return max(0.0, float(str(val)))
                    except (ValueError, TypeError):
                        return 0.0
            return val

        def get_bool(control: Any, default: bool) -> bool:
            val = get_val(control)
            return bool(val) if val is not None else default

        appearance = AppearanceSettings(
            theme=str(get_val(self.controls.get("appearance.theme")) or "null-dark"),
            font_family=str(
                get_val(self.controls.get("appearance.font_family"))
                or self.settings.appearance.font_family
            ),
            font_size=int(
                get_val(self.controls.get("appearance.font_size"))
                or self.settings.appearance.font_size
            ),
            line_height=self.settings.appearance.line_height,
            show_timestamps=get_bool(
                self.controls.get("appearance.show_timestamps"), True
            ),
            show_line_numbers=get_bool(
                self.controls.get("appearance.show_line_numbers"), True
            ),
        )

        editor = EditorSettings(
            tab_size=int(get_val(self.controls.get("editor.tab_size")) or 4),
            word_wrap=get_bool(self.controls.get("editor.word_wrap"), True),
            auto_indent=get_bool(self.controls.get("editor.auto_indent"), True),
            vim_mode=get_bool(self.controls.get("editor.vim_mode"), False),
        )

        terminal = TerminalSettings(
            shell=str(get_val(self.controls.get("terminal.shell")) or ""),
            scrollback_lines=int(
                get_val(self.controls.get("terminal.scrollback_lines")) or 10000
            ),
            auto_save_session=get_bool(
                self.controls.get("terminal.auto_save_session"), True
            ),
            auto_save_interval=int(
                get_val(self.controls.get("terminal.auto_save_interval")) or 30
            ),
            confirm_on_exit=get_bool(
                self.controls.get("terminal.confirm_on_exit"), True
            ),
            clear_on_exit=get_bool(self.controls.get("terminal.clear_on_exit"), False),
            cursor_style=str(
                get_val(self.controls.get("terminal.cursor_style")) or "block"
            ),
            cursor_blink=get_bool(self.controls.get("terminal.cursor_blink"), True),
            bold_is_bright=get_bool(self.controls.get("terminal.bold_is_bright"), True),
        )

        ai = AISettings(
            provider=str(get_val(self.controls.get("ai.provider")) or ""),
            context_window=int(get_val(self.controls.get("ai.context_window")) or 4000),
            max_tokens=int(get_val(self.controls.get("ai.max_tokens")) or 2048),
            temperature=float(get_val(self.controls.get("ai.temperature")) or 0.7),
            stream_responses=get_bool(self.controls.get("ai.stream_responses"), True),
            autocomplete_enabled=get_bool(
                self.controls.get("ai.autocomplete_enabled"), False
            ),
            autocomplete_provider=str(
                get_val(self.controls.get("ai.autocomplete_provider")) or ""
            ),
            autocomplete_model=str(
                get_val(self.controls.get("ai.autocomplete_model")) or ""
            ),
            embedding_provider=str(
                get_val(self.controls.get("ai.embedding_provider")) or ""
            ),
            embedding_model=str(get_val(self.controls.get("ai.embedding_model")) or ""),
            embedding_endpoint=str(
                get_val(self.controls.get("ai.embedding_endpoint")) or ""
            ),
        )

        voice = VoiceSettings(
            enabled=get_bool(self.controls.get("voice.enabled"), False),
            hotkey=self.settings.voice.hotkey,
            stt_provider=str(
                get_val(self.controls.get("voice.stt_provider")) or "openai"
            ),
            stt_model=str(get_val(self.controls.get("voice.stt_model")) or "whisper-1"),
            language=str(get_val(self.controls.get("voice.language")) or "en"),
            push_to_talk=get_bool(self.controls.get("voice.push_to_talk"), True),
        )

        return Settings(
            appearance=appearance, editor=editor, terminal=terminal, ai=ai, voice=voice
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "reset-btn":
            self._reset_to_defaults()
        elif event.button.id == "reset-keys-btn":
            self._reset_keybindings()

    def _validate_settings(self, settings) -> dict[str, str]:
        from config import Config, ValidationError

        for input_id in FIELD_TO_INPUT_ID.values():
            try:
                self.query_one(f"#{input_id}", Input).remove_class("input-invalid")
            except NoMatches:
                pass

        api_key = Config.get(f"ai.{settings.ai.provider}.api_key", "")

        try:
            settings.ai.validate(api_key=api_key)
            return {}
        except ValidationError as e:
            for field_name in e.errors:
                input_id = FIELD_TO_INPUT_ID.get(field_name)
                if input_id:
                    try:
                        self.query_one(f"#{input_id}", Input).add_class("input-invalid")
                    except NoMatches:
                        pass
            return e.errors

    def action_save(self):
        """Save settings and close."""
        from config import Config, save_settings

        new_settings = self._collect_values()

        errors = self._validate_settings(new_settings)
        if errors:
            error_msgs = [f"{k}: {v}" for k, v in errors.items()]
            self.notify(f"Validation failed: {', '.join(error_msgs)}", severity="error")
            return

        save_settings(new_settings)

        # SYNC TO SQLITE (Config)
        # Ensure critical keys used by app logic are synced
        Config.set("theme", new_settings.appearance.theme)
        Config.set("ai.provider", new_settings.ai.provider)
        Config.set("ai.autocomplete.enabled", str(new_settings.ai.autocomplete_enabled))
        Config.set("ai.autocomplete.provider", new_settings.ai.autocomplete_provider)
        Config.set("ai.autocomplete.model", new_settings.ai.autocomplete_model)

        Config.set("ai.embedding_provider", new_settings.ai.embedding_provider)
        Config.set(
            f"ai.embedding.{new_settings.ai.embedding_provider}.model",
            new_settings.ai.embedding_model,
        )
        Config.set(
            f"ai.embedding.{new_settings.ai.embedding_provider}.endpoint",
            new_settings.ai.embedding_endpoint,
        )

        # Apply theme immediately
        try:
            self.app.theme = new_settings.appearance.theme
        except Exception:
            pass

        # Apply cursor settings immediately
        try:
            from utils.terminal import apply_cursor_settings

            apply_cursor_settings(
                style=new_settings.terminal.cursor_style,
                blink=new_settings.terminal.cursor_blink,
            )
        except Exception:
            pass

        # Update InputController's cursor settings
        try:
            from widgets.input import InputController

            input_widget = self.app.query_one("#input", InputController)
            input_widget.cursor_blink = new_settings.terminal.cursor_blink

            # Apply cursor style class
            cursor_style = new_settings.terminal.cursor_style
            input_widget.remove_class("cursor-block", "cursor-beam", "cursor-underline")
            input_widget.add_class(f"cursor-{cursor_style}")
        except Exception:
            pass

        # Sync font and cursor settings to host terminal's config file (silently)
        try:
            from utils.terminal import sync_terminal_config

            sync_terminal_config(
                font_family=new_settings.appearance.font_family,
                font_size=float(new_settings.appearance.font_size),
                cursor_style=new_settings.terminal.cursor_style,
                cursor_blink=new_settings.terminal.cursor_blink,
            )
        except Exception:
            pass

        self._save_keybindings()

        self.notify("Settings updated", timeout=2)
        self.dismiss(new_settings)

    def action_cancel(self):
        """Cancel without saving."""
        self.dismiss(None)

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        from config import Settings, save_settings

        default_settings = Settings()
        save_settings(default_settings)
        self.notify("Settings reset to defaults. Reopening...")
        self.dismiss(default_settings)

    def _reset_keybindings(self):
        from config import get_keybinding_manager

        manager = get_keybinding_manager()
        manager.reset_to_defaults()
        self.notify("Keybindings reset to defaults. Reopening...")
        self.dismiss(None)

    def _save_keybindings(self):
        from config import KeybindingManager, get_keybinding_manager

        manager = get_keybinding_manager()
        conflicts = []

        for key, control in self.controls.items():
            if key.startswith("keybinding."):
                binding_id = key[11:]
                new_key = getattr(control, "value", "")
                if new_key:
                    is_valid, _ = KeybindingManager.validate_key(new_key)
                    if is_valid:
                        binding_conflicts = manager.set_binding(binding_id, new_key)
                        conflicts.extend(binding_conflicts)

        manager.save()

        if conflicts:
            conflict_keys = list({c.key for c in conflicts})
            self.notify(
                f"Keybindings saved with conflicts: {', '.join(conflict_keys)}",
                severity="warning",
            )
