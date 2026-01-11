"""MCP server configuration screen."""

from typing import ClassVar

from textual.binding import BindingType

from .base import Binding, Button, ComposeResult, Container, Input, Label, ModalScreen


class MCPServerConfigScreen(ModalScreen):
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    MCPServerConfigScreen {
        align: center middle;
    }

    #mcp-config-container {
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
    }

    #mcp-config-container > Label:first-child {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    .input-label {
        margin-top: 1;
        text-style: bold;
    }

    .input-hint {
        color: $text-muted;
        text-style: italic;
    }

    #mcp-config-container Input {
        margin-bottom: 0;
    }

    #buttons {
        margin-top: 2;
        height: auto;
        align: center middle;
    }

    #buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, name: str = "", current_config: dict | None = None):
        super().__init__()
        self.server_name = name
        self.current_config = current_config or {}
        self.is_edit = bool(name)

    def compose(self) -> ComposeResult:
        with Container(id="mcp-config-container"):
            title = (
                f"Edit MCP Server: {self.server_name}"
                if self.is_edit
                else "Add MCP Server"
            )
            yield Label(title)

            yield Label("Server Name", classes="input-label")
            yield Input(
                placeholder="e.g., filesystem, github, sqlite",
                id="name",
                value=self.server_name,
                disabled=self.is_edit,
            )

            yield Label("Command", classes="input-label")
            yield Label(
                "The executable to run (e.g., npx, python, node)", classes="input-hint"
            )
            yield Input(
                placeholder="npx",
                id="command",
                value=self.current_config.get("command", ""),
            )

            yield Label("Arguments", classes="input-label")
            yield Label(
                "Space-separated arguments for the command", classes="input-hint"
            )
            args = self.current_config.get("args", [])
            args_str = " ".join(args) if isinstance(args, list) else str(args)
            yield Input(
                placeholder="-y @modelcontextprotocol/server-filesystem /path",
                id="args",
                value=args_str,
            )

            yield Label("Environment Variables", classes="input-label")
            yield Label("KEY=value pairs, space-separated", classes="input-hint")
            env = self.current_config.get("env", {})
            env_str = (
                " ".join(f"{k}={v}" for k, v in env.items())
                if isinstance(env, dict)
                else ""
            )
            yield Input(
                placeholder="GITHUB_TOKEN=xxx API_KEY=yyy", id="env", value=env_str
            )

            with Container(id="buttons"):
                yield Button("Save", variant="default", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        if self.is_edit:
            self.query_one("#command", Input).focus()
        else:
            self.query_one("#name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#save", Button).press()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            name = self.query_one("#name", Input).value.strip()
            command = self.query_one("#command", Input).value.strip()
            args_str = self.query_one("#args", Input).value.strip()
            env_str = self.query_one("#env", Input).value.strip()

            if not name:
                self.notify("Server name is required", severity="error")
                return
            if not command:
                self.notify("Command is required", severity="error")
                return

            import shlex

            args = shlex.split(args_str) if args_str else []

            env = {}
            if env_str:
                try:
                    pairs = shlex.split(env_str)
                    for pair in pairs:
                        if "=" in pair:
                            key, value = pair.split("=", 1)
                            env[key] = value
                except Exception:
                    for pair in env_str.split():
                        if "=" in pair:
                            key, value = pair.split("=", 1)
                            env[key] = value

            result = {"name": name, "command": command, "args": args, "env": env}
            self.dismiss(result)
        else:
            self.dismiss(None)

    def action_dismiss(self) -> None:
        self.dismiss(None)
