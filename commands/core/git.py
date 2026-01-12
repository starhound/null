from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class GitCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_git(self, args: list[str]):
        """Git operations. Usage: /git [status|diff|commit|undo|log|stash]"""
        if not args:
            await self._git_status()
            return

        subcommand = args[0].lower()

        if subcommand == "status":
            await self._git_status()
        elif subcommand == "diff":
            await self._git_diff(args[1:])
        elif subcommand == "commit":
            await self._git_commit(" ".join(args[1:]))
        elif subcommand == "undo":
            await self._git_undo()
        elif subcommand == "log":
            await self._git_log(args[1:])
        elif subcommand == "stash":
            if len(args) > 1 and args[1] == "pop":
                await self._git_stash_pop()
            else:
                await self._git_stash(" ".join(args[1:]))
        else:
            self.notify(f"Unknown git command: {subcommand}", severity="warning")

    async def cmd_diff(self, args: list[str]):
        """Alias for /git diff"""
        await self._git_diff(args)

    async def cmd_undo(self, args: list[str]):
        """Alias for /git undo"""
        await self._git_undo()

    async def _git_status(self):
        from managers.git import GitManager

        gm = GitManager()
        status = await gm.get_status()
        await self.show_output("/git status", status)

    async def _git_diff(self, args: list[str]):
        from managers.git import GitManager
        from widgets.blocks.diff_view import DiffViewWidget
        from widgets.history import HistoryViewport

        file_path = args[0] if args else None
        gm = GitManager()
        diff = await gm.get_diff(file_path)

        if not diff:
            self.notify("No changes found")
            return

        # Use DiffViewWidget for syntax highlighting
        history_vp = self.app.query_one("#history", HistoryViewport)
        widget = DiffViewWidget(diff, f"Diff: {file_path or 'All'}")
        await history_vp.mount(widget)
        widget.scroll_visible()

    async def _git_commit(self, msg: str):
        from managers.git import GitManager

        gm = GitManager()

        if not msg:
            if not self.app.ai_provider:
                self.notify(
                    "AI provider required for auto-commit message", severity="error"
                )
                return

            self.notify("Generating commit message...")
            diff = await gm.get_diff(cached=True)  # Staged changes
            if not diff:
                # Try unstaged if nothing staged
                diff = await gm.get_diff()
                if not diff:
                    self.notify("Nothing to commit", severity="warning")
                    return

                # Auto-stage all for convenience if user didn't stage
                await gm.stage_all()

            msg = await gm.generate_commit_message(diff, self.app.ai_provider)

        success, output = await gm.commit(msg)
        if success:
            self.notify(f"Committed: {msg}")
            self.app._update_status_bar()  # Update git status
        else:
            self.notify(f"Commit failed: {output}", severity="error")

    async def _git_undo(self):
        from managers.git import GitManager

        gm = GitManager()
        success, output = await gm.undo_last_commit()
        if success:
            self.notify("Undid last commit (changes preserved)")
            self.app._update_status_bar()
        else:
            self.notify(f"Undo failed: {output}", severity="error")

    async def _git_log(self, args: list[str]):
        limit = int(args[0]) if args and args[0].isdigit() else 5
        from managers.git import GitManager

        gm = GitManager()
        log = await gm.get_log(limit)
        await self.show_output(f"/git log {limit}", log)

    async def _git_stash(self, msg: str):
        from managers.git import GitManager

        gm = GitManager()
        success, output = await gm.stash(msg)
        if success:
            self.notify("Stashed changes")
            self.app._update_status_bar()
        else:
            self.notify(f"Stash failed: {output}", severity="error")

    async def _git_stash_pop(self):
        from managers.git import GitManager

        gm = GitManager()
        success, output = await gm.stash_pop()
        if success:
            self.notify("Applied stash")
            self.app._update_status_bar()
        else:
            self.notify(f"Stash pop failed: {output}", severity="error")
