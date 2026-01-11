# MCP Server Catalog

Null Terminal integrates the **[Model Context Protocol](https://modelcontextprotocol.io/)**, allowing your AI to connect to external systems, databases, and APIs.

## Featured Servers

These are the most commonly used servers to supercharge your workflow.

<div class="grid cards" markdown>

-   **Filesystem**
    ---
    Allow the AI to read, write, and manage files on your local machine. Essential for coding agents.
    [:octicons-arrow-right-24: Official Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem)

-   **GitHub**
    ---
    Manage repositories, issues, and pull requests directly from chat.
    [:octicons-arrow-right-24: Official Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/github)

-   **PostgreSQL**
    ---
    Query your database, inspect schemas, and analyze data safely.
    [:octicons-arrow-right-24: Official Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)

-   **Brave Search**
    ---
    Give your AI access to the live internet for research and documentation lookups.
    [:octicons-arrow-right-24: Brave Search](https://github.com/brave/brave-search-mcp-server)

-   **Heroku**
    ---
    Manage your deployments, logs, and dynos.
    [:octicons-arrow-right-24: Heroku MCP](https://github.com/heroku/heroku-mcp-server)

-   **Slack**
    ---
    Read channels, send messages, and summarize threads.
    [:octicons-arrow-right-24: Slack](https://github.com/zencoderai/slack-mcp-server)

</div>

---

## Complete Catalog

Browse the full list of 130+ supported servers by category.

=== "Development"

    Tools for coding, testing, and version control.

    | Server | Description | Links |
    |--------|-------------|-------|
    | **git** | Local Git operations | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/git) |
    | **gitlab** | GitLab projects & MRs | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/gitlab) |
    | **sentry** | Error tracking & alerts | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/sentry) |
    | **docker** | Container management | [Docker](https://www.docker.com/) |
    | **kubernetes** | K8s cluster management | [Kubernetes](https://kubernetes.io/) |
    | **npm** | Package search | [npm](https://www.npmjs.com/) |
    | **pypi** | Python package info | [PyPI](https://pypi.org/) |
    | **aws-cdk** | IaC documentation | [AWS CDK](https://aws.amazon.com/cdk/) |
    | **circleci** | CI/CD pipelines | [Repo](https://github.com/CircleCI-Public/mcp-server-circleci) |
    | **code-runner** | Execute snippets | [Repo](https://github.com/formulahendry/mcp-server-code-runner) |
    | **chrome-devtools** | Browser automation | [Repo](https://github.com/ChromeDevTools/chrome-devtools-mcp) |

=== "Cloud & Ops"

    Manage infrastructure and services.

    | Server | Description | Links |
    |--------|-------------|-------|
    | **aws** | AWS Services (EC2, S3) | [Repo](https://github.com/awslabs/mcp) |
    | **gcp** | Google Cloud Platform | [GCP](https://cloud.google.com/) |
    | **azure** | Microsoft Azure | [Repo](https://github.com/microsoft/mcp/tree/main/servers/Azure.Mcp.Server) |
    | **cloudflare** | DNS & Workers | [Repo](https://github.com/cloudflare/mcp-server-cloudflare) |
    | **vercel** | Frontend deployments | [Vercel](https://vercel.com/) |
    | **netlify** | Web hosting | [Netlify](https://www.netlify.com/) |
    | **digitalocean** | Cloud infrastructure | [DigitalOcean](https://www.digitalocean.com/) |
    | **fly** | App deployment | [Fly.io](https://fly.io/) |
    | **ansible** | Playbook execution | [Ansible](https://www.ansible.com/) |
    | **terraform** | Infrastructure code | [Terraform](https://www.terraform.io/) |

=== "Database"

    Connect to your data stores.

    | Server | Description | Links |
    |--------|-------------|-------|
    | **sqlite** | Local SQLite files | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite) |
    | **mysql** | MySQL databases | [MySQL](https://www.mysql.com/) |
    | **redis** | Key-value store | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/redis) |
    | **mongodb** | Document store | [MongoDB](https://www.mongodb.com/) |
    | **elasticsearch** | Search engine | [Elastic](https://www.elastic.co/) |
    | **supabase** | Postgres + Auth | [Supabase](https://supabase.com/) |
    | **snowflake** | Data cloud | [Snowflake](https://www.snowflake.com/) |
    | **clickhouse** | Analytics DB | [Repo](https://github.com/ClickHouse/mcp-clickhouse) |
    | **qdrant** | Vector database | [Qdrant](https://qdrant.tech/) |

=== "Productivity"

    Connect your workspace tools.

    | Server | Description | Links |
    |--------|-------------|-------|
    | **notion** | Pages & Databases | [Repo](https://github.com/makenotion/notion-mcp-server) |
    | **obsidian** | Local vault notes | [Obsidian](https://obsidian.md/) |
    | **google-drive** | File access | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive) |
    | **gmail** | Read/Send email | [Gmail](https://www.google.com/gmail/) |
    | **calendar** | Google Calendar | [Google](https://calendar.google.com/) |
    | **todoist** | Task management | [Todoist](https://todoist.com/) |
    | **trello** | Kanban boards | [Trello](https://trello.com/) |
    | **slack** | Messaging | [Repo](https://github.com/zencoderai/slack-mcp-server) |
    | **zoom** | Meetings | [Zoom](https://zoom.us/) |

=== "AI & Search"

    Enhance intelligence and retrieval.

    | Server | Description | Links |
    |--------|-------------|-------|
    | **exa** | AI Neural Search | [Exa](https://exa.ai/) |
    | **tavily** | Search for agents | [Tavily](https://tavily.com/) |
    | **arxiv** | Research papers | [arXiv](https://arxiv.org/) |
    | **huggingface** | Models & Datasets | [HuggingFace](https://huggingface.co/) |
    | **openai** | GPT Models | [OpenAI](https://openai.com/) |
    | **pinecone** | Vector Store | [Pinecone](https://www.pinecone.io/) |
    | **memory** | Knowledge Graph | [Repo](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) |

---

## Managing Servers

### Installation

Use the interactive catalog to browse and install servers:

```bash
/mcp catalog
```

### Configuration

Servers are configured in `~/.null/mcp.json`. You can edit this file directly or use commands.

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your-token-here"
      }
    }
  }
}
```

### Commands

| Command | Action |
|---------|--------|
| `/mcp list` | View status of all servers |
| `/mcp add` | Wizard to add a new server |
| `/mcp edit <name>` | Edit configuration for a server |
| `/mcp logs <name>` | View server logs for debugging |
