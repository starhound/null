"""Save file dialog screen."""

from typing import ClassVar

from textual.binding import BindingType

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    Input,
    Label,
    ModalScreen,
)


class SaveFileDialog(ModalScreen):
    """Dialog to prompt for a filename and save content."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, suggested_name: str = "code.txt", content: str = ""):
        super().__init__()
        self.suggested_name = suggested_name
        self.content = content

    def compose(self) -> ComposeResult:
        with Container(id="save-dialog-container"):
            yield Label("Save Code to File")
            yield Label("Enter filename:", classes="input-label")
            yield Input(
                value=self.suggested_name,
                placeholder="filename.py",
                id="filename-input",
            )
            with Horizontal(id="save-dialog-buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_mount(self):
        """Focus the input on mount."""
        self.query_one("#filename-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        """Handle enter key in input."""
        self._do_save()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._do_save()
        else:
            self.dismiss(None)

    def action_cancel(self):
        """Cancel the dialog."""
        self.dismiss(None)

    def _do_save(self):
        """Save the file and dismiss."""
        filename = self.query_one("#filename-input", Input).value.strip()
        if not filename:
            self.notify("Please enter a filename", severity="warning")
            return

        try:
            from pathlib import Path

            filepath = Path.cwd() / filename

            # Create parent directories if needed
            filepath.parent.mkdir(parents=True, exist_ok=True)

            filepath.write_text(self.content, encoding="utf-8")
            self.notify(f"Saved to {filepath}")
            self.dismiss(str(filepath))
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")
