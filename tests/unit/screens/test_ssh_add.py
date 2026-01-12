"""Tests for the SSH add/edit host screen."""

from unittest.mock import MagicMock, patch

from screens.ssh_add import SSHAddScreen


class TestSSHAddScreen:
    """Tests for SSHAddScreen initialization and structure."""

    def test_init_creates_screen(self):
        """Screen can be instantiated."""
        screen = SSHAddScreen()
        assert screen is not None

    def test_default_css_defined(self):
        """Screen has DEFAULT_CSS defined."""
        assert SSHAddScreen.DEFAULT_CSS is not None
        assert len(SSHAddScreen.DEFAULT_CSS) > 0
        assert "SSHAddScreen" in SSHAddScreen.DEFAULT_CSS
        assert "#ssh-form" in SSHAddScreen.DEFAULT_CSS


class TestSSHAddScreenOnMount:
    """Tests for on_mount behavior."""

    def test_on_mount_focuses_alias_input(self):
        """on_mount should focus the alias input field."""
        screen = SSHAddScreen()
        mock_input = MagicMock()
        screen.query_one = MagicMock(return_value=mock_input)

        screen.on_mount()

        screen.query_one.assert_called_once()
        mock_input.focus.assert_called_once()


class TestSSHAddScreenInputSubmitted:
    """Tests for input submission behavior."""

    def test_input_submitted_calls_save_host(self):
        """on_input_submitted should trigger _save_host."""
        screen = SSHAddScreen()
        screen._save_host = MagicMock()

        mock_event = MagicMock()
        screen.on_input_submitted(mock_event)

        screen._save_host.assert_called_once()


class TestSSHAddScreenButtonHandling:
    """Tests for button press handling."""

    def test_cancel_button_dismisses(self):
        """Cancel button should dismiss the screen."""
        screen = SSHAddScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "cancel"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with()

    def test_save_button_calls_save_host(self):
        """Save button should trigger _save_host."""
        screen = SSHAddScreen()
        screen._save_host = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "save"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen._save_host.assert_called_once()

    def test_unknown_button_no_action(self):
        """Unknown button ID should not trigger any action."""
        screen = SSHAddScreen()
        screen.dismiss = MagicMock()
        screen._save_host = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "unknown"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_not_called()
        screen._save_host.assert_not_called()


class TestSSHAddScreenSaveHost:
    """Tests for _save_host method."""

    def _create_mock_inputs(
        self,
        alias="test-host",
        hostname="192.168.1.1",
        username="root",
        port="22",
        key_path="",
        jump_host="",
        password="",
    ):
        """Helper to create mock input values."""
        return {
            "#alias": MagicMock(value=alias),
            "#hostname": MagicMock(value=hostname),
            "#username": MagicMock(value=username),
            "#port": MagicMock(value=port),
            "#key_path": MagicMock(value=key_path),
            "#jump_host": MagicMock(value=jump_host),
            "#password": MagicMock(value=password),
        }

    def test_save_host_missing_alias_notifies_error(self):
        """Missing alias should show error notification."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_inputs = self._create_mock_inputs(alias="", hostname="example.com")
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        screen._save_host()

        screen.notify.assert_called_once()
        assert "required" in screen.notify.call_args[0][0].lower()
        assert screen.notify.call_args[1]["severity"] == "error"
        screen.dismiss.assert_not_called()

    def test_save_host_missing_hostname_notifies_error(self):
        """Missing hostname should show error notification."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_inputs = self._create_mock_inputs(alias="my-host", hostname="")
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        screen._save_host()

        screen.notify.assert_called_once()
        assert "required" in screen.notify.call_args[0][0].lower()
        assert screen.notify.call_args[1]["severity"] == "error"
        screen.dismiss.assert_not_called()

    def test_save_host_missing_both_alias_and_hostname_notifies_error(self):
        """Missing both alias and hostname should show error notification."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_inputs = self._create_mock_inputs(alias="", hostname="")
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        screen._save_host()

        screen.notify.assert_called_once()
        assert "required" in screen.notify.call_args[0][0].lower()
        assert screen.notify.call_args[1]["severity"] == "error"
        screen.dismiss.assert_not_called()

    def test_save_host_invalid_port_notifies_error(self):
        """Invalid port number should show error notification."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_inputs = self._create_mock_inputs(
            alias="test-host", hostname="example.com", port="not-a-number"
        )
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        screen._save_host()

        screen.notify.assert_called_once()
        assert "port" in screen.notify.call_args[0][0].lower()
        assert "number" in screen.notify.call_args[0][0].lower()
        assert screen.notify.call_args[1]["severity"] == "error"
        screen.dismiss.assert_not_called()

    def test_save_host_empty_port_notifies_error(self):
        """Empty port string should show error notification."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_inputs = self._create_mock_inputs(
            alias="test-host", hostname="example.com", port=""
        )
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        screen._save_host()

        screen.notify.assert_called_once()
        assert "port" in screen.notify.call_args[0][0].lower()
        assert screen.notify.call_args[1]["severity"] == "error"
        screen.dismiss.assert_not_called()

    def test_save_host_success_with_required_fields_only(self):
        """Successful save with only required fields."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_storage = MagicMock()
        mock_storage.add_ssh_host = MagicMock()

        mock_app = MagicMock()
        mock_app.storage = mock_storage

        mock_inputs = self._create_mock_inputs(
            alias="prod-server",
            hostname="prod.example.com",
            username="",
            port="22",
            key_path="",
            jump_host="",
            password="",
        )
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        with patch.object(
            type(screen), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            screen._save_host()

        mock_storage.add_ssh_host.assert_called_once_with(
            alias="prod-server",
            hostname="prod.example.com",
            port=22,
            username=None,
            key_path=None,
            password=None,
            jump_host=None,
        )
        screen.notify.assert_called_once()
        assert "saved" in screen.notify.call_args[0][0].lower()
        assert "prod-server" in screen.notify.call_args[0][0]
        screen.dismiss.assert_called_once_with(True)

    def test_save_host_success_with_all_fields(self):
        """Successful save with all fields populated."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_storage = MagicMock()
        mock_storage.add_ssh_host = MagicMock()

        mock_app = MagicMock()
        mock_app.storage = mock_storage

        mock_inputs = self._create_mock_inputs(
            alias="staging",
            hostname="staging.example.com",
            username="deploy",
            port="2222",
            key_path="~/.ssh/staging_key",
            jump_host="bastion",
            password="secret123",
        )
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        with patch.object(
            type(screen), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            screen._save_host()

        mock_storage.add_ssh_host.assert_called_once_with(
            alias="staging",
            hostname="staging.example.com",
            port=2222,
            username="deploy",
            key_path="~/.ssh/staging_key",
            password="secret123",
            jump_host="bastion",
        )
        screen.notify.assert_called_once()
        assert "staging" in screen.notify.call_args[0][0]
        screen.dismiss.assert_called_once_with(True)

    def test_save_host_storage_exception_notifies_error(self):
        """Storage exception should show error notification."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_storage = MagicMock()
        mock_storage.add_ssh_host = MagicMock(
            side_effect=Exception("Database connection failed")
        )

        mock_app = MagicMock()
        mock_app.storage = mock_storage

        mock_inputs = self._create_mock_inputs(
            alias="test-host",
            hostname="example.com",
            username="root",
            port="22",
        )
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        with patch.object(
            type(screen), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            screen._save_host()

        screen.notify.assert_called_once()
        assert "failed" in screen.notify.call_args[0][0].lower()
        assert "Database connection failed" in screen.notify.call_args[0][0]
        assert screen.notify.call_args[1]["severity"] == "error"
        screen.dismiss.assert_not_called()

    def test_save_host_converts_empty_optional_fields_to_none(self):
        """Empty optional fields should be converted to None."""
        screen = SSHAddScreen()
        screen.notify = MagicMock()
        screen.dismiss = MagicMock()

        mock_storage = MagicMock()
        mock_storage.add_ssh_host = MagicMock()

        mock_app = MagicMock()
        mock_app.storage = mock_storage

        mock_inputs = self._create_mock_inputs(
            alias="dev",
            hostname="dev.local",
            username="",
            port="22",
            key_path="",
            jump_host="",
            password="",
        )
        screen.query_one = MagicMock(side_effect=lambda sel, _: mock_inputs[sel])

        with patch.object(
            type(screen), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            screen._save_host()

        call_kwargs = mock_storage.add_ssh_host.call_args[1]
        assert call_kwargs["username"] is None
        assert call_kwargs["key_path"] is None
        assert call_kwargs["password"] is None
        assert call_kwargs["jump_host"] is None

    def test_save_host_with_different_port_values(self):
        """Various valid port numbers should be accepted."""
        test_ports = ["1", "22", "443", "8080", "65535"]

        for port_str in test_ports:
            screen = SSHAddScreen()
            screen.notify = MagicMock()
            screen.dismiss = MagicMock()

            mock_storage = MagicMock()
            mock_storage.add_ssh_host = MagicMock()

            mock_app = MagicMock()
            mock_app.storage = mock_storage

            mock_inputs = self._create_mock_inputs(
                alias=f"host-{port_str}",
                hostname="example.com",
                port=port_str,
            )
            screen.query_one = MagicMock(
                side_effect=lambda sel, _, inputs=mock_inputs: inputs[sel]
            )

            with patch.object(
                type(screen),
                "app",
                new_callable=lambda app=mock_app: property(lambda self, app=app: app),
            ):
                screen._save_host()

            call_kwargs = mock_storage.add_ssh_host.call_args[1]
            assert call_kwargs["port"] == int(port_str)


class TestSSHAddScreenCSSStyles:
    """Tests for CSS style definitions."""

    def test_css_contains_form_container(self):
        """CSS should define ssh-form container styles."""
        css = SSHAddScreen.DEFAULT_CSS
        assert "#ssh-form" in css
        assert "width:" in css or "width" in css

    def test_css_contains_header_styles(self):
        """CSS should define header styles."""
        css = SSHAddScreen.DEFAULT_CSS
        assert ".header" in css
        assert "text-align" in css or "text-style" in css

    def test_css_contains_input_styles(self):
        """CSS should define input field styles."""
        css = SSHAddScreen.DEFAULT_CSS
        assert "Input" in css

    def test_css_contains_button_styles(self):
        """CSS should define button styles."""
        css = SSHAddScreen.DEFAULT_CSS
        assert "Button" in css

    def test_css_contains_form_actions(self):
        """CSS should define form actions container."""
        css = SSHAddScreen.DEFAULT_CSS
        assert "#form-actions" in css

    def test_css_contains_creds_row(self):
        """CSS should define credentials row grid."""
        css = SSHAddScreen.DEFAULT_CSS
        assert "#creds-row" in css
        assert "grid-size" in css
