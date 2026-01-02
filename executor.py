import asyncio
import os
import signal
from typing import Callable, Optional

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

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True,
                executable=shell
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
