"""Widgets package for Null terminal."""

from .app_header import AppHeader
from .block_search import BlockSearch

# Import block widgets from the blocks subpackage
from .blocks import (
    AIResponseBlock,
    AgentResponseBlock,
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
from .sidebar import Sidebar
from .status_bar import StatusBar
from .suggester import CommandItem, CommandSuggester

__all__ = [
    "AIResponseBlock",
    "AgentResponseBlock",
    "AppHeader",
    "BaseBlockWidget",
    "BlockBody",
    "BlockFooter",
    "BlockHeader",
    "BlockMeta",
    "BlockSearch",
    "BlockWidget",
    "CodeBlockWidget",
    "CommandBlock",
    "CommandItem",
    "CommandPalette",
    "CommandSuggester",
    "ExecutionWidget",
    "HistorySearch",
    "HistoryViewport",
    "InputController",
    "PaletteAction",
    "Sidebar",
    "StatusBar",
    "SystemBlock",
    "ThinkingWidget",
    "create_block",
    "execute_code",
    "get_file_extension",
]
