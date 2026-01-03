from collections.abc import Callable
from typing import Optional

import asyncssh


class SSHSession:
    def __init__(
        self,
        hostname: str,
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        key_path: str | None = None,
        tunnel: Optional["SSHSession"] = None,
    ):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.tunnel = tunnel
        self._conn: asyncssh.SSHClientConnection | None = None
        self._stdin: asyncssh.SSHWriter[bytes] | None = None
        self._stdout: asyncssh.SSHReader[bytes] | None = None
        self._stderr: asyncssh.SSHReader[bytes] | None = None

    async def connect(self):
        """Establish SSH connection."""
        if self._conn:
            return

        client_keys = []
        if self.key_path:
            client_keys = [self.key_path]

        # Connection options
        connect_kwargs = {
            "host": self.hostname,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "client_keys": client_keys if self.key_path else None,
            "known_hosts": None,
        }

        if self.tunnel:
            # Ensure tunnel is connected
            await self.tunnel.connect()
            # Connect via tunnel
            if self.tunnel._conn is not None:
                self._conn = await self.tunnel._conn.connect_ssh(**connect_kwargs)
        else:
            # Direct connection
            self._conn = await asyncssh.connect(**connect_kwargs)

    async def start_shell(
        self,
        term_type: str = "xterm-256color",
        cols: int = 80,
        lines: int = 24,
        input_handler: Callable[[str], None] | None = None,
    ) -> tuple[asyncssh.SSHWriter[bytes], asyncssh.SSHReader[bytes], asyncssh.SSHReader[bytes]]:
        """Start an interactive shell."""
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
        """Run a single command and return result."""
        if not self._conn:
            await self.connect()
        if self._conn is None:
            raise RuntimeError("SSH connection not established")
        return await self._conn.run(command)

    def close(self):
        if self._conn:
            self._conn.close()

    def resize(self, cols: int, lines: int):
        if self._stdin:  # Open session object
            # Access underlying channel to resize
            # AsyncSSH doesn't expose resize easily on the streams directly,
            # need the channel/session object.
            # self._conn.open_session returns (stdin, stdout, stderr)
            # stdout is a SSHReader, which has a .channel property
            if self._stdout is not None:
                channel = getattr(self._stdout, "channel", None)
                if channel is not None:
                    change_size = getattr(channel, "change_terminal_size", None)
                    if change_size is not None:
                        change_size(cols, lines)
