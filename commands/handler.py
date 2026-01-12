"""Main command handler that routes to command modules."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from .ai import AICommands
from .config import ConfigCommands
from .core import CoreCommands
from .mcp import MCPCommands
from .rag import RAGCommands
from .session import SessionCommands
from .share import ShareCommands
from .todo import TodoCommands

if TYPE_CHECKING:
    from app import NullApp


@dataclass
class CommandInfo:
    """Information about a slash command."""

    name: str
    description: str
    shortcut: str = ""
    subcommands: list[tuple[str, str]] = field(default_factory=list)


class SlashCommandHandler:
    """Routes and executes slash commands."""

    def __init__(self, app: NullApp):
        self.app = app

        # Initialize command modules
        self._core = CoreCommands(app)
        self._ai = AICommands(app)
        self._rag = RAGCommands(app)
        self._session = SessionCommands(app)
        self._share = ShareCommands(app)
        self._mcp = MCPCommands(app)
        self._config = ConfigCommands(app)
        self._todo = TodoCommands(app)

        # Build command routing table with descriptions
        self._command_registry: dict[str, tuple[Callable, CommandInfo]] = {
            # Core commands
            "help": (
                self._core.cmd_help,
                CommandInfo("help", "Show help screen", "F1"),
            ),
            "status": (
                self._core.cmd_status,
                CommandInfo("status", "Show current status"),
            ),
            "git": (
                self._core.cmd_git,
                CommandInfo(
                    "git",
                    "Git operations",
                    "",
                    subcommands=[
                        ("status", "Show git status"),
                        ("diff [file]", "Show changes"),
                        ("commit [msg]", "Commit (AI message if empty)"),
                        ("undo", "Undo last commit"),
                        ("log [n]", "Show recent commits"),
                        ("stash [msg]", "Stash changes"),
                        ("stash pop", "Apply stash"),
                    ],
                ),
            ),
            "diff": (
                self._core.cmd_diff,
                CommandInfo("diff", "Show git diff (shortcut for /git diff)"),
            ),
            "undo": (
                self._core.cmd_undo,
                CommandInfo("undo", "Undo last git commit"),
            ),
            "fix": (
                self._core.cmd_fix,
                CommandInfo(
                    "fix",
                    "Generate fix for last error",
                    "",
                    subcommands=[
                        ("", "Fix last detected error"),
                        ("<error>", "Parse and fix provided error text"),
                    ],
                ),
            ),
            "watch": (
                self._core.cmd_watch,
                CommandInfo(
                    "watch",
                    "Toggle error watch mode",
                    "",
                    subcommands=[
                        ("", "Toggle watch mode on/off"),
                        ("stop", "Disable watch mode"),
                    ],
                ),
            ),
            "review": (
                self._core.cmd_review,
                CommandInfo(
                    "review",
                    "Review pending code changes",
                    "",
                    subcommands=[
                        ("", "Show pending changes"),
                        ("status", "Show review status"),
                        ("accept [file] [hunk]", "Accept changes"),
                        ("reject [file] [hunk]", "Reject changes"),
                        ("apply", "Apply accepted changes"),
                        ("clear", "Clear all pending"),
                        ("show <file>", "Show file diff"),
                    ],
                ),
            ),
            "issue": (
                self._core.cmd_issue,
                CommandInfo(
                    "issue",
                    "GitHub issue operations",
                    "",
                    subcommands=[
                        ("<number>", "View issue details"),
                        ("list", "List open issues"),
                        ("create", "Create new issue"),
                    ],
                ),
            ),
            "pr": (
                self._core.cmd_pr,
                CommandInfo(
                    "pr",
                    "GitHub PR operations",
                    "",
                    subcommands=[
                        ("<number>", "View PR details"),
                        ("list", "List open PRs"),
                        ("create", "Create new PR"),
                        ("diff <number>", "Show PR diff"),
                    ],
                ),
            ),
            "cmd": (
                self._core.cmd_cmd,
                CommandInfo(
                    "cmd",
                    "Translate natural language to shell command",
                    "",
                    subcommands=[
                        ("<description>", "Describe what you want to do"),
                    ],
                ),
            ),
            "explain": (
                self._core.cmd_explain,
                CommandInfo(
                    "explain",
                    "Explain a shell command",
                    "",
                    subcommands=[
                        ("<command>", "Command to explain"),
                    ],
                ),
            ),
            "clear": (
                self._core.cmd_clear,
                CommandInfo("clear", "Clear history and context", "Ctrl+L"),
            ),
            "reload": (
                self._core.cmd_reload,
                CommandInfo("reload", "Reload configuration and themes"),
            ),
            "map": (
                self._core.cmd_map,
                CommandInfo(
                    "map",
                    "Show project architecture",
                    "",
                    subcommands=[
                        ("", "Show full architecture"),
                        ("<path>", "Show architecture for specific path"),
                        ("--format mermaid", "Output as mermaid diagram"),
                        ("--depth N", "Limit analysis depth"),
                        ("<component>", "Show component details"),
                    ],
                ),
            ),
            "quit": (
                self._core.cmd_quit,
                CommandInfo("quit", "Exit application", "Ctrl+C"),
            ),
            "exit": (self._core.cmd_exit, CommandInfo("exit", "Exit application")),
            # SSH commands
            "ssh": (
                self._core.cmd_ssh,
                CommandInfo("ssh", "Connect to SSH host (e.g. /ssh alias)"),
            ),
            "ssh-add": (
                self._core.cmd_ssh_add,
                CommandInfo("ssh-add", "Add (save) a new SSH host"),
            ),
            "ssh-list": (
                self._core.cmd_ssh_list,
                CommandInfo("ssh-list", "List saved SSH hosts"),
            ),
            "ssh-del": (
                self._core.cmd_ssh_del,
                CommandInfo("ssh-del", "Delete a saved SSH host"),
            ),
            # AI commands
            "provider": (
                self._ai.cmd_provider,
                CommandInfo(
                    "provider",
                    "Select AI provider",
                    "F4",
                    subcommands=[
                        ("ollama", "Configure Ollama (local)"),
                        ("lm_studio", "Configure LM Studio (local)"),
                        ("openai", "Configure OpenAI"),
                        ("anthropic", "Configure Anthropic"),
                        ("google", "Configure Google Gemini"),
                        ("azure", "Configure Azure OpenAI"),
                        ("bedrock", "Configure AWS Bedrock"),
                        ("mistral", "Configure Mistral AI"),
                        ("deepseek", "Configure DeepSeek"),
                        ("openrouter", "Configure OpenRouter"),
                        ("xai", "Configure xAI (Grok)"),
                        ("cohere", "Configure Cohere"),
                        ("together", "Configure Together AI"),
                        ("fireworks", "Configure Fireworks AI"),
                        ("perplexity", "Configure Perplexity"),
                        ("cloudflare", "Configure Cloudflare Workers AI"),
                        ("huggingface", "Configure HuggingFace"),
                        ("llama_cpp", "Configure Llama.cpp Server"),
                        ("custom", "Configure Custom HTTP Provider"),
                        ("nvidia", "Configure NVIDIA NIM"),
                        ("groq", "Configure Groq"),
                    ],
                ),
            ),
            "providers": (
                self._ai.cmd_providers,
                CommandInfo("providers", "Manage all AI providers"),
            ),
            "model": (
                self._ai.cmd_model,
                CommandInfo(
                    "model",
                    "Select AI model",
                    "F2",
                    subcommands=[
                        ("embedding [provider] [model]", "Set embedding model for RAG"),
                        ("autocomplete [provider] [model]", "Set autocomplete model"),
                        ("autocomplete on|off", "Enable/disable autocomplete"),
                        ("status", "Show all model configurations"),
                        ("<provider> <model>", "Set main LLM directly"),
                    ],
                ),
            ),
            "prompts": (
                self._ai.cmd_prompts,
                CommandInfo("prompts", "Manage system prompts"),
            ),
            "ai": (self._ai.cmd_ai, CommandInfo("ai", "Toggle AI mode", "Ctrl+Space")),
            "chat": (self._ai.cmd_chat, CommandInfo("chat", "Toggle AI mode")),
            "agent": (
                self._ai.cmd_agent,
                CommandInfo(
                    "agent",
                    "Agent mode control",
                    subcommands=[
                        ("status", "Show current agent status"),
                        ("history", "Show session history"),
                        ("stats", "Show cumulative statistics"),
                        ("stop", "Cancel active session"),
                        ("pause", "Pause active session"),
                        ("resume", "Resume paused session"),
                        ("clear", "Clear history and stats"),
                        ("tools", "List available tools"),
                        ("inspect", "Open agent inspector"),
                        ("config", "View/set agent config"),
                        ("save [name]", "Save current/last session"),
                        ("load <id>", "Load a saved session"),
                        ("list", "List saved sessions"),
                        ("export [id]", "Export session to markdown"),
                        ("delete <id>", "Delete a saved session"),
                        ("on", "Enable agent mode"),
                        ("off", "Disable agent mode"),
                    ],
                ),
            ),
            "orchestrate": (
                self._ai.cmd_orchestrate,
                CommandInfo(
                    "orchestrate",
                    "Multi-agent orchestration",
                    subcommands=[
                        ("<goal>", "Start orchestration with goal"),
                        ("status", "Show orchestration status"),
                        ("stop", "Stop active orchestration"),
                    ],
                ),
            ),
            "compact": (
                self._ai.cmd_compact,
                CommandInfo("compact", "Summarize context to save tokens"),
            ),
            "context": (
                self._ai.cmd_context,
                CommandInfo("context", "Inspect context messages"),
            ),
            "plan": (
                self._ai.cmd_plan,
                CommandInfo(
                    "plan",
                    "Create and manage AI-generated plans",
                    "",
                    subcommands=[
                        ("<goal>", "Generate a plan for the goal"),
                        ("show", "Show current plan"),
                        ("approve [id|all]", "Approve step(s)"),
                        ("skip <id>", "Skip a step"),
                        ("execute", "Execute approved steps"),
                        ("cancel", "Cancel current plan"),
                    ],
                ),
            ),
            "workflow": (
                self._core.cmd_workflow,
                CommandInfo(
                    "workflow",
                    "Manage workflow templates",
                    "",
                    subcommands=[
                        ("list", "List all workflows"),
                        ("run <name>", "Run a workflow"),
                        ("save [name]", "Save session as workflow"),
                        ("import <file>", "Import workflow from YAML"),
                        ("export <name>", "Export workflow to YAML"),
                    ],
                ),
            ),
            "branch": (
                self._core.cmd_branch,
                CommandInfo(
                    "branch",
                    "Manage conversation branches",
                    "",
                    subcommands=[
                        ("list", "List all branches"),
                        ("switch <name>", "Switch to branch"),
                        ("new <name>", "Create new branch (or use 'f' key)"),
                    ],
                ),
            ),
            "bg": (
                self._ai.cmd_bg,
                CommandInfo(
                    "bg",
                    "Run AI agents in background",
                    "",
                    subcommands=[
                        ("<goal>", "Start background task"),
                        ("list", "List all tasks"),
                        ("status <id>", "Show task status"),
                        ("cancel <id>", "Cancel task"),
                        ("logs <id>", "Show task logs"),
                        ("clear", "Clear completed"),
                    ],
                ),
            ),
            # RAG commands
            "index": (
                self._rag.cmd_index,
                CommandInfo(
                    "index",
                    "Manage knowledge base (build/status/search)",
                    subcommands=[
                        ("status", "Show index statistics"),
                        ("build [path]", "Index a directory"),
                        ("search <query>", "Search the index"),
                        ("clear", "Clear the index"),
                    ],
                ),
            ),
            "recall": (
                self._rag.cmd_recall,
                CommandInfo("recall", "Search interaction history"),
            ),
            # Session commands
            "session": (
                self._session.cmd_session,
                CommandInfo(
                    "session",
                    "Manage sessions",
                    subcommands=[
                        ("save [name]", "Save current session"),
                        ("load <name>", "Load a saved session"),
                        ("list", "List saved sessions"),
                        ("new", "Start new session"),
                        ("delete <name>", "Delete a session"),
                    ],
                ),
            ),
            "export": (
                self._session.cmd_export,
                CommandInfo(
                    "export",
                    "Export conversation",
                    "Ctrl+S",
                    subcommands=[
                        ("md", "Export to Markdown"),
                        ("json", "Export to JSON"),
                        ("txt", "Export to plain text"),
                    ],
                ),
            ),
            "share": (
                self._share.cmd_share,
                CommandInfo(
                    "share",
                    "Share session in various formats",
                    subcommands=[
                        ("", "Share to clipboard (markdown)"),
                        ("--format json", "Share as JSON"),
                        ("--format markdown", "Share as Markdown"),
                        ("--format html", "Share as HTML"),
                        ("--output <path>", "Save to file"),
                        ("--anonymize", "Anonymize sensitive data"),
                    ],
                ),
            ),
            # MCP commands
            "mcp": (
                self._mcp.cmd_mcp,
                CommandInfo(
                    "mcp",
                    "Manage MCP servers",
                    subcommands=[
                        ("list", "List configured MCP servers"),
                        ("catalog", "Browse MCP server catalog"),
                        ("add", "Add a new MCP server manually"),
                        ("edit <name>", "Edit an MCP server config"),
                        ("remove <name>", "Remove an MCP server"),
                        ("enable <name>", "Enable an MCP server"),
                        ("disable <name>", "Disable an MCP server"),
                        ("reconnect [name]", "Reconnect MCP server(s)"),
                        ("tools", "Show available MCP tools"),
                        ("resources", "List available MCP resources"),
                        ("read <uri>", "Read an MCP resource"),
                    ],
                ),
            ),
            "tools": (
                self._mcp.cmd_tools_ui,
                CommandInfo("tools", "Browse available MCP tools"),
            ),
            "todo": (
                self._todo.cmd_todo,
                CommandInfo("todo", "Manage tasks (add/list/done/del)"),
            ),
            # Config commands
            "config": (self._config.cmd_config, CommandInfo("config", "Open settings")),
            "settings": (
                self._config.cmd_settings,
                CommandInfo("settings", "Open settings"),
            ),
            "theme": (
                self._config.cmd_theme,
                CommandInfo("theme", "Change UI theme", "F3"),
            ),
            "profile": (
                self._ai.cmd_profile,
                CommandInfo(
                    "profile",
                    "Manage agent profiles",
                    subcommands=[
                        ("list", "List all profiles"),
                        ("<name>", "Activate a profile"),
                        ("create [from <id>]", "Create new profile"),
                        ("edit <name>", "Edit a profile"),
                        ("export <name>", "Export profile to YAML"),
                        ("import <file>", "Import profile from YAML"),
                        ("delete <name>", "Delete a profile"),
                        ("active", "Show active profile"),
                    ],
                ),
            ),
        }

        # Legacy _commands dict for backward compatibility
        self._commands = {k: v[0] for k, v in self._command_registry.items()}

    def get_all_commands(self) -> list[CommandInfo]:
        """Get list of all available commands with their info."""
        return [info for _, info in self._command_registry.values()]

    def get_command_info(self, name: str) -> CommandInfo | None:
        """Get info for a specific command."""
        entry = self._command_registry.get(name)
        return entry[1] if entry else None

    async def handle(self, text: str):
        """Route and execute a slash command."""
        try:
            parts = shlex.split(text)
        except ValueError as e:
            self.app.notify(f"Invalid command syntax: {e}", severity="error")
            return

        if not parts:
            return

        command = parts[0][1:]  # strip /
        args = parts[1:]

        entry = self._command_registry.get(command)
        if entry:
            handler = entry[0]
            await handler(args)
        else:
            self.app.notify(f"Unknown command: {command}", severity="warning")
