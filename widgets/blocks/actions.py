"""Action bar widget for AI response blocks."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label, Static


class ActionButton(Button):
    """Action button using proper Textual Button widget."""

    class Pressed(Message, bubble=True):
        """Message sent when an action button is clicked."""

        def __init__(self, action: str, block_id: str):
            super().__init__()
            self.action = action
            self.block_id = block_id

    def __init__(
        self,
        label: str,
        action: str,
        block_id: str,
        disabled: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(label, id=id, classes=classes, disabled=disabled)
        self.action = action
        self.block_id = block_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press - emit our custom Pressed message."""
        event.stop()
        self.post_message(self.Pressed(self.action, self.block_id))


class ActionBar(Horizontal):
    """Container for action buttons on AI blocks."""

    def __init__(
        self,
        block_id: str,
        show_fork: bool = True,
        show_edit: bool = True,
        meta_text: str = "",
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.block_id = block_id
        self.show_fork = show_fork
        self.show_edit = show_edit
        self.meta_text = meta_text

    def compose(self) -> ComposeResult:
        yield ActionButton("Copy", "copy", self.block_id, id="copy-btn")
        yield ActionButton("Retry", "retry", self.block_id, id="retry-btn")
        if self.show_edit:
            yield ActionButton("Edit", "edit", self.block_id, id="edit-btn")
        if self.show_fork:
            yield ActionButton("Fork", "fork", self.block_id, id="fork-btn")

        # Spacer to push meta to the right
        yield Static("", classes="action-spacer")

        # Meta info on the right
        if self.meta_text:
            yield Label(self.meta_text, classes="action-meta")

    def update_meta(self, meta_text: str) -> None:
        """Update the meta text."""
        self.meta_text = meta_text
        try:
            meta_label = self.query_one(".action-meta", Label)
            meta_label.update(meta_text)
        except Exception:
            pass

    def show_copy_feedback(self) -> None:
        try:
            copy_btn = self.query_one("#copy-btn", ActionButton)
            original_label = copy_btn.label
            copy_btn.label = "✓ Copied"
            copy_btn.add_class("copied")
            self.set_timer(
                1.5, lambda: self._reset_copy_button(copy_btn, original_label)
            )
        except Exception:
            pass

    def _reset_copy_button(self, btn: ActionButton, original_label) -> None:
        try:
            btn.label = original_label
            btn.remove_class("copied")
        except Exception:
            pass

    def _reset_copy_button(self, btn: ActionButton, original_label) -> None:
        try:
            btn.label = original_label
            btn.remove_class("copied")
        except Exception:
            pass
