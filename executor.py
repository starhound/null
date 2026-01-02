import asyncio
import os
import pty
import signal
import fcntl
import struct
import termios
from typing import Callable, Optional


class ExecutionEngine:
    """Engine for executing shell commands with PTY support for proper colors."""

    def __init__(self):
        self._pid: Optional[int] = None
        self._master_fd: Optional[int] = None
        self._cancelled = False

    async def run_command_and_get_rc(self, command: str, callback: Callable[[str], None]) -> int:
        """
        Runs command in a PTY, calls callback with output, returns exit code.
        Returns -1 if cancelled.
        """
        shell = os.environ.get("SHELL", "/bin/bash")
        self._cancelled = False

        # Build environment with color support
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        env.setdefault("COLORTERM", "truecolor")
        env.setdefault("CLICOLOR", "1")
        env.setdefault("CLICOLOR_FORCE", "1")
        env.setdefault("FORCE_COLOR", "1")

        try:
            # Create PTY
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd

            # Set terminal size (80x24 default, could be dynamic)
            try:
                winsize = struct.pack('HHHH', 24, 120, 0, 0)
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
            except Exception:
                pass

            # Fork the process
            pid = os.fork()

            if pid == 0:
                # Child process
                os.close(master_fd)
                os.setsid()

                # Set up slave as controlling terminal
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

                # Redirect stdio to slave
                os.dup2(slave_fd, 0)
                os.dup2(slave_fd, 1)
                os.dup2(slave_fd, 2)

                if slave_fd > 2:
                    os.close(slave_fd)

                # Execute the command with interactive shell to load aliases
                os.execvpe(shell, [shell, "-i", "-c", command], env)

            # Parent process
            os.close(slave_fd)
            self._pid = pid

            # Make master non-blocking for async reading
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Read output asynchronously
            loop = asyncio.get_event_loop()
            buffer = b""

            while True:
                if self._cancelled:
                    break

                try:
                    # Use asyncio to read without blocking
                    data = await loop.run_in_executor(
                        None, self._read_master, master_fd
                    )

                    if data is None:
                        # Check if process exited
                        result = os.waitpid(pid, os.WNOHANG)
                        if result[0] != 0:
                            break
                        await asyncio.sleep(0.01)
                        continue

                    if data:
                        buffer += data
                        # Process complete lines
                        while b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            # Strip carriage returns from line endings
                            decoded = line.rstrip(b'\r').decode('utf-8', errors='replace') + '\n'
                            callback(decoded)
                        # Also output partial lines (for progress indicators etc)
                        if buffer and b'\r' in buffer:
                            decoded = buffer.decode('utf-8', errors='replace')
                            callback(decoded)
                            buffer = b""

                except (IOError, OSError) as e:
                    if e.errno == 5:  # EIO - PTY closed
                        break
                    await asyncio.sleep(0.01)

            # Output any remaining buffer
            if buffer:
                callback(buffer.decode('utf-8', errors='replace'))

            # Wait for process to finish and get exit code
            if self._cancelled:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                callback("\n[Cancelled]\n")
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
                return -1

            try:
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    return os.WEXITSTATUS(status)
                elif os.WIFSIGNALED(status):
                    return 128 + os.WTERMSIG(status)
                return 255
            except ChildProcessError:
                return 0

        except Exception as e:
            callback(f"Error executing command: {e}\n")
            return 127
        finally:
            self._pid = None
            if self._master_fd is not None:
                try:
                    os.close(self._master_fd)
                except Exception:
                    pass
                self._master_fd = None

    def _read_master(self, fd: int) -> Optional[bytes]:
        """Read from master fd, returns None if would block."""
        try:
            return os.read(fd, 4096)
        except BlockingIOError:
            return None
        except OSError as e:
            if e.errno == 5:  # EIO
                raise
            return None

    def cancel(self):
        """Cancel the currently running process."""
        self._cancelled = True
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except Exception:
                try:
                    os.kill(self._pid, signal.SIGKILL)
                except Exception:
                    pass

    @property
    def is_running(self) -> bool:
        """Check if a process is currently running."""
        return self._pid is not None
