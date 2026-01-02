"""Widgets package for Null terminal."""

from .input import InputController
from .suggester import CommandItem, CommandSuggester
from .history import HistoryViewport
from .status_bar import StatusBar
from .history_search import HistorySearch

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
    create_block,
)

__all__ = [
    "InputController",
    "CommandItem",
    "CommandSuggester",
    "HistoryViewport",
    "StatusBar",
    "HistorySearch",
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
    "create_block",
]
