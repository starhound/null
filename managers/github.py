"""GitHub integration manager for issue and PR context."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field


@dataclass
class GitHubComment:
    """Represents a GitHub comment."""

    author: str
    body: str
    created_at: str


@dataclass
class GitHubIssue:
    """Represents a GitHub issue."""

    number: int
    title: str
    body: str
    state: str
    labels: list[str] = field(default_factory=list)
    comments: list[GitHubComment] = field(default_factory=list)
    linked_prs: list[int] = field(default_factory=list)


@dataclass
class GitHubPR:
    """Represents a GitHub pull request."""

    number: int
    title: str
    body: str
    state: str
    base_branch: str
    head_branch: str
    diff: str = ""
    files_changed: list[str] = field(default_factory=list)
    comments: list[GitHubComment] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)


class GitHubContextManager:
    """Manages GitHub issue and PR context."""

    def __init__(self):
        self._repo: str | None = None

    async def _run_gh(self, *args: str) -> tuple[str, int]:
        """Run gh CLI command and return output and return code."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "gh",
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await proc.communicate()
            return stdout.decode("utf-8", errors="replace"), proc.returncode or 0
        except FileNotFoundError:
            return "gh CLI not installed. Install from https://cli.github.com/", 1

    async def detect_repo(self) -> str | None:
        """Detect current repo from git remote."""
        if self._repo:
            return self._repo

        output, rc = await self._run_gh(
            "repo", "view", "--json", "nameWithOwner", "-q", "nameWithOwner"
        )
        if rc == 0:
            self._repo = output.strip()
            return self._repo
        return None

    async def get_issue(self, number: int) -> GitHubIssue | None:
        """Fetch issue details using gh CLI."""
        repo = await self.detect_repo()
        if not repo:
            return None

        # Fetch issue details
        output, rc = await self._run_gh(
            "issue",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "number,title,body,state,labels",
        )
        if rc != 0:
            return None

        try:
            data = json.loads(output)
            labels = [label["name"] for label in data.get("labels", [])]

            # Fetch comments
            comments_output, comments_rc = await self._run_gh(
                "issue",
                "view",
                str(number),
                "--repo",
                repo,
                "--json",
                "comments",
            )
            comments = []
            if comments_rc == 0:
                comments_data = json.loads(comments_output)
                for comment in comments_data.get("comments", []):
                    comments.append(
                        GitHubComment(
                            author=comment.get("author", {}).get("login", "unknown"),
                            body=comment.get("body", ""),
                            created_at=comment.get("createdAt", ""),
                        )
                    )

            return GitHubIssue(
                number=data["number"],
                title=data["title"],
                body=data["body"],
                state=data["state"],
                labels=labels,
                comments=comments,
            )
        except (json.JSONDecodeError, KeyError):
            return None

    async def get_pr(self, number: int) -> GitHubPR | None:
        """Fetch PR details using gh CLI."""
        repo = await self.detect_repo()
        if not repo:
            return None

        # Fetch PR details
        output, rc = await self._run_gh(
            "pr",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "number,title,body,state,baseRefName,headRefName,files",
        )
        if rc != 0:
            return None

        try:
            data = json.loads(output)
            files_changed = [f.get("path", "") for f in data.get("files", [])]

            # Fetch comments
            comments_output, comments_rc = await self._run_gh(
                "pr",
                "view",
                str(number),
                "--repo",
                repo,
                "--json",
                "comments",
            )
            comments = []
            if comments_rc == 0:
                comments_data = json.loads(comments_output)
                for comment in comments_data.get("comments", []):
                    comments.append(
                        GitHubComment(
                            author=comment.get("author", {}).get("login", "unknown"),
                            body=comment.get("body", ""),
                            created_at=comment.get("createdAt", ""),
                        )
                    )

            # Fetch checks
            checks_output, checks_rc = await self._run_gh(
                "pr",
                "view",
                str(number),
                "--repo",
                repo,
                "--json",
                "statusCheckRollup",
            )
            checks = []
            if checks_rc == 0:
                checks_data = json.loads(checks_output)
                checks = checks_data.get("statusCheckRollup", [])

            return GitHubPR(
                number=data["number"],
                title=data["title"],
                body=data["body"],
                state=data["state"],
                base_branch=data["baseRefName"],
                head_branch=data["headRefName"],
                files_changed=files_changed,
                comments=comments,
                checks=checks,
            )
        except (json.JSONDecodeError, KeyError):
            return None

    async def get_pr_diff(self, number: int) -> str:
        """Get PR diff."""
        repo = await self.detect_repo()
        if not repo:
            return ""

        output, rc = await self._run_gh(
            "pr",
            "diff",
            str(number),
            "--repo",
            repo,
        )
        return output if rc == 0 else ""

    async def list_issues(
        self, state: str = "open", limit: int = 10
    ) -> list[GitHubIssue]:
        """List issues."""
        repo = await self.detect_repo()
        if not repo:
            return []

        output, rc = await self._run_gh(
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "number,title,state,labels",
        )
        if rc != 0:
            return []

        try:
            data = json.loads(output)
            issues = []
            for item in data:
                labels = [label["name"] for label in item.get("labels", [])]
                issues.append(
                    GitHubIssue(
                        number=item["number"],
                        title=item["title"],
                        body="",
                        state=item["state"],
                        labels=labels,
                    )
                )
            return issues
        except (json.JSONDecodeError, KeyError):
            return []

    async def list_prs(self, state: str = "open", limit: int = 10) -> list[GitHubPR]:
        """List PRs."""
        repo = await self.detect_repo()
        if not repo:
            return []

        output, rc = await self._run_gh(
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "number,title,state,baseRefName,headRefName",
        )
        if rc != 0:
            return []

        try:
            data = json.loads(output)
            prs = []
            for item in data:
                prs.append(
                    GitHubPR(
                        number=item["number"],
                        title=item["title"],
                        body="",
                        state=item["state"],
                        base_branch=item["baseRefName"],
                        head_branch=item["headRefName"],
                    )
                )
            return prs
        except (json.JSONDecodeError, KeyError):
            return []

    async def create_issue(self, title: str, body: str) -> int | None:
        """Create a new issue."""
        repo = await self.detect_repo()
        if not repo:
            return None

        output, rc = await self._run_gh(
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--body",
            body,
            "--json",
            "number",
        )
        if rc != 0:
            return None

        try:
            data = json.loads(output)
            return data.get("number")
        except json.JSONDecodeError:
            return None

    async def create_pr(self, title: str, body: str, base: str = "main") -> int | None:
        """Create a PR from current branch."""
        repo = await self.detect_repo()
        if not repo:
            return None

        output, rc = await self._run_gh(
            "pr",
            "create",
            "--repo",
            repo,
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
            "--json",
            "number",
        )
        if rc != 0:
            return None

        try:
            data = json.loads(output)
            return data.get("number")
        except json.JSONDecodeError:
            return None

    async def comment_on_issue(self, number: int, body: str) -> bool:
        """Add comment to issue."""
        repo = await self.detect_repo()
        if not repo:
            return False

        _, rc = await self._run_gh(
            "issue",
            "comment",
            str(number),
            "--repo",
            repo,
            "--body",
            body,
        )
        return rc == 0

    def format_issue_context(self, issue: GitHubIssue) -> str:
        """Format issue as context string for AI."""
        lines = [
            f"# Issue #{issue.number}: {issue.title}",
            f"**State:** {issue.state}",
        ]

        if issue.labels:
            lines.append(f"**Labels:** {', '.join(issue.labels)}")

        if issue.body:
            lines.append(f"\n## Description\n{issue.body}")

        if issue.comments:
            lines.append("\n## Comments")
            for comment in issue.comments:
                lines.append(f"\n**@{comment.author}** ({comment.created_at}):")
                lines.append(comment.body)

        return "\n".join(lines)

    def format_pr_context(self, pr: GitHubPR) -> str:
        """Format PR as context string for AI."""
        lines = [
            f"# PR #{pr.number}: {pr.title}",
            f"**State:** {pr.state}",
            f"**Base:** {pr.base_branch} ← **Head:** {pr.head_branch}",
        ]

        if pr.body:
            lines.append(f"\n## Description\n{pr.body}")

        if pr.files_changed:
            lines.append(f"\n## Files Changed ({len(pr.files_changed)})")
            for file in pr.files_changed:
                lines.append(f"- {file}")

        if pr.checks:
            lines.append("\n## Checks")
            for check in pr.checks:
                status = check.get("status", "unknown")
                name = check.get("name", "unknown")
                lines.append(f"- {name}: {status}")

        if pr.comments:
            lines.append("\n## Comments")
            for comment in pr.comments:
                lines.append(f"\n**@{comment.author}** ({comment.created_at}):")
                lines.append(comment.body)

        return "\n".join(lines)
