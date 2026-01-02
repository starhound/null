from textual.app import ComposeResult
from textual.events import Click
from textual import on

from models import BlockState
from .base import BaseBlockWidget
from .parts import BlockHeader, BlockMeta, BlockFooter
from .thinking import ThinkingWidget
from .execution import ExecutionWidget


class AIResponseBlock(BaseBlockWidget):
    """Block widget for AI responses with thinking and execution sections."""

    def __init__(self, block: BlockState):
        super().__init__(block)
        self.header = BlockHeader(block)
        self.meta_widget = BlockMeta(block)
        self.thinking_widget = ThinkingWidget(block)
        self.exec_widget = ExecutionWidget(block)
        self.footer_widget = BlockFooter(block)

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.meta_widget
        yield self.thinking_widget
        yield self.exec_widget
        if self.footer_widget._has_content():
            yield self.footer_widget

    def update_output(self, new_content: str = ""):
        """Update the AI response display."""
        if self.thinking_widget:
            self.thinking_widget.thinking_text = self.block.content_output
        if self.exec_widget:
            self.exec_widget.exec_output = getattr(self.block, 'content_exec_output', '')

    def update_metadata(self):
        """Refresh the header and metadata widgets."""
        try:
            self.header.remove()
            self.header = BlockHeader(self.block)
            self.mount(self.header, before=self.children[0])

            if self.meta_widget:
                self.meta_widget.remove()
                self.meta_widget = BlockMeta(self.block)
                if len(self.children) > 1:
                    self.mount(self.meta_widget, after=self.header)
                else:
                    self.mount(self.meta_widget)
        except Exception:
            pass

    def set_loading(self, loading: bool):
        """Set the loading state and update widgets."""
        self.block.is_running = loading

        try:
            self.footer_widget.remove()
        except Exception:
            pass

        self.footer_widget = BlockFooter(self.block)
        if self.footer_widget._has_content():
            self.mount(self.footer_widget)

        if self.thinking_widget:
            if not loading:
                self.thinking_widget.stop_loading()
                self.thinking_widget.force_render()

    @on(Click, "#retry-btn")
    def on_retry_clicked(self, event: Click):
        """Handle retry label click."""
        event.stop()
        self.post_message(self.RetryRequested(self.block.id))

    @on(Click, "#edit-btn")
    def on_edit_clicked(self, event: Click):
        """Handle edit label click."""
        event.stop()
        self.post_message(self.EditRequested(self.block.id, self.block.content_input))
