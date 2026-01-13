from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.validation import Integer
from textual.widgets import Button, Input, Label

if TYPE_CHECKING:
    from app import NullApp


class SSHAddScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="ssh-form"):
            yield Label("Add SSH Host", classes="header")

            yield Label("Alias (unique name)")
            yield Input(placeholder="e.g. prod-db", id="alias")

            yield Label("Hostname")
            yield Input(placeholder="example.com or IP", id="hostname")

            with Grid(id="creds-row"):
                with Vertical():
                    yield Label("Username")
                    yield Input(placeholder="root", id="username")
                with Vertical():
                    yield Label("Port")
                    yield Input(str(22), validators=[Integer()], id="port")

            yield Label("Key Path (optional)")
            yield Input(placeholder="~/.ssh/id_rsa", id="key_path")

            yield Label("Jump Host Alias (optional)")
            yield Input(placeholder="bastion", id="jump_host")

            yield Label("Password (optional)")
            yield Input(placeholder="Top Secret", password=True, id="password")

            with Horizontal(id="form-actions"):
                yield Button("Cancel", variant="error", id="cancel")
                yield Button("Save", variant="success", id="save")

    def on_mount(self) -> None:
        self.query_one("#alias", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._save_host()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "cancel":
            self.dismiss()
        elif event.button.id == "save":
            self._save_host()

    def _save_host(self):
        alias = self.query_one("#alias", Input).value
        hostname = self.query_one("#hostname", Input).value
        username = self.query_one("#username", Input).value
        port_str = self.query_one("#port", Input).value
        key_path = self.query_one("#key_path", Input).value
        jump_host = self.query_one("#jump_host", Input).value
        password = self.query_one("#password", Input).value

        if not alias or not hostname:
            self.notify("Alias and Hostname are required", severity="error")
            return

        try:
            port = int(port_str)
        except ValueError:
            self.notify("Port must be a number", severity="error")
            return

        try:
            app: NullApp = self.app  # type: ignore[assignment]
            app.storage.add_ssh_host(
                alias=alias,
                hostname=hostname,
                port=port,
                username=username or None,
                key_path=key_path or None,
                password=password or None,
                jump_host=jump_host or None,
            )
            self.notify(f"Saved SSH host: {alias}")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Failed to save SSH host: {e!s}", severity="error")
