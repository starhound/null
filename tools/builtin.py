"""Built-in tools for the AI to use."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class BuiltinTool:
    """A built-in tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[str]]
    requires_approval: bool = True  # Whether to ask user before executing


async def run_command(command: str, working_dir: str | None = None) -> str:
    """Execute a shell command and return the output."""
    cwd = working_dir or os.getcwd()

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


async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    if not _is_safe_path(path):
        return f"[Security Error: Access to path '{path}' is restricted. Only files within the project directory can be modified.]"

    try:
        expanded = os.path.expanduser(path)
        if not os.path.isabs(expanded):
            expanded = os.path.abspath(expanded)

        def _write_file_sync():
            # Create parent directories if needed
            os.makedirs(os.path.dirname(expanded), exist_ok=True)

            with open(expanded, "w", encoding="utf-8") as f:
                f.write(content)

            return f"[Successfully wrote {len(content)} bytes to {path}]"

        return await asyncio.to_thread(_write_file_sync)

    except Exception as e:
        return f"[Error writing file: {e!s}]"


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
]


def get_builtin_tool(name: str) -> BuiltinTool | None:
    """Get a built-in tool by name."""
    for tool in BUILTIN_TOOLS:
        if tool.name == name:
            return tool
    return None
