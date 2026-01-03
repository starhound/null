"""Block widgets for different content types."""

from models import BlockState, BlockType

from .actions import ActionBar, ActionButton
from .agent_response import AgentResponseBlock
from .ai_response import AIResponseBlock
from .base import BaseBlockWidget
from .code_block import (
    CodeBlockWidget,
    execute_code,
    extract_code_blocks,
    get_file_extension,
)
from .command import CommandBlock
from .execution import ExecutionWidget
from .frame import BlockFrame, FrameSeparator
from .iteration import (
    IterationHeader,
    IterationSeparator,
    IterationWidget,
    ThinkingSection,
    ToolCallItem,
)
from .iteration_container import IterationContainer
from .parts import BlockBody, BlockFooter, BlockHeader, BlockMeta, StopButton
from .system import SystemBlock
from .terminal import TerminalBlock
from .thinking import ThinkingWidget
from .tool_accordion import ToolAccordion, ToolAccordionItem
from .tool_call import ToolCallBlock


def create_block(block: BlockState) -> BaseBlockWidget:
    """Factory function to create the appropriate block widget for a BlockState."""
    if block.type == BlockType.COMMAND:
        return CommandBlock(block)
    elif block.type == BlockType.AI_RESPONSE:
        return AIResponseBlock(block)
    elif block.type == BlockType.AGENT_RESPONSE:
        return AgentResponseBlock(block)
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
    "AIResponseBlock",
    "ActionBar",
    "ActionButton",
    "AgentResponseBlock",
    "BaseBlockWidget",
    "BlockBody",
    "BlockFooter",
    "BlockFrame",
    "BlockHeader",
    "BlockMeta",
    "BlockWidget",
    "CodeBlockWidget",
    "CommandBlock",
    "ExecutionWidget",
    "FrameSeparator",
    "IterationContainer",
    "IterationHeader",
    "IterationSeparator",
    "IterationWidget",
    "SystemBlock",
    "TerminalBlock",
    "ThinkingSection",
    "ThinkingWidget",
    "ToolAccordion",
    "ToolAccordionItem",
    "ToolCallBlock",
    "ToolCallItem",
    "create_block",
    "execute_code",
    "extract_code_blocks",
    "get_file_extension",
]
