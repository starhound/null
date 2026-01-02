"""Block widgets for different content types."""

from models import BlockState, BlockType

from .base import BaseBlockWidget
from .command import CommandBlock
from .ai_response import AIResponseBlock
from .system import SystemBlock
from .tool_call import ToolCallBlock
from .parts import BlockHeader, BlockMeta, BlockBody, BlockFooter, StopButton
from .thinking import ThinkingWidget
from .execution import ExecutionWidget
from .code_block import CodeBlockWidget, extract_code_blocks, execute_code, get_file_extension
from .terminal import TerminalBlock


def create_block(block: BlockState) -> BaseBlockWidget:
    """Factory function to create the appropriate block widget for a BlockState."""
    if block.type == BlockType.COMMAND:
        return CommandBlock(block)
    elif block.type == BlockType.AI_RESPONSE:
        return AIResponseBlock(block)
    elif block.type == BlockType.SYSTEM_MSG:
        return SystemBlock(block)
    elif block.type == BlockType.TOOL_CALL:
        return ToolCallBlock(block)
    elif block.type == BlockType.AI_QUERY:
        # AI queries are typically combined with AI responses now
        # but if standalone, treat like system message
        return SystemBlock(block)
    else:
        # Default fallback
        return CommandBlock(block)


# For backwards compatibility, alias BlockWidget to the factory
class BlockWidget:
    """Backwards-compatible wrapper that creates the appropriate block type."""

    def __new__(cls, block: BlockState) -> BaseBlockWidget:
        return create_block(block)


__all__ = [
    'BaseBlockWidget',
    'BlockWidget',
    'CommandBlock',
    'AIResponseBlock',
    'SystemBlock',
    'ToolCallBlock',
    'TerminalBlock',
    'BlockHeader',
    'BlockMeta',
    'BlockBody',
    'BlockFooter',
    'ThinkingWidget',
    'ExecutionWidget',
    'CodeBlockWidget',
    'extract_code_blocks',
    'execute_code',
    'get_file_extension',
    'create_block',
]
