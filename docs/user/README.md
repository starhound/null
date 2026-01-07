# Null Terminal User Guide

Null Terminal is a block-based terminal emulator with integrated multi-provider AI chat and autonomous agent capabilities.

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

### Agent Mode
Enable autonomous task execution where the AI can:
- Execute shell commands
- Read and write files
- Use MCP tools
- Chain multiple operations together

Toggle with `/agent` command.

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

## Essential Commands

| Command | Description |
|---------|-------------|
| `/ai` | Toggle AI mode |
| `/agent` | Toggle agent mode |
| `/model` | Select AI model |
| `/provider` | Configure AI provider |
| `/config` | Open settings |
| `/help` | Show help |
| `/clear` | Clear history |
| `/export` | Export conversation |
| `/todo` | Open task dashboard |
| `/prompts` | Manage system prompts |

## Documentation

- [Commands Reference](commands.md) - All slash commands
- [Keyboard Shortcuts](shortcuts.md) - All keyboard shortcuts
- [AI Providers](providers.md) - Setting up AI providers
- [Configuration](configuration.md) - Settings and options
- [MCP Servers](mcp.md) - Model Context Protocol setup
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
