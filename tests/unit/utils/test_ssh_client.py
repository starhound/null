from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.ssh_client import SSHSession


class TestSSHSession:
    def test_init_defaults(self):
        session = SSHSession("example.com")
        assert session.hostname == "example.com"
        assert session.port == 22
        assert session.username is None
        assert session.password is None
        assert session.key_path is None
        assert session.tunnel is None
        assert session._conn is None

    def test_init_with_all_params(self):
        tunnel = SSHSession("bastion.example.com")
        session = SSHSession(
            hostname="target.example.com",
            port=2222,
            username="admin",
            password="secret",
            key_path="/home/user/.ssh/id_rsa",
            tunnel=tunnel,
        )
        assert session.hostname == "target.example.com"
        assert session.port == 2222
        assert session.username == "admin"
        assert session.password == "secret"
        assert session.key_path == "/home/user/.ssh/id_rsa"
        assert session.tunnel is tunnel

    @pytest.mark.asyncio
    async def test_connect_direct(self):
        session = SSHSession("example.com", username="user")
        mock_conn = AsyncMock()
        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn
            await session.connect()
        assert session._conn is mock_conn
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_skips_if_already_connected(self):
        session = SSHSession("example.com")
        session._conn = MagicMock()
        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            await session.connect()
        mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_with_key_path(self):
        session = SSHSession("example.com", key_path="/path/to/key")
        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock()
            await session.connect()
        call_kwargs = mock_connect.call_args.kwargs
        assert call_kwargs["client_keys"] == ["/path/to/key"]

    @pytest.mark.asyncio
    async def test_connect_via_tunnel(self):
        tunnel = SSHSession("bastion.example.com")
        tunnel._conn = AsyncMock()
        tunnel._conn.connect_ssh = AsyncMock(return_value=AsyncMock())
        session = SSHSession("target.example.com", tunnel=tunnel)
        with patch("asyncssh.connect", new_callable=AsyncMock):
            await session.connect()
        tunnel._conn.connect_ssh.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_shell(self):
        session = SSHSession("example.com")
        mock_conn = AsyncMock()
        mock_stdin = AsyncMock()
        mock_stdout = AsyncMock()
        mock_stderr = AsyncMock()
        mock_conn.open_session = AsyncMock(
            return_value=(mock_stdin, mock_stdout, mock_stderr)
        )
        session._conn = mock_conn
        stdin, stdout, stderr = await session.start_shell()
        assert stdin is mock_stdin
        assert stdout is mock_stdout
        assert stderr is mock_stderr
        mock_conn.open_session.assert_called_once_with(
            term_type="xterm-256color", term_size=(80, 24)
        )

    @pytest.mark.asyncio
    async def test_start_shell_custom_terminal(self):
        session = SSHSession("example.com")
        mock_conn = AsyncMock()
        mock_conn.open_session = AsyncMock(
            return_value=(AsyncMock(), AsyncMock(), AsyncMock())
        )
        session._conn = mock_conn
        await session.start_shell(term_type="vt100", cols=120, lines=40)
        mock_conn.open_session.assert_called_once_with(
            term_type="vt100", term_size=(120, 40)
        )

    @pytest.mark.asyncio
    async def test_start_shell_connects_if_needed(self):
        session = SSHSession("example.com")
        mock_conn = AsyncMock()
        mock_conn.open_session = AsyncMock(
            return_value=(AsyncMock(), AsyncMock(), AsyncMock())
        )
        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn
            await session.start_shell()
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_shell_raises_if_connection_fails(self):
        session = SSHSession("example.com")
        session._conn = None
        with (
            patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect,
            pytest.raises(RuntimeError, match="not established"),
        ):
            mock_connect.return_value = None
            await session.start_shell()

    @pytest.mark.asyncio
    async def test_run_command(self):
        session = SSHSession("example.com")
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.stdout = "output"
        mock_result.returncode = 0
        mock_conn.run = AsyncMock(return_value=mock_result)
        session._conn = mock_conn
        result = await session.run_command("ls -la")
        assert result.stdout == "output"
        mock_conn.run.assert_called_once_with("ls -la")

    @pytest.mark.asyncio
    async def test_run_command_connects_if_needed(self):
        session = SSHSession("example.com")
        mock_conn = AsyncMock()
        mock_conn.run = AsyncMock(return_value=MagicMock())
        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn
            await session.run_command("whoami")
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command_raises_if_no_connection(self):
        session = SSHSession("example.com")
        with (
            patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect,
            pytest.raises(RuntimeError, match="not established"),
        ):
            mock_connect.return_value = None
            await session.run_command("test")

    def test_close(self):
        session = SSHSession("example.com")
        mock_conn = MagicMock()
        session._conn = mock_conn
        session.close()
        mock_conn.close.assert_called_once()

    def test_close_no_connection(self):
        session = SSHSession("example.com")
        session.close()

    def test_resize(self):
        session = SSHSession("example.com")
        mock_channel = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.channel = mock_channel
        session._stdin = MagicMock()
        session._stdout = mock_stdout
        session.resize(100, 50)
        mock_channel.change_terminal_size.assert_called_once_with(100, 50)

    def test_resize_no_stdin(self):
        session = SSHSession("example.com")
        session._stdin = None
        session.resize(100, 50)

    def test_resize_no_channel(self):
        session = SSHSession("example.com")
        session._stdin = MagicMock()
        session._stdout = MagicMock(spec=[])
        session.resize(100, 50)
