from textual.app import ComposeResult

from models import BlockState
from .base import BaseBlockWidget
from .parts import BlockHeader, BlockBody


class SystemBlock(BaseBlockWidget):
    """Block widget for system messages."""

    def __init__(self, block: BlockState):
        super().__init__(block)
        self.header = BlockHeader(block)
        self.body_widget = BlockBody(block.content_output or "")

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.body_widget

    def update_output(self, new_content: str = ""):
        """Update the system message display."""
        if self.body_widget:
            self.body_widget.content_text = self.block.content_output
