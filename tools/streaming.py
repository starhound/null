"""Streaming tool execution with real-time progress updates."""

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolStatus(Enum):
    """Status of a streaming tool execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolProgress:
    """Progress update from a streaming tool."""

    status: ToolStatus
    output: str  # Cumulative output
    progress: float | None = None  # 0.0 - 1.0 if determinable
    elapsed: float = 0.0  # Seconds since start
    exit_code: int | None = None

    @property
    def is_complete(self) -> bool:
        """Check if the tool has finished executing."""
        return self.status in (
            ToolStatus.COMPLETED,
            ToolStatus.FAILED,
            ToolStatus.CANCELLED,
        )


@dataclass
class StreamingToolCall:
    """A tool call that supports streaming output."""

    id: str
    name: str
    arguments: dict[str, Any]
    _cancelled: bool = field(default=False, repr=False)

    def cancel(self) -> None:
        """Request cancellation of this tool execution."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


ProgressCallback = Callable[[ToolProgress], None]


async def run_command_streaming(
    command: str,
    working_dir: str | None = None,
    timeout: float = 300.0,
    on_progress: ProgressCallback | None = None,
    tool_call: StreamingToolCall | None = None,
) -> str:
    """Execute a shell command with streaming output.

    Args:
        command: The shell command to execute
        working_dir: Working directory for the command
        timeout: Maximum execution time in seconds
        on_progress: Callback for progress updates
        tool_call: Optional StreamingToolCall for cancellation support

    Returns:
        The complete command output
    """
    import os

    cwd = working_dir or os.getcwd()
    output_buffer: list[str] = []
    start_time = time.time()

    def emit_progress(status: ToolStatus, exit_code: int | None = None) -> None:
        if on_progress:
            on_progress(
                ToolProgress(
                    status=status,
                    output="".join(output_buffer),
                    elapsed=time.time() - start_time,
                    exit_code=exit_code,
                )
            )

    try:
        # Create subprocess with PTY-like behavior for better output
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        emit_progress(ToolStatus.RUNNING)

        assert process.stdout is not None

        # Stream output line by line
        while True:
            # Check for cancellation
            if tool_call and tool_call.is_cancelled:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except TimeoutError:
                    process.kill()
                emit_progress(ToolStatus.CANCELLED)
                return "".join(output_buffer) + "\n[Cancelled by user]"

            try:
                # Read with timeout to allow checking cancellation
                line = await asyncio.wait_for(process.stdout.readline(), timeout=0.1)
            except TimeoutError:
                # Check overall timeout
                if time.time() - start_time > timeout:
                    process.terminate()
                    emit_progress(ToolStatus.FAILED, exit_code=-1)
                    return "".join(output_buffer) + f"\n[Timed out after {timeout}s]"
                continue

            if not line:
                # EOF reached
                break

            chunk = line.decode("utf-8", errors="replace")
            output_buffer.append(chunk)
            emit_progress(ToolStatus.RUNNING)

        # Wait for process to complete
        await process.wait()
        exit_code = process.returncode

        final_output = "".join(output_buffer)

        if exit_code == 0:
            emit_progress(ToolStatus.COMPLETED, exit_code=exit_code)
        else:
            if not final_output.endswith("\n"):
                final_output += "\n"
            final_output += f"[Exit code: {exit_code}]"
            emit_progress(ToolStatus.FAILED, exit_code=exit_code)

        return final_output

    except asyncio.CancelledError:
        emit_progress(ToolStatus.CANCELLED)
        raise
    except Exception as e:
        error_msg = f"[Error executing command: {e!s}]"
        output_buffer.append(error_msg)
        emit_progress(ToolStatus.FAILED)
        return "".join(output_buffer)


async def stream_command(
    command: str,
    working_dir: str | None = None,
    timeout: float = 300.0,
    tool_call: StreamingToolCall | None = None,
) -> AsyncIterator[ToolProgress]:
    """Execute a command and yield progress updates as an async iterator.

    This is an alternative API that yields ToolProgress updates directly.

    Args:
        command: The shell command to execute
        working_dir: Working directory for the command
        timeout: Maximum execution time in seconds
        tool_call: Optional StreamingToolCall for cancellation support

    Yields:
        ToolProgress updates as the command executes
    """
    import os

    cwd = working_dir or os.getcwd()
    output_buffer: list[str] = []
    start_time = time.time()

    def make_progress(status: ToolStatus, exit_code: int | None = None) -> ToolProgress:
        return ToolProgress(
            status=status,
            output="".join(output_buffer),
            elapsed=time.time() - start_time,
            exit_code=exit_code,
        )

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )

        yield make_progress(ToolStatus.RUNNING)

        assert process.stdout is not None

        while True:
            # Check cancellation
            if tool_call and tool_call.is_cancelled:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except TimeoutError:
                    process.kill()
                output_buffer.append("\n[Cancelled by user]")
                yield make_progress(ToolStatus.CANCELLED)
                return

            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=0.1)
            except TimeoutError:
                if time.time() - start_time > timeout:
                    process.terminate()
                    output_buffer.append(f"\n[Timed out after {timeout}s]")
                    yield make_progress(ToolStatus.FAILED, exit_code=-1)
                    return
                continue

            if not line:
                break

            chunk = line.decode("utf-8", errors="replace")
            output_buffer.append(chunk)
            yield make_progress(ToolStatus.RUNNING)

        await process.wait()
        exit_code = process.returncode

        if exit_code != 0:
            output_buffer.append(f"\n[Exit code: {exit_code}]")
            yield make_progress(ToolStatus.FAILED, exit_code=exit_code)
        else:
            yield make_progress(ToolStatus.COMPLETED, exit_code=exit_code)

    except asyncio.CancelledError:
        yield make_progress(ToolStatus.CANCELLED)
        raise
    except Exception as e:
        output_buffer.append(f"[Error: {e!s}]")
        yield make_progress(ToolStatus.FAILED)


# Progress parsing for common commands
PROGRESS_PATTERNS: dict[str, list[tuple[str, float]]] = {
    "npm": [
        ("npm WARN", 0.3),
        ("added", 0.9),
        ("packages in", 1.0),
    ],
    "pip": [
        ("Collecting", 0.2),
        ("Downloading", 0.5),
        ("Installing", 0.8),
        ("Successfully installed", 1.0),
    ],
    "cargo": [
        ("Compiling", 0.3),
        ("Finished", 1.0),
    ],
    "pytest": [
        ("collected", 0.1),
        ("passed", 0.9),
        ("failed", 0.9),
    ],
}


def estimate_progress(command: str, output: str) -> float | None:
    """Estimate progress based on command type and output patterns.

    Returns a value between 0.0 and 1.0, or None if progress can't be determined.
    """
    cmd_lower = command.lower()

    for cmd_prefix, patterns in PROGRESS_PATTERNS.items():
        if cmd_prefix in cmd_lower:
            # Find the highest matching pattern
            max_progress = 0.0
            for pattern, progress in patterns:
                if pattern.lower() in output.lower():
                    max_progress = max(max_progress, progress)
            if max_progress > 0:
                return max_progress

    return None
