"""MCP Server Catalog - curated list of popular MCP servers."""

from dataclasses import dataclass


@dataclass
class CatalogEntry:
    name: str
    description: str
    command: str
    args: list[str]
    env_keys: list[str]
    category: str
    url: str


CATALOG: list[CatalogEntry] = [
    # === File System & Local ===
    CatalogEntry(
        name="filesystem",
        description="Read/write files, directory operations",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
        env_keys=[],
        category="filesystem",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    ),
    CatalogEntry(
        name="sqlite",
        description="Query and manage SQLite databases",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sqlite", "/path/to/database.db"],
        env_keys=[],
        category="database",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
    ),
    CatalogEntry(
        name="postgres",
        description="Query PostgreSQL databases",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres"],
        env_keys=["POSTGRES_CONNECTION_STRING"],
        category="database",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
    ),
    # === Code & Development ===
    CatalogEntry(
        name="github",
        description="GitHub repos, issues, PRs, and more",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env_keys=["GITHUB_TOKEN"],
        category="development",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/github",
    ),
    CatalogEntry(
        name="gitlab",
        description="GitLab projects, issues, merge requests",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-gitlab"],
        env_keys=["GITLAB_TOKEN", "GITLAB_URL"],
        category="development",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/gitlab",
    ),
    CatalogEntry(
        name="git",
        description="Git operations on local repositories",
        command="uvx",
        args=["mcp-server-git", "--repository", "/path/to/repo"],
        env_keys=[],
        category="development",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/git",
    ),
    # === Web & Search ===
    CatalogEntry(
        name="brave-search",
        description="Web search via Brave Search API",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env_keys=["BRAVE_API_KEY"],
        category="search",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
    ),
    CatalogEntry(
        name="fetch",
        description="Fetch and parse web pages",
        command="uvx",
        args=["mcp-server-fetch"],
        env_keys=[],
        category="web",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
    ),
    CatalogEntry(
        name="puppeteer",
        description="Browser automation with Puppeteer",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-puppeteer"],
        env_keys=[],
        category="web",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
    ),
    CatalogEntry(
        name="playwright",
        description="Browser automation with Playwright",
        command="npx",
        args=["-y", "@playwright/mcp@latest"],
        env_keys=[],
        category="web",
        url="https://github.com/microsoft/playwright-mcp",
    ),
    # === Cloud & Services ===
    CatalogEntry(
        name="aws-kb",
        description="AWS Bedrock Knowledge Base retrieval",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-aws-kb-retrieval"],
        env_keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
        category="cloud",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/aws-kb-retrieval",
    ),
    CatalogEntry(
        name="google-drive",
        description="Access Google Drive files",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-gdrive"],
        env_keys=["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        category="cloud",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive",
    ),
    CatalogEntry(
        name="google-maps",
        description="Google Maps search and directions",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-google-maps"],
        env_keys=["GOOGLE_MAPS_API_KEY"],
        category="cloud",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/google-maps",
    ),
    CatalogEntry(
        name="slack",
        description="Slack channels, messages, and users",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-slack"],
        env_keys=["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
        category="communication",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
    ),
    # === Memory & Knowledge ===
    CatalogEntry(
        name="memory",
        description="Persistent memory using knowledge graph",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        env_keys=[],
        category="memory",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
    ),
    CatalogEntry(
        name="qdrant",
        description="Vector search with Qdrant",
        command="uvx",
        args=["mcp-server-qdrant"],
        env_keys=["QDRANT_URL", "QDRANT_API_KEY"],
        category="database",
        url="https://github.com/qdrant/mcp-server-qdrant",
    ),
    # === Utilities ===
    CatalogEntry(
        name="time",
        description="Current time and timezone conversion",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-time"],
        env_keys=[],
        category="utility",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/time",
    ),
    CatalogEntry(
        name="sequential-thinking",
        description="Dynamic problem-solving through thought sequences",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
        env_keys=[],
        category="utility",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/sequential-thinking",
    ),
    CatalogEntry(
        name="everything",
        description="Reference/test server with all MCP features",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        env_keys=[],
        category="utility",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/everything",
    ),
    # === Third Party Popular ===
    CatalogEntry(
        name="context7",
        description="Up-to-date documentation for libraries",
        command="npx",
        args=["-y", "@anthropic/context7-mcp@latest"],
        env_keys=[],
        category="development",
        url="https://context7.com",
    ),
    CatalogEntry(
        name="linear",
        description="Linear issues and projects",
        command="npx",
        args=["-y", "@tacticlaunch/mcp-linear"],
        env_keys=["LINEAR_API_KEY"],
        category="development",
        url="https://github.com/tacticlaunch/mcp-linear",
    ),
    CatalogEntry(
        name="notion",
        description="Notion pages and databases",
        command="npx",
        args=["-y", "@suekou/mcp-notion-server"],
        env_keys=["NOTION_API_KEY"],
        category="productivity",
        url="https://github.com/suekou/mcp-notion-server",
    ),
    CatalogEntry(
        name="obsidian",
        description="Obsidian vault notes and search",
        command="npx",
        args=["-y", "mcp-obsidian", "/path/to/vault"],
        env_keys=[],
        category="productivity",
        url="https://github.com/smithery-ai/mcp-obsidian",
    ),
    CatalogEntry(
        name="todoist",
        description="Todoist tasks and projects",
        command="npx",
        args=["-y", "@abhiz123/todoist-mcp-server"],
        env_keys=["TODOIST_API_TOKEN"],
        category="productivity",
        url="https://github.com/abhiz123/todoist-mcp-server",
    ),
    CatalogEntry(
        name="sentry",
        description="Sentry error tracking and issues",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sentry"],
        env_keys=["SENTRY_AUTH_TOKEN", "SENTRY_ORG"],
        category="development",
        url="https://github.com/modelcontextprotocol/servers/tree/main/src/sentry",
    ),
    CatalogEntry(
        name="raygun",
        description="Raygun crash reporting",
        command="npx",
        args=["-y", "@raygun/mcp-server-raygun"],
        env_keys=["RAYGUN_PAT"],
        category="development",
        url="https://github.com/MindscapeHQ/mcp-server-raygun",
    ),
]

CATEGORIES = {
    "filesystem": "File System",
    "database": "Database",
    "development": "Development",
    "search": "Search",
    "web": "Web & Browser",
    "cloud": "Cloud Services",
    "communication": "Communication",
    "memory": "Memory & Knowledge",
    "productivity": "Productivity",
    "utility": "Utilities",
}


def get_by_category(category: str) -> list[CatalogEntry]:
    return [e for e in CATALOG if e.category == category]


def get_by_name(name: str) -> CatalogEntry | None:
    for entry in CATALOG:
        if entry.name == name:
            return entry
    return None


def search(query: str) -> list[CatalogEntry]:
    query = query.lower()
    return [
        e for e in CATALOG if query in e.name.lower() or query in e.description.lower()
    ]
