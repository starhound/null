# Slash Commands Reference

All commands are prefixed with `/` and executed from the input prompt.

## Core Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help screen |
| `/status` | Display session status (provider, model, tokens, cost) |
| `/clear` | Clear history and context |
| `/quit` or `/exit` | Exit the application |
| `/git` | Show git status |
| `/reload` | Reload configuration and themes |

## AI Commands

| Command | Description |
|---------|-------------|
| `/ai` | Toggle AI mode on/off |
| `/chat` | Toggle AI mode (alias) |
| `/agent` | Toggle agent mode (autonomous execution) |
| `/model` | Open model selection screen |
| `/model <provider> <model>` | Set model directly (e.g., `/model ollama llama3.2`) |
| `/provider` | Open provider configuration |
| `/provider <name>` | Switch to specific provider |
| `/providers` | Open providers management screen |
| `/compact` | Summarize conversation to reduce tokens |
| `/context` | Inspect current AI context messages |

## Planning & Tasks

| Command | Description |
|---------|-------------|
| `/plan <goal>` | Generate a plan for the goal |
| `/plan show` | Show current plan |
| `/plan approve` | Approve all pending steps |
| `/plan execute` | Start executing approved steps |
| `/plan save <name>` | Save plan as workflow template |
| `/plan load <name>` | Load saved plan |
| `/todo` | Open task manager |
| `/todo add <task>` | Add a new task |
| `/todo list` | List tasks in chat |
| `/todo done <id>` | Mark task as done |
| `/todo del <id>` | Delete task |

## Git Operations

| Command | Description |
|---------|-------------|
| `/diff [file]` | Show diff for file or all changes |
| `/commit [message]` | Commit staged changes |
| `/undo` | Revert last AI commit |
| `/git log` | Show recent commits |
| `/git stash` | Stash changes |
| `/git checkout <file>` | Discard changes |

## Workflows & Agents

| Command | Description |
|---------|-------------|
| `/workflow` | Browse workflows |
| `/workflow run <name>` | Run a workflow |
| `/workflow save [name]` | Save session as workflow |
| `/bg <goal>` | Start background task |
| `/bg list` | List background tasks |
| `/bg status <id>` | Show task status |
| `/bg logs <id>` | Show task logs |
| `/bg cancel <id>` | Cancel running task |
| `/orchestrate <goal>` | Start multi-agent task |
| `/agents` | List agent profiles |

## Prompt/Persona Commands

| Command | Description |
|---------|-------------|
| `/prompts` | Open prompt editor |
| `/prompts list` | List available prompts |
| `/prompts show <key>` | Show prompt content |
| `/prompts dir` | Show prompts directory path |
| `/prompts reload` | Reload prompts from disk |

## Session Commands

| Command | Description |
|---------|-------------|
| `/export` | Export to markdown (default) |
| `/export md` | Export to markdown |
| `/export json` | Export to JSON |
| `/session save [name]` | Save session with optional name |
| `/session load [name]` | Load a saved session |
| `/session list` | List saved sessions |
| `/session new` | Start new session |

## Collaboration

| Command | Description |
|---------|-------------|
| `/share` | Share current session |
| `/share team` | Share to team workspace |
| `/import <url>` | Import shared session |

## MCP Commands

| Command | Description |
|---------|-------------|
| `/mcp` or `/mcp list` | List MCP servers and status |
| `/mcp tools` | List available MCP tools |
| `/mcp add` | Add new MCP server |
| `/mcp edit <name>` | Edit MCP server config |
| `/mcp remove <name>` | Remove MCP server |
| `/mcp enable <name>` | Enable MCP server |
| `/mcp disable <name>` | Disable MCP server |
| `/mcp reconnect [name]` | Reconnect to server(s) |
| `/tools` | Browse available MCP tools |

## Configuration Commands

| Command | Description |
|---------|-------------|
| `/config` or `/settings` | Open settings screen |
| `/theme` | Open theme selector |
| `/theme <name>` | Set theme directly |

## SSH Commands

| Command | Description |
|---------|-------------|
| `/ssh <alias>` | Connect to saved SSH host |
| `/ssh-add [alias host user port key]` | Add SSH configuration |
| `/ssh-list` | List saved SSH hosts |
| `/ssh-del <alias>` | Delete SSH host |

## Advanced

| Command | Description |
|---------|-------------|
| `/map` | Visualize project architecture |
| `/cmd <description>` | Translate natural language to shell command |
| `/explain <command>` | Explain a shell command |
| `/fix` | Auto-correct the last error |
| `/watch` | Monitor output for errors and auto-fix |

---

## Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Space` | Toggle between AI and CLI modes |
| `Ctrl+P` | Open command palette |
| `Ctrl+\` | Toggle file sidebar |
| `Ctrl+R` | History search |
| `Ctrl+F` | Find in blocks |
| `Ctrl+L` | Clear screen/history |
| `F1` | Open Help |
| `F2` | Select Model |
| `F3` | Open Settings |
| `F4` | Manage Providers |
