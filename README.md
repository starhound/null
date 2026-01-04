
# Null Terminal

> **"Shell in the Void."**

> [!NOTE]
> Null Terminal is under active development. Features and APIs may change.

Null is a next-generation TUI (Terminal User Interface) designed for the modern AI-integrated workflow. Built on [Textual](https://textual.textualize.io/), it blends the raw power of the command line with the intelligence of LLMs, all wrapped in a sleek, cyber-noir aesthetic.

<p align="center">
  <img src="docs/null_graphic.png" alt="Null Terminal" width="600">
</p>

## 📖 Documentation

-   [**User Guide**](docs/user/README.md): Comprehensive guide with commands, shortcuts, and configuration.
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

### Install via pipx

```bash
pipx install null-terminal
null
```

### Run with Docker

```bash
docker run -it ghcr.io/starhound/null:latest
```

### From Source (Development)

```bash
git clone https://github.com/starhound/null.git
cd null
uv sync
uv run main.py
```

### Configure

Type `/settings` to configure your AI provider, or press `F3` to change theme.

## 🎬 Demo

<p align="center">
  <img src="docs/demo.gif" alt="Null Terminal Demo" width="700">
</p>

## ⌨️ Key Controls

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` | Toggle AI/CLI mode |
| `Ctrl+P` | Command palette |
| `Ctrl+C` | Cancel or quit |
| `F1` | Help screen |
| `F2` | Select model |
| `F3` | Change theme |
| `F4` | Select provider |

See [full shortcut reference](docs/user/shortcuts.md) for more.

---

<p align="center">
  Built with 🖤 by Starhound
</p>
