
# Null Terminal

> **"Shell in the Void."**

Null is a next-generation TUI (Terminal User Interface) designed for the modern AI-integrated workflow. Built on [Textual](https://textual.textualize.io/), it blends the raw power of the command line with the intelligence of LLMs, all wrapped in a sleek, cyber-noir aesthetic.

<p align="center">
  <img src="docs/null_graphic.png" alt="Null Terminal" width="600">
</p>

## 📖 Documentation

-   [**User Guide**](docs/USER_GUIDE.md): Keybindings, commands, and configuration.
-   [**Architecture**](docs/ARCHITECTURE.md): System design, event loops, and state management.
-   [**Development**](docs/DEVELOPMENT.md): Setup, contributing, and extending the codebase.

## ✨ Features

-   **AI Integration**: Seamless chat with OpenAI, Ollama, LM Studio, and more.
-   **Input Modes**: Switch between shell and AI modes with ease.
-   **Context Awareness**: Smartly manages files and conversation history.
-   **Local Tool Use**: AI can run commands, read files, and analyze code directly.
-   **Chain of Thought**: Visualize the reasoning process of advanced models (e.g., DeepSeek R1).
-   **Cyber-Noir Aesthetics**: Beautiful, customizable themes and animations.

## 🚀 Quick Start

1.  **Install dependencies**:
    ```bash
    uv sync
    ```

2.  **Run the terminal**:
    ```bash
    uv run main.py
    ```

3.  **Configure**:
    Press `F3` or type `/settings` to configure your AI provider and theme.

## ⌨️ Key Controls

-   `Ctrl+P`: Focus Prompt
-   `F1`: Help
-   `F2`: Model Selection
-   `F3`: Settings
-   `Ctrl+D`: Quit

---

<p align="center">
  Built with 🖤 by Starhound
</p>
