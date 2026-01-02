"""Widgets package for Null terminal."""

from .input import InputController
from .suggester import CommandItem, CommandSuggester
from .history import HistoryViewport
from .status_bar import StatusBar
from .history_search import HistorySearch
from .block_search import BlockSearch
from .palette import CommandPalette, PaletteAction

# Import block widgets from the blocks subpackage
from .blocks import (
    BlockWidget,
    BaseBlockWidget,
    CommandBlock,
    AIResponseBlock,
    SystemBlock,
    BlockHeader,
    BlockBody,
    BlockFooter,
    BlockMeta,
    ThinkingWidget,
    ExecutionWidget,
    CodeBlockWidget,
    execute_code,
    get_file_extension,
    create_block,
)

__all__ = [
    "InputController",
    "CommandItem",
    "CommandSuggester",
    "HistoryViewport",
    "StatusBar",
    "HistorySearch",
    "BlockSearch",
    "CommandPalette",
    "PaletteAction",
    # Block widgets
    "BlockWidget",
    "BaseBlockWidget",
    "CommandBlock",
    "AIResponseBlock",
    "SystemBlock",
    "BlockHeader",
    "BlockBody",
    "BlockFooter",
    "BlockMeta",
    "ThinkingWidget",
    "ExecutionWidget",
    "CodeBlockWidget",
    "execute_code",
    "get_file_extension",
    "create_block",
]
