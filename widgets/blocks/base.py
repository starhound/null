import re
from typing import ClassVar

from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widgets import Static

from models import BlockState

from .copy_types import CopyType


class BaseBlockWidget(Static):
    """Base class for all block widgets."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("c", "show_copy_menu", "Copy Menu", show=False),
        Binding(
            "C", "copy_content", "Quick Copy", show=False
        ),  # Shift+C for quick copy
        Binding("y", "copy_content", "Copy", show=False),  # vim-style yank
        Binding("r", "retry_block", "Retry", show=False),
        Binding("e", "edit_block", "Edit", show=False),
        Binding("f", "fork_block", "Fork", show=False),
    ]

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

    class CopyRequested(Message):
        def __init__(self, block_id: str, content: str, copy_type: str = CopyType.FULL):
            self.block_id = block_id
            self.content = content
            self.copy_type = copy_type
            super().__init__()

    class CopyMenuRequested(Message):
        def __init__(self, block_id: str):
            self.block_id = block_id
            super().__init__()

    class ForkRequested(Message):
        """Sent when user clicks fork button to create a conversation branch."""

        def __init__(self, block_id: str):
            self.block_id = block_id
            super().__init__()

    class ViewRequested(Message):
        def __init__(self, block_id: str, view_type: str):
            self.block_id = block_id
            self.view_type = view_type
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

    def get_code_blocks(self) -> str:
        """Extract code blocks from content."""
        content = self.block.content_output or ""
        if not content:
            return ""

        code_blocks = []
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            code_blocks.extend(matches)
        else:
            inline_pattern = r"`([^`]+)`"
            inline_matches = re.findall(inline_pattern, content)
            code_blocks.extend(inline_matches)

        return "\n\n".join(block.strip() for block in code_blocks)

    def to_markdown(self) -> str:
        """Format content with markdown headers."""
        content = self.block.content_output or ""
        if not content:
            return ""

        model = self.block.metadata.get("model", "AI")
        timestamp = self.block.metadata.get("timestamp", "")

        header = f"## Response from {model}"
        if timestamp:
            header += f"\n*{timestamp}*"

        return f"{header}\n\n{content}"

    def get_raw_content(self) -> str:
        """Get plain text content without formatting."""
        content = self.block.content_output or ""
        if not content:
            return ""

        text = re.sub(r"```\w*\n?", "", content)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*+]\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        return text.strip()

    def get_content_for_copy(self, copy_type: str) -> str:
        """Get content formatted for the specified copy type."""
        if copy_type == CopyType.CODE:
            return self.get_code_blocks()
        elif copy_type == CopyType.MARKDOWN:
            return self.to_markdown()
        elif copy_type == CopyType.RAW:
            return self.get_raw_content()
        else:
            return self.block.content_output or ""

    def action_copy_content(self) -> None:
        content = self.block.content_output or ""
        if content:
            self.post_message(self.CopyRequested(self.block.id, content))

    def action_show_copy_menu(self) -> None:
        self.post_message(self.CopyMenuRequested(self.block.id))

    def action_retry_block(self) -> None:
        self.post_message(self.RetryRequested(self.block.id))

    def action_edit_block(self) -> None:
        content = self.block.content_input or ""
        self.post_message(self.EditRequested(self.block.id, content))

    def action_fork_block(self) -> None:
        self.post_message(self.ForkRequested(self.block.id))
