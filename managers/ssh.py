"""SSH Connection Pool Manager with keep-alive and session restore."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import asyncssh

from managers.ssh_known_hosts import HostKeyStatus, KnownHostsManager

logger = logging.getLogger(__name__)


class SSHConnectionState(Enum):
    """SSH connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class SSHConnectionInfo:
    """Information about a pooled SSH connection."""

    host: str
    port: int
    username: str | None
    key: str  # Unique key: host:port:username
    state: SSHConnectionState = SSHConnectionState.DISCONNECTED
    connection: asyncssh.SSHClientConnection | None = None
    connected_at: datetime | None = None
    last_activity: datetime | None = None
    last_ping: datetime | None = None
    retry_count: int = 0
    max_retries: int = 5
    error_message: str | None = None
    # Connection config
    password: str | None = None
    key_path: str | None = None
    tunnel_key: str | None = None  # Key of jump host connection

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return (
            self.state == SSHConnectionState.CONNECTED and self.connection is not None
        )

    @property
    def uptime(self) -> float:
        """Get connection uptime in seconds."""
        if self.connected_at:
            return (datetime.now() - self.connected_at).total_seconds()
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for status display."""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat()
            if self.connected_at
            else None,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "uptime": self.uptime,
            "retry_count": self.retry_count,
            "error": self.error_message,
        }


class SSHConnectionPool:
    """Manages pooled SSH connections with keep-alive and auto-reconnect."""

    def __init__(
        self,
        keep_alive_interval: float = 30.0,
        max_idle_time: float = 300.0,
        auto_reconnect: bool = True,
    ):
        """Initialize SSH connection pool.

        Args:
            keep_alive_interval: Seconds between keep-alive pings (default 30s)
            max_idle_time: Maximum idle time before closing connection (default 5min)
            auto_reconnect: Whether to auto-reconnect on disconnect
        """
        self._connections: dict[str, SSHConnectionInfo] = {}
        self._keep_alive_interval = keep_alive_interval
        self._max_idle_time = max_idle_time
        self._auto_reconnect = auto_reconnect

        # Keep-alive task
        self._keep_alive_task: asyncio.Task[Any] | None = None
        self._running = False

        # Callbacks for state changes
        self._state_callbacks: list[Callable[[str, SSHConnectionState], Any]] = []
        self._background_tasks: set[asyncio.Task[Any]] = set()

        # Locks for thread-safe operations
        self._connection_locks: dict[str, asyncio.Lock] = {}

        self._known_hosts_manager = KnownHostsManager()
        self._known_hosts_manager.load()

    def _get_connection_key(
        self, host: str, port: int = 22, username: str | None = None
    ) -> str:
        """Generate unique key for a connection."""
        return f"{host}:{port}:{username or 'default'}"

    def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a connection key."""
        if key not in self._connection_locks:
            self._connection_locks[key] = asyncio.Lock()
        return self._connection_locks[key]

    async def start(self) -> None:
        """Start the connection pool and keep-alive loop."""
        if self._running:
            return

        self._running = True
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        logger.info("SSH connection pool started")

    async def stop(self) -> None:
        """Stop the connection pool and close all connections."""
        self._running = False

        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
            self._keep_alive_task = None

        # Close all connections
        for key in list(self._connections.keys()):
            await self.close_connection(key)

        # Wait for background tasks
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        logger.info("SSH connection pool stopped")

    async def get_connection(
        self,
        host: str,
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        key_path: str | None = None,
        tunnel_host: str | None = None,
        tunnel_port: int = 22,
        tunnel_username: str | None = None,
    ) -> SSHConnectionInfo:
        """Get or create a pooled SSH connection.

        Args:
            host: Target hostname
            port: Target port
            username: SSH username
            password: SSH password (optional)
            key_path: Path to SSH private key (optional)
            tunnel_host: Jump host for tunneling (optional)
            tunnel_port: Jump host port
            tunnel_username: Jump host username

        Returns:
            SSHConnectionInfo with active connection
        """
        key = self._get_connection_key(host, port, username)
        lock = self._get_lock(key)

        async with lock:
            # Check if we have an existing connected connection
            if key in self._connections:
                info = self._connections[key]
                if info.is_connected:
                    info.last_activity = datetime.now()
                    return info

                # Connection exists but not connected - try to reconnect
                if info.state != SSHConnectionState.CONNECTING:
                    await self._connect(info)
                    return info

            # Create new connection info
            tunnel_key = None
            if tunnel_host:
                tunnel_key = self._get_connection_key(
                    tunnel_host, tunnel_port, tunnel_username
                )

            info = SSHConnectionInfo(
                host=host,
                port=port,
                username=username,
                key=key,
                password=password,
                key_path=key_path,
                tunnel_key=tunnel_key,
            )
            self._connections[key] = info

            # Connect
            await self._connect(info)
            return info

    async def _connect(self, info: SSHConnectionInfo) -> None:
        """Establish SSH connection."""
        info.state = SSHConnectionState.CONNECTING
        info.error_message = None
        self._notify_state_change(info.key, info.state)

        try:
            # Handle tunnel connection first
            tunnel_conn = None
            if info.tunnel_key and info.tunnel_key in self._connections:
                tunnel_info = self._connections[info.tunnel_key]
                if not tunnel_info.is_connected:
                    await self._connect(tunnel_info)
                tunnel_conn = tunnel_info.connection

            client_keys = [info.key_path] if info.key_path else None
            known_hosts_path = self._known_hosts_manager.known_hosts_path
            connect_kwargs = {
                "host": info.host,
                "port": info.port,
                "username": info.username,
                "password": info.password,
                "client_keys": client_keys,
                "known_hosts": str(known_hosts_path)
                if known_hosts_path.exists()
                else (),
                "keepalive_interval": self._keep_alive_interval,
                "keepalive_count_max": 3,
            }

            if tunnel_conn:
                # Connect through tunnel
                info.connection = await tunnel_conn.connect_ssh(**connect_kwargs)
            else:
                # Direct connection
                info.connection = await asyncssh.connect(**connect_kwargs)

            info.state = SSHConnectionState.CONNECTED
            info.connected_at = datetime.now()
            info.last_activity = datetime.now()
            info.last_ping = datetime.now()
            info.retry_count = 0
            logger.info(f"SSH connected to {info.host}:{info.port}")

        except asyncssh.DisconnectError as e:
            info.state = SSHConnectionState.ERROR
            info.error_message = f"Disconnect: {e}"
            info.connection = None
            logger.error(f"SSH disconnect error for {info.host}: {e}")

        except asyncssh.PermissionDenied as e:
            info.state = SSHConnectionState.ERROR
            info.error_message = f"Permission denied: {e}"
            info.connection = None
            logger.error(f"SSH permission denied for {info.host}: {e}")

        except Exception as e:
            info.state = SSHConnectionState.ERROR
            info.error_message = str(e)
            info.connection = None
            logger.error(f"SSH connection error for {info.host}: {e}")

        self._notify_state_change(info.key, info.state)

    async def close_connection(self, key: str) -> None:
        """Close a specific connection."""
        if key not in self._connections:
            return

        info = self._connections[key]
        if info.connection:
            try:
                info.connection.close()
                await info.connection.wait_closed()
            except Exception as e:
                logger.warning(f"Error closing SSH connection {key}: {e}")

        info.state = SSHConnectionState.DISCONNECTED
        info.connection = None
        info.connected_at = None
        self._notify_state_change(key, info.state)
        logger.info(f"SSH connection closed: {key}")

    async def remove_connection(self, key: str) -> None:
        """Close and remove a connection from the pool."""
        await self.close_connection(key)
        if key in self._connections:
            del self._connections[key]
        if key in self._connection_locks:
            del self._connection_locks[key]

    async def _keep_alive_loop(self) -> None:
        """Background loop for keep-alive pings and idle cleanup."""
        while self._running:
            try:
                await asyncio.sleep(self._keep_alive_interval)

                now = datetime.now()
                for key, info in list(self._connections.items()):
                    if not info.is_connected:
                        # Try to reconnect if auto-reconnect enabled
                        if (
                            self._auto_reconnect
                            and info.state == SSHConnectionState.ERROR
                            and info.retry_count < info.max_retries
                        ):
                            await self._try_reconnect(info)
                        continue

                    # Check idle time
                    if info.last_activity:
                        idle_time = (now - info.last_activity).total_seconds()
                        if idle_time > self._max_idle_time:
                            logger.info(f"Closing idle SSH connection: {key}")
                            await self.close_connection(key)
                            continue

                    # Send keep-alive ping
                    await self._ping_connection(info)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in keep-alive loop: {e}")

    async def _ping_connection(self, info: SSHConnectionInfo) -> bool:
        """Send a keep-alive ping to verify connection is alive."""
        if not info.connection:
            return False

        try:
            await asyncio.wait_for(
                info.connection.run("echo ping", check=True),
                timeout=10.0,
            )
            info.last_ping = datetime.now()
            return True

        except TimeoutError:
            logger.warning(f"SSH keep-alive timeout for {info.host}")
            await self._handle_disconnect(info)
            return False

        except Exception as e:
            logger.warning(f"SSH keep-alive failed for {info.host}: {e}")
            await self._handle_disconnect(info)
            return False

    async def _handle_disconnect(self, info: SSHConnectionInfo) -> None:
        """Handle unexpected disconnection."""
        info.state = SSHConnectionState.DISCONNECTED
        info.error_message = "Connection lost"

        if info.connection:
            try:
                info.connection.close()
            except Exception:
                pass
            info.connection = None

        self._notify_state_change(info.key, info.state)

        # Try to reconnect if enabled
        if self._auto_reconnect and info.retry_count < info.max_retries:
            await self._try_reconnect(info)

    async def _try_reconnect(self, info: SSHConnectionInfo) -> None:
        """Attempt to reconnect with exponential backoff."""
        info.retry_count += 1
        info.state = SSHConnectionState.RECONNECTING
        self._notify_state_change(info.key, info.state)

        # Exponential backoff: 1s, 2s, 4s, 8s, 16s
        delay = min(2 ** (info.retry_count - 1), 16)
        logger.info(
            f"Reconnecting to {info.host} in {delay}s (attempt {info.retry_count}/{info.max_retries})"
        )

        await asyncio.sleep(delay)

        if not self._running:
            return

        await self._connect(info)

    async def restore_session(
        self,
        host: str,
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        key_path: str | None = None,
    ) -> SSHConnectionInfo:
        """Restore a disconnected session.

        Forces a reconnection attempt, resetting retry count.
        """
        key = self._get_connection_key(host, port, username)
        lock = self._get_lock(key)

        async with lock:
            if key in self._connections:
                info = self._connections[key]
                info.retry_count = 0  # Reset retry count
                info.password = password or info.password
                info.key_path = key_path or info.key_path
            else:
                info = SSHConnectionInfo(
                    host=host,
                    port=port,
                    username=username,
                    key=key,
                    password=password,
                    key_path=key_path,
                )
                self._connections[key] = info

            await self._connect(info)
            return info

    def get_connection_info(self, key: str) -> SSHConnectionInfo | None:
        """Get info for a specific connection."""
        return self._connections.get(key)

    def get_connection_by_host(
        self, host: str, port: int = 22, username: str | None = None
    ) -> SSHConnectionInfo | None:
        """Get connection info by host details."""
        key = self._get_connection_key(host, port, username)
        return self._connections.get(key)

    def list_connections(self) -> list[SSHConnectionInfo]:
        """List all pooled connections."""
        return list(self._connections.values())

    def get_status(self) -> dict[str, Any]:
        """Get overall pool status."""
        connections = [info.to_dict() for info in self._connections.values()]
        connected_count = sum(
            1 for info in self._connections.values() if info.is_connected
        )

        return {
            "running": self._running,
            "total_connections": len(self._connections),
            "connected_count": connected_count,
            "keep_alive_interval": self._keep_alive_interval,
            "max_idle_time": self._max_idle_time,
            "auto_reconnect": self._auto_reconnect,
            "connections": connections,
        }

    def add_state_callback(
        self, callback: Callable[[str, SSHConnectionState], Any]
    ) -> None:
        """Register callback for connection state changes.

        Args:
            callback: Function called with (connection_key, new_state)
        """
        self._state_callbacks.append(callback)

    def remove_state_callback(
        self, callback: Callable[[str, SSHConnectionState], Any]
    ) -> None:
        """Remove a state callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _notify_state_change(self, key: str, state: SSHConnectionState) -> None:
        """Notify all callbacks of a state change."""
        for callback in self._state_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    task = asyncio.create_task(callback(key, state))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                else:
                    callback(key, state)
            except Exception as e:
                logger.error(f"Error in SSH state callback: {e}")

    # Configuration methods
    def set_keep_alive_interval(self, interval: float) -> None:
        """Update keep-alive interval (seconds)."""
        self._keep_alive_interval = max(5.0, interval)

    def set_max_idle_time(self, time: float) -> None:
        """Update max idle time (seconds)."""
        self._max_idle_time = max(60.0, time)

    def set_auto_reconnect(self, enabled: bool) -> None:
        """Enable or disable auto-reconnect."""
        self._auto_reconnect = enabled
