# SCREENS KNOWLEDGE BASE

**Generated:** 2026-01-05
**Context:** Textual ModalScreens, User Configuration, Dynamic UI

## OVERVIEW
Specialized domain for transient modal interfaces managing application state, user preferences, and interactive dialogs.

## STRUCTURE
```
screens/
├── base.py           # Shared imports and widget exports for screens
├── config.py         # Tabbed settings (Appearance, Editor, Terminal, AI)
├── providers.py      # AI provider selection and configuration status
├── provider.py       # Detailed per-provider setup (API keys, endpoints)
├── mcp.py            # Model Context Protocol server management
├── selection.py      # Generic searchable selection lists (e.g., model picker)
├── confirm.py        # Generic confirmation dialogs
└── help.py           # Shortcut reference and documentation viewer
```

## WHERE TO LOOK
| Feature | Location | Role |
|---------|----------|------|
| **Global Settings** | `config.py` | Main configuration UI (Tabs: AI, UI, Editor) |
| **AI Model Picker** | `selection.py` | Searchable list for `F2` model selection |
| **API Key Setup** | `provider.py` | Interactive forms for provider credentials |
| **Tool/MCP Config** | `mcp.py` | Management of MCP server connections |
| **SSH/Remote** | `ssh.py` | Remote session management and setup |

## CONVENTIONS (ModalScreen)
*   **Inheritance**: All modules must inherit from `ModalScreen` or a screen-specific base.
*   **Standard Bindings**: `escape` to dismiss/cancel, `enter` or `ctrl+s` to confirm/save.
*   **Transient State**: Screens should be "pure" views; they fetch data in `__init__` and `dismiss()` results.
*   **Base Imports**: Import common Textual widgets via `from .base import ...` for uniformity.
*   **Row Patterns**: Use helper methods (e.g., `_setting_row`) to maintain consistent horizontal layouts.

## ANTI-PATTERNS
*   **No Business Logic**: Keep execution logic in `handlers/`; screens only collect/display data.
*   **No Direct Styles**: Do NOT use `styles.color` in Python; apply TCSS classes from `main.tcss`.
*   **Avoid Fat Compose**: Extract complex sub-sections into private `_render_*` methods.
*   **No Global Config Write**: Screens should return data via `dismiss()`, letting the caller handle persistence.
*   **Blocking I/O**: Use `async` handlers for any network or disk operations during screen interaction.
