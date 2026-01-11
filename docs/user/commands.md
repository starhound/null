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

## Prompt/Persona Commands

| Command | Description |
|---------|-------------|
| `/prompts` | Open prompt editor |
| `/prompts list` | List available prompts |
| `/prompts show <key>` | Show prompt content |
| `/prompts dir` | Show prompts directory path |
| `/prompts reload` | Reload prompts from disk |

### Built-in Prompts

| Key | Name | Description |
|-----|------|-------------|
| `default` | Default | Balanced assistant |
| `concise` | Concise | Minimal responses |
| `agent` | Agent | Task execution optimized |
| `code` | Orchestration Helper | Automation focus |
| `devops` | DevOps | System admin focus |

Add custom prompts in `~/.null/prompts/` as `.txt` or `.md` files.

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
| `/tools-ui` | (Deprecated) Same as `/tools` |

## Task Management

| Command | Description |
|---------|-------------|
| `/todo` | Open task dashboard |
| `/todo add <task>` | Add a new task |
| `/todo list` | List tasks in chat |
| `/todo done <id>` | Mark task as done |
| `/todo del <id>` | Delete task |

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

## Built-in Shell Commands

These work in CLI mode without `/` prefix:

| Command | Description |
|---------|-------------|
| `cd <path>` | Change directory |
| `pwd` | Print working directory |
| `clear` | Clear terminal screen |
