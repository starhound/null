# MCP Servers (Model Context Protocol)

MCP allows AI models to interact with external tools and services.

## What is MCP?

The Model Context Protocol (MCP) is a standard for connecting AI models to external capabilities:
- **Tools**: Functions the AI can call (e.g., web search, database queries)
- **Resources**: Data the AI can access (e.g., file contents, API data)

## MCP Server Catalog

Null Terminal includes a curated catalog of 100+ MCP servers across 18 categories. Browse and install servers with a single command:

```bash
/mcp catalog
```

This opens an interactive browser where you can:
- Browse servers by category (File System, Database, Development, Cloud, etc.)
- Search for servers by name or description
- See which servers are already installed (marked with [Installed])
- Install servers with pre-filled configuration

### Available Categories

| Category | Description |
|----------|-------------|
| File System | File and directory operations |
| Database | SQL, NoSQL, and vector databases |
| Development | GitHub, GitLab, CI/CD tools |
| Sysadmin | Docker, Kubernetes, SSH |
| Monitoring | Prometheus, Grafana, Datadog |
| Cloud | AWS, GCP, Azure, Cloudflare |
| Web | Browser automation, web scraping |
| Search | Brave, Exa, Tavily, Google |
| Communication | Slack, Discord, Email |
| Productivity | Notion, Obsidian, Todoist |
| Memory | Knowledge graphs, vector stores |
| Finance | Stripe, Plaid, stock data |
| Social | Twitter, Reddit, YouTube |
| Utility | Time, weather, calculations |
| AI | OpenAI, Anthropic, HuggingFace |
| E-commerce | Shopify, WooCommerce |
| Analytics | Google Analytics, Mixpanel |
| CRM | Salesforce, HubSpot, Zendesk |

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

### Browse Catalog
```bash
/mcp catalog
# Opens interactive catalog browser
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

- **Built-in Catalog**: Use `/mcp catalog` to browse 100+ curated servers
- **Official MCP servers**: https://github.com/modelcontextprotocol/servers
- **Community servers**: Search GitHub for "mcp-server"
- **Build your own**: See MCP SDK documentation

## Environment Variables

Many MCP servers require API keys or credentials. Set them in the server configuration:

```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx"
    }
  }
}
```

Common environment variables by server type:

| Server | Required Variables |
|--------|-------------------|
| GitHub | `GITHUB_TOKEN` |
| Slack | `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` |
| Brave Search | `BRAVE_API_KEY` |
| PostgreSQL | `POSTGRES_CONNECTION_STRING` |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Google APIs | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |

The catalog shows required environment variables for each server before installation.
