from collections.abc import Callable
from typing import Optional

import asyncssh


class SSHSession:
    def __init__(
        self,
        hostname: str,
        port: int = 22,
        username: str = None,
        password: str = None,
        key_path: str = None,
        tunnel: Optional["SSHSession"] = None,
    ):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.tunnel = tunnel
        self._conn: asyncssh.SSHClientConnection | None = None
        self._stdin = None
        self._stdout = None
        self._stderr = None

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
    ):
        """Start an interactive shell."""
        if not self._conn:
            await self.connect()

        self._stdin, self._stdout, self._stderr = await self._conn.open_session(
            term_type=term_type, term_size=(cols, lines)
        )
        return self._stdin, self._stdout, self._stderr

    async def run_command(self, command: str) -> asyncssh.SSHCompletedProcess:
        """Run a single command and return result."""
        if not self._conn:
            await self.connect()
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
            if isinstance(self._stdout, asyncssh.SSHReader):
                self._stdout.channel.change_terminal_size(cols, lines)
