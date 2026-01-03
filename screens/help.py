"""Help screen."""

from typing import ClassVar

from textual.binding import BindingType

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    DataTable,
    Label,
    ModalScreen,
)


class HelpScreen(ModalScreen):
    """Screen to show available commands."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Label("Help - Available Commands")
            yield DataTable()
            yield Button("Close [Esc]", variant="default", id="close_btn")

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("Command", "Description", "Shortcut")

        # Get commands from the handler if available
        commands = []
        if hasattr(self.app, "command_handler"):
            for info in self.app.command_handler.get_all_commands():
                commands.append(
                    (f"/{info.name}", info.description, info.shortcut or "")
                )
        else:
            # Fallback hardcoded list
            commands = [
                ("/help", "Show this help screen", "F1"),
                ("/config", "Open settings", ""),
                ("/provider", "Select and configure AI provider", "F4"),
                ("/providers", "Manage all AI providers", ""),
                ("/theme", "Change the UI theme", "F3"),
                ("/model", "List and select AI models", "F2"),
                ("/prompts", "Manage system prompts", ""),
                ("/agent", "Toggle autonomous agent mode", ""),
                ("/mcp", "Manage MCP servers", ""),
                ("/tools", "Browse available MCP tools", ""),
                ("/session", "Manage sessions", ""),
                ("/export", "Export conversation", "Ctrl+S"),
                ("/status", "Show current status", ""),
                ("/clear", "Clear history", "Ctrl+L"),
                ("/compact", "Summarize context", ""),
                ("/quit", "Exit the application", "Ctrl+C"),
            ]

        table.add_rows(commands)
        table.cursor_type = "row"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close_btn":
            self.dismiss()

    def action_dismiss(self):
        self.dismiss()
