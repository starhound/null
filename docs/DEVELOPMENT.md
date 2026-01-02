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

-   `app.py`: The heart of the TUI.
-   `styles/`: Contains all TCSS (Textual CSS) files.
-   `widgets/`: Custom widget implementations.
-   `ai/`: AI logic and provider adapters.

## How-To Guides

### 1. Adding a New Slash Command

Commands are defined in `commands/core.py`.

1.  Open `commands/core.py`.
2.  Add a method to the `CommandSet` class.
3.  Decorate it with `@command("command_name")`.

```python
class CoreCommands:
    # ...
    async def cmd_hello(self, args: str):
        """Say hello to the user."""
        self.app.push_message(f"Hello, {args}!")
```

### 2. Adding a New AI Provider

1.  Create a new file in `ai/` (e.g., `ai/myprovider.py`).
2.  Inherit from `AIProvider`.
3.  Implement the required methods (`stream_chat`, `list_models`).
4.  Register it in `ai/factory.py`.

```python
from .base import AIProvider

class MyProvider(AIProvider):
    async def stream_chat(self, messages, **kwargs):
        # Implementation...
        yield chunk
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
-   **Log to file**: Python's `logging` module is configured to write to `null.log` (if enabled).
-   **Textual Devtools**: Run `textual console` in one terminal, and `uv run textul run --dev main.py` in another to see a live DOM tree and log output.
