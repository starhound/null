from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.validation import Integer
from textual.widgets import Button, Input, Label


class SSHAddScreen(ModalScreen):
    """Screen to add or edit an SSH host."""

    DEFAULT_CSS = """
    SSHAddScreen {
        align: center middle;
        background: $background 80%;
    }

    #ssh-form {
        width: 50;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 0 1; 
        /* Removed vertical padding to let content drive height */
    }

    /* Header styling */
    .header {
        text-align: center;
        text-style: bold;
        border-bottom: solid $primary;
        margin: 1 0;
        color: $text;
        height: auto;
    }

    /* Labels */
    #ssh-form Label {
        margin-top: 1;
        width: 100%;
        color: $text-muted;
        height: 1;
    }
    
    /* Inputs */
    #ssh-form Input {
        margin: 0;
        height: 1;
        border: none;
        background: $panel;
        padding: 0 1;
        min-height: 1;
    }
    
    /* Creds row grid */
    #creds-row {
        height: auto;
        grid-size: 2;
        grid-gutter: 1;
        margin-top: 0;
    }
    
    #creds-row Vertical {
        height: auto;
        width: 100%;
    }

    /* Actions */
    #form-actions {
        margin-top: 1;
        margin-bottom: 1;
        align: right middle;
        height: auto;
        width: 100%;
    }

    #form-actions Button {
        margin-left: 1;
        min-width: 8;
        height: 1;
        border: none;
    }
    """

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

        self.app.storage.add_ssh_host(
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
