"""Process manager for tracking and controlling running commands."""

import os
import signal
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProcessInfo:
    """Information about a running process."""

    pid: int
    command: str
    block_id: str
    start_time: datetime = field(default_factory=datetime.now)
    is_tui: bool = False
    master_fd: int | None = None  # PTY master fd for sending signals
    executor: Any = None  # ExecutionEngine instance


class ProcessManager:
    """Manages running processes and provides control operations."""

    def __init__(self):
        self._processes: dict[str, ProcessInfo] = {}
        self._on_change_callbacks: list[Callable[[], None]] = []

    def register(
        self,
        block_id: str,
        pid: int,
        command: str,
        master_fd: int | None = None,
        is_tui: bool = False,
        executor: Any = None,
    ) -> None:
        """Register a new running process."""
        self._processes[block_id] = ProcessInfo(
            pid=pid,
            command=command,
            block_id=block_id,
            master_fd=master_fd,
            is_tui=is_tui,
            executor=executor,
        )
        self._notify_change()

    def unregister(self, block_id: str) -> None:
        """Unregister a process (when it completes or is stopped)."""
        if block_id in self._processes:
            del self._processes[block_id]
            self._notify_change()

    def get(self, block_id: str) -> ProcessInfo | None:
        """Get info for a specific process."""
        return self._processes.get(block_id)

    def get_running(self) -> list[ProcessInfo]:
        """Get all running processes."""
        return list(self._processes.values())

    def get_count(self) -> int:
        """Get count of running processes."""
        return len(self._processes)

    def is_running(self, block_id: str) -> bool:
        """Check if a process is running."""
        return block_id in self._processes

    def stop(self, block_id: str, force: bool = False) -> bool:
        """Stop a process by block ID.

        Args:
            block_id: The block ID of the process to stop
            force: If True, send SIGKILL instead of SIGTERM

        Returns:
            True if signal was sent, False if process not found
        """
        info = self._processes.get(block_id)
        if not info:
            return False

        try:
            if info.executor:
                try:
                    info.executor.cancel()
                except Exception:
                    pass

            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(info.pid, sig)
            return True
        except ProcessLookupError:
            # Process already dead
            self.unregister(block_id)
            return False
        except Exception:
            return False

    def send_interrupt(self, block_id: str) -> bool:
        """Send SIGINT (Ctrl+C) to a process.

        Returns:
            True if signal was sent, False if process not found
        """
        info = self._processes.get(block_id)
        if not info:
            return False

        try:
            os.kill(info.pid, signal.SIGINT)
            return True
        except ProcessLookupError:
            self.unregister(block_id)
            return False
        except Exception:
            return False

    def send_input(self, block_id: str, data: bytes) -> bool:
        """Send input data to a process's PTY.

        Args:
            block_id: The block ID of the process
            data: Bytes to write to the PTY

        Returns:
            True if data was written, False otherwise
        """
        info = self._processes.get(block_id)
        if not info or info.master_fd is None:
            return False

        try:
            os.write(info.master_fd, data)
            return True
        except Exception:
            return False

    def stop_all(self, force: bool = False) -> int:
        """Stop all running processes.

        Returns:
            Number of processes signaled
        """
        count = 0
        for block_id in list(self._processes.keys()):
            if self.stop(block_id, force=force):
                count += 1
        return count

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register a callback to be notified when processes change."""
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify all registered callbacks of a change."""
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception:
                pass

    def set_tui_mode(self, block_id: str, is_tui: bool) -> None:
        """Update TUI mode status for a process."""
        info = self._processes.get(block_id)
        if info:
            info.is_tui = is_tui
            self._notify_change()
