"""Reliability utilities for memory management, retries, and resilience."""

import asyncio
import functools
import logging
import os
import signal
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# =============================================================================
# Memory Management
# =============================================================================

MAX_BLOCK_CONTENT_SIZE = 1024 * 1024  # 1MB per block
MAX_TOTAL_BLOCKS_SIZE = 50 * 1024 * 1024  # 50MB total
TRUNCATION_MESSAGE = "\n\n[Content truncated - exceeded size limit]"


@dataclass
class MemoryLimits:
    """Configuration for memory limits."""

    max_block_size: int = MAX_BLOCK_CONTENT_SIZE
    max_total_size: int = MAX_TOTAL_BLOCKS_SIZE
    truncate_large_content: bool = True


def truncate_content(
    content: str, max_size: int = MAX_BLOCK_CONTENT_SIZE
) -> tuple[str, bool]:
    """Truncate content if it exceeds max size.

    Returns:
        Tuple of (content, was_truncated)
    """
    if len(content) <= max_size:
        return content, False

    truncated = content[: max_size - len(TRUNCATION_MESSAGE)] + TRUNCATION_MESSAGE
    return truncated, True


def get_content_size(content: str | bytes) -> int:
    """Get size of content in bytes."""
    if isinstance(content, str):
        return len(content.encode("utf-8", errors="replace"))
    return len(content)


# =============================================================================
# Retry Logic
# =============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        socket.error,
    )


async def retry_async(
    func: Callable[..., T],
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> T:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Arguments to pass to func
        config: Retry configuration
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func

    Raises:
        Last exception if all retries fail
    """
    config = config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            if attempt < config.max_attempts - 1:
                delay = min(
                    config.base_delay * (config.exponential_base**attempt),
                    config.max_delay,
                )
                logger.warning(
                    "Retry %d/%d for %s after %.1fs: %s",
                    attempt + 1,
                    config.max_attempts,
                    func.__name__,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d retries failed for %s", config.max_attempts, func.__name__
                )

    raise last_exception


def with_retry(config: RetryConfig | None = None):
    """Decorator for adding retry logic to async functions."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, config=config, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Network/Offline Detection
# =============================================================================


@dataclass
class NetworkStatus:
    """Current network connectivity status."""

    is_online: bool
    latency_ms: float | None = None
    last_check: float = 0
    error: str | None = None


async def check_network_connectivity(
    hosts: list[str] | None = None,
    timeout: float = 5.0,
) -> NetworkStatus:
    """Check if network is available by attempting connections.

    Args:
        hosts: List of hosts to try (defaults to common DNS servers)
        timeout: Connection timeout in seconds

    Returns:
        NetworkStatus with connectivity info
    """
    import time

    hosts = hosts or ["8.8.8.8", "1.1.1.1", "208.67.222.222"]

    start = time.time()
    for host in hosts:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, 53), timeout=timeout
            )
            latency = (time.time() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return NetworkStatus(
                is_online=True, latency_ms=latency, last_check=time.time()
            )
        except Exception:
            continue

    return NetworkStatus(
        is_online=False,
        last_check=time.time(),
        error="Could not connect to any DNS server",
    )


_cached_network_status: NetworkStatus | None = None
_network_check_interval = 30.0  # seconds


async def is_online(force_check: bool = False) -> bool:
    """Check if network is available (cached).

    Args:
        force_check: Force a new network check

    Returns:
        True if online, False otherwise
    """
    global _cached_network_status
    import time

    if (
        force_check
        or _cached_network_status is None
        or time.time() - _cached_network_status.last_check > _network_check_interval
    ):
        _cached_network_status = await check_network_connectivity()

    return _cached_network_status.is_online


# =============================================================================
# Concurrent Request Management
# =============================================================================


class RequestQueue:
    """Queue for managing concurrent AI requests."""

    def __init__(self, max_concurrent: int = 1):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._current_request_id: str | None = None
        self._lock = asyncio.Lock()

    async def acquire(self, request_id: str) -> bool:
        """Try to acquire a slot for a request.

        Args:
            request_id: Unique identifier for this request

        Returns:
            True if acquired, False if should be rejected
        """
        async with self._lock:
            if self._current_request_id is not None:
                logger.warning(
                    "Rejecting request %s - another request in progress", request_id
                )
                return False
            self._current_request_id = request_id

        await self._semaphore.acquire()
        return True

    def release(self, request_id: str) -> None:
        """Release a request slot."""
        if self._current_request_id == request_id:
            self._current_request_id = None
            self._semaphore.release()

    @property
    def is_busy(self) -> bool:
        """Check if a request is currently in progress."""
        return self._current_request_id is not None


# =============================================================================
# PTY Cleanup
# =============================================================================

_child_pids: set[int] = set()


def register_child_process(pid: int) -> None:
    """Register a child process for cleanup tracking."""
    _child_pids.add(pid)


def unregister_child_process(pid: int) -> None:
    """Unregister a child process."""
    _child_pids.discard(pid)


def cleanup_child_processes() -> None:
    """Kill all registered child processes."""
    for pid in list(_child_pids):
        try:
            os.kill(pid, signal.SIGTERM)
            logger.debug("Sent SIGTERM to child process %d", pid)
        except OSError:
            pass
        _child_pids.discard(pid)


def cleanup_orphaned_ptys() -> None:
    """Clean up any orphaned PTY processes."""
    try:
        import subprocess

        result = subprocess.run(
            ["pkill", "-f", "null-terminal-pty"], capture_output=True, timeout=5
        )
        if result.returncode == 0:
            logger.info("Cleaned up orphaned PTY processes")
    except Exception as e:
        logger.debug("PTY cleanup check: %s", e)


# =============================================================================
# Config Backup
# =============================================================================


def backup_config(config_path: Path, max_backups: int = 5) -> Path | None:
    """Create a backup of a config file before modifying.

    Args:
        config_path: Path to config file
        max_backups: Maximum number of backups to keep

    Returns:
        Path to backup file, or None if failed
    """
    if not config_path.exists():
        return None

    backup_dir = config_path.parent / ".backups"
    backup_dir.mkdir(exist_ok=True)

    import time

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{config_path.name}.{timestamp}.bak"

    try:
        import shutil

        shutil.copy2(config_path, backup_path)
        logger.debug("Created config backup: %s", backup_path)

        # Clean old backups
        backups = sorted(backup_dir.glob(f"{config_path.name}.*.bak"))
        for old_backup in backups[:-max_backups]:
            old_backup.unlink()

        return backup_path
    except Exception as e:
        logger.error("Failed to backup config: %s", e)
        return None


def restore_config(config_path: Path) -> bool:
    """Restore the most recent config backup.

    Args:
        config_path: Path to config file

    Returns:
        True if restored successfully
    """
    backup_dir = config_path.parent / ".backups"
    if not backup_dir.exists():
        return False

    backups = sorted(backup_dir.glob(f"{config_path.name}.*.bak"))
    if not backups:
        return False

    try:
        import shutil

        shutil.copy2(backups[-1], config_path)
        logger.info("Restored config from: %s", backups[-1])
        return True
    except Exception as e:
        logger.error("Failed to restore config: %s", e)
        return False


# =============================================================================
# Tool Timeout
# =============================================================================


async def run_with_timeout(
    coro,
    timeout: float,
    timeout_message: str = "Operation timed out",
) -> Any:
    """Run a coroutine with a timeout.

    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        timeout_message: Message for timeout error

    Returns:
        Result of coroutine

    Raises:
        TimeoutError if timeout exceeded
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(timeout_message)


# =============================================================================
# Context Overflow Warning
# =============================================================================


@dataclass
class ContextUsage:
    """Track context window usage."""

    current_tokens: int = 0
    max_tokens: int = 128000  # Default for GPT-4
    warning_threshold: float = 0.8
    critical_threshold: float = 0.95

    @property
    def usage_percent(self) -> float:
        return self.current_tokens / self.max_tokens if self.max_tokens > 0 else 0

    @property
    def is_warning(self) -> bool:
        return self.usage_percent >= self.warning_threshold

    @property
    def is_critical(self) -> bool:
        return self.usage_percent >= self.critical_threshold

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.current_tokens)


# =============================================================================
# Unicode Handling
# =============================================================================


def safe_string_width(text: str) -> int:
    """Calculate display width of string, handling wide characters.

    Handles CJK characters, emoji, and other wide characters.
    """
    try:
        import unicodedata

        width = 0
        for char in text:
            if unicodedata.east_asian_width(char) in ("F", "W"):
                width += 2
            elif unicodedata.category(char) == "Mn":  # Combining marks
                width += 0
            else:
                width += 1
        return width
    except Exception:
        return len(text)


def truncate_to_width(text: str, max_width: int, suffix: str = "...") -> str:
    """Truncate string to fit within display width."""
    if safe_string_width(text) <= max_width:
        return text

    suffix_width = safe_string_width(suffix)
    target_width = max_width - suffix_width

    result = []
    current_width = 0
    for char in text:
        char_width = safe_string_width(char)
        if current_width + char_width > target_width:
            break
        result.append(char)
        current_width += char_width

    return "".join(result) + suffix


# =============================================================================
# Large File Handling
# =============================================================================


async def stream_large_file(
    path: Path,
    chunk_size: int = 64 * 1024,  # 64KB chunks
    max_size: int = 10 * 1024 * 1024,  # 10MB max
):
    """Stream a large file in chunks.

    Args:
        path: Path to file
        chunk_size: Size of each chunk
        max_size: Maximum total bytes to read

    Yields:
        Chunks of file content
    """
    bytes_read = 0
    try:
        async with asyncio.open_file(path, "rb") as f:
            while bytes_read < max_size:
                chunk = await f.read(min(chunk_size, max_size - bytes_read))
                if not chunk:
                    break
                bytes_read += len(chunk)
                yield chunk
    except AttributeError:
        # Fallback for sync file reading
        with open(path, "rb") as f:
            while bytes_read < max_size:
                chunk = f.read(min(chunk_size, max_size - bytes_read))
                if not chunk:
                    break
                bytes_read += len(chunk)
                yield chunk


def read_file_with_limit(
    path: Path,
    max_size: int = 1024 * 1024,  # 1MB
    encoding: str = "utf-8",
) -> tuple[str, bool]:
    """Read a file with size limit.

    Args:
        path: Path to file
        max_size: Maximum bytes to read
        encoding: Text encoding

    Returns:
        Tuple of (content, was_truncated)
    """
    try:
        file_size = path.stat().st_size
        was_truncated = file_size > max_size

        with open(path, "r", encoding=encoding, errors="replace") as f:
            content = f.read(max_size)

        if was_truncated:
            content += f"\n\n[File truncated - {file_size:,} bytes total, showing first {max_size:,}]"

        return content, was_truncated
    except Exception as e:
        return f"Error reading file: {e}", False


# =============================================================================
# Crash Recovery
# =============================================================================

CRASH_STATE_FILE = ".null_crash_state"


def save_crash_state(state: dict, config_dir: Path) -> None:
    """Save state for crash recovery.

    Args:
        state: State dictionary to save
        config_dir: Directory to save state file
    """
    import json

    crash_file = config_dir / CRASH_STATE_FILE
    try:
        with open(crash_file, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error("Failed to save crash state: %s", e)


def load_crash_state(config_dir: Path) -> dict | None:
    """Load crash recovery state if exists.

    Args:
        config_dir: Directory containing state file

    Returns:
        State dictionary or None
    """
    import json

    crash_file = config_dir / CRASH_STATE_FILE
    if not crash_file.exists():
        return None

    try:
        with open(crash_file, "r") as f:
            state = json.load(f)
        crash_file.unlink()  # Remove after loading
        return state
    except Exception as e:
        logger.error("Failed to load crash state: %s", e)
        return None


# =============================================================================
# Startup Validation
# =============================================================================


@dataclass
class ValidationResult:
    """Result of startup validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_environment() -> ValidationResult:
    """Validate the runtime environment.

    Checks:
    - Python version
    - Required directories
    - Permissions
    - Dependencies
    """
    errors = []
    warnings = []

    # Check Python version
    if sys.version_info < (3, 11):
        errors.append(
            f"Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor}"
        )

    # Check home directory
    home = Path.home()
    null_dir = home / ".null"

    if null_dir.exists():
        if not os.access(null_dir, os.W_OK):
            errors.append(f"No write permission to {null_dir}")
    else:
        try:
            null_dir.mkdir(parents=True)
        except Exception as e:
            errors.append(f"Cannot create config directory: {e}")

    # Check for required commands
    for cmd in ["git"]:
        import shutil

        if not shutil.which(cmd):
            warnings.append(f"Optional command '{cmd}' not found")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# =============================================================================
# Log Rotation
# =============================================================================


def setup_log_rotation(
    log_file: Path,
    max_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 3,
) -> logging.Handler:
    """Setup rotating file handler for logs.

    Args:
        log_file: Path to log file
        max_size: Maximum size before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured RotatingFileHandler
    """
    from logging.handlers import RotatingFileHandler

    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    return handler


# =============================================================================
# Graceful Shutdown
# =============================================================================

_shutdown_handlers: list[Callable[[], None]] = []
_shutdown_in_progress = False


def register_shutdown_handler(handler: Callable[[], None]) -> None:
    """Register a function to be called on graceful shutdown."""
    _shutdown_handlers.append(handler)


def graceful_shutdown(signum=None, frame=None) -> None:
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    global _shutdown_in_progress

    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True

    logger.info("Graceful shutdown initiated (signal: %s)", signum)

    # Run registered handlers
    for handler in _shutdown_handlers:
        try:
            handler()
        except Exception as e:
            logger.error("Shutdown handler error: %s", e)

    # Clean up child processes
    cleanup_child_processes()

    logger.info("Shutdown complete")


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)
