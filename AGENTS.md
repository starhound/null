# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-05
**Context:** Python 3.12+, Textual TUI, AsyncIO, AI Integration

## OVERVIEW
Null Terminal is a cyber-noir TUI that blends a standard shell with AI capabilities (Ollama, OpenAI, Anthropic). Built on **Textual**, it uses a "Block" architecture where command outputs and AI responses are distinct, interactive widgets.

## STRUCTURE
```
.
├── main.py            # Entry point (uv run main.py)
├── app.py             # NullApp orchestrator & event loop
├── nullrc.py          # Local config manager (.nullrc)
├── executor.py        # PTY/Process execution engine
├── ai/                # AI Providers (Ollama, OpenAI, etc.)
├── commands/          # Slash command implementations
├── config/            # Settings, Storage (SQLite), Encryption
├── handlers/          # Input & Execution logic (Complexity Hotspot)
├── screens/           # Modal UI screens (Settings, Providers)
├── styles/            # TCSS stylesheets (main.tcss)
├── widgets/           # UI Components
│   └── blocks/        # Core Block architecture
└── tests/             # Pytest suite (Unit + Integration)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **New Slash Command** | `commands/` | Prefix `cmd_`, register in `handler.py` |
| **New AI Provider** | `ai/` | Inherit `LLMProvider`, register in `factory.py` |
| **UI Styling** | `styles/main.tcss` | Use variables (`$primary`), avoid hardcoding |
| **AI logic/flow** | `handlers/execution.py` | Tool calling loop, streaming, agent mode |
| **Configuration** | `config/` | `ai.py` (settings), `storage.py` (DB) |
| **Terminal Compat** | `utils/terminal.py` | Adapters for Kitty, WezTerm, etc. |

## CODE MAP (Key Symbols)
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `NullApp` | Class | `app.py` | Main TUI application, global state |
| `LLMProvider` | ABC | `ai/base.py` | Base for all AI integrations |
| `BaseBlockWidget` | Class | `widgets/blocks/base.py` | Parent of all output blocks |
| `ExecutionHandler` | Class | `handlers/execution.py` | Manages AI/Command execution flow |
| `SlashCommandHandler`| Class | `commands/handler.py` | Routes `/commands` to methods |

## CONVENTIONS
*   **Flat Layout**: No `src/` directory. Root contains app modules.
*   **Async First**: Extensive use of `asyncio`. Tests use `pytest-asyncio`.
*   **Textual Reactivity**: UI state driven by `reactive` properties.
*   **Tool Use**: AI tools defined in `commands/mcp.py` or internal handlers.
*   **Testing**: `mock_home` fixture is MANDATORY to protect user config.

## ANTI-PATTERNS (THIS PROJECT)
*   **No Global Config**: Do NOT touch `~/.null` in tests; use fixtures.
*   **No Synchronous AI**: All AI calls must be async/streaming.
*   **No Direct Styles**: Do NOT hardcode colors in Python; use TCSS classes.
*   **No Print**: Use `self.notify()` or `self.log()`; stdout is captured.
*   **No NPM**: Remove legacy `npm` references from `nullrc.py`.

## COMMANDS
```bash
uv run main.py                  # Run App
uv run pytest tests/            # Run Tests
uv run ruff check .             # Lint
uv run textual console          # Debug Console
```

## NOTES
*   `handlers/execution.py` is the complexity hotspot (>1200 lines). Modify with care.
*   Integration tests use `pilot` pattern (Textual) and require `mock_ai_components`.
