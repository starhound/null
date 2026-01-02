from textual.app import ComposeResult

from models import BlockState
from .base import BaseBlockWidget
from .parts import BlockHeader, BlockBody, BlockFooter


class CommandBlock(BaseBlockWidget):
    """Block widget for CLI commands."""

    DEFAULT_CSS = """
    CommandBlock {
        layout: vertical;
        height: auto;
        min-height: 0;
        background: $surface-darken-2;
        margin-bottom: 1;
        padding: 0;
        border-left: thick $success;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__(block)
        self.header = BlockHeader(block)
        self.body_widget = BlockBody(block.content_output or "")
        self.footer_widget = BlockFooter(block)

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.body_widget
        if self.footer_widget._has_content():
            yield self.footer_widget

    def update_output(self, new_content: str = ""):
        """Update the command output display."""
        if self.body_widget:
            self.body_widget.content_text = self.block.content_output

    def set_loading(self, loading: bool):
        """Set the loading state and update footer."""
        self.block.is_running = loading

        try:
            self.footer_widget.remove()
        except Exception:
            pass

        self.footer_widget = BlockFooter(self.block)
        if self.footer_widget._has_content():
            self.mount(self.footer_widget)
