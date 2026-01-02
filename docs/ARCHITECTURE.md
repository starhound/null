# Null Terminal Architecture

Null Terminal is a modern, AI-integrated terminal emulator built on the [Textual](https://textual.textualize.io/) framework. It combines a robust TUI with pluggable AI providers to create a seamless "Chat with your Code" experience.

## System Overview

The application is structured around three core pillars:
1.  **The UI Layer** (Textual Widgets & Screens)
2.  **The AI Layer** (Providers & Streaming)
3.  **The State Layer** (Configuration & Context)

### 1. The UI Layer

The `NullApp` class (`app.py`) is the entry point. It orchestrates the main event loop and manages the high-level layout.

#### Core Widgets
-   **`InputArea`**: A specialized input controller that handles user prompts, multiline editing, and command suggestions (`CommandSuggester`).
-   **`HistoryViewport`**: A `VerticalScroll` container that holds the conversation history. It renders `BaseBlockWidget` instances.
-   **`ExecutionWidget`**: A widget for displaying terminal command outputs and code execution results.
-   **`ThinkingWidget`**: A collapsible widget that displays the AI's "Chain of Thought" or reasoning steps.
-   **`AIResponseBlock`**: A complex block that renders Markdown responses, handles syntax highlighting, and allows for editing/retrying.

#### Screens
-   **`MainScreen`**: The primary interface.
-   **`ConfigScreen`**: A modal for settings (`/settings`).
-   **`ModelListScreen`**: A modal for selecting AI models (`/model`).
-   **`HelpScreen`**: A reference for keybindings and commands (`/help`).

### 2. The AI Layer

The AI system is designed to be provider-agnostic.

#### Interfaces
-   **`AIProvider`**: The abstract base class that all providers must implement. It defines methods for `stream_chat`, `list_models`, and `get_model_info`.
-   **`AIFactory`**: A factory pattern (`ai/factory.py`) that instantiates the correct provider based on configuration (e.g., `OllamaProvider`, `OpenAIProvider`, `LMStudioProvider`).

#### Streaming & Tools
Responses are streamed token-by-token. The `AIManager` handles the streaming iterator and parses specific events:
-   **Text Chunks**: Standard partial responses.
-   **Tool Calls**: Requests to execute local tools (e.g., `list_files`, `read_file`).
-   **Thinking process**: Specific to reasoning models (e.g., DeepSeek R1), captured in `<think>` tags and rendered in the `ThinkingWidget`.

### 3. The State Layer

#### Configuration (`settings.py` & `config.py`)
Settings are persisted using a dual approach:
-   **SQLite (`null.db`)**: Stores persistent user preferences (Theme, Provider, API Keys).
-   **`nullrc.py`**: A Python configuration file for defining custom tools, prompts, and advanced logic.

#### Context Management (`context.py`)
The `ContextManager` tracks the "LLM Context Window".
-   **Automatic Context**: It can automatically attach open files or recent command outputs.
-   **Manual Context**: Users can pin files via commands (`/add`).
-   **Pruning**: It intelligently truncates context to fit within the model's token limit.

## Directory Structure

```
null/
├── ai/                 # AI Provider implementations
├── commands/           # Slash command logic (/help, /theme, etc.)
├── handlers/           # Event handlers for specific tasks (tools, execution)
├── mcp/                # Model Context Protocol implementation
├── screens/            # Full-screen UI components
├── styles/             # Textual CSS (TCSS) files
├── utils/              # Helper utilities (terminal detection, formatting)
├── widgets/            # Reusable UI components
├── app.py              # Main application entry point
└── main.py             # CLI launcher
```

## Event Flow Example: User sends a prompt

1.  **Input**: User types "Refactor this file" and hits Enter.
2.  **`InputArea`**: Emits a `Submit` event.
3.  **`NullApp`**: Catches event, creates a `UserMessageBlock` in history.
4.  **`Executor`**:
    *   Captures current context (open files, etc.).
    *   Calls `AIManager.stream_chat(prompt, context)`.
5.  **`AIManager`**:
    *   Selects active provider.
    *   Sends request.
    *   Yields chunks.
6.  **`NullApp`**:
    *   Creates `AIResponseBlock`.
    *   Updates block with streamed chunks in real-time.
    *   If `<think>` tag detected -> Updates `ThinkingWidget`.
    *   If tool call detected -> `ToolHandler` runs tool -> Sends result back to AI.
