# Null Terminal

> **"Shell in the Void."**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-blueviolet)](https://textual.textualize.io/)

!!! note "Status"
    Null Terminal is under active development. Features and APIs are evolving rapidly.

**Null Terminal** is a next-generation TUI designed for the modern AI-integrated workflow. It bridges the gap between manual shell operations and autonomous agent workflows, wrapped in a sleek, cyber-noir aesthetic.

<p align="center">
  <img src="demo.gif" alt="Null Terminal Demo" width="800">
</p>

---

## The Null Philosophy

We believe the terminal shouldn't just be a text buffer—it should be an intelligent workspace.

-   **Hybrid Workflow**: Seamlessly switch between manual CLI control and AI assistance.
-   **Context Aware**: The AI sees what you see—output, errors, and file content.
-   **Agentic Power**: Delegate complex, multi-step tasks to autonomous agents.
-   **Extensible**: Connect to any external service via the Model Context Protocol (MCP).

---

## Key Capabilities

<div class="grid cards" markdown>

-   **🧠 Multi-Provider AI**
    ---
    Connect to your preferred intelligence.
    
    *   **Local**: Ollama, LM Studio, Llama.cpp (Privacy-first, free)
    *   **Cloud**: OpenAI, Anthropic, Google Gemini, Azure, Bedrock, Groq
    *   **Reasoning**: Visualize the thinking process of advanced models.

-   **🤖 Autonomous Agents**
    ---
    Turn instructions into action.
    
    *   **Agent Mode**: Give high-level goals like "Refactor auth module".
    *   **Planning Mode**: Review execution plans before code changes.
    *   **Background Tasks**: Spawn agents to work while you use the shell.

-   **🔌 MCP Integration**
    ---
    Extend your terminal's reach.
    
    *   **100+ Integrations**: Postgres, GitHub, Slack, Linear, etc.
    *   **Zero Config**: Install directly from the built-in catalog.
    *   **Tool Use**: AI naturally uses tools to fetch data and act.

-   **🛠️ Ops & Admin Tools**
    ---
    Built for engineers.
    
    *   **Git-Native**: Auto-commit, diffs, and context management.
    *   **Task Management**: Integrated `/todo` dashboard.
    *   **Session Management**: Save, load, and share workspaces.

</div>

---

## Quick Start

### Installation

=== "pipx (Recommended)"
    ```bash
    pipx install null-terminal
    null
    ```

=== "Docker"
    ```bash
    docker run -it --rm ghcr.io/starhound/null-terminal:latest
    ```

=== "Source"
    ```bash
    git clone https://github.com/starhound/null-terminal.git
    cd null-terminal
    uv sync
    uv run main.py
    ```

See the [Installation Guide](user/installation.md) for detailed instructions.

### First Steps

1.  **Configure AI**: Press `F3` or type `/settings` to set up your provider.
2.  **Select Model**: Press `F2` or type `/model` to choose your LLM.
3.  **Toggle Mode**: Press `Ctrl+Space` to switch between CLI (manual) and AI (chat) modes.

### Common Workflows

**Analyze Logs**
> "Check /var/log/syslog for the last 10 errors and summarize them."

**Refactor Code**
> "Read src/main.py and refactor the `process_data` function to be async."

**Research & Implementation**
> `/agent` "Research the best Python library for PDF extraction, then create a script to extract text from `doc.pdf`."

---

## Documentation Structure

<div class="grid cards" markdown>

-   [:material-book-open-page-variant: User Guide](user/index.md)
    ---
    Comprehensive manual for all features, installation, and configuration.

-   [:material-slash-forward: Command Reference](user/commands.md)
    ---
    Dictionary of all slash commands, shortcuts, and parameters.

-   [:material-server-network: MCP Catalog](mcp-servers.md)
    ---
    Browse and configure supported external tools and servers.

-   [:material-domain: Architecture](ARCHITECTURE.md)
    ---
    Deep dive into the system design, components, and data flow.

</div>

---

## Contributing

Null is open source and community-driven.

-   [Contribution Guide](contributing.md)
-   [Feature Roadmap](roadmap.md)
-   [GitHub Repository](https://github.com/starhound/null-terminal)

<p align="center">
  Built with 🖤 by <a href="https://github.com/starhound">Starhound</a>
</p>
