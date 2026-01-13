"""Integration tests for SSH Manager functionality.

Tests cover:
1. SSHScreen displays list of saved connections
2. Adding a new connection opens SSHAddScreen
3. Editing a connection
4. Deleting a connection
5. Connecting to a saved host
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.widgets import Button, Input

from app import NullApp
from screens.ssh import SSHScreen
from screens.ssh_add import SSHAddScreen


@pytest.fixture
def mock_ssh_session():
    """Create a mock SSH session."""
    session = MagicMock()
    session.close = MagicMock()
    session.connected = True
    return session


@pytest.fixture
def sample_ssh_hosts():
    """Sample SSH host data."""
    return [
        {
            "alias": "prod-server",
            "hostname": "prod.example.com",
            "port": 22,
            "username": "admin",
            "jump_host": None,
        },
        {
            "alias": "staging",
            "hostname": "staging.example.com",
            "port": 2222,
            "username": "deploy",
            "jump_host": None,
        },
        {
            "alias": "bastion",
            "hostname": "bastion.example.com",
            "port": 22,
            "username": "root",
            "jump_host": None,
        },
    ]


class TestSSHScreenDisplaysSavedConnections:
    """Test that SSH functionality can display saved connections."""

    @pytest.mark.asyncio
    async def test_list_ssh_hosts_returns_saved_connections(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Storage should return list of saved SSH hosts."""
        mock_storage.add_ssh_host(
            "test-server", "test.example.com", port=22, username="user"
        )
        mock_storage.add_ssh_host(
            "dev-server", "dev.example.com", port=2222, username="dev"
        )

        hosts = mock_storage.list_ssh_hosts()

        assert len(hosts) == 2
        aliases = [h["alias"] for h in hosts]
        assert "test-server" in aliases
        assert "dev-server" in aliases

    @pytest.mark.asyncio
    async def test_empty_hosts_list(self, temp_home, mock_storage, mock_ai_components):
        """Empty database should return empty list."""
        hosts = mock_storage.list_ssh_hosts()
        assert hosts == []

    @pytest.mark.asyncio
    async def test_hosts_sorted_by_alias(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """SSH hosts should be sorted alphabetically by alias."""
        mock_storage.add_ssh_host("zebra", "z.example.com")
        mock_storage.add_ssh_host("alpha", "a.example.com")
        mock_storage.add_ssh_host("middle", "m.example.com")

        hosts = mock_storage.list_ssh_hosts()
        aliases = [h["alias"] for h in hosts]

        assert aliases == ["alpha", "middle", "zebra"]


class TestAddConnectionOpensSSHAddScreen:
    """Test that adding a new connection opens SSHAddScreen."""

    @pytest.mark.asyncio
    async def test_push_ssh_add_screen(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Pushing SSHAddScreen should display the add form."""
        app = NullApp()
        async with app.run_test(size=(120, 50)) as pilot:
            app.push_screen(SSHAddScreen())
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen, SSHAddScreen)
            assert app.screen.query_one("#alias", Input) is not None

    @pytest.mark.asyncio
    async def test_ssh_add_screen_default_port(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Port field should default to 22."""
        app = NullApp()
        async with app.run_test(size=(120, 50)) as pilot:
            app.push_screen(SSHAddScreen())
            await pilot.pause()
            await pilot.pause()

            port_input = app.screen.query_one("#port", Input)
            assert port_input.value == "22"


class TestEditConnection:
    """Test editing an existing SSH connection."""

    @pytest.mark.asyncio
    async def test_update_existing_host(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Updating an existing host should overwrite values."""
        mock_storage.add_ssh_host(
            "server", "old.example.com", port=22, username="olduser"
        )
        mock_storage.add_ssh_host(
            "server", "new.example.com", port=3333, username="newuser"
        )

        host = mock_storage.get_ssh_host("server")

        assert host["hostname"] == "new.example.com"
        assert host["port"] == 3333
        assert host["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_partial_update_preserves_alias(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Updating should preserve the alias."""
        mock_storage.add_ssh_host("myhost", "original.com", port=22)
        mock_storage.add_ssh_host("myhost", "updated.com", port=8022)

        hosts = mock_storage.list_ssh_hosts()
        assert len(hosts) == 1
        assert hosts[0]["alias"] == "myhost"

    @pytest.mark.asyncio
    async def test_get_ssh_host_for_editing(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """get_ssh_host should return full host details for editing."""
        mock_storage.add_ssh_host(
            alias="edit-test",
            hostname="edit.example.com",
            port=2222,
            username="editor",
            key_path="~/.ssh/edit_key",
            password="secret123",
            jump_host="bastion",
        )

        host = mock_storage.get_ssh_host("edit-test")

        assert host["alias"] == "edit-test"
        assert host["hostname"] == "edit.example.com"
        assert host["port"] == 2222
        assert host["username"] == "editor"
        assert host["key_path"] == "~/.ssh/edit_key"
        assert host["password"] == "secret123"
        assert host["jump_host"] == "bastion"


class TestDeleteConnection:
    """Test deleting SSH connections."""

    @pytest.mark.asyncio
    async def test_delete_existing_host(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """delete_ssh_host should remove the host."""
        mock_storage.add_ssh_host("to-delete", "delete.example.com")
        assert mock_storage.get_ssh_host("to-delete") is not None

        mock_storage.delete_ssh_host("to-delete")

        assert mock_storage.get_ssh_host("to-delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_host_no_error(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Deleting nonexistent host should not raise."""
        mock_storage.delete_ssh_host("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_delete_leaves_other_hosts(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Deleting one host should not affect others."""
        mock_storage.add_ssh_host("keep1", "keep1.example.com")
        mock_storage.add_ssh_host("delete-me", "delete.example.com")
        mock_storage.add_ssh_host("keep2", "keep2.example.com")

        mock_storage.delete_ssh_host("delete-me")

        hosts = mock_storage.list_ssh_hosts()
        aliases = [h["alias"] for h in hosts]

        assert "keep1" in aliases
        assert "keep2" in aliases
        assert "delete-me" not in aliases
        assert len(hosts) == 2


class TestConnectToSavedHost:
    """Test connecting to a saved SSH host."""

    @pytest.mark.asyncio
    async def test_ssh_screen_detach_closes_session(
        self, temp_home, mock_storage, mock_ai_components, mock_ssh_session
    ):
        """Detaching should close the SSH session."""
        from textual.widgets import Static

        mock_terminal = MagicMock(spec=Static)
        mock_terminal.return_value = Static("Mock SSH Terminal")

        with patch("screens.ssh.SSHTerminal", mock_terminal):
            app = NullApp()
            async with app.run_test(size=(120, 50)) as pilot:
                screen = SSHScreen(mock_ssh_session, alias="test-host")
                app.push_screen(screen)
                await pilot.pause()

                screen.action_detach()
                await pilot.pause()

                mock_ssh_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_host_config_for_connection(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """get_ssh_host should return config needed for connection."""
        mock_storage.add_ssh_host(
            alias="connect-test",
            hostname="connect.example.com",
            port=22,
            username="connector",
            key_path="~/.ssh/id_rsa",
        )

        host = mock_storage.get_ssh_host("connect-test")

        assert host is not None
        assert host["hostname"] == "connect.example.com"
        assert host["port"] == 22
        assert host["username"] == "connector"

    @pytest.mark.asyncio
    async def test_get_nonexistent_host_returns_none(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Getting nonexistent host should return None."""
        result = mock_storage.get_ssh_host("does-not-exist")
        assert result is None


class TestSSHAddScreenInteraction:
    """Test SSHAddScreen form interactions."""

    @pytest.mark.asyncio
    async def test_save_button_saves_host(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Clicking save with valid data should save the host."""
        with patch("app.Config._get_storage", return_value=mock_storage):
            with patch("handlers.input.Config._get_storage", return_value=mock_storage):
                app = NullApp()
                async with app.run_test(size=(120, 50)) as pilot:
                    app.push_screen(SSHAddScreen())
                    await pilot.pause()
                    await pilot.pause()

                    app.screen.query_one("#alias", Input).value = "new-host"
                    app.screen.query_one("#hostname", Input).value = "new.example.com"
                    app.screen.query_one("#username", Input).value = "newuser"
                    await pilot.pause()

                    save_btn = app.screen.query_one("#save", Button)
                    save_btn.press()
                    await pilot.pause()
                    await pilot.pause()

                    host = mock_storage.get_ssh_host("new-host")
                    assert host is not None
                    assert host["hostname"] == "new.example.com"

    @pytest.mark.asyncio
    async def test_cancel_button_dismisses_without_save(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Cancel should dismiss screen without saving."""
        app = NullApp()
        async with app.run_test(size=(120, 50)) as pilot:
            app.push_screen(SSHAddScreen())
            await pilot.pause()
            await pilot.pause()

            app.screen.query_one("#alias", Input).value = "unsaved"
            app.screen.query_one("#hostname", Input).value = "unsaved.example.com"
            await pilot.pause()

            cancel_btn = app.screen.query_one("#cancel", Button)
            cancel_btn.press()
            await pilot.pause()
            await pilot.pause()

            assert not isinstance(app.screen, SSHAddScreen)
            assert mock_storage.get_ssh_host("unsaved") is None

    @pytest.mark.asyncio
    async def test_save_requires_alias_and_hostname(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Save should fail if alias or hostname is empty."""
        app = NullApp()
        async with app.run_test(size=(120, 50)) as pilot:
            app.push_screen(SSHAddScreen())
            await pilot.pause()
            await pilot.pause()

            # Leave alias and hostname empty, try to save
            save_btn = app.screen.query_one("#save", Button)
            save_btn.press()
            await pilot.pause()

            # Screen should still be open (save failed)
            assert isinstance(app.screen, SSHAddScreen)


class TestSSHPasswordEncryption:
    """Test that SSH passwords are encrypted."""

    @pytest.mark.asyncio
    async def test_password_is_encrypted_in_db(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Password should be encrypted when stored."""
        mock_storage.add_ssh_host(
            alias="encrypted-test",
            hostname="enc.example.com",
            password="supersecret",
        )

        cursor = mock_storage.conn.cursor()
        cursor.execute(
            "SELECT encrypted_password FROM ssh_hosts WHERE alias = ?",
            ("encrypted-test",),
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["encrypted_password"] != "supersecret"
        assert row["encrypted_password"] is not None

    @pytest.mark.asyncio
    async def test_password_decrypted_on_retrieval(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Password should be decrypted when retrieved."""
        mock_storage.add_ssh_host(
            alias="decrypt-test",
            hostname="dec.example.com",
            password="mypassword",
        )

        host = mock_storage.get_ssh_host("decrypt-test")

        assert host["password"] == "mypassword"


class TestSSHJumpHost:
    """Test SSH jump host (bastion) functionality."""

    @pytest.mark.asyncio
    async def test_save_with_jump_host(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """Should be able to save host with jump host."""
        mock_storage.add_ssh_host("bastion", "bastion.example.com")
        mock_storage.add_ssh_host(
            alias="internal",
            hostname="internal.example.com",
            jump_host="bastion",
        )

        host = mock_storage.get_ssh_host("internal")

        assert host["jump_host"] == "bastion"

    @pytest.mark.asyncio
    async def test_list_hosts_includes_jump_host(
        self, temp_home, mock_storage, mock_ai_components
    ):
        """list_ssh_hosts should include jump_host field."""
        mock_storage.add_ssh_host(
            alias="with-jump",
            hostname="jump.example.com",
            jump_host="mybastion",
        )

        hosts = mock_storage.list_ssh_hosts()
        host = next(h for h in hosts if h["alias"] == "with-jump")

        assert "jump_host" in host
        assert host["jump_host"] == "mybastion"
