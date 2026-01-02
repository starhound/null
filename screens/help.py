"""Help screen."""

from .base import ModalScreen, ComposeResult, Binding, Container, Label, DataTable, Button


class HelpScreen(ModalScreen):
    """Screen to show available commands."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Label("Help - Available Commands")
            yield DataTable()
            yield Button("Close [Esc]", variant="default", id="close_btn")

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("Command", "Description")
        table.add_rows([
            ("/help", "Show this help screen"),
            ("/config", "Open settings"),
            ("/provider", "Select and configure AI provider"),
            ("/theme <name>", "Change the UI theme"),
            ("/model", "List and select AI models"),
            ("/prompts", "Manage system prompts"),
            ("/mcp", "Manage MCP servers"),
            ("/session", "Manage sessions"),
            ("/export", "Export conversation"),
            ("/status", "Show current status"),
            ("/clear", "Clear history"),
            ("/compact", "Summarize context"),
            ("/quit", "Exit the application"),
        ])
        table.cursor_type = "row"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close_btn":
            self.dismiss()

    def action_dismiss(self):
        self.dismiss()
