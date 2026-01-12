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
        branch = await gm.get_branch()
        staged = await gm.get_staged_files()
        unstaged = await gm.get_unstaged_files()
        untracked = await gm.get_untracked_files()

        lines = [f"Branch: {branch or 'unknown'}"]
        if staged:
            lines.append(f"\nStaged ({len(staged)}):")
            for f in staged[:10]:
                lines.append(f"  + {f}")
            if len(staged) > 10:
                lines.append(f"  ... and {len(staged) - 10} more")
        if unstaged:
            lines.append(f"\nModified ({len(unstaged)}):")
            for f in unstaged[:10]:
                lines.append(f"  ~ {f}")
            if len(unstaged) > 10:
                lines.append(f"  ... and {len(unstaged) - 10} more")
        if untracked:
            lines.append(f"\nUntracked ({len(untracked)}):")
            for f in untracked[:10]:
                lines.append(f"  ? {f}")
            if len(untracked) > 10:
                lines.append(f"  ... and {len(untracked) - 10} more")
        if not staged and not unstaged and not untracked:
            lines.append("\nWorking tree clean")

        await self.show_output("/git status", "\n".join(lines))

    async def _git_diff(self, args: list[str]):
        from managers.git import GitManager
        from widgets.blocks.diff_view import DiffViewWidget
        from widgets.history import HistoryViewport

        file_path = args[0] if args else None
        gm = GitManager()
        diff = await gm.get_diff(file=file_path)

        if not diff:
            self.notify("No changes found")
            return

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
            diff = await gm.get_diff(staged=True)
            if not diff:
                diff = await gm.get_diff()
                if not diff:
                    self.notify("Nothing to commit", severity="warning")
                    return
                await gm.stage_all()

            msg = await gm.generate_commit_message(self.app.ai_provider)

        result = await gm.commit(msg)
        if result.success:
            self.notify(f"Committed: {msg}")
            self.app._update_status_bar()
        else:
            self.notify(f"Commit failed: {result.error}", severity="error")

    async def _git_undo(self):
        from managers.git import GitManager

        gm = GitManager()
        success = await gm.undo_last_commit()
        if success:
            self.notify("Undid last commit (changes preserved)")
            self.app._update_status_bar()
        else:
            self.notify("Undo failed", severity="error")

    async def _git_log(self, args: list[str]):
        limit = int(args[0]) if args and args[0].isdigit() else 5
        from managers.git import GitManager

        gm = GitManager()
        commits = await gm.get_recent_commits(limit)

        if not commits:
            self.notify("No commits found")
            return

        lines = []
        for c in commits:
            date_str = c.date.strftime("%Y-%m-%d %H:%M")
            lines.append(f"{c.sha[:7]} {date_str} {c.message}")

        await self.show_output(f"/git log {limit}", "\n".join(lines))

    async def _git_stash(self, msg: str):
        from managers.git import GitManager

        gm = GitManager()
        success = await gm.stash(msg if msg else None)
        if success:
            self.notify("Stashed changes")
            self.app._update_status_bar()
        else:
            self.notify("Stash failed", severity="error")

    async def _git_stash_pop(self):
        from managers.git import GitManager

        gm = GitManager()
        success = await gm.stash_pop()
        if success:
            self.notify("Applied stash")
            self.app._update_status_bar()
        else:
            self.notify("Stash pop failed", severity="error")
