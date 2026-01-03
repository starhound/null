"""Custom themes for Null terminal."""

import json
from pathlib import Path

from textual.theme import Theme

# =============================================================================
# Cyber Noir - The signature Null Terminal aesthetic
# Deep darkness with neon accents, layered visual depth, and dramatic contrast
# =============================================================================
NULL_DARK = Theme(
    name="null-dark",
    dark=True,
    # Neon accent palette
    primary="#00D4FF",  # Electric cyan - AI responses, primary actions
    secondary="#BD00FF",  # Vivid magenta - agent mode, system
    accent="#00FF88",  # Matrix green - CLI, success states
    # Text with high clarity
    foreground="#E0E6F0",  # Bright silver-blue
    # Layered dark backgrounds (deepest to elevated)
    background="#08090D",  # Near-black void
    surface="#0E1018",  # Slightly raised
    panel="#151822",  # Card/panel surfaces
    # Semantic colors with neon intensity
    success="#00FF88",  # Neon green
    warning="#FFB800",  # Electric amber
    error="#FF3366",  # Hot pink-red
    boost="#00FFCC",  # Teal glow
    luminosity_spread=0.18,  # Dramatic variation for depth
    text_alpha=0.95,
    variables={
        "block-cursor-background": "#00D4FF",
        "block-cursor-foreground": "#08090D",
        "input-cursor-background": "#00D4FF",
        "input-cursor-foreground": "#08090D",
        # Noir-specific layering colors
        "noir-void": "#000000",
        "noir-deep": "#08090D",
        "noir-shadow": "#0E1018",
        "noir-surface": "#151822",
        "noir-elevated": "#1C2030",
        "noir-highlight": "#252A3A",
        # Glow intensities for focus states
        "glow-cyan": "#00D4FF",
        "glow-magenta": "#BD00FF",
        "glow-green": "#00FF88",
    },
)

# Warmer variant with orange/amber accents (Claude-like)
NULL_WARM = Theme(
    name="null-warm",
    dark=True,
    primary="#F59E0B",  # Amber - primary accent
    secondary="#EC4899",  # Pink - secondary accent
    accent="#FB923C",  # Orange - highlights
    foreground="#E7E5E4",  # Stone 200 - main text
    background="#0C0A09",  # Stone 950 - deep warm black
    surface="#1C1917",  # Stone 900 - elevated surface
    panel="#292524",  # Stone 800 - panel background
    success="#4ADE80",  # Green 400 - success
    warning="#FACC15",  # Yellow 400 - warnings
    error="#FB7185",  # Rose 400 - errors
    boost="#2DD4BF",  # Teal - special highlights
    luminosity_spread=0.10,
    text_alpha=0.90,
    variables={
        "block-cursor-background": "#F59E0B",
        "block-cursor-foreground": "#0C0A09",
    },
)

# Minimal monochrome with subtle blue tints
NULL_MONO = Theme(
    name="null-mono",
    dark=True,
    primary="#94A3B8",  # Slate 400 - subtle primary
    secondary="#64748B",  # Slate 500 - secondary
    accent="#7DD3FC",  # Sky 300 - rare highlights
    foreground="#CBD5E1",  # Slate 300 - main text
    background="#020617",  # Slate 950 - deepest black
    surface="#0F172A",  # Slate 900 - surface
    panel="#1E293B",  # Slate 800 - panels
    success="#86EFAC",  # Green 300
    warning="#FDE047",  # Yellow 300
    error="#FCA5A5",  # Red 300
    boost="#67E8F9",  # Cyan 300
    luminosity_spread=0.08,  # Very subtle variation
    text_alpha=0.88,  # Softer text
)

# Light theme option
NULL_LIGHT = Theme(
    name="null-light",
    dark=False,
    primary="#2563EB",  # Blue 600
    secondary="#7C3AED",  # Violet 600
    accent="#0891B2",  # Cyan 600
    foreground="#1E293B",  # Slate 800 - dark text
    background="#F8FAFC",  # Slate 50 - off-white
    surface="#FFFFFF",  # Pure white cards
    panel="#F1F5F9",  # Slate 100 - panels
    success="#059669",  # Emerald 600
    warning="#D97706",  # Amber 600
    error="#DC2626",  # Red 600
    boost="#0D9488",  # Teal 600
    luminosity_spread=0.15,
    text_alpha=0.95,
)


# Built-in themes
BUILTIN_THEMES = {
    "null-dark": NULL_DARK,
    "null-warm": NULL_WARM,
    "null-mono": NULL_MONO,
    "null-light": NULL_LIGHT,
}


def load_user_themes() -> dict[str, Theme]:
    """Load custom themes from ~/.null/themes/*.json"""
    themes: dict[str, Theme] = {}
    themes_dir = Path.home() / ".null" / "themes"

    if not themes_dir.exists():
        # Create directory with example theme
        themes_dir.mkdir(parents=True, exist_ok=True)
        _create_example_theme(themes_dir)
        return themes

    for theme_file in themes_dir.glob("*.json"):
        try:
            theme = _load_theme_file(theme_file)
            if theme:
                themes[theme.name] = theme
        except Exception:
            pass  # Skip invalid theme files

    return themes


def _load_theme_file(path: Path) -> Theme | None:
    """Load a single theme from a JSON file."""
    try:
        with open(path) as f:
            data = json.load(f)

        # Required fields
        name = data.get("name", path.stem)
        primary = data.get("primary")
        if not primary:
            return None

        return Theme(
            name=name,
            dark=data.get("dark", True),
            primary=primary,
            secondary=data.get("secondary"),
            accent=data.get("accent"),
            foreground=data.get("foreground"),
            background=data.get("background"),
            surface=data.get("surface"),
            panel=data.get("panel"),
            success=data.get("success"),
            warning=data.get("warning"),
            error=data.get("error"),
            boost=data.get("boost"),
            luminosity_spread=data.get("luminosity_spread", 0.15),
            text_alpha=data.get("text_alpha", 0.95),
            variables=data.get("variables", {}),
        )
    except Exception:
        return None


def _create_example_theme(themes_dir: Path):
    """Create an example theme file for users."""
    example = {
        "name": "example-custom",
        "dark": True,
        "primary": "#FF6B6B",
        "secondary": "#4ECDC4",
        "accent": "#FFE66D",
        "foreground": "#F7FFF7",
        "background": "#1A1A2E",
        "surface": "#16213E",
        "panel": "#0F3460",
        "success": "#95E1A3",
        "warning": "#FFE66D",
        "error": "#FF6B6B",
        "luminosity_spread": 0.12,
        "text_alpha": 0.92,
        "_comment": "This is an example theme. Edit or copy to create your own!",
    }

    example_path = themes_dir / "example-custom.json.example"
    try:
        with open(example_path, "w") as f:
            json.dump(example, f, indent=2)
    except Exception:
        pass


def get_all_themes() -> dict[str, Theme]:
    """Get all themes (built-in + user)."""
    themes = dict(BUILTIN_THEMES)
    themes.update(load_user_themes())
    return themes


# For backwards compatibility
THEMES = BUILTIN_THEMES
