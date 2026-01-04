"""First-run AI disclaimer screen."""

from typing import ClassVar

from textual.binding import BindingType

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    ModalScreen,
    Static,
    Vertical,
)

DISCLAIMER_TEXT = """\
By using Null Terminal's AI features, you acknowledge and accept the following:

• AI models can produce incorrect, misleading, or harmful output
• AI responses should not be treated as professional advice
• You are responsible for reviewing and validating all AI-generated content
• AI may execute commands on your system when using tool capabilities
• Sensitive data shared with AI providers is subject to their privacy policies

The developers of Null Terminal are not liable for any damages, data loss, \
or consequences arising from the use of AI features.

Use AI features at your own risk."""


class DisclaimerScreen(ModalScreen[bool]):
    """First-run disclaimer that must be accepted to use the app."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "accept", "Accept"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="disclaimer-dialog"):
            with Vertical(id="disclaimer-content"):
                yield Static("⚠️  AI USAGE DISCLAIMER  ⚠️", id="disclaimer-title")
                yield Static(DISCLAIMER_TEXT, id="disclaimer-message")
                with Horizontal(id="disclaimer-buttons"):
                    yield Button("I Accept", id="confirm-yes", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "confirm-yes":
            self.dismiss(True)

    def action_accept(self):
        self.dismiss(True)
