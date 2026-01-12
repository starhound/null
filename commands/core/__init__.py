from typing import TYPE_CHECKING

from ..base import CommandMixin
from .basic import BasicCommands
from .branch import BranchCommands
from .error import ErrorCommands
from .git import GitCommands
from .github import GitHubCommands
from .review import ReviewCommands
from .ssh import SSHCommands
from .workflow import WorkflowCommands

if TYPE_CHECKING:
    from app import NullApp


class CoreCommands(
    BasicCommands,
    GitCommands,
    SSHCommands,
    ErrorCommands,
    ReviewCommands,
    GitHubCommands,
    WorkflowCommands,
    BranchCommands,
    CommandMixin,
):
    """Core application commands."""

    def __init__(self, app: "NullApp"):
        self.app = app
        # Initialize mixins
        BasicCommands.__init__(self, app)
        GitCommands.__init__(self, app)
        SSHCommands.__init__(self, app)
        ErrorCommands.__init__(self, app)
        ReviewCommands.__init__(self, app)
        GitHubCommands.__init__(self, app)
        WorkflowCommands.__init__(self, app)
        BranchCommands.__init__(self, app)
