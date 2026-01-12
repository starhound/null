"""Widgets package for Null terminal."""

from .app_header import AppHeader
from .background_sidebar import (
    BackgroundTaskCancelRequested,
    BackgroundTaskSelected,
    BackgroundTasksSidebar,
    NewBackgroundTaskRequested,
    TaskItemWidget,
)
from .block_search import BlockSearch
from .blocks import (
    AgentResponseBlock,
    AIResponseBlock,
    BaseBlockWidget,
    BlockBody,
    BlockFooter,
    BlockHeader,
    BlockMeta,
    BlockWidget,
    CodeBlockWidget,
    CommandBlock,
    CommitBlockWidget,
    CorrectionLoopBlock,
    DiffViewWidget,
    ExecutionWidget,
    SystemBlock,
    ThinkingWidget,
    create_block,
    execute_code,
    get_file_extension,
)
from .branch_navigator import BranchForkRequested, BranchNavigator, BranchSelected
from .history import HistoryViewport
from .history_search import HistorySearch
from .input import InputController
from .nl2shell_preview import NL2ShellPreview
from .palette import CommandPalette, PaletteAction
from .sidebar import Sidebar
from .status_bar import StatusBar
from .suggester import CommandItem, CommandSuggester

__all__ = [
    "AIResponseBlock",
    "AgentResponseBlock",
    "AppHeader",
    "BackgroundTaskCancelRequested",
    "BackgroundTaskSelected",
    "BackgroundTasksSidebar",
    "BaseBlockWidget",
    "BlockBody",
    "BlockFooter",
    "BlockHeader",
    "BlockMeta",
    "BlockSearch",
    "BlockWidget",
    "BranchForkRequested",
    "BranchNavigator",
    "BranchSelected",
    "CodeBlockWidget",
    "CommandBlock",
    "CommandItem",
    "CommandPalette",
    "CommandSuggester",
    "CommitBlockWidget",
    "CorrectionLoopBlock",
    "DiffViewWidget",
    "ExecutionWidget",
    "HistorySearch",
    "HistoryViewport",
    "InputController",
    "NL2ShellPreview",
    "NewBackgroundTaskRequested",
    "PaletteAction",
    "Sidebar",
    "StatusBar",
    "SystemBlock",
    "TaskItemWidget",
    "ThinkingWidget",
    "create_block",
    "execute_code",
    "get_file_extension",
]
