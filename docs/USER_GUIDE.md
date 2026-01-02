# User Guide

Welcome to Null Terminal. This guide covers everything you need to know to navigate, configure, and master the terminal.

## Keybindings

### Navigation
| Key | Action |
| :--- | :--- |
| `Ctrl+P` | Focusing on Input Area (General) |
| `PageUp` / `PageDown` | Scroll conversation history |
| `Home` / `End` | Jump to top/bottom of history |
| `Ctrl+C` | Cancel current generation or clear input |

### Input Area
| Key | Action |
| :--- | :--- |
| `Enter` | Submit command or prompt |
| `Shift+Enter` | Insert newline (multiline mode) |
| `Up` / `Down` | Cycle through command history |
| `Tab` | Autocomplete command or file path |

### Application
| Key | Action |
| :--- | :--- |
| `F1` | Open Help screen |
| `F2` | Open Model Selector |
| `F3` | Open Settings |
| `Ctrl+D` | Quit application |

## Slash Commands

Commands are special instructions starting with `/`.

| Command | Description |
| :--- | :--- |
| `/status` | Show current AI provider, model, and session costs |
| `/clear` | Clear conversation history |
| `/model` | Open model selection menu |
| `/theme` | Open theme selection menu |
| `/help` | Show help screen |
| `/settings` | Open configuration screen |
| `/add <file>` | Add file content to AI context |
| `/drop <file>` | Remove file from AI context |
| `/copy` | Copy last AI response to clipboard |
| `/exit` | Quit the application |

## AI Configuration

### Selecting a Model
Press `F2` or type `/model` to open the Model Selector.
-   **Locally Detected**: Models from LM Studio or Ollama running locally.
-   **Cloud Providers**: OpenAI, Anthropic, etc. (requires API key).

### Context Management
Null Terminal automatically manages your context window.
-   **Auto-Context**: It creates a "smart context" based on your recent activities.
-   **Explicit Context**: Use `/add path/to/file.py` to ensure the AI "sees" a specific file.

## Settings

Access via `F3` or `/settings`.

### Appearance
-   **Theme**: Choose from built-in themes (Null Dark, Monokai, Dracula, etc.).
-   **Font**: Change font family and size (if supported by your terminal).
    *   *Note: Some terminals like VS Code Integrated Terminal manage fonts externally.*
-   **UI Options**: Toggle timestamps, line numbers, etc.

### AI
-   **Provider**: efficiency vs intelligence? Choose your default.
-   **Context Window**: Manually limit token usage (default: 4096).
-   **Temperature**: Adjust creativity (0.0 = deterministic, 1.0 = creative).

### Terminal
-   **Shell**: Set your preferred shell (bash, zsh, fish).
-   **Scrollback**: Limit history lines for performance.

## Tips & Tricks

-   **Chain of Thought**: Models like DeepSeek-R1 will show a "Thinking..." block. Click to expand and see the reasoning process.
-   **Code Execution**: When the AI generates shell commands, you can click "Run" to execute them directly in the terminal.
-   **Clipboard**: Use the copy button on any code block to grab the snippet instantly.
