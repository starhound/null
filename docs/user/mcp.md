# MCP Servers (Model Context Protocol)

MCP allows AI models to interact with external tools and services.

## What is MCP?

The Model Context Protocol (MCP) is a standard for connecting AI models to external capabilities:
- **Tools**: Functions the AI can call (e.g., web search, database queries)
- **Resources**: Data the AI can access (e.g., file contents, API data)

## Configuration

MCP servers are configured in `~/.null/mcp.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/home/user"],
      "env": {},
      "enabled": true
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-api-key"
      },
      "enabled": true
    }
  }
}
```

## Managing MCP Servers

### List Servers
```bash
/mcp
# or
/mcp list
```

### Add Server
```bash
/mcp add
# Opens configuration dialog
```

### Edit Server
```bash
/mcp edit <name>
```

### Enable/Disable
```bash
/mcp enable <name>
/mcp disable <name>
```

### Remove Server
```bash
/mcp remove <name>
```

### Reconnect
```bash
/mcp reconnect          # Reconnect all
/mcp reconnect <name>   # Reconnect specific server
```

### View Tools
```bash
/mcp tools    # List all available tools
/tools-ui     # Open tools browser
```

## Popular MCP Servers

### Filesystem Access
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@anthropic/mcp-server-filesystem", "/path/to/allow"],
    "enabled": true
  }
}
```

### Brave Search
```json
{
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@anthropic/mcp-server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "your-key"
    },
    "enabled": true
  }
}
```

### GitHub
```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@anthropic/mcp-server-github"],
    "env": {
      "GITHUB_TOKEN": "your-token"
    },
    "enabled": true
  }
}
```

### Postgres Database
```json
{
  "postgres": {
    "command": "npx",
    "args": ["-y", "@anthropic/mcp-server-postgres", "postgresql://..."],
    "enabled": true
  }
}
```

### Custom Python Server
```json
{
  "my-server": {
    "command": "python",
    "args": ["/path/to/my_mcp_server.py"],
    "env": {
      "MY_CONFIG": "value"
    },
    "enabled": true
  }
}
```

## Using MCP Tools

### In Chat Mode
When you ask the AI to perform a task, it can use MCP tools:

```
You: Search for recent news about AI
AI: [Uses brave_search tool]
    Here are the recent news articles...
```

### In Agent Mode
Enable agent mode for autonomous tool use:

```bash
/agent
```

The AI will automatically chain tool calls to complete tasks.

### Tool Approval
By default, tool execution requires approval. The AI will request permission before executing sensitive operations.

## Status Bar

The status bar shows MCP connection status:
- Number of connected servers
- Green indicator when connected

## Troubleshooting

### Server Won't Connect
1. Check the command exists: `which npx` or `which python`
2. Verify the server package: `npx -y @anthropic/mcp-server-<name>`
3. Check environment variables are set
4. View logs in terminal output

### Tools Not Appearing
1. Ensure server is enabled: `/mcp list`
2. Reconnect: `/mcp reconnect <name>`
3. Check `/mcp tools` for available tools

### Permission Errors
- Filesystem server needs read access to specified paths
- Database servers need valid connection strings
- API servers need valid API keys in environment

## Finding MCP Servers

- **Official Anthropic servers**: https://github.com/anthropics/mcp-servers
- **Community servers**: Search GitHub for "mcp-server"
- **Build your own**: See MCP SDK documentation
