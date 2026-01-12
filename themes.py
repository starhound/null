"""Theme management for Null terminal.

Loads themes from:
1. styles/themes/*.json (built-in themes, shipped with app)
2. ~/.null/themes/*.json (user custom themes)

On first run, built-in themes are copied to ~/.null/themes/ for easy customization.
"""

import json
from pathlib import Path

from textual.theme import Theme

# Directory containing built-in theme JSON files
BUILTIN_THEMES_DIR = Path(__file__).parent / "styles" / "themes"

# User themes directory
USER_THEMES_DIR = Path.home() / ".null" / "themes"


def _load_theme_from_dict(data: dict, name_fallback: str = "") -> Theme | None:
    """Create a Theme from a dictionary."""
    try:
        name = data.get("name", name_fallback)
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


def _load_theme_file(path: Path) -> tuple[Theme | None, dict | None]:
    """Load a theme from a JSON file.

    Returns: (Theme object, raw dict data)
    """
    try:
        with open(path) as f:
            data = json.load(f)
        theme = _load_theme_from_dict(data, path.stem)
        return theme, data
    except Exception:
        return None, None


def _load_builtin_themes() -> dict[str, Theme]:
    """Load built-in themes from styles/themes/*.json"""
    themes: dict[str, Theme] = {}

    if not BUILTIN_THEMES_DIR.exists():
        return themes

    for theme_file in BUILTIN_THEMES_DIR.glob("*.json"):
        theme, _ = _load_theme_file(theme_file)
        if theme:
            themes[theme.name] = theme

    return themes


def _ensure_user_themes_dir() -> None:
    """Create user themes directory and copy built-in themes if needed."""
    if not USER_THEMES_DIR.exists():
        USER_THEMES_DIR.mkdir(parents=True, exist_ok=True)

    # Check if we need to copy built-in themes
    marker_file = USER_THEMES_DIR / ".initialized"
    if marker_file.exists():
        return

    # Copy built-in themes to user directory for customization
    if BUILTIN_THEMES_DIR.exists():
        for theme_file in BUILTIN_THEMES_DIR.glob("*.json"):
            dest = USER_THEMES_DIR / theme_file.name
            if not dest.exists():
                try:
                    # Read and rewrite to ensure consistent formatting
                    with open(theme_file) as f:
                        data = json.load(f)
                    # Add a hint that this is a copy
                    data["_note"] = "Copy of built-in theme. Edit freely!"
                    with open(dest, "w") as f:
                        json.dump(data, f, indent=2)
                except Exception:
                    pass

    # Create example custom theme
    _create_example_theme(USER_THEMES_DIR)

    # Mark as initialized
    try:
        marker_file.write_text("initialized")
    except Exception:
        pass


def _create_example_theme(themes_dir: Path) -> None:
    """Create an example custom theme file for users."""
    example = {
        "name": "my-custom-theme",
        "description": "Example custom theme - rename and edit!",
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
        "boost": "#4ECDC4",
        "luminosity_spread": 0.12,
        "text_alpha": 0.92,
        "variables": {
            "block-cursor-background": "#FF6B6B",
            "block-cursor-foreground": "#1A1A2E",
        },
    }

    example_path = themes_dir / "my-custom-theme.json.example"
    try:
        with open(example_path, "w") as f:
            json.dump(example, f, indent=2)
    except Exception:
        pass


def load_user_themes() -> dict[str, Theme]:
    """Load custom themes from ~/.null/themes/*.json"""
    themes: dict[str, Theme] = {}

    _ensure_user_themes_dir()

    for theme_file in USER_THEMES_DIR.glob("*.json"):
        # Skip example files
        if theme_file.name.endswith(".example"):
            continue
        theme, _ = _load_theme_file(theme_file)
        if theme:
            themes[theme.name] = theme

    return themes


def get_builtin_themes() -> dict[str, Theme]:
    """Get only built-in themes."""
    return _load_builtin_themes()


def get_all_themes() -> dict[str, Theme]:
    """Get all themes (built-in + user).

    User themes override built-in themes with the same name.
    """
    # Start with built-in themes
    themes = _load_builtin_themes()

    # User themes override built-in
    themes.update(load_user_themes())

    return themes


# Fallback themes if JSON files are missing
_FALLBACK_NULL_DARK = Theme(
    name="null-dark",
    dark=True,
    primary="#00D4FF",
    secondary="#BD00FF",
    accent="#00FF88",
    foreground="#E0E6F0",
    background="#08090D",
    surface="#0E1018",
    panel="#151822",
    success="#00FF88",
    warning="#FFB800",
    error="#FF3366",
    boost="#00FFCC",
    luminosity_spread=0.18,
    text_alpha=0.95,
)


def get_all_themes_with_fallback() -> dict[str, Theme]:
    """Get all themes with fallback if no themes found."""
    themes = get_all_themes()

    # Ensure at least null-dark exists
    if not themes:
        themes["null-dark"] = _FALLBACK_NULL_DARK

    return themes


# For backwards compatibility
BUILTIN_THEMES = get_builtin_themes() or {"null-dark": _FALLBACK_NULL_DARK}
THEMES = BUILTIN_THEMES
