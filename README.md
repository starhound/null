# Null Terminal

> **"Shell in the Void."**

> [!NOTE]
> Null Terminal is under active development and not yet officially released. Features and APIs may change.

Null is a next-generation TUI (Terminal User Interface) designed for the modern AI-integrated workflow. Built on [Textual](https://textual.textualize.io/), it blends the raw power of the command line with the intelligence of LLMs, all wrapped in a sleek, cyber-noir aesthetic.

<p align="center">
  <img src="docs/null_graphic.png" alt="Null Terminal" width="600">
</p>

## ✨ Features

### 🧠 Advanced AI Integration
-   **Multi-Provider Support**: Seamlessly switch between Ollama, OpenAI, Anthropic, Bedrock, and more.
-   **Local RAG / Knowledge Base**: Index your local codebase with `/index build` and chat with it using semantic search.
-   **Autonomous Agents**: Toggle `/agent` mode to let the AI execute multi-step tasks, run shell commands, and edit files autonomously.
-   **Local RLLM Training**: Train LLMs from scratch using the "Chat with Code" engine directly in the terminal.
-   **Context Inspector**: View exactly what the AI sees with `/context`.

### 🛠️ Developer Workflow Tools
-   **Task Dashboard**: Integrated kanban-style todo manager (`/todo`) to track your work without leaving the terminal.
-   **Prompt Editor**: Create and manage custom system prompts and personas with a full UI (`/prompts`).
-   **Git Integration**: Real-time git status tracking in the status bar and `/git` command support.
-   **File Explorer**: Interactive sidebar for navigating your project structure.

### 🔌 Extensibility & MCP
-   **MCP Support**: Full support for the **Model Context Protocol**. Connect external tools and resources (databases, APIs) that the AI can use.
-   **Tool Management**: Inspect available tools with `/mcp tools` and manage server connections.

### ⚡ Performance & UX
-   **Block-Based Interface**: Distinct visual blocks for Commands, AI Responses, and System messages.
-   **Smart Autocomplete**: Context-aware suggestions for commands and arguments.
-   **High-Performance PTY**: Low-latency execution for standard shell commands.
-   **Cross-Platform Installer**: Native Windows installer (EXE) and standard pipx support for Linux/Mac.
-   **Interactive TUI Mode**: Full support for running interactive applications like `vim`, `htop`, and `ssh` directly inside blocks.

## 🚀 Quick Start

### 1. Installation

See [**Installation Guide**](docs/user/installation.md) for detailed instructions for Windows, Linux, and Mac.

**Via pipx (Linux/Mac):**
```bash
pipx install null-terminal
null
```

**Windows:**
Download the latest installer from releases or run from source.

### 2. Configuration
On first run, type `/settings` to configure your AI provider (e.g., Ollama URL or OpenAI API Key).

### 3. Basic Usage

| Goal | Command / Action |
|------|------------------|
| **Toggle AI Mode** | Press `Ctrl+Space` or type `/ai` |
| **Run Command** | Just type it (e.g. `ls -la`) |
| **Chat with Code** | `/index build` then ask questions |
| **Manage Tasks** | `/todo` to open dashboard |
| **Change Theme** | `/theme` or press `F3` |

## ⌨️ Key Controls

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` | Toggle Input Mode (CLI ↔ AI) |
| `Ctrl+P` | Command Palette |
| `Ctrl+\` | Toggle File Tree Sidebar |
| `Ctrl+R` | Run History Search |
| `F1` | Help Screen |
| `F2` | Select Model |
| `F3` | Change Theme |

## 📖 Documentation

-   [**User Guide**](docs/user/README.md): Detailed usage instructions.
-   [**Installation**](docs/user/installation.md): Setup for all platforms.
-   [**SSH Guide**](docs/user/ssh.md): Managing remote connections.
-   [**RLLM Training**](docs/user/training.md): Training models from scratch.
-   [**Commands Reference**](docs/user/commands.md): List of all slash commands.
-   [**Architecture**](docs/ARCHITECTURE.md): System design for contributors.

---

<p align="center">
  Built with 🖤 by Starhound
</p>
