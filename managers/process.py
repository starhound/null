"""Process manager for tracking and controlling running commands."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore

if TYPE_CHECKING:
    pass


@dataclass
class ResourceUsage:
    """Resource usage statistics for a process."""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    num_threads: int = 1
    status: str = "running"


@dataclass
class ProcessNode:
    """A node in the process tree representing a process and its children."""

    pid: int
    name: str
    command: str
    parent_pid: int | None
    children: list[ProcessNode] = field(default_factory=list)
    resources: ResourceUsage = field(default_factory=ResourceUsage)
    depth: int = 0

    def get_all_pids(self) -> list[int]:
        """Get all PIDs in this subtree (self + all descendants)."""
        pids = [self.pid]
        for child in self.children:
            pids.extend(child.get_all_pids())
        return pids


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
    resources: ResourceUsage = field(default_factory=ResourceUsage)


class ProcessTree:
    """Manages process tree relationships and operations."""

    def __init__(self):
        self._cache: dict[int, ProcessNode] = {}
        self._last_update: datetime | None = None
        self._cache_ttl_seconds = 2.0

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._last_update is None:
            return False
        age = (datetime.now() - self._last_update).total_seconds()
        return age < self._cache_ttl_seconds

    def get_process_tree(self, root_pid: int) -> ProcessNode | None:
        """Build a process tree starting from root_pid.

        Args:
            root_pid: The PID of the root process

        Returns:
            ProcessNode representing the tree, or None if process not found
        """
        if not PSUTIL_AVAILABLE:
            # Fallback: return basic info without tree
            try:
                os.kill(root_pid, 0)  # Check if process exists
                return ProcessNode(
                    pid=root_pid,
                    name="unknown",
                    command="unknown",
                    parent_pid=None,
                )
            except (ProcessLookupError, PermissionError):
                return None

        try:
            proc = psutil.Process(root_pid)
            return self._build_node(proc, depth=0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def _build_node(self, proc: psutil.Process, depth: int = 0) -> ProcessNode:
        """Recursively build a ProcessNode from a psutil.Process."""
        try:
            name = proc.name()
            cmdline = proc.cmdline()
            command = " ".join(cmdline) if cmdline else name
            parent = proc.parent()
            parent_pid = parent.pid if parent else None

            # Get resource usage
            resources = self._get_resources(proc)

            node = ProcessNode(
                pid=proc.pid,
                name=name,
                command=command[:100],  # Truncate long commands
                parent_pid=parent_pid,
                resources=resources,
                depth=depth,
            )

            # Build children
            try:
                children = proc.children(recursive=False)
                for child in children:
                    try:
                        child_node = self._build_node(child, depth=depth + 1)
                        node.children.append(child_node)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return node

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            raise e

    def _get_resources(self, proc: psutil.Process) -> ResourceUsage:
        """Get resource usage for a process."""
        try:
            with proc.oneshot():
                cpu = proc.cpu_percent(interval=0)
                mem_info = proc.memory_info()
                mem_percent = proc.memory_percent()
                num_threads = proc.num_threads()
                status = proc.status()

            return ResourceUsage(
                cpu_percent=cpu,
                memory_mb=mem_info.rss / (1024 * 1024),
                memory_percent=mem_percent,
                num_threads=num_threads,
                status=status,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ResourceUsage()

    def get_children_pids(self, pid: int, recursive: bool = True) -> list[int]:
        """Get all child PIDs of a process.

        Args:
            pid: Parent process ID
            recursive: If True, include all descendants; otherwise only direct children

        Returns:
            List of child PIDs
        """
        if not PSUTIL_AVAILABLE:
            return []

        try:
            proc = psutil.Process(pid)
            children = proc.children(recursive=recursive)
            return [c.pid for c in children]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []

    def get_total_resources(self, pid: int) -> ResourceUsage:
        """Get combined resource usage for a process and all its children.

        Args:
            pid: Root process ID

        Returns:
            Combined ResourceUsage for the process tree
        """
        if not PSUTIL_AVAILABLE:
            return ResourceUsage()

        total = ResourceUsage()
        try:
            proc = psutil.Process(pid)
            procs = [proc] + proc.children(recursive=True)

            for p in procs:
                try:
                    resources = self._get_resources(p)
                    total.cpu_percent += resources.cpu_percent
                    total.memory_mb += resources.memory_mb
                    total.memory_percent += resources.memory_percent
                    total.num_threads += resources.num_threads
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            total.status = "running"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            total.status = "dead"

        return total


class ProcessManager:
    """Manages running processes and provides control operations."""

    def __init__(self):
        self._processes: dict[str, ProcessInfo] = {}
        self._on_change_callbacks: list[Callable[[], None]] = []
        self._process_tree = ProcessTree()
        self._resource_update_task: asyncio.Task | None = None

    @property
    def process_tree(self) -> ProcessTree:
        """Get the process tree manager."""
        return self._process_tree

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

    def get_process_tree_view(self, block_id: str) -> ProcessNode | None:
        """Get the process tree for a registered process.

        Args:
            block_id: The block ID of the registered process

        Returns:
            ProcessNode tree or None if not found
        """
        info = self._processes.get(block_id)
        if not info:
            return None
        return self._process_tree.get_process_tree(info.pid)

    def update_resources(self, block_id: str) -> ResourceUsage:
        """Update and return resource usage for a process.

        Args:
            block_id: The block ID of the process

        Returns:
            Updated ResourceUsage
        """
        info = self._processes.get(block_id)
        if not info:
            return ResourceUsage()

        resources = self._process_tree.get_total_resources(info.pid)
        info.resources = resources
        return resources

    def update_all_resources(self) -> dict[str, ResourceUsage]:
        """Update resource usage for all tracked processes.

        Returns:
            Dict mapping block_id to ResourceUsage
        """
        results = {}
        for block_id in list(self._processes.keys()):
            results[block_id] = self.update_resources(block_id)
        return results

    async def start_resource_monitoring(self, interval: float = 2.0) -> None:
        """Start background task to periodically update resource usage.

        Args:
            interval: Update interval in seconds
        """
        if self._resource_update_task is not None:
            return

        async def monitor():
            while True:
                try:
                    self.update_all_resources()
                    self._notify_change()
                except Exception:
                    pass
                await asyncio.sleep(interval)

        self._resource_update_task = asyncio.create_task(monitor())

    def stop_resource_monitoring(self) -> None:
        """Stop the background resource monitoring task."""
        if self._resource_update_task:
            self._resource_update_task.cancel()
            self._resource_update_task = None

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

    async def graceful_kill(
        self,
        block_id: str,
        timeout: float = 5.0,
        include_children: bool = True,
    ) -> bool:
        """Gracefully kill a process: SIGTERM first, then SIGKILL after timeout.

        Args:
            block_id: The block ID of the process to kill
            timeout: Seconds to wait after SIGTERM before sending SIGKILL
            include_children: If True, also kill all child processes

        Returns:
            True if process was killed, False if not found or error
        """
        info = self._processes.get(block_id)
        if not info:
            return False

        pid = info.pid
        pids_to_kill = [pid]

        # Get children if requested
        if include_children:
            children = self._process_tree.get_children_pids(pid, recursive=True)
            pids_to_kill.extend(children)

        # Cancel executor if present
        if info.executor:
            try:
                info.executor.cancel()
            except Exception:
                pass

        # Send SIGTERM to all processes (children first, then parent)
        for target_pid in reversed(pids_to_kill):
            try:
                os.kill(target_pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                continue

        # Wait for timeout
        await asyncio.sleep(timeout)

        # Check if processes are still alive and send SIGKILL
        for target_pid in reversed(pids_to_kill):
            try:
                os.kill(target_pid, 0)
                os.kill(target_pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                continue

        await asyncio.sleep(0.1)

        # Reap zombie processes
        for target_pid in pids_to_kill:
            try:
                os.waitpid(target_pid, os.WNOHANG)
            except (ChildProcessError, OSError):
                pass

        # Verify main process is dead
        try:
            os.kill(pid, 0)
            return False
        except ProcessLookupError:
            self.unregister(block_id)
            return True
        except PermissionError:
            return False

    async def graceful_kill_pid(
        self,
        pid: int,
        timeout: float = 5.0,
        include_children: bool = True,
    ) -> bool:
        """Gracefully kill a process by PID (not necessarily registered).

        Args:
            pid: The process ID to kill
            timeout: Seconds to wait after SIGTERM before sending SIGKILL
            include_children: If True, also kill all child processes

        Returns:
            True if process was killed, False otherwise
        """
        pids_to_kill = [pid]

        if include_children:
            children = self._process_tree.get_children_pids(pid, recursive=True)
            pids_to_kill.extend(children)

        # Send SIGTERM to all (children first)
        for target_pid in reversed(pids_to_kill):
            try:
                os.kill(target_pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                continue

        await asyncio.sleep(timeout)

        for target_pid in reversed(pids_to_kill):
            try:
                os.kill(target_pid, 0)
                os.kill(target_pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                continue

        await asyncio.sleep(0.1)

        # Reap zombie processes
        for target_pid in pids_to_kill:
            try:
                os.waitpid(target_pid, os.WNOHANG)
            except (ChildProcessError, OSError):
                pass

        try:
            os.kill(pid, 0)
            return False
        except ProcessLookupError:
            return True
        except PermissionError:
            return False

    def kill_children(self, block_id: str, force: bool = False) -> int:
        """Kill all child processes of a registered process.

        Args:
            block_id: The block ID of the parent process
            force: If True, use SIGKILL; otherwise SIGTERM

        Returns:
            Number of child processes signaled
        """
        info = self._processes.get(block_id)
        if not info:
            return 0

        children = self._process_tree.get_children_pids(info.pid, recursive=True)
        sig = signal.SIGKILL if force else signal.SIGTERM
        count = 0

        # Kill in reverse order (deepest children first)
        for child_pid in reversed(children):
            try:
                os.kill(child_pid, sig)
                count += 1
            except (ProcessLookupError, PermissionError):
                continue

        return count

    async def kill_all_children(
        self,
        block_id: str,
        timeout: float = 3.0,
    ) -> int:
        """Gracefully kill all child processes.

        Args:
            block_id: The block ID of the parent process
            timeout: Seconds to wait before SIGKILL

        Returns:
            Number of child processes killed
        """
        info = self._processes.get(block_id)
        if not info:
            return 0

        children = self._process_tree.get_children_pids(info.pid, recursive=True)
        if not children:
            return 0

        # SIGTERM all children (deepest first)
        for child_pid in reversed(children):
            try:
                os.kill(child_pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                continue

        await asyncio.sleep(timeout)

        # SIGKILL any survivors
        count = 0
        for child_pid in reversed(children):
            try:
                os.kill(child_pid, 0)  # Check if alive
                os.kill(child_pid, signal.SIGKILL)
                count += 1
            except ProcessLookupError:
                count += 1  # Already dead, still counts as killed
            except PermissionError:
                continue

        return count

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

    def resize_pty(self, block_id: str, cols: int, rows: int) -> bool:
        """Resize PTY and send SIGWINCH to process.

        Args:
            block_id: The block ID of the process
            cols: New column count
            rows: New row count

        Returns:
            True if resize was successful, False otherwise
        """
        info = self._processes.get(block_id)
        if info and info.master_fd:
            import fcntl
            import struct
            import termios

            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(info.master_fd, termios.TIOCSWINSZ, winsize)
                os.kill(info.pid, signal.SIGWINCH)
                return True
            except Exception:
                return False
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

    async def graceful_stop_all(self, timeout: float = 5.0) -> int:
        """Gracefully stop all running processes.

        Args:
            timeout: Seconds to wait after SIGTERM before SIGKILL

        Returns:
            Number of processes killed
        """
        count = 0
        block_ids = list(self._processes.keys())

        # Send SIGTERM to all
        for block_id in block_ids:
            info = self._processes.get(block_id)
            if info:
                # Kill children first
                self.kill_children(block_id, force=False)
                try:
                    os.kill(info.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    continue

        await asyncio.sleep(timeout)

        # SIGKILL any survivors
        for block_id in block_ids:
            info = self._processes.get(block_id)
            if info:
                try:
                    os.kill(info.pid, 0)  # Check if alive
                    os.kill(info.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    continue
                count += 1
                self.unregister(block_id)

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

    def format_tree(self, block_id: str) -> str:
        """Format a process tree as a string for display.

        Args:
            block_id: The block ID of the root process

        Returns:
            Formatted tree string
        """
        tree = self.get_process_tree_view(block_id)
        if not tree:
            return "Process not found"

        lines = []
        self._format_node(tree, lines, prefix="", is_last=True)
        return "\n".join(lines)

    def _format_node(
        self,
        node: ProcessNode,
        lines: list[str],
        prefix: str = "",
        is_last: bool = True,
    ) -> None:
        """Recursively format a ProcessNode for display."""
        connector = "└── " if is_last else "├── "
        res = node.resources

        # Format resource info
        resource_str = ""
        if PSUTIL_AVAILABLE:
            resource_str = f" [CPU:{res.cpu_percent:.1f}% MEM:{res.memory_mb:.1f}MB]"

        name = node.name[:20] if len(node.name) > 20 else node.name
        lines.append(f"{prefix}{connector}{node.pid} {name}{resource_str}")

        # Prepare prefix for children
        child_prefix = prefix + ("    " if is_last else "│   ")

        for i, child in enumerate(node.children):
            is_child_last = i == len(node.children) - 1
            self._format_node(child, lines, child_prefix, is_child_last)
