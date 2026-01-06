"""Manager for conversation branches (forking)."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import BlockState


class BranchManager:
    """Manages different branches of a conversation."""

    def __init__(self):
        self.branches: dict[str, list[BlockState]] = {}
        self.current_branch: str = "main"

    def fork(self, name: str, blocks: list[BlockState], fork_point_id: str) -> str:
        """Create a new branch from a fork point."""
        # Find the fork point index
        index = -1
        for i, block in enumerate(blocks):
            if block.id == fork_point_id:
                index = i
                break

        if index == -1:
            raise ValueError(f"Fork point {fork_point_id} not found")

        # New branch gets blocks up to and including fork point
        self.branches[name] = blocks[: index + 1]
        self.current_branch = name
        return name

    def switch(self, name: str) -> list[BlockState]:
        """Switch to a different branch."""
        if name not in self.branches:
            raise ValueError(f"Branch {name} not found")
        self.current_branch = name
        return self.branches[name]

    def list_branches(self) -> list[str]:
        """List all available branches."""
        return list(self.branches.keys())
