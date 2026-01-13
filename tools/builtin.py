"""Built-in tools for the AI to use."""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from commands.todo import TodoManager
from managers.review import ProposedChange
from security.sanitizer import configure_sanitizer, get_sanitizer

if TYPE_CHECKING:
    from managers.agent import AgentManager

logger = logging.getLogger(__name__)

_agent_manager: "AgentManager | None" = None


def set_agent_manager(manager: "AgentManager") -> None:
    global _agent_manager
    _agent_manager = manager


def get_agent_manager() -> "AgentManager | None":
    return _agent_manager


def init_command_sanitizer() -> None:
    """Initialize the command sanitizer from settings."""
    try:
        from config.settings import get_settings

        settings = get_settings()
        configure_sanitizer(
            allowlist_mode=settings.security.command_allowlist_mode,
            custom_blocked_patterns=settings.security.blocked_command_patterns,
        )
    except Exception as e:
        logger.warning(f"Failed to load security settings: {e}")


@dataclass
class BuiltinTool:
    """A built-in tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[str]]
    requires_approval: bool = True  # Whether to ask user before executing


async def run_command(
    command: str,
    working_dir: str | None = None,
    on_progress: Callable[[Any], None] | None = None,
    tool_call: Any | None = None,
) -> str:
    """Execute a shell command and return the output.

    If on_progress is provided, streams output in real-time via callbacks.
    """
    sanitizer = get_sanitizer()
    is_safe, _, warnings = sanitizer.sanitize_command(command)

    if not is_safe:
        warning_text = "; ".join(warnings)
        logger.warning(f"Blocked command: {command[:100]} - {warning_text}")
        return f"[Security Error: Command blocked]\n{warning_text}"

    cwd = working_dir or os.getcwd()

    if on_progress:
        from .streaming import run_command_streaming

        return await run_command_streaming(
            command=command,
            working_dir=cwd,
            timeout=300.0,
            on_progress=on_progress,
            tool_call=tool_call,
        )

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60.0)

        output = stdout.decode("utf-8", errors="replace")
        exit_code = process.returncode

        if exit_code != 0:
            return f"{output}\n[Exit code: {exit_code}]"
        return output

    except TimeoutError:
        return "[Command timed out after 60 seconds]"
    except Exception as e:
        return f"[Error executing command: {e!s}]"


def _is_safe_path(path: str) -> bool:
    try:
        target = os.path.realpath(os.path.expanduser(path))
        cwd = os.path.realpath(os.getcwd())
        return target.startswith(cwd)
    except Exception:
        return False


async def read_file(path: str, max_lines: int | None = None) -> str:
    """Read a file and return its contents."""
    if not _is_safe_path(path):
        return f"[Security Error: Access to path '{path}' is restricted. Only files within the project directory can be accessed.]"

    try:
        expanded = os.path.expanduser(path)
        if not os.path.isabs(expanded):
            expanded = os.path.abspath(expanded)

        if not os.path.exists(expanded):
            return f"[File not found: {path}]"

        if not os.path.isfile(expanded):
            return f"[Not a file: {path}]"

        def _read_file_sync():
            with open(expanded, encoding="utf-8", errors="replace") as f:
                if max_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"\n... (truncated at {max_lines} lines)")
                            break
                        lines.append(line)
                    return "".join(lines)
                else:
                    content = f.read()
                    # Truncate very large files
                    if len(content) > 50000:
                        return content[:50000] + "\n... (truncated at 50000 chars)"
                    return content

        return await asyncio.to_thread(_read_file_sync)

    except Exception as e:
        return f"[Error reading file: {e!s}]"


def _generate_diff_summary(change: ProposedChange) -> str:
    if change.is_new_file:
        return "[New file created]"

    if not change.hunks:
        return "[No changes detected]"

    max_lines_per_section = 5
    lines = [f"[Diff: +{change.total_additions}/-{change.total_deletions}]"]
    for hunk in change.hunks:
        lines.append(
            f"@@ -{hunk.start_line},{hunk.deletions} +{hunk.start_line},{hunk.additions} @@"
        )
        for line in hunk.original_lines[:max_lines_per_section]:
            lines.append(f"- {line}")
        if len(hunk.original_lines) > max_lines_per_section:
            lines.append(
                f"  ... ({len(hunk.original_lines) - max_lines_per_section} more lines removed)"
            )
        for line in hunk.proposed_lines[:max_lines_per_section]:
            lines.append(f"+ {line}")
        if len(hunk.proposed_lines) > max_lines_per_section:
            lines.append(
                f"  ... ({len(hunk.proposed_lines) - max_lines_per_section} more lines added)"
            )

    return "\n".join(lines)


async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    if not _is_safe_path(path):
        return f"[Security Error: Access to path '{path}' is restricted. Only files within the project directory can be modified.]"

    try:
        expanded = os.path.expanduser(path)
        if not os.path.isabs(expanded):
            expanded = os.path.abspath(expanded)

        original_content: str | None = None
        if os.path.exists(expanded) and os.path.isfile(expanded):
            try:

                def _read_original():
                    with open(expanded, encoding="utf-8", errors="replace") as f:
                        return f.read()

                original_content = await asyncio.to_thread(_read_original)
            except Exception:
                pass

        def _write_file_sync():
            os.makedirs(os.path.dirname(expanded) or ".", exist_ok=True)

            with open(expanded, "w", encoding="utf-8") as f:
                f.write(content)

            return f"[Successfully wrote {len(content)} bytes to {path}]"

        result = await asyncio.to_thread(_write_file_sync)

        if original_content is not None:
            change = ProposedChange.from_content(
                file=path,
                original=original_content,
                proposed=content,
            )
            diff_summary = _generate_diff_summary(change)
            return f"{result}\n{diff_summary}"

        return f"{result}\n[New file created]"

    except Exception as e:
        return f"[Error writing file: {e!s}]"


async def todo_list() -> str:
    manager = TodoManager()
    todos = manager.load()

    if not todos:
        return "No tasks found."

    lines = []
    for t in todos:
        icon = (
            "☐"
            if t["status"] == "pending"
            else ("🔄" if t["status"] == "in_progress" else "✅")
        )
        lines.append(f"{t['id']} {icon} [{t['status']}] {t['content']}")

    return "\n".join(lines)


async def todo_add(content: str) -> str:
    manager = TodoManager()
    item = manager.add(content)
    return f"Added task {item['id']}: {item['content']}"


async def todo_update(todo_id: str, status: str) -> str:
    if status not in ("pending", "in_progress", "done"):
        return f"Invalid status '{status}'. Must be: pending, in_progress, or done"

    manager = TodoManager()
    if manager.update_status(todo_id, status):
        return f"Updated task {todo_id} to '{status}'"
    return f"Task {todo_id} not found"


async def todo_delete(todo_id: str) -> str:
    manager = TodoManager()
    if manager.delete(todo_id):
        return f"Deleted task {todo_id}"
    return f"Task {todo_id} not found"


async def agent_status() -> str:
    manager = get_agent_manager()
    if not manager:
        return "[Agent manager not initialized]"

    status = manager.get_status()

    if not status["active"]:
        return f"Agent: idle\nTotal sessions: {status['history_count']}"

    session = status["current_session"]
    lines = [
        f"Agent: {session['state']}",
        f"Session: {session['id']}",
        f"Task: {session['task']}",
        f"Iterations: {session['iterations']}",
        f"Tool calls: {session['tool_calls']}",
        f"Duration: {session['duration']:.1f}s",
    ]
    if session["errors"]:
        lines.append(f"Errors: {session['errors']}")

    return "\n".join(lines)


async def agent_history(limit: int = 5) -> str:
    manager = get_agent_manager()
    if not manager:
        return "[Agent manager not initialized]"

    sessions = manager.get_history(limit=limit)
    if not sessions:
        return "No session history available."

    lines = ["Recent agent sessions:"]
    for s in reversed(sessions):
        status = "cancelled" if s.state.value == "cancelled" else "completed"
        lines.append(
            f"  {s.id} | {status} | {s.iterations} iters | "
            f"{s.tool_calls} tools | {s.duration:.1f}s"
        )

    return "\n".join(lines)


async def agent_stats() -> str:
    manager = get_agent_manager()
    if not manager:
        return "[Agent manager not initialized]"

    stats = manager.stats.to_dict()

    if stats["total_sessions"] == 0:
        return "No agent sessions recorded yet."

    lines = [
        f"Total sessions: {stats['total_sessions']}",
        f"Total iterations: {stats['total_iterations']}",
        f"Total tool calls: {stats['total_tool_calls']}",
        f"Total tokens: {stats['total_tokens']}",
        f"Total duration: {stats['total_duration']:.1f}s",
        f"Errors: {stats['error_count']}",
        f"Avg iterations/session: {stats['avg_iterations_per_session']:.1f}",
        f"Avg tools/session: {stats['avg_tools_per_session']:.1f}",
    ]

    if stats["tool_usage"]:
        lines.append("\nTool usage:")
        for tool, count in sorted(
            stats["tool_usage"].items(), key=lambda x: x[1], reverse=True
        )[:5]:
            lines.append(f"  {tool}: {count}")

    return "\n".join(lines)


async def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """List contents of a directory."""
    if not _is_safe_path(path):
        return f"[Security Error: Access to path '{path}' is restricted. Only directories within the project directory can be listed.]"

    try:
        expanded = os.path.expanduser(path)
        if not os.path.isabs(expanded):
            expanded = os.path.abspath(expanded)

        if not os.path.exists(expanded):
            return f"[Directory not found: {path}]"

        if not os.path.isdir(expanded):
            return f"[Not a directory: {path}]"

        entries = []
        for entry in sorted(os.listdir(expanded)):
            if not show_hidden and entry.startswith("."):
                continue

            full_path = os.path.join(expanded, entry)
            if os.path.isdir(full_path):
                entries.append(f"{entry}/")
            else:
                size = os.path.getsize(full_path)
                entries.append(f"{entry} ({size} bytes)")

        if not entries:
            return "[Directory is empty]"

        return "\n".join(entries)

    except Exception as e:
        return f"[Error listing directory: {e!s}]"


# Define built-in tools with their schemas
BUILTIN_TOOLS: list[BuiltinTool] = [
    BuiltinTool(
        name="run_command",
        description="Execute a shell command in the terminal. Use this to run CLI commands, scripts, or system utilities.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for the command (optional)",
                },
            },
            "required": ["command"],
        },
        handler=run_command,
        requires_approval=True,
    ),
    BuiltinTool(
        name="read_file",
        description="Read the contents of a file. Use this to examine source code, configuration files, or any text file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (optional)",
                },
            },
            "required": ["path"],
        },
        handler=read_file,
        requires_approval=False,
    ),
    BuiltinTool(
        name="write_file",
        description="Write content to a file. Creates the file if it doesn't exist, or overwrites if it does.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        handler=write_file,
        requires_approval=True,
    ),
    BuiltinTool(
        name="list_directory",
        description="List the contents of a directory. Shows files and subdirectories.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory (defaults to current directory)",
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Whether to show hidden files (default: false)",
                },
            },
            "required": [],
        },
        handler=list_directory,
        requires_approval=False,
    ),
    BuiltinTool(
        name="todo_list",
        description="List all tasks in the todo list with their IDs, status, and content.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=todo_list,
        requires_approval=False,
    ),
    BuiltinTool(
        name="todo_add",
        description="Add a new task to the todo list.",
        input_schema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The task description",
                },
            },
            "required": ["content"],
        },
        handler=todo_add,
        requires_approval=False,
    ),
    BuiltinTool(
        name="todo_update",
        description="Update the status of an existing task. Status can be: pending, in_progress, or done.",
        input_schema={
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "The task ID (8 character string)",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done"],
                    "description": "The new status for the task",
                },
            },
            "required": ["todo_id", "status"],
        },
        handler=todo_update,
        requires_approval=False,
    ),
    BuiltinTool(
        name="todo_delete",
        description="Delete a task from the todo list.",
        input_schema={
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "The task ID to delete",
                },
            },
            "required": ["todo_id"],
        },
        handler=todo_delete,
        requires_approval=False,
    ),
    BuiltinTool(
        name="agent_status",
        description="Get the current agent status including state, session info, iterations, and tool calls.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=agent_status,
        requires_approval=False,
    ),
    BuiltinTool(
        name="agent_history",
        description="Get recent agent session history with stats for each session.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of sessions to return (default: 5)",
                },
            },
            "required": [],
        },
        handler=agent_history,
        requires_approval=False,
    ),
    BuiltinTool(
        name="agent_stats",
        description="Get cumulative agent statistics across all sessions including tool usage breakdown.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=agent_stats,
        requires_approval=False,
    ),
]


def get_builtin_tool(name: str) -> BuiltinTool | None:
    """Get a built-in tool by name."""
    for tool in BUILTIN_TOOLS:
        if tool.name == name:
            return tool
    return None
