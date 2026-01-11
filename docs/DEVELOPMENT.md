# Development Guide

This guide is for developers who want to contribute to Null Terminal or extend its functionality.

## Development Environment Setup

We use `uv` for dependency management.

1.  **Install uv**:
    ```bash
    pip install uv
    ```

2.  **Install dependencies**:
    ```bash
    uv sync
    ```

3.  **Run the application**:
    ```bash
    uv run main.py
    ```

4.  **Run logic tests** (if available):
    ```bash
    uv run pytest
    ```

## Project Structure

```
null/
├── app.py              # Main NullApp class - TUI orchestrator
├── main.py             # CLI entry point
├── models.py           # Core data models (BlockState, BlockType)
├── context.py          # Context window management
├── executor.py         # PTY/Process execution engine
├── nullrc.py           # Local config manager (.nullrc)
├── themes.py           # Theme definitions and loading
│
├── ai/                 # AI Provider Layer
│   ├── base.py         # LLMProvider ABC, StreamChunk, pricing
│   ├── factory.py      # Provider registry and instantiation
│   ├── manager.py      # Multi-provider lifecycle management
│   ├── thinking.py     # Reasoning extraction strategies
│   ├── rag.py          # RAG/Vector store implementation
│   └── [providers].py  # Individual provider implementations
│
├── commands/           # Slash Command System
│   ├── handler.py      # Command routing and registry
│   ├── base.py         # CommandMixin utilities
│   └── [modules].py    # Command implementations by domain
│
├── handlers/           # Execution Handlers
│   ├── input.py        # Input routing (AI vs CLI vs Command)
│   ├── ai_executor.py  # AI streaming, tool calling, agent loops
│   └── cli_executor.py # Shell command execution
│
├── managers/           # State Managers
│   ├── agent.py        # Agent session lifecycle
│   ├── branch.py       # Conversation branching
│   ├── process.py      # Background process tracking
│   └── recall.py       # History recall/search
│
├── mcp/                # Model Context Protocol
│   ├── manager.py      # Multi-server connection management
│   ├── client.py       # MCP client implementation
│   ├── config.py       # Server configuration
│   └── catalog.py      # MCP server catalog/discovery
│
├── screens/            # Modal UI Screens
├── widgets/            # Reusable UI Components
│   └── blocks/         # Block architecture (Command, AI, Agent)
├── styles/             # TCSS stylesheets
├── tools/              # Built-in tool definitions
├── prompts/            # System prompt management
├── config/             # Settings, storage, encryption
└── tests/              # Test suite (unit + integration)
```

## How-To Guides

### 1. Adding a New Slash Command

Commands are organized into modules in `commands/` and registered in `commands/handler.py`.

**Step 1**: Add the command method to the appropriate module (e.g., `commands/core.py`):

```python
from commands.base import CommandMixin

class CoreCommands(CommandMixin):
    async def cmd_hello(self, args: list[str]):
        """Say hello to the user."""
        name = args[0] if args else "World"
        self.notify(f"Hello, {name}!")
```

**Step 2**: Register the command in `commands/handler.py`:

```python
from .core import CoreCommands

class SlashCommandHandler:
    def __init__(self, app: NullApp):
        self._core = CoreCommands(app)
        
        self._command_registry: dict[str, tuple[Callable, CommandInfo]] = {
            # ... existing commands ...
            "hello": (
                self._core.cmd_hello,
                CommandInfo("hello", "Say hello to the user"),
            ),
        }
```

**Key conventions**:
- Method name must start with `cmd_` prefix
- Handler must be `async` and accept `args: list[str]`
- Use `self.notify()` for transient messages
- Use `self.show_output()` for block-based results
- Add subcommands via `CommandInfo.subcommands` list

### 2. Adding a New AI Provider

1.  Create a new file in `ai/` (e.g., `ai/myprovider.py`).
2.  Inherit from `LLMProvider` (the base class).
3.  Implement required methods: `validate_connection`, `list_models`, and streaming generation.
4.  Register it in `ai/factory.py`.

```python
from collections.abc import AsyncGenerator
from .base import LLMProvider, StreamChunk, Message

class MyProvider(LLMProvider):
    def __init__(self, api_key: str, endpoint: str = "https://api.example.com"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = "default-model"
    
    async def validate_connection(self) -> bool:
        """Check if the provider is reachable."""
        # Return True if connection is valid
        return True
    
    async def list_models(self) -> list[str]:
        """List available models."""
        return ["model-1", "model-2"]
    
    def supports_tools(self) -> bool:
        """Return True if this provider supports tool calling."""
        return True
    
    async def generate(
        self, messages: list[Message], **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completion."""
        # Yield StreamChunk objects with text, tool_calls, usage
        yield StreamChunk(text="Hello!", is_complete=True)
```

**Then register in `ai/factory.py`**:
```python
PROVIDERS = {
    # ... existing providers ...
    "myprovider": {
        "class": MyProvider,
        "name": "My Provider",
        "description": "Custom AI provider",
        "config_fields": ["api_key", "endpoint"],
    },
}
```

### 3. Styling with TCSS

Textual usage TCSS (similar to CSS). Files are located in `styles/`.
-   `main.tcss`: The global stylesheet.
-   Use variables for colors (e.g., `$primary`, `$background`) to support theming.

**Example**:
```css
MyWidget {
    background: $surface;
    border: solid $primary;
    padding: 1;
}
```

## Debugging

Since TUI apps take over the terminal, standard `print()` debugging is difficult.
-   **Use `self.notify("message")`**: Shows a toast notification in the UI.
-   **Use `self.log("message")`**: Logs to Textual's internal logger (visible in devtools).
-   **Log to file**: Python's `logging` module is configured to write to `null.log` (if enabled).
-   **Textual Devtools**: Run `textual console` in one terminal, and `uv run textual run --dev main.py` in another to see a live DOM tree and log output.

## Testing

We use pytest with pytest-asyncio for testing. The test suite includes both unit tests and integration tests.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/unit/ai/test_factory.py

# Run integration tests only
uv run pytest tests/integration/
```

### Test Fixtures

Key fixtures defined in `tests/conftest.py`:

| Fixture | Purpose |
|---------|---------|
| `mock_home` | **MANDATORY** - Protects user `~/.null` by using temp directory |
| `mock_storage` | Creates test database in temp directory |
| `temp_workdir` | Temp directory set as current working directory |
| `mock_llm_provider` | Mock AI provider for testing |

### Writing Tests

```python
import pytest

@pytest.mark.asyncio
async def test_my_feature(mock_home, mock_storage):
    """Test with protected home directory."""
    # mock_home ensures no real user data is touched
    from config import Config
    config = Config.load_all()
    assert config is not None
```

For integration tests with the TUI, use the `pilot` pattern:

```python
@pytest.mark.asyncio
async def test_app_interaction(mock_home):
    from app import NullApp
    
    app = NullApp()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+p")  # Open command palette
        await pilot.pause()
        assert app.query_one("#command-palette").display == True
```

## Deployment

### Docker

Build and run Null Terminal in a container:

```bash
# Build image
docker build -t null-terminal .

# Run container
docker run -it null-terminal
```

### PIP Installation

You can install the package locally:

```bash
pip install .
```

This creates a `null` (or `null-terminal`) command in your environment:

null
```

### Packaging for Windows

We use **PyInstaller** to freeze the application and **Inno Setup** to create the installer.

1.  **Install Requirements:**
    ```bash
    pip install pyinstaller
    ```
    *Note: You also need Inno Setup installed (iscc).*

2.  **Build Executable:**
    ```bash
    pyinstaller null.spec
    ```
    This creates `dist/null.exe`.

3.  **Create Installer:**
    Compile the `installer/setup.iss` script (if available) or use the Inno Setup Compiler on the generated files.

