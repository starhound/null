"""Custom themes for Null terminal."""

from textual.theme import Theme


# Sleek dark theme inspired by modern terminals like Warp and Claude CLI
NULL_DARK = Theme(
    name="null-dark",
    dark=True,
    primary="#6B8AFF",        # Soft blue - primary accent
    secondary="#8B5CF6",      # Purple - secondary accent
    accent="#38BDF8",         # Sky blue - highlights
    foreground="#E2E8F0",     # Slate 200 - main text
    background="#0F1219",     # Deep navy-black
    surface="#1A1F2E",        # Elevated surface
    panel="#232938",          # Panel/card background
    success="#34D399",        # Emerald - success states
    warning="#FBBF24",        # Amber - warnings
    error="#F87171",          # Red 400 - errors
    boost="#2DD4BF",          # Teal - special highlights
    luminosity_spread=0.12,   # Subtle luminosity variation
    text_alpha=0.92,          # Slightly softer text
    variables={
        "block-cursor-background": "#6B8AFF",
        "block-cursor-foreground": "#0F1219",
        "scrollbar-background": "#1A1F2E",
        "scrollbar": "#3B4559",
        "scrollbar-hover": "#4B5569",
    },
)

# Warmer variant with orange/amber accents (Claude-like)
NULL_WARM = Theme(
    name="null-warm",
    dark=True,
    primary="#F59E0B",        # Amber - primary accent
    secondary="#EC4899",      # Pink - secondary accent
    accent="#FB923C",         # Orange - highlights
    foreground="#F1F5F9",     # Slate 100 - main text
    background="#0C0A09",     # Stone 950 - deep warm black
    surface="#1C1917",        # Stone 900 - elevated surface
    panel="#292524",          # Stone 800 - panel background
    success="#4ADE80",        # Green 400 - success
    warning="#FACC15",        # Yellow 400 - warnings
    error="#FB7185",          # Rose 400 - errors
    boost="#2DD4BF",          # Teal - special highlights
    luminosity_spread=0.12,
    text_alpha=0.92,
    variables={
        "block-cursor-background": "#F59E0B",
        "block-cursor-foreground": "#0C0A09",
    },
)

# Minimal monochrome with subtle blue tints
NULL_MONO = Theme(
    name="null-mono",
    dark=True,
    primary="#94A3B8",        # Slate 400 - subtle primary
    secondary="#64748B",      # Slate 500 - secondary
    accent="#7DD3FC",         # Sky 300 - rare highlights
    foreground="#CBD5E1",     # Slate 300 - main text
    background="#020617",     # Slate 950 - deepest black
    surface="#0F172A",        # Slate 900 - surface
    panel="#1E293B",          # Slate 800 - panels
    success="#86EFAC",        # Green 300
    warning="#FDE047",        # Yellow 300
    error="#FCA5A5",          # Red 300
    boost="#67E8F9",          # Cyan 300
    luminosity_spread=0.08,   # Very subtle variation
    text_alpha=0.88,          # Softer text
)

# Light theme option
NULL_LIGHT = Theme(
    name="null-light",
    dark=False,
    primary="#2563EB",        # Blue 600
    secondary="#7C3AED",      # Violet 600
    accent="#0891B2",         # Cyan 600
    foreground="#1E293B",     # Slate 800 - dark text
    background="#FAFBFC",     # Near white
    surface="#FFFFFF",        # Pure white cards
    panel="#F1F5F9",          # Slate 100 - panels
    success="#059669",        # Emerald 600
    warning="#D97706",        # Amber 600
    error="#DC2626",          # Red 600
    boost="#0D9488",          # Teal 600
    luminosity_spread=0.15,
    text_alpha=0.95,
)


# All custom themes
THEMES = {
    "null-dark": NULL_DARK,
    "null-warm": NULL_WARM,
    "null-mono": NULL_MONO,
    "null-light": NULL_LIGHT,
}
