import asyncio
import codecs
import fcntl
import os
import pty
import signal
import struct
import termios
from collections.abc import Callable
from typing import Literal

from config import get_settings


def _waitpid_nohang(pid: int) -> tuple[int, int]:
    """Wrapper for os.waitpid with WNOHANG to use in executor."""
    return os.waitpid(pid, os.WNOHANG)


def _waitpid_blocking(pid: int) -> tuple[int, int]:
    """Wrapper for os.waitpid (blocking) to use in executor."""
    return os.waitpid(pid, 0)


# Alternate screen buffer sequences (apps like vim)
ALTERNATE_SCREEN_ENTER = [
    b"\x1b[?1049h",  # Most common (xterm) - vim, nano, less
    b"\x1b[?1047h",  # Alternate buffer
    b"\x1b[?47h",  # Legacy xterm
]
ALTERNATE_SCREEN_EXIT = [
    b"\x1b[?1049l",
    b"\x1b[?1047l",
    b"\x1b[?47l",
]

# Full-screen TUI indicators (apps like top that don't use alternate screen)
# These apps clear screen and hide cursor
TUI_ENTER_INDICATORS = [
    b"\x1b[?25l\x1b[H",  # Hide cursor + home (top)
    b"\x1b[H\x1b[2J\x1b[?25l",  # Home + clear + hide cursor
    b"\x1b[2J\x1b[H\x1b[?25l",  # Clear + home + hide cursor
]
TUI_EXIT_INDICATORS = [
    b"\x1b[?25h",  # Show cursor
]


class ExecutionEngine:
    """Engine for executing shell commands with PTY support for proper colors."""

    def __init__(self) -> None:
        self._pid: int | None = None
        self._master_fd: int | None = None
        self._cancelled = False
        self._in_tui_mode = False
        self._detection_buffer = b""
        # Incremental UTF-8 decoder to handle multibyte chars split across reads
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    @property
    def pid(self) -> int | None:
        """Get the current process ID."""
        return self._pid

    @property
    def master_fd(self) -> int | None:
        """Get the PTY master file descriptor."""
        return self._master_fd

    @property
    def in_tui_mode(self) -> bool:
        """Check if currently in TUI (alternate screen) mode."""
        return self._in_tui_mode

    def _detect_screen_mode(self, data: bytes) -> Literal["enter", "exit"] | None:
        """Detect if data contains TUI mode switch sequences.

        Detects both:
        1. Alternate screen buffer (vim, nano, less)
        2. Full-screen clear (top, htop)

        Returns:
            'enter' if entering TUI mode, 'exit' if exiting, None otherwise
        """
        # Check for alternate screen buffer (highest priority)
        for seq in ALTERNATE_SCREEN_ENTER:
            if seq in data:
                return "enter"
        for seq in ALTERNATE_SCREEN_EXIT:
            if seq in data:
                return "exit"

        # Check for TUI-style apps that don't use alternate screen
        # Only trigger if we see clear screen AND hide cursor together
        has_clear = b"\x1b[2J" in data or b"\x1b[H\x1b[J" in data
        has_hide_cursor = b"\x1b[?25l" in data

        if has_clear and has_hide_cursor and not self._in_tui_mode:
            return "enter"

        # Check for cursor show (might indicate TUI exit)
        if self._in_tui_mode and b"\x1b[?25h" in data:
            # Only exit if we also see some indication of normal mode
            # This prevents false exits from apps that briefly show cursor
            has_show_cursor = b"\x1b[?25h" in data
            if has_show_cursor and not has_hide_cursor:
                return "exit"

        return None

    async def run_command_and_get_rc(
        self,
        command: str,
        callback: Callable[[str], None],
        mode_callback: Callable[[str, bytes], None] | None = None,
        raw_callback: Callable[[bytes], None] | None = None,
        ready_event: asyncio.Event | None = None,
    ) -> int:
        """
        Runs command in a PTY, calls callback with output, returns exit code.

        Args:
            command: The shell command to run
            callback: Called with decoded line output (for normal display)
            mode_callback: Called when TUI mode changes ('enter'/'exit', raw_data)
            raw_callback: Called with raw bytes when in TUI mode (for pyte)

        Returns:
            Exit code, or -1 if cancelled.
        """
        settings = get_settings()
        shell = settings.terminal.shell or os.environ.get("SHELL", "/bin/bash")
        self._cancelled = False
        self._in_tui_mode = False
        self._detection_buffer = b""
        # Reset decoder for new command
        self._decoder.reset()

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
                winsize = struct.pack("HHHH", 24, 120, 0, 0)
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

                os.execvpe(shell, [shell, "-c", command], env)

            # Parent process
            os.close(slave_fd)
            self._pid = pid
            if ready_event:
                ready_event.set()

            # Make master non-blocking
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            # Read output asynchronously
            loop = asyncio.get_running_loop()
            buffer = b""

            while True:
                if self._cancelled:
                    break

                # Optimistic read loop - drain the buffer before yielding
                # This significantly improves throughput for large outputs (cat, ls -R)
                data_read = False
                while True:
                    try:
                        # Non-blocking read attempt
                        chunk = os.read(master_fd, 65536)  # Read up to 64KB
                        if not chunk:
                            # EOF detected during read loop
                            break

                        data_read = True

                        # --- Processing Logic (Inline for speed) ---
                        # Check for TUI mode changes
                        check_data = self._detection_buffer + chunk
                        mode_change = self._detect_screen_mode(check_data)

                        if len(check_data) > 50:
                            self._detection_buffer = check_data[-50:]
                        else:
                            self._detection_buffer = check_data

                        if mode_change == "enter" and not self._in_tui_mode:
                            self._in_tui_mode = True
                            if mode_callback:
                                mode_callback("enter", chunk)
                            if raw_callback:
                                raw_callback(chunk)
                            buffer = b""
                            continue
                        elif mode_change == "exit" and self._in_tui_mode:
                            self._in_tui_mode = False
                            if mode_callback:
                                mode_callback("exit", chunk)
                            buffer = b""
                            continue

                        if self._in_tui_mode:
                            if raw_callback:
                                raw_callback(chunk)
                            continue

                        # Normal line buffering
                        buffer += chunk
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            decoded = self._decoder.decode(line.rstrip(b"\r")) + "\n"
                            callback(decoded)

                        # Partial flush check happens after the burst

                    except BlockingIOError:
                        # No more data currently available
                        break
                    except OSError:
                        # PTY closed or error
                        break

                # After draining the buffer, check if we need to flush partials
                if data_read and buffer:
                    # Partial flush logic for prompts
                    lower_buf = buffer.lower()
                    is_prompt = (
                        b"\r" in buffer
                        or b"password" in lower_buf
                        or b"passphrase" in lower_buf
                        or b"[y/n]" in lower_buf
                        or b"(yes/no)" in lower_buf
                        or b"continue?" in lower_buf
                        or buffer.rstrip().endswith(b":")
                        or buffer.rstrip().endswith(b"?")
                    )
                    if is_prompt:
                        decoded = self._decoder.decode(buffer)
                        callback(decoded)
                        buffer = b""

                # Now check for exit or sleep
                if not data_read:
                    # No data was read in this cycle, check if process died
                    try:
                        pid_result = os.waitpid(pid, os.WNOHANG)  # noqa: ASYNC222
                        if pid_result[0] != 0:
                            break
                    except ChildProcessError:
                        break

                    # Wait for data availability (yield to loop)
                    await asyncio.sleep(0.01)
                else:
                    # We read data, so we yield briefly to let UI update, then loop back immediately
                    await asyncio.sleep(0)

            # Output any remaining buffer
            if buffer:
                callback(self._decoder.decode(buffer, final=True))

            # Wait for process to finish and get exit code
            if self._cancelled:
                try:
                    os.kill(pid, signal.SIGTERM)
                    # Give it a moment to terminate gracefully
                    await asyncio.sleep(0.1)
                    # Force kill if still running
                    try:
                        os.kill(pid, 0)  # Check if still alive
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass
                callback("\n[Cancelled]\n")
                try:
                    await loop.run_in_executor(None, _waitpid_blocking, pid)
                except ChildProcessError:
                    pass
                return -1

            try:
                _, status = await loop.run_in_executor(None, _waitpid_blocking, pid)
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
            self._in_tui_mode = False
            if self._master_fd is not None:
                try:
                    os.close(self._master_fd)
                except Exception:
                    pass
                self._master_fd = None

    def cancel(self) -> None:
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
