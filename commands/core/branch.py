from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class BranchCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_branch(self, args: list[str]):
        """Manage branches. Usage: /branch [list|switch|new]"""

        bm = getattr(self.app, "branch_manager", None)
        if not bm:
            self.notify("Branch manager not initialized", severity="error")
            return

        if not args:
            await self._branch_list(bm)
            return

        subcommand = args[0].lower()
        if subcommand == "list":
            await self._branch_list(bm)
        elif subcommand == "switch" and len(args) > 1:
            await self._branch_switch(bm, args[1])
        elif subcommand == "new" and len(args) > 1:
            await self._branch_new(bm, args[1])
        else:
            self.notify("Usage: /branch [list|switch|new]", severity="warning")

    async def _branch_list(self, bm):
        branches = bm.list_branches()
        output = "Branches:\n" + "\n".join([f"- {b.name}" for b in branches])
        await self.show_output("/branch list", output)

    async def _branch_switch(self, bm, name: str):
        if bm.switch_branch(name):
            self.notify(f"Switched to branch: {name}")
        else:
            self.notify(f"Branch not found: {name}", severity="error")

    async def _branch_new(self, bm, name: str):
        bm.create_branch(name)
        self.notify(f"Created branch: {name}")
