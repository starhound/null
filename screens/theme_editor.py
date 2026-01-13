"""Theme editor screen for creating and customizing themes."""

import json
import re
from pathlib import Path
from typing import ClassVar

from textual.binding import BindingType
from textual.message import Message
from textual.reactive import reactive
from textual.theme import Theme

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
    Vertical,
    VerticalScroll,
)

# User themes directory
USER_THEMES_DIR = Path.home() / ".null" / "themes"

# Color properties in a theme
THEME_COLORS = [
    ("primary", "Primary", "Main accent color"),
    ("secondary", "Secondary", "Secondary accent"),
    ("accent", "Accent", "Highlight color"),
    ("foreground", "Foreground", "Text color"),
    ("background", "Background", "App background"),
    ("surface", "Surface", "Block backgrounds"),
    ("panel", "Panel", "Elevated surfaces"),
    ("success", "Success", "Success indicators"),
    ("warning", "Warning", "Warning indicators"),
    ("error", "Error", "Error indicators"),
    ("boost", "Boost", "Extra emphasis"),
]


class ColorSwatch(Static):
    """A color swatch that displays a color."""

    def __init__(self, color: str = "#000000", **kwargs):
        super().__init__("", **kwargs)
        self._color = color
        self.styles.background = color

    def set_color(self, color: str) -> None:
        """Update the swatch color."""
        self._color = color
        try:
            self.styles.background = color
        except Exception:
            pass


class ColorInput(Input):
    """Input for hex color values with validation."""

    class ColorChanged(Message):
        """Fired when color value changes and is valid."""

        def __init__(self, key: str, color: str):
            super().__init__()
            self.key = key
            self.color = color

    def __init__(self, color_key: str, value: str = "#000000", **kwargs):
        super().__init__(value=value, **kwargs)
        self.color_key = color_key
        self._last_valid = value

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate hex color format."""
        value = event.value.strip()
        if self._is_valid_hex(value):
            self.remove_class("input-invalid")
            self._last_valid = value
            self.post_message(self.ColorChanged(self.color_key, value))
        else:
            self.add_class("input-invalid")

    @staticmethod
    def _is_valid_hex(value: str) -> bool:
        """Check if value is a valid hex color."""
        return bool(re.match(r"^#[0-9A-Fa-f]{6}$", value))


class ThemePreviewWidget(Static):
    """Widget showing a preview of theme colors."""

    def __init__(self, theme_data: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self._theme_data = theme_data or {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="theme-preview-row"):
            for key, label, _ in THEME_COLORS[:6]:  # First 6 colors
                color = self._theme_data.get(key, "#808080")
                with Vertical(classes="preview-color-item"):
                    yield ColorSwatch(
                        color, id=f"preview-{key}", classes="preview-swatch"
                    )
                    yield Label(label[:3], classes="preview-label")

    def update_color(self, key: str, color: str) -> None:
        """Update a single color in the preview."""
        try:
            swatch = self.query_one(f"#preview-{key}", ColorSwatch)
            swatch.set_color(color)
        except Exception:
            pass


class ThemeEditorScreen(ModalScreen):
    """Screen for editing and creating custom themes."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    # Current theme data being edited
    theme_data: reactive[dict] = reactive({}, init=False)

    def __init__(self, base_theme: str | None = None):
        """Initialize theme editor.

        Args:
            base_theme: Name of theme to use as starting point, or None for new theme.
        """
        super().__init__()
        self._base_theme = base_theme
        self._original_app_theme: str | None = None
        self._controls: dict[str, ColorInput | Input | Switch] = {}
        self._preview: ThemePreviewWidget | None = None
        self._live_preview_enabled = True

    def compose(self) -> ComposeResult:
        with Container(id="theme-editor-outer"):
            with Static(id="theme-editor-header"):
                yield Label("Theme Editor")

            with VerticalScroll(id="theme-editor-scroll"):
                yield Static("Theme Info", classes="editor-section-header")
                yield from self._metadata_section()

                yield Static("Preview", classes="editor-section-header")
                yield from self._preview_section()

                yield Static("Colors", classes="editor-section-header")
                yield from self._colors_section()

                yield Static("Advanced", classes="editor-section-header")
                yield from self._advanced_section()

            with Horizontal(id="theme-editor-footer"):
                yield Button("Save Theme", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")
                yield Static("", classes="spacer")
                yield Button("Reset", id="reset-btn", variant="warning")

    def _metadata_section(self) -> ComposeResult:
        """Render theme metadata inputs."""
        with Horizontal(classes="editor-row"):
            yield Label("Name:", classes="editor-label")
            name_input = Input(
                value=self.theme_data.get("name", "my-theme"),
                placeholder="my-custom-theme",
                id="theme-name",
            )
            self._controls["name"] = name_input
            yield name_input

        with Horizontal(classes="editor-row"):
            yield Label("Description:", classes="editor-label")
            desc_input = Input(
                value=self.theme_data.get("description", ""),
                placeholder="A brief description",
                id="theme-description",
            )
            self._controls["description"] = desc_input
            yield desc_input

        with Horizontal(classes="editor-row"):
            yield Label("Dark Mode:", classes="editor-label")
            dark_switch = Switch(
                value=self.theme_data.get("dark", True), id="theme-dark"
            )
            self._controls["dark"] = dark_switch
            yield dark_switch
            yield Static(
                "On" if self.theme_data.get("dark", True) else "Off",
                id="dark-label",
                classes="switch-label",
            )

    def _preview_section(self) -> ComposeResult:
        """Render live preview section."""
        with Horizontal(classes="editor-row"):
            yield Label("Live Preview:", classes="editor-label")
            preview_switch = Switch(value=True, id="live-preview-switch")
            yield preview_switch
            yield Static("On", id="live-preview-label", classes="switch-label")

        self._preview = ThemePreviewWidget(self.theme_data, id="theme-preview-widget")
        yield self._preview

    def _colors_section(self) -> ComposeResult:
        """Render color editor section."""
        for key, label, hint in THEME_COLORS:
            color = self.theme_data.get(key, "#808080")
            with Horizontal(classes="editor-row color-row"):
                yield Label(f"{label}:", classes="editor-label")
                with Horizontal(classes="color-input-group"):
                    swatch = ColorSwatch(
                        color, id=f"swatch-{key}", classes="color-swatch"
                    )
                    yield swatch
                    color_input = ColorInput(
                        key, color, id=f"color-{key}", classes="color-input"
                    )
                    self._controls[key] = color_input
                    yield color_input
                yield Label(hint, classes="editor-hint")

    def _advanced_section(self) -> ComposeResult:
        """Render advanced settings section."""
        with Horizontal(classes="editor-row"):
            yield Label("Luminosity:", classes="editor-label")
            lum_input = Input(
                value=str(self.theme_data.get("luminosity_spread", 0.15)),
                type="number",
                id="luminosity-spread",
            )
            self._controls["luminosity_spread"] = lum_input
            yield lum_input
            yield Label("0.1-0.3 typical", classes="editor-hint")

        with Horizontal(classes="editor-row"):
            yield Label("Text Alpha:", classes="editor-label")
            alpha_input = Input(
                value=str(self.theme_data.get("text_alpha", 0.95)),
                type="number",
                id="text-alpha",
            )
            self._controls["text_alpha"] = alpha_input
            yield alpha_input
            yield Label("0.8-1.0 typical", classes="editor-hint")

    def on_mount(self) -> None:
        """Initialize theme data when mounted."""
        self._original_app_theme = self.app.theme
        self._load_base_theme()

    def _load_base_theme(self) -> None:
        """Load the base theme data."""
        if self._base_theme:
            # Try to load from file
            theme_data = self._load_theme_from_name(self._base_theme)
            if theme_data:
                # Create a copy for editing
                self.theme_data = dict(theme_data)
                # Append "-copy" to name to avoid overwriting
                if "name" in self.theme_data:
                    self.theme_data["name"] = f"{self.theme_data['name']}-copy"
            else:
                self._init_default_theme()
        else:
            self._init_default_theme()

        self._update_all_controls()

    def _load_theme_from_name(self, name: str) -> dict | None:
        """Load theme data from a theme name."""
        from themes import BUILTIN_THEMES_DIR, USER_THEMES_DIR

        # Try user themes first
        for themes_dir in [USER_THEMES_DIR, BUILTIN_THEMES_DIR]:
            if themes_dir.exists():
                for theme_file in themes_dir.glob("*.json"):
                    try:
                        with open(theme_file) as f:
                            data = json.load(f)
                        if data.get("name") == name:
                            return data
                    except Exception:
                        continue
        return None

    def _init_default_theme(self) -> None:
        """Initialize with default theme values."""
        self.theme_data = {
            "name": "my-custom-theme",
            "description": "Custom theme",
            "dark": True,
            "primary": "#00D4FF",
            "secondary": "#BD00FF",
            "accent": "#00FF88",
            "foreground": "#E0E6F0",
            "background": "#08090D",
            "surface": "#0E1018",
            "panel": "#151822",
            "success": "#00FF88",
            "warning": "#FFB800",
            "error": "#FF3366",
            "boost": "#00FFCC",
            "luminosity_spread": 0.15,
            "text_alpha": 0.95,
            "variables": {},
        }

    def _update_all_controls(self) -> None:
        """Update all control values from theme_data."""
        for key, control in self._controls.items():
            if key in self.theme_data:
                value = self.theme_data[key]
                if isinstance(control, Switch):
                    control.value = bool(value)
                elif isinstance(control, Input):
                    control.value = str(value)

        if self._preview:
            for key, _, _ in THEME_COLORS:
                if key in self.theme_data:
                    self._preview.update_color(key, self.theme_data[key])

    def on_color_input_color_changed(self, message: ColorInput.ColorChanged) -> None:
        """Handle color input changes."""
        self.theme_data[message.key] = message.color

        try:
            swatch = self.query_one(f"#swatch-{message.key}", ColorSwatch)
            swatch.set_color(message.color)
        except Exception:
            pass

        if self._preview:
            self._preview.update_color(message.key, message.color)

        if self._live_preview_enabled:
            self._apply_live_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes."""
        if event.switch.id == "theme-dark":
            self.theme_data["dark"] = event.value
            try:
                label = self.query_one("#dark-label", Static)
                label.update("On" if event.value else "Off")
            except Exception:
                pass
            if self._live_preview_enabled:
                self._apply_live_preview()
        elif event.switch.id == "live-preview-switch":
            self._live_preview_enabled = event.value
            try:
                label = self.query_one("#live-preview-label", Static)
                label.update("On" if event.value else "Off")
            except Exception:
                pass
            if event.value:
                self._apply_live_preview()
            elif self._original_app_theme:
                self.app.theme = self._original_app_theme

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for non-color fields."""
        input_id = event.input.id
        if input_id == "theme-name":
            self.theme_data["name"] = event.value
        elif input_id == "theme-description":
            self.theme_data["description"] = event.value
        elif input_id == "luminosity-spread":
            try:
                self.theme_data["luminosity_spread"] = float(event.value)
                if self._live_preview_enabled:
                    self._apply_live_preview()
            except ValueError:
                pass
        elif input_id == "text-alpha":
            try:
                self.theme_data["text_alpha"] = float(event.value)
                if self._live_preview_enabled:
                    self._apply_live_preview()
            except ValueError:
                pass

    def _apply_live_preview(self) -> None:
        """Apply current theme data as live preview."""
        try:
            theme = self._create_theme_from_data()
            if theme:
                # Register and apply the preview theme
                self.app.register_theme(theme)
                self.app.theme = theme.name
        except Exception as e:
            self.log.warning(f"Failed to apply live preview: {e}")

    def _create_theme_from_data(self) -> Theme | None:
        """Create a Theme object from current data."""
        try:
            return Theme(
                name=self.theme_data.get("name", "preview-theme"),
                dark=self.theme_data.get("dark", True),
                primary=self.theme_data.get("primary", "#00D4FF"),
                secondary=self.theme_data.get("secondary"),
                accent=self.theme_data.get("accent"),
                foreground=self.theme_data.get("foreground"),
                background=self.theme_data.get("background"),
                surface=self.theme_data.get("surface"),
                panel=self.theme_data.get("panel"),
                success=self.theme_data.get("success"),
                warning=self.theme_data.get("warning"),
                error=self.theme_data.get("error"),
                boost=self.theme_data.get("boost"),
                luminosity_spread=self.theme_data.get("luminosity_spread", 0.15),
                text_alpha=self.theme_data.get("text_alpha", 0.95),
                variables=self.theme_data.get("variables", {}),
            )
        except Exception:
            return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "reset-btn":
            self._reset_to_base()

    def _reset_to_base(self) -> None:
        """Reset to base theme."""
        self._load_base_theme()
        self.notify("Theme reset to base values")

    def action_save(self) -> None:
        """Save the theme to user themes directory."""
        name = self.theme_data.get("name", "").strip()
        if not name:
            self.notify("Theme name is required", severity="error")
            return

        filename = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower())
        if not filename:
            filename = "custom-theme"

        USER_THEMES_DIR.mkdir(parents=True, exist_ok=True)
        theme_path = USER_THEMES_DIR / f"{filename}.json"

        try:
            save_data = {
                k: v for k, v in self.theme_data.items() if not k.startswith("_")
            }

            with open(theme_path, "w") as f:
                json.dump(save_data, f, indent=2)

            theme = self._create_theme_from_data()
            if theme:
                self.app.register_theme(theme)

            self.notify(f"Theme saved to {theme_path.name}")
            self.dismiss(name)

        except Exception as e:
            self.notify(f"Failed to save theme: {e}", severity="error")

    def action_cancel(self) -> None:
        """Cancel editing and restore original theme."""
        if self._original_app_theme:
            try:
                self.app.theme = self._original_app_theme
            except Exception:
                pass
        self.dismiss(None)


class ThemePalettePreview(Static):
    """A compact color palette preview for theme selection."""

    def __init__(self, theme_name: str, **kwargs):
        super().__init__(**kwargs)
        self._theme_name = theme_name
        self._colors: list[str] = []
        self._load_colors()

    def _load_colors(self) -> None:
        """Load colors from theme."""
        from themes import BUILTIN_THEMES_DIR, USER_THEMES_DIR

        for themes_dir in [USER_THEMES_DIR, BUILTIN_THEMES_DIR]:
            if themes_dir.exists():
                for theme_file in themes_dir.glob("*.json"):
                    try:
                        with open(theme_file) as f:
                            data = json.load(f)
                        if data.get("name") == self._theme_name:
                            self._colors = [
                                data.get("primary", "#808080"),
                                data.get("secondary", "#808080"),
                                data.get("accent", "#808080"),
                                data.get("background", "#808080"),
                                data.get("success", "#808080"),
                                data.get("error", "#808080"),
                            ]
                            return
                    except Exception:
                        continue

    def compose(self) -> ComposeResult:
        with Horizontal(classes="palette-swatches"):
            for i, color in enumerate(self._colors[:6]):
                yield Static("", classes=f"palette-swatch palette-{i}")

    def on_mount(self) -> None:
        """Apply colors to swatches."""
        for i, color in enumerate(self._colors[:6]):
            try:
                swatch = self.query_one(f".palette-{i}")
                swatch.styles.background = color
            except Exception:
                pass
