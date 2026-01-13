from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import asyncssh

if TYPE_CHECKING:
    from managers.ssh import SSHConnectionPool

logger = logging.getLogger(__name__)


class SSHSession:
    def __init__(
        self,
        hostname: str,
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        key_path: str | None = None,
        tunnel: SSHSession | None = None,
        pool: SSHConnectionPool | None = None,
    ):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.tunnel = tunnel
        self._pool = pool
        self._conn: asyncssh.SSHClientConnection | None = None
        self._stdin: asyncssh.SSHWriter[bytes] | None = None
        self._stdout: asyncssh.SSHReader[bytes] | None = None
        self._stderr: asyncssh.SSHReader[bytes] | None = None
        self._connected = False
        self._disconnect_callbacks: list[Callable[[], Any]] = []
        self._reconnect_task: asyncio.Task[Any] | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._conn is not None

    @property
    def connection_key(self) -> str:
        return f"{self.hostname}:{self.port}:{self.username or 'default'}"

    async def connect(self) -> None:
        if self._conn:
            return

        client_keys = []
        if self.key_path:
            client_keys = [self.key_path]

        connect_kwargs: dict[str, Any] = {
            "host": self.hostname,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "client_keys": client_keys if self.key_path else None,
            "known_hosts": None,
            "keepalive_interval": 30,
            "keepalive_count_max": 3,
        }

        if self.tunnel:
            await self.tunnel.connect()
            if self.tunnel._conn is not None:
                self._conn = await self.tunnel._conn.connect_ssh(**connect_kwargs)
        else:
            self._conn = await asyncssh.connect(**connect_kwargs)

        self._connected = True
        logger.info(f"SSH connected to {self.hostname}:{self.port}")

    async def start_shell(
        self,
        term_type: str = "xterm-256color",
        cols: int = 80,
        lines: int = 24,
        input_handler: Callable[[str], None] | None = None,
    ) -> tuple[
        asyncssh.SSHWriter[bytes], asyncssh.SSHReader[bytes], asyncssh.SSHReader[bytes]
    ]:
        if not self._conn:
            await self.connect()

        if self._conn is None:
            raise RuntimeError("SSH connection not established")

        stdin, stdout, stderr = await self._conn.open_session(
            term_type=term_type, term_size=(cols, lines)
        )
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        return stdin, stdout, stderr

    async def run_command(self, command: str) -> asyncssh.SSHCompletedProcess:
        if not self._conn:
            await self.connect()
        if self._conn is None:
            raise RuntimeError("SSH connection not established")
        return await self._conn.run(command)

    async def send_keepalive(self) -> bool:
        if not self._conn or not self._connected:
            return False
        try:
            result = await asyncio.wait_for(
                self._conn.run("echo ping", check=True),
                timeout=10.0,
            )
            return result.exit_status == 0
        except Exception as e:
            logger.warning(f"Keep-alive failed for {self.hostname}: {e}")
            return False

    async def reconnect(self) -> bool:
        self.close()
        try:
            await self.connect()
            return True
        except Exception as e:
            logger.error(f"Reconnect failed for {self.hostname}: {e}")
            return False

    def close(self) -> None:
        self._connected = False
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        self._stdin = None
        self._stdout = None
        self._stderr = None
        self._notify_disconnect()

    def add_disconnect_callback(self, callback: Callable[[], Any]) -> None:
        self._disconnect_callbacks.append(callback)

    def remove_disconnect_callback(self, callback: Callable[[], Any]) -> None:
        if callback in self._disconnect_callbacks:
            self._disconnect_callbacks.remove(callback)

    def _notify_disconnect(self) -> None:
        for callback in self._disconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    task = asyncio.create_task(callback())
                    task.add_done_callback(lambda t: None)
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in disconnect callback: {e}")

    def resize(self, cols: int, lines: int) -> None:
        if self._stdin:
            if self._stdout is not None:
                channel = getattr(self._stdout, "channel", None)
                if channel is not None:
                    change_size = getattr(channel, "change_terminal_size", None)
                    if change_size is not None:
                        change_size(cols, lines)

    def get_status(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "connected": self._connected,
            "has_shell": self._stdin is not None,
        }
