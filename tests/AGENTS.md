# TESTS KNOWLEDGE BASE

**Context:** Pytest, Asyncio, Textual Pilot, AI Mocking

## OVERVIEW
Comprehensive test suite covering unit logic and full TUI integration for the Null Terminal.

## STRUCTURE
```
tests/
├── conftest.py            # Global fixtures (mock_home, temp_dir, mock_storage)
├── integration/           # TUI-level tests using Textual's Pilot
│   ├── conftest.py        # App-specific fixtures (running_app, mock_ai_components)
│   ├── test_app.py        # Lifecycle & Orchestration
│   └── test_input.py      # Input handling & Slash commands
└── unit/                  # Isolated logic tests
    ├── ai/                # LLM providers & thinking logic
    ├── config/            # Settings, Storage, Keys
    ├── models/            # State & Schema validation
    └── tools/             # Built-in and registry logic
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **New UI Test** | `tests/integration/` | Use `running_app` fixture |
| **New AI Mock** | `tests/integration/conftest.py` | Add to `mock_ai_components` |
| **Global Fixture** | `tests/conftest.py` | Shared across unit & integration |
| **Tool/Prompt Test** | `tests/unit/` | Fast, no-UI logic tests |

## CONVENTIONS
*   **Fixtures**:
    *   `mock_home`: MANDATORY to protect user `~/.null` (uses temp dir).
    *   `running_app`: Provides a `pilot` and `app` instance for TUI tests.
    *   `mock_ai_components`: Automatically mocks AI/MCP to prevent network calls.
*   **Pilot Pattern**:
    *   Use `await pilot.press("...")` for key input.
    *   Use `await pilot.pause()` after state changes or input.
    *   Use `app.query_one()` to verify widget state.
*   **Asyncio**: All TUI tests must be `async` and use `@pytest.mark.asyncio`.

## ANTI-PATTERNS
*   **No Real Network**: NEVER allow network calls to LLM providers or MCP servers.
*   **No Dirty Home**: NEVER read/write to `~/.null` or `~/.nullrc`.
*   **No Synchronous Pilot**: Avoid `time.sleep()`; use `await pilot.pause()` or `asyncio.sleep()`.
*   **No Hardcoded Paths**: Always use fixtures like `temp_dir` or `mock_home`.
