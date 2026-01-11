# Command Reference

Null Terminal uses **Slash Commands** (`/command`) to control the application, manage AI settings, and execute specialized tasks.

!!! tip "Tip"
    Press `Ctrl+P` to open the **Command Palette** for a searchable list of all commands.

---

## Command Categories

=== "Essential"

    Core application controls and session management.

    | Command | Description | Example |
    |---------|-------------|---------|
    | `/help` | Open the keyboard shortcuts and help screen. | `/help` |
    | `/status` | Show current session tokens, cost, and provider. | `/status` |
    | `/clear` | Clear the terminal history and reset context. | `/clear` |
    | `/quit` | Exit the application. | `/quit` |
    | `/reload` | Reload configuration, themes, and prompts. | `/reload` |
    | `/export` | Export the current session to Markdown. | `/export session-1.md` |
    | `/session` | Manage saved sessions (save/load/list). | `/session save debug-log` |

=== "AI & Agents"

    Control the intelligence engine.

    | Command | Description | Example |
    |---------|-------------|---------|
    | `/ai` | Toggle between CLI and AI Chat mode. | `/ai` |
    | `/agent` | Toggle **Agent Mode** for autonomous tasks. | `/agent` |
    | `/model` | Switch AI models (e.g., GPT-4o to Claude 3.5). | `/model anthropic claude-3-5-sonnet-20240620` |
    | `/provider` | Switch AI providers (e.g., Ollama to OpenAI). | `/provider ollama` |
    | `/prompts` | Manage system prompts and personas. | `/prompts list` |
    | `/plan` | Create a task plan before execution. | `/plan Refactor auth module` |
    | `/bg` | Run an agent task in the background. | `/bg Analyze logs` |
    | `/orchestrate`| Start a multi-agent workflow. | `/orchestrate Build a landing page` |

=== "Tools & Git"

    Integrations and developer tools.

    | Command | Description | Example |
    |---------|-------------|---------|
    | `/mcp` | Manage MCP servers (tools). | `/mcp catalog` |
    | `/git` | Show git status summary. | `/git` |
    | `/diff` | Show diff for a file. | `/diff src/main.py` |
    | `/commit` | Auto-generate commit message and commit. | `/commit` |
    | `/todo` | Open the task dashboard. | `/todo` |
    | `/ssh` | Connect to a saved SSH host. | `/ssh prod-server` |
    | `/map` | Visualize project architecture. | `/map src/` |

=== "Settings"

    Configuration and customization.

    | Command | Description | Example |
    |---------|-------------|---------|
    | `/settings` | Open the full configuration UI. | `/settings` |
    | `/theme` | Switch color theme. | `/theme dracula` |
    | `/mcp edit` | Edit MCP server config. | `/mcp edit github` |

---

## Global Shortcuts

Shortcuts allow for rapid navigation without typing commands.

| Key | Action | Context |
|-----|--------|---------|
| `Ctrl+Space` | **Toggle Mode** (CLI ↔ AI) | Global |
| `Ctrl+P` | **Command Palette** | Global |
| `Ctrl+\` | **Toggle Sidebar** (Files) | Global |
| `Ctrl+R` | **History Search** | Input |
| `Ctrl+L` | **Clear Screen** | Global |
| `F1` | **Help Screen** | Global |
| `F2` | **Select Model** | Global |
| `F3` | **Settings** | Global |
| `F4` | **Providers** | Global |
| `Esc` | **Cancel / Close** | Global |

---

## Common Scenarios

### 1. Switching to a Local Model
Protect privacy by switching to a local LLM.
```bash
/provider ollama
/model llama3.2
```

### 2. Autonomous Refactoring
Let the agent plan and execute a refactor.
```bash
/agent
/plan Refactor user.py to use Pydantic v2
# (Review plan in UI)
/plan execute
```

### 3. Background Research
Research a topic while coding.
```bash
/bg Research the top 3 Python libraries for PDF generation and save summary to docs/research.md
# Continue working...
```
