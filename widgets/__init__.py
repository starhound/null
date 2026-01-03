"""Widgets package for Null terminal."""

from .block_search import BlockSearch

# Import block widgets from the blocks subpackage
from .blocks import (
    AIResponseBlock,
    BaseBlockWidget,
    BlockBody,
    BlockFooter,
    BlockHeader,
    BlockMeta,
    BlockWidget,
    CodeBlockWidget,
    CommandBlock,
    ExecutionWidget,
    SystemBlock,
    ThinkingWidget,
    create_block,
    execute_code,
    get_file_extension,
)
from .history import HistoryViewport
from .history_search import HistorySearch
from .input import InputController
from .palette import CommandPalette, PaletteAction
from .status_bar import StatusBar
from .suggester import CommandItem, CommandSuggester

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
