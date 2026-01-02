"""Tool call block widget for agent mode."""

from textual.app import ComposeResult

from models import BlockState
from .base import BaseBlockWidget
from .parts import BlockHeader, BlockBody, BlockMeta


class ToolCallBlock(BaseBlockWidget):
    """Block widget for tool call executions in agent mode."""

    def __init__(self, block: BlockState):
        super().__init__(block)
        self.header = BlockHeader(block)
        self.meta = BlockMeta(block)
        self.body_widget = BlockBody(block.content_output or "")

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.meta
        yield self.body_widget

    def update_output(self, new_content: str = ""):
        """Update the tool call output display."""
        if self.body_widget:
            self.body_widget.content_text = self.block.content_output

    def update_metadata(self):
        """Update metadata display."""
        if self.meta:
            self.meta.block = self.block
            self.meta.refresh()
