"""Action bar widget for AI response blocks."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Label
from textual.message import Message
from textual.events import Click


class ActionButton(Static):
    """ASCII-styled action button."""

    DEFAULT_CSS = """
    ActionButton {
        width: auto;
        height: 1;
        padding: 0 1;
        margin: 0 1 0 0;
        color: $text-muted;
    }
    ActionButton:hover {
        color: $accent;
        background: $surface-lighten-1;
    }
    ActionButton.-disabled {
        color: $text-disabled;
    }
    """

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
        classes: str | None = None
    ):
        super().__init__(label, id=id, classes=classes)
        self.action = action
        self.block_id = block_id
        self._disabled = disabled
        if disabled:
            self.add_class("-disabled")

    def on_click(self, event: Click) -> None:
        """Handle click events."""
        event.stop()
        event.prevent_default()
        if not self._disabled:
            self.post_message(self.Pressed(self.action, self.block_id))


class ActionBar(Horizontal):
    """Container for action buttons on AI blocks."""

    DEFAULT_CSS = """
    ActionBar {
        width: 100%;
        height: auto;
        padding: 0 1;
        align: left middle;
    }
    ActionBar .action-spacer {
        width: 1fr;
    }
    ActionBar .action-meta {
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(
        self,
        block_id: str,
        show_fork: bool = True,
        show_edit: bool = True,
        meta_text: str = "",
        id: str | None = None,
        classes: str | None = None
    ):
        super().__init__(id=id, classes=classes)
        self.block_id = block_id
        self.show_fork = show_fork
        self.show_edit = show_edit
        self.meta_text = meta_text

    def compose(self) -> ComposeResult:
        yield ActionButton("[Copy]", "copy", self.block_id, id="copy-btn")
        yield ActionButton("[Retry]", "retry", self.block_id, id="retry-btn")
        if self.show_edit:
            yield ActionButton("[Edit]", "edit", self.block_id, id="edit-btn")
        if self.show_fork:
            yield ActionButton("[Fork]", "fork", self.block_id, id="fork-btn")

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
