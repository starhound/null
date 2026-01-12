from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class GitHubCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_issue(self, args: list[str]):
        """GitHub issue operations."""
        from managers.github import GitHubContextManager

        gh = GitHubContextManager()

        if not args:
            await self._issue_list(gh)
            return

        subcommand = args[0].lower()
        if subcommand == "list":
            await self._issue_list(gh)
        elif subcommand == "create":
            await self._issue_create(gh)
        elif subcommand.isdigit():
            await self._issue_view(gh, int(subcommand))
        else:
            self.notify("Usage: /issue [list|create|<number>]", severity="warning")

    async def _issue_list(self, gh):
        issues = await gh.list_issues()
        await self.show_output("/issue list", issues)

    async def _issue_view(self, gh, number: int):
        issue = await gh.get_issue(number)
        await self.show_output(f"/issue {number}", issue)

    async def _issue_create(self, gh):
        # Interactive creation
        pass

    async def cmd_pr(self, args: list[str]):
        """GitHub PR operations."""
        from managers.github import GitHubContextManager

        gh = GitHubContextManager()

        if not args:
            await self._pr_list(gh)
            return

        subcommand = args[0].lower()
        if subcommand == "list":
            await self._pr_list(gh)
        elif subcommand == "create":
            await self._pr_create(gh)
        elif subcommand == "diff" and len(args) > 1:
            await self._pr_diff(gh, args[1])
        elif subcommand.isdigit():
            await self._pr_view(gh, int(subcommand))
        else:
            self.notify("Usage: /pr [list|create|diff|<number>]", severity="warning")

    async def _pr_list(self, gh):
        prs = await gh.list_prs()
        await self.show_output("/pr list", prs)

    async def _pr_view(self, gh, number: int):
        pr = await gh.get_pr(number)
        await self.show_output(f"/pr {number}", pr)

    async def _pr_create(self, gh):
        pass

    async def _pr_diff(self, gh, number):
        diff = await gh.get_pr_diff(number)
        await self.show_output(f"/pr diff {number}", diff)
