"""Confirmation dialog screen."""

from typing import ClassVar

from textual.binding import BindingType

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    Label,
    ModalScreen,
    Static,
    Vertical,
)


class ConfirmDialog(ModalScreen[bool]):
    """A simple confirmation dialog that returns True/False."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, title: str = "Confirm", message: str = "Are you sure?"):
        super().__init__()
        self.title_text = title
        self.message_text = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            with Vertical(id="confirm-content"):
                yield Static(self.title_text, id="confirm-title")
                yield Label(self.message_text, id="confirm-message")
                with Horizontal(id="confirm-buttons"):
                    yield Button("Yes", id="confirm-yes", variant="primary")
                    yield Button("No", id="confirm-no", variant="default")

    def on_mount(self) -> None:
        self.query_one("#confirm-yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


ConfirmScreen = ConfirmDialog
