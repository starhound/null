# Null Terminal

**Null** is a modern, block-based terminal emulator and shell wrapper built with Python and Textual. It re-imagines the command-line interface by separating interactions into distinct "Blocks", decoupling input from output, and integrating "Bring Your Own Model" (BYOM) AI directly into the workflow.

## ✨ Features

*   **Block-Based UI**: Commands and outputs are isolated in scrollable blocks.
*   **Detached Input**: Type without your cursor getting lost in streaming output.
*   **AI Integration**: Seamlessly switch between local (Ollama, LM Studio) and cloud (OpenAI, Azure, Bedrock, xAI) models.
*   **Secure Storage**: Configuration and history uses SQLite, with sensitive keys encrypted via OS Keyring.
*   **Command Palette**: Access themes, models, and help via `Ctrl+P`.
*   **Cross-Platform**: Runs on Windows, Linux, and macOS.

## 🚀 Installation

Requires Python 3.11+.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/starhound/null.git
    cd null
    ```

2.  **Install dependencies** (using `uv` is recommended):
    ```bash
    uv sync
    # OR
    pip install -r requirements.txt
    ```

3.  **Run the application**:
    ```bash
    uv run main.py
    # OR
    python main.py
    ```

## 🎮 Usage

### Basic Commands
Type any shell command (`ls`, `echo`, `git status`) and press **Enter**.

### AI Integration
Null Terminal supports multiple AI providers.

1.  **Select a Provider**:
    *   Command: `/provider`
    *   Palette: `Ctrl+P` -> "Select Provider"
    *   Shortcut: `F4`

2.  **Configure**:
    *   Enter your **API Key** or **Endpoint URL** in the popup form.

3.  **Select a Model**:
    *   Command: `/model` or `/model <provider> <name>`
    *   Palette: `Ctrl+P` -> "Select Model"
    *   Shortcut: `F2`

### Key Bindings

| Key | Action |
| :--- | :--- |
| `Ctrl+C` | Quit Application |
| `Ctrl+L` | Clear History (Visual) |
| `Ctrl+P` | Open Command Palette |
| `F1` | Show Help |
| `F2` | Select AI Model |
| `F3` | Change Theme |
| `F4` | Configure AI Provider |
| `Up/Down` | Cycle Command History |

### Slash Commands

*   `/help`: Show available commands.
*   `/theme <name>`: Switch theme (e.g., `monokai`, `dracula`).
*   `/provider`: Configure AI provider.
*   `/model`: List/Select AI models.
*   `/clear`: Clear the viewport.
*   `/quit`: Exit.

## 🛠️ Configuration

Configuration is stored in `~/.null/null.db`.
*   **Sensitive Data**: API keys are encrypted using `cryptography` + system keyring (or a secure local key file fallback).
*   **History**: Command history is persisted to the database.

## 🤝 Contributing

PRs are welcome! Please ensure you use `uv` for dependency management.

1.  Fork the repo.
2.  Create a feature branch.
3.  Submit a Pull Request.

## 📄 License

MIT License.
