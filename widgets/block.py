from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.message import Message
from textual.events import Click
from textual import on

from models import BlockState, BlockType
from .block_parts import BlockHeader, BlockBody, BlockFooter, BlockMeta
from .thinking import ThinkingWidget
from .execution import ExecutionWidget


class BlockWidget(Static):
    """A widget representing a single interaction block."""

    class RetryRequested(Message):
        """Sent when user clicks retry button."""
        def __init__(self, block_id: str):
            self.block_id = block_id
            super().__init__()

    class EditRequested(Message):
        """Sent when user clicks edit button."""
        def __init__(self, block_id: str, content: str):
            self.block_id = block_id
            self.content = content
            super().__init__()

    DEFAULT_CSS = """
    BlockWidget {
        layout: vertical;
        height: auto;
        min-height: 0;
        background: $surface-darken-1;
        margin-bottom: 1;
        padding: 0;
        border-left: thick $surface-lighten-2;
    }

    /* CLI Command blocks - green accent */
    BlockWidget.block-command {
        border-left: thick $success;
        background: $surface-darken-2;
    }

    /* AI Query blocks - amber/yellow accent */
    BlockWidget.block-ai-query {
        border-left: thick $warning;
        background: $surface-darken-1;
    }

    /* AI Response blocks - blue/purple accent */
    BlockWidget.block-ai-response {
        border-left: thick $primary;
        background: $surface;
        margin-bottom: 1;
    }

    /* System message blocks - cyan accent */
    BlockWidget.block-system {
        border-left: thick $secondary;
        background: $surface-darken-1;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

        # Add type-specific CSS class
        if block.type == BlockType.COMMAND:
            self.add_class("block-command")
        elif block.type == BlockType.AI_QUERY:
            self.add_class("block-ai-query")
        elif block.type == BlockType.AI_RESPONSE:
            self.add_class("block-ai-response")
        elif block.type == BlockType.SYSTEM_MSG:
            self.add_class("block-system")

        self.header = BlockHeader(block)
        self.meta_widget = None

        # Sub-widgets
        self.body_widget = None
        self.thinking_widget = None
        self.exec_widget = None
        self.footer_widget = BlockFooter(block)

        if block.type == BlockType.AI_RESPONSE:
            self.meta_widget = BlockMeta(block)
            self.thinking_widget = ThinkingWidget(block)
            self.exec_widget = ExecutionWidget(block)
        else:
            # Determine body content based on block type
            if block.type == BlockType.AI_QUERY:
                text = block.content_input
            elif block.type in (BlockType.COMMAND, BlockType.SYSTEM_MSG):
                text = block.content_output
            else:
                text = block.content_output or block.content_input
            self.body_widget = BlockBody(text or "")

    def compose(self) -> ComposeResult:
        yield self.header

        if self.meta_widget:
            yield self.meta_widget

        if self.thinking_widget:
            yield self.thinking_widget

        if self.exec_widget:
            yield self.exec_widget

        if self.body_widget:
            yield self.body_widget

        yield self.footer_widget

    def update_output(self, new_content: str = ""):
        """Update the block's output display. Uses block state for content."""
        if self.block.type == BlockType.AI_RESPONSE:
            if self.thinking_widget:
                self.thinking_widget.thinking_text = self.block.content_output
            if self.exec_widget:
                self.exec_widget.exec_output = getattr(self.block, 'content_exec_output', '')
        else:
            if self.body_widget:
                self.body_widget.content_text = self.block.content_output

    def update_metadata(self):
        """Refresh the header and metadata widgets."""
        try:
            # Update header
            self.header.remove()
            self.header = BlockHeader(self.block)
            self.mount(self.header, before=self.children[0])

            # Update metadata widget if present
            if self.meta_widget:
                self.meta_widget.remove()
                self.meta_widget = BlockMeta(self.block)
                # Mount after header
                if len(self.children) > 1:
                    self.mount(self.meta_widget, after=self.header)
                else:
                    self.mount(self.meta_widget)
        except Exception:
            pass

    def set_loading(self, loading: bool):
        self.block.is_running = loading
        self.footer_widget.remove()
        self.footer_widget = BlockFooter(self.block)
        self.mount(self.footer_widget)

        # Update thinking widget loading state
        if self.thinking_widget:
            if not loading:
                self.thinking_widget.stop_loading()
                self.thinking_widget.force_render()

    def set_exit_code(self, code: int):
        self.block.exit_code = code
        self.set_loading(False)

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
