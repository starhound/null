from textual.app import ComposeResult
from textual.widgets import Static
from textual.message import Message
from textual.events import Click
from textual import on

from models import BlockState, BlockType


class BaseBlockWidget(Static):
    """Base class for all block widgets."""

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

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def update_output(self, new_content: str = ""):
        """Update the block's output display. Override in subclasses."""
        pass

    def update_metadata(self):
        """Refresh the header and metadata widgets. Override in subclasses."""
        pass

    def set_loading(self, loading: bool):
        """Set the loading state. Override in subclasses."""
        self.block.is_running = loading

    def set_exit_code(self, code: int):
        """Set exit code and stop loading."""
        self.block.exit_code = code
        self.set_loading(False)
