"""Tests for SSH Connection Pool Manager."""

import asyncio
import base64
import hashlib
import hmac
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.ssh import SSHConnectionInfo, SSHConnectionPool, SSHConnectionState
from managers.ssh_known_hosts import HostKeyInfo, HostKeyStatus, KnownHostsManager


class TestSSHConnectionState:
    def test_all_states_defined(self):
        assert SSHConnectionState.DISCONNECTED.value == "disconnected"
        assert SSHConnectionState.CONNECTING.value == "connecting"
        assert SSHConnectionState.CONNECTED.value == "connected"
        assert SSHConnectionState.ERROR.value == "error"
        assert SSHConnectionState.RECONNECTING.value == "reconnecting"


class TestSSHConnectionInfo:
    def test_init_defaults(self):
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        assert info.host == "example.com"
        assert info.port == 22
        assert info.username == "user"
        assert info.state == SSHConnectionState.DISCONNECTED
        assert info.connection is None
        assert info.retry_count == 0

    def test_is_connected_false_when_disconnected(self):
        info = SSHConnectionInfo(
            host="example.com", port=22, username=None, key="example.com:22:default"
        )
        assert info.is_connected is False

    def test_is_connected_true_when_connected(self):
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username=None,
            key="example.com:22:default",
            state=SSHConnectionState.CONNECTED,
            connection=MagicMock(),
        )
        assert info.is_connected is True

    def test_uptime_zero_when_not_connected(self):
        info = SSHConnectionInfo(
            host="example.com", port=22, username=None, key="example.com:22:default"
        )
        assert info.uptime == 0.0

    def test_to_dict(self):
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        data = info.to_dict()
        assert data["host"] == "example.com"
        assert data["port"] == 22
        assert data["username"] == "user"
        assert data["state"] == "disconnected"
        assert data["uptime"] == 0.0


class TestSSHConnectionPool:
    def test_init_defaults(self):
        pool = SSHConnectionPool()
        assert pool._keep_alive_interval == 30.0
        assert pool._max_idle_time == 300.0
        assert pool._auto_reconnect is True
        assert pool._running is False

    def test_init_custom_params(self):
        pool = SSHConnectionPool(
            keep_alive_interval=60.0,
            max_idle_time=600.0,
            auto_reconnect=False,
        )
        assert pool._keep_alive_interval == 60.0
        assert pool._max_idle_time == 600.0
        assert pool._auto_reconnect is False

    def test_get_connection_key(self):
        pool = SSHConnectionPool()
        assert pool._get_connection_key("host.com", 22, "user") == "host.com:22:user"
        assert pool._get_connection_key("host.com", 22, None) == "host.com:22:default"
        assert (
            pool._get_connection_key("host.com", 2222, "root") == "host.com:2222:root"
        )

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        pool = SSHConnectionPool()
        await pool.start()
        assert pool._running is True
        assert pool._keep_alive_task is not None
        await pool.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self):
        pool = SSHConnectionPool()
        await pool.start()
        await pool.stop()
        assert pool._running is False
        assert pool._keep_alive_task is None

    @pytest.mark.asyncio
    async def test_get_connection_creates_new_connection(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            info = await pool.get_connection(
                host="example.com",
                port=22,
                username="user",
            )

            assert info.host == "example.com"
            assert info.port == 22
            assert info.username == "user"
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_reuses_existing(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            info1 = await pool.get_connection(host="example.com", username="user")
            info2 = await pool.get_connection(host="example.com", username="user")

            assert info1.key == info2.key
            assert mock_connect.call_count == 1

    @pytest.mark.asyncio
    async def test_close_connection(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_conn.wait_closed = AsyncMock()
            mock_connect.return_value = mock_conn

            info = await pool.get_connection(host="example.com")
            await pool.close_connection(info.key)

            assert info.state == SSHConnectionState.DISCONNECTED
            assert info.connection is None
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_connection(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_conn.wait_closed = AsyncMock()
            mock_connect.return_value = mock_conn

            info = await pool.get_connection(host="example.com")
            key = info.key
            await pool.remove_connection(key)

            assert key not in pool._connections

    def test_list_connections_empty(self):
        pool = SSHConnectionPool()
        assert pool.list_connections() == []

    @pytest.mark.asyncio
    async def test_list_connections_with_data(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            await pool.get_connection(host="host1.com")
            await pool.get_connection(host="host2.com")

            connections = pool.list_connections()
            assert len(connections) == 2

    def test_get_status(self):
        pool = SSHConnectionPool()
        status = pool.get_status()

        assert status["running"] is False
        assert status["total_connections"] == 0
        assert status["connected_count"] == 0
        assert status["keep_alive_interval"] == 30.0
        assert status["max_idle_time"] == 300.0
        assert status["auto_reconnect"] is True

    def test_set_keep_alive_interval(self):
        pool = SSHConnectionPool()
        pool.set_keep_alive_interval(60.0)
        assert pool._keep_alive_interval == 60.0
        pool.set_keep_alive_interval(1.0)
        assert pool._keep_alive_interval == 5.0

    def test_set_max_idle_time(self):
        pool = SSHConnectionPool()
        pool.set_max_idle_time(600.0)
        assert pool._max_idle_time == 600.0
        pool.set_max_idle_time(30.0)
        assert pool._max_idle_time == 60.0

    def test_set_auto_reconnect(self):
        pool = SSHConnectionPool()
        pool.set_auto_reconnect(False)
        assert pool._auto_reconnect is False
        pool.set_auto_reconnect(True)
        assert pool._auto_reconnect is True

    def test_add_state_callback(self):
        pool = SSHConnectionPool()
        callback = MagicMock()
        pool.add_state_callback(callback)
        assert callback in pool._state_callbacks

    def test_remove_state_callback(self):
        pool = SSHConnectionPool()
        callback = MagicMock()
        pool.add_state_callback(callback)
        pool.remove_state_callback(callback)
        assert callback not in pool._state_callbacks

    @pytest.mark.asyncio
    async def test_restore_session(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            info = await pool.restore_session(
                host="example.com",
                username="user",
                password="pass",
            )

            assert info.state == SSHConnectionState.CONNECTED
            assert info.retry_count == 0

    @pytest.mark.asyncio
    async def test_connection_error_sets_error_state(self):
        pool = SSHConnectionPool()

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            info = await pool.get_connection(host="example.com")

            assert info.state == SSHConnectionState.ERROR
            assert "Connection failed" in info.error_message

    @pytest.mark.asyncio
    async def test_state_callback_called_on_connect(self):
        pool = SSHConnectionPool()
        callback = MagicMock()
        pool.add_state_callback(callback)

        with patch("asyncssh.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            await pool.get_connection(host="example.com")

            assert callback.call_count >= 1

    def test_get_connection_by_host(self):
        pool = SSHConnectionPool()
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        pool._connections[info.key] = info

        result = pool.get_connection_by_host("example.com", 22, "user")
        assert result == info

        result_none = pool.get_connection_by_host("other.com", 22, "user")
        assert result_none is None

    def test_get_connection_info(self):
        pool = SSHConnectionPool()
        info = SSHConnectionInfo(
            host="example.com",
            port=22,
            username="user",
            key="example.com:22:user",
        )
        pool._connections[info.key] = info

        result = pool.get_connection_info("example.com:22:user")
        assert result == info

        result_none = pool.get_connection_info("nonexistent")
        assert result_none is None


@pytest.fixture
def temp_ssh_dir(tmp_path: Path) -> Path:
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(mode=0o700)
    return ssh_dir


@pytest.fixture
def sample_key_data() -> bytes:
    return b"ssh-ed25519-test-key-data-for-testing-purposes"


@pytest.fixture
def sample_rsa_key() -> bytes:
    return b"ssh-rsa-test-key-data-different-from-ed25519"


@pytest.fixture
def known_hosts_file(temp_ssh_dir: Path, sample_key_data: bytes) -> Path:
    known_hosts = temp_ssh_dir / "known_hosts"
    key_b64 = base64.b64encode(sample_key_data).decode()
    known_hosts.write_text(
        f"github.com ssh-ed25519 {key_b64}\n"
        f"[gitlab.com]:2222 ssh-ed25519 {key_b64}\n"
        f"example.com,alias.example.com ssh-ed25519 {key_b64}\n"
    )
    return known_hosts


class TestHostKeyInfo:
    def test_fingerprint_calculation(self, sample_key_data: bytes) -> None:
        info = HostKeyInfo(
            hostname="test.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
            status=HostKeyStatus.VERIFIED,
        )

        expected_digest = hashlib.sha256(sample_key_data).digest()
        expected_fp = f"SHA256:{base64.b64encode(expected_digest).decode().rstrip('=')}"

        assert info.fingerprint == expected_fp

    def test_empty_key_data(self) -> None:
        info = HostKeyInfo(
            hostname="test.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=b"",
            status=HostKeyStatus.UNKNOWN,
        )
        assert info.fingerprint == ""


class TestKnownHostsManager:
    def test_load_missing_file(self, temp_ssh_dir: Path) -> None:
        manager = KnownHostsManager(temp_ssh_dir / "known_hosts")
        assert manager.load() is True
        assert manager.list_known_hosts() == []

    def test_load_existing_file(
        self, known_hosts_file: Path, sample_key_data: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        assert manager.load() is True

        hosts = manager.list_known_hosts()
        assert "github.com" in hosts
        assert "[gitlab.com]:2222" in hosts
        assert "example.com" in hosts
        assert "alias.example.com" in hosts

    def test_verify_known_host(
        self, known_hosts_file: Path, sample_key_data: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        result = manager.verify_host_key(
            hostname="github.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
        )
        assert result.status == HostKeyStatus.VERIFIED

    def test_verify_unknown_host(
        self, known_hosts_file: Path, sample_key_data: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        result = manager.verify_host_key(
            hostname="unknown.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
        )
        assert result.status == HostKeyStatus.UNKNOWN

    def test_verify_key_mismatch(
        self, known_hosts_file: Path, sample_rsa_key: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        result = manager.verify_host_key(
            hostname="github.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_rsa_key,
        )
        assert result.status == HostKeyStatus.MISMATCH
        assert "MISMATCH" in (result.error_message or "")

    def test_verify_nonstandard_port(
        self, known_hosts_file: Path, sample_key_data: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        result = manager.verify_host_key(
            hostname="gitlab.com",
            port=2222,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
        )
        assert result.status == HostKeyStatus.VERIFIED

    def test_add_host_key_no_confirm(
        self, temp_ssh_dir: Path, sample_key_data: bytes
    ) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        manager = KnownHostsManager(known_hosts)

        result = manager.add_host_key(
            hostname="newhost.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
            confirm=False,
        )
        assert result is True
        assert known_hosts.exists()
        assert "newhost.com" in known_hosts.read_text()

    def test_add_host_key_with_callback_accept(
        self, temp_ssh_dir: Path, sample_key_data: bytes
    ) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        manager = KnownHostsManager(known_hosts)
        manager.set_confirm_callback(lambda info: True)

        result = manager.add_host_key(
            hostname="newhost.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
            confirm=True,
        )
        assert result is True

    def test_add_host_key_with_callback_reject(
        self, temp_ssh_dir: Path, sample_key_data: bytes
    ) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        manager = KnownHostsManager(known_hosts)
        manager.set_confirm_callback(lambda info: False)

        result = manager.add_host_key(
            hostname="newhost.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
            confirm=True,
        )
        assert result is False
        assert not known_hosts.exists()

    def test_add_host_key_nonstandard_port(
        self, temp_ssh_dir: Path, sample_key_data: bytes
    ) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        manager = KnownHostsManager(known_hosts)

        manager.add_host_key(
            hostname="newhost.com",
            port=2222,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
            confirm=False,
        )
        content = known_hosts.read_text()
        assert "[newhost.com]:2222" in content

    def test_remove_host_key(
        self, known_hosts_file: Path, sample_key_data: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        manager.load()

        assert manager.remove_host_key("github.com") is True
        assert "github.com" not in manager.list_known_hosts()
        assert "github.com" not in known_hosts_file.read_text()

    def test_remove_nonexistent_host(self, known_hosts_file: Path) -> None:
        manager = KnownHostsManager(known_hosts_file)
        manager.load()
        assert manager.remove_host_key("nonexistent.com") is False

    def test_get_host_fingerprint(
        self, known_hosts_file: Path, sample_key_data: bytes
    ) -> None:
        manager = KnownHostsManager(known_hosts_file)
        fingerprint = manager.get_host_fingerprint("github.com")
        assert fingerprint is not None
        assert fingerprint.startswith("SHA256:")

    def test_get_fingerprint_unknown_host(self, known_hosts_file: Path) -> None:
        manager = KnownHostsManager(known_hosts_file)
        assert manager.get_host_fingerprint("unknown.com") is None

    def test_hashed_hostname_verification(
        self, temp_ssh_dir: Path, sample_key_data: bytes
    ) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"

        hostname = "hashed.example.com"
        salt = os.urandom(20)
        hash_value = hmac.new(salt, hostname.encode(), "sha1").digest()

        salt_b64 = base64.b64encode(salt).decode()
        hash_b64 = base64.b64encode(hash_value).decode()
        key_b64 = base64.b64encode(sample_key_data).decode()

        known_hosts.write_text(f"|1|{salt_b64}|{hash_b64} ssh-ed25519 {key_b64}\n")

        manager = KnownHostsManager(known_hosts)
        result = manager.verify_host_key(
            hostname=hostname,
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
        )
        assert result.status == HostKeyStatus.VERIFIED

    def test_permission_error_handling(
        self, temp_ssh_dir: Path, sample_key_data: bytes
    ) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        known_hosts.write_text("")
        os.chmod(known_hosts, 0o000)

        manager = KnownHostsManager(known_hosts)

        try:
            result = manager.load()
            assert result is False
        finally:
            os.chmod(known_hosts, 0o644)

    def test_invalid_line_skipped(self, temp_ssh_dir: Path) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        known_hosts.write_text(
            "invalid line\n"
            "also invalid\n"
            f"valid.com ssh-ed25519 {base64.b64encode(b'test').decode()}\n"
        )

        manager = KnownHostsManager(known_hosts)
        assert manager.load() is True
        assert "valid.com" in manager.list_known_hosts()

    def test_creates_ssh_dir_on_add(
        self, tmp_path: Path, sample_key_data: bytes
    ) -> None:
        ssh_dir = tmp_path / "nonexistent" / ".ssh"
        known_hosts = ssh_dir / "known_hosts"
        manager = KnownHostsManager(known_hosts)

        result = manager.add_host_key(
            hostname="test.com",
            port=22,
            key_type="ssh-ed25519",
            key_data=sample_key_data,
            confirm=False,
        )

        assert result is True
        assert ssh_dir.exists()
        assert (ssh_dir.stat().st_mode & 0o777) == 0o700

    def test_strict_mode_property(self, temp_ssh_dir: Path) -> None:
        manager = KnownHostsManager(temp_ssh_dir / "known_hosts", strict_mode=False)
        assert manager.strict_mode is False

        manager2 = KnownHostsManager(temp_ssh_dir / "known_hosts", strict_mode=True)
        assert manager2.strict_mode is True

    def test_known_hosts_path_property(self, temp_ssh_dir: Path) -> None:
        known_hosts = temp_ssh_dir / "known_hosts"
        manager = KnownHostsManager(known_hosts)
        assert manager.known_hosts_path == known_hosts
