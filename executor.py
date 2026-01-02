import asyncio
import os
import re
import signal
from typing import Callable, Optional


# Commands that support --color=always flag
COLOR_COMMANDS = {
    'ls', 'grep', 'egrep', 'fgrep', 'diff', 'ip', 'pacman', 'tree',
}

# Commands that support color via different flags
COLOR_FLAGS = {
    'git': ['config', 'color.ui=always'],  # Handled via env var instead
}


def _add_color_to_command(command: str) -> str:
    """Add color flags to commands that support them."""
    # Split on pipes and process each part
    parts = command.split('|')
    result_parts = []

    for part in parts:
        part = part.strip()
        if not part:
            result_parts.append(part)
            continue

        # Get the base command (first word)
        tokens = part.split()
        if not tokens:
            result_parts.append(part)
            continue

        base_cmd = os.path.basename(tokens[0])

        # Check if it's a color-supporting command without color flag already
        if base_cmd in COLOR_COMMANDS:
            if '--color' not in part and '-G' not in part:
                # Insert --color=always after the command name
                tokens.insert(1, '--color=always')
                part = ' '.join(tokens)

        result_parts.append(part)

    return ' | '.join(result_parts)


class ExecutionEngine:
    """Engine for executing shell commands with cancellation support."""

    def __init__(self):
        self.active_process: Optional[asyncio.subprocess.Process] = None
        self._cancelled = False

    async def run_command_and_get_rc(self, command: str, callback: Callable[[str], None]) -> int:
        """
        Runs command, calls callback with stdout lines, returns exit code.
        Returns -1 if cancelled.
        """
        # Respect SHELL env var, default to /bin/bash on Linux
        shell = os.environ.get("SHELL", "/bin/bash")
        self._cancelled = False

        # Build environment with color output enabled by default
        env = os.environ.copy()
        env.setdefault("CLICOLOR", "1")
        env.setdefault("CLICOLOR_FORCE", "1")
        env.setdefault("FORCE_COLOR", "1")
        # Git color support
        env.setdefault("GIT_CONFIG_PARAMETERS", "'color.ui=always'")
        # Ensure TERM supports colors
        if env.get("TERM", "").startswith("dumb"):
            env["TERM"] = "xterm-256color"

        # Add color flags to supported commands
        command = _add_color_to_command(command)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True,
                executable=shell,
                env=env
            )
            self.active_process = process

            if process.stdout:
                while True:
                    if self._cancelled:
                        break
                    try:
                        line = await asyncio.wait_for(process.stdout.readline(), timeout=0.1)
                        if not line:
                            break
                        decoded_line = line.decode("utf-8", errors="replace")
                        callback(decoded_line)
                    except asyncio.TimeoutError:
                        continue

            # Wait for the process to exit
            try:
                if self._cancelled:
                    callback("\n[Cancelled]\n")
                    return -1
                return await process.wait()
            except ChildProcessError:
                return process.returncode if process.returncode is not None else 255

        except asyncio.CancelledError:
            callback("\n[Cancelled]\n")
            return -1
        except Exception as e:
            callback(f"Error executing command: {e}\n")
            return 127
        finally:
            self.active_process = None

    def cancel(self):
        """Cancel the currently running process."""
        self._cancelled = True
        if self.active_process:
            try:
                # Try graceful termination first
                self.active_process.terminate()
            except ProcessLookupError:
                pass  # Process already exited
            except Exception:
                try:
                    # Force kill if terminate fails
                    self.active_process.kill()
                except Exception:
                    pass

    @property
    def is_running(self) -> bool:
        """Check if a process is currently running."""
        return self.active_process is not None
