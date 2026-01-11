# Null Terminal User Guide

Null Terminal is a block-based terminal emulator with integrated multi-provider AI chat and autonomous agent capabilities. It bridges the gap between traditional CLI tools and modern AI assistance.

## Quick Start

```bash
# Run the application
uv run main.py

# Or if installed
null-terminal
```

## Core Concepts

### Block-Based Interface
Every command and AI interaction creates a distinct "block" in the terminal:
- **Command Blocks**: Shell command execution with output
- **AI Response Blocks**: Chat responses with metadata (tokens, cost)
- **Agent Blocks**: Multi-step autonomous task execution
- **System Blocks**: Status messages and notifications

### Two Modes
- **CLI Mode** (default): Execute shell commands directly
- **AI Mode**: Chat with your configured AI provider

Toggle between modes with `Ctrl+Space` or `/ai`.

### Agent Capabilities
Enable autonomous task execution where the AI can:
- Execute shell commands and file operations
- **Plan Complex Tasks**: Create roadmaps with `/plan`
- **Git Integration**: Auto-commit changes with generated messages
- **Use MCP Tools**: Connect to external services (databases, cloud, etc.)
- **Orchestrate Workflows**: Run multi-agent tasks

Toggle agent mode with `/agent`.

## Essential Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` | Toggle AI/CLI mode |
| `Ctrl+C` | Cancel operation or quit |
| `Ctrl+P` | Command palette |
| `F1` | Help screen |
| `F2` | Select AI model |
| `F3` | Change theme |
| `Escape` | Cancel current operation |

## Feature Highlights

- **Planning Mode**: Review and approve AI plans before execution. [Learn more](planning.md)
- **Git Operations**: Seamless integration with git workflows. [Learn more](git.md)
- **Workflows & Agents**: Save sessions and run background tasks. [Learn more](workflow.md)
- **MCP Integration**: Connect 100+ external tools. [Learn more](mcp.md)

## Documentation

- [Commands Reference](commands.md) - All slash commands
- [Keyboard Shortcuts](shortcuts.md) - All keyboard shortcuts
- [AI Providers](providers.md) - Setting up AI providers
- [Planning Mode](planning.md) - Task planning and execution
- [Git Operations](git.md) - Version control integration
- [Workflows & Agents](workflow.md) - Templates and multi-agent tasks
- [MCP Servers](mcp.md) - Model Context Protocol setup
- [Configuration](configuration.md) - Settings and options
- [Themes](themes.md) - Customizing appearance
- [Tools & Agent Mode](tools.md) - AI tool use
- [Sessions](sessions.md) - Saving and loading sessions

## File Locations

| Path | Purpose |
|------|---------|
| `~/.null/config.json` | Settings |
| `~/.null/null.db` | Database (sessions, API keys) |
| `~/.null/mcp.json` | MCP server configs |
| `~/.null/themes/` | Custom themes |
| `~/.null/prompts/` | Custom system prompts |
| `~/.null/todos.json` | Task list |
