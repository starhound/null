"""Git operations manager for AI-native git workflows."""

import asyncio
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.base import LLMProvider


@dataclass
class GitDiff:
    """Represents a git diff."""

    file: str
    additions: int
    deletions: int
    content: str
    is_new: bool = False
    is_deleted: bool = False
    is_renamed: bool = False
    old_path: str | None = None


@dataclass
class GitCommit:
    """Represents a git commit."""

    sha: str
    message: str
    author: str
    date: datetime
    files: list[str] = field(default_factory=list)
    is_ai_generated: bool = False


@dataclass
class CommitResult:
    """Result of a commit operation."""

    success: bool
    sha: str | None = None
    message: str | None = None
    error: str | None = None
    files_committed: list[str] = field(default_factory=list)


class GitManager:
    """Manages git operations with AI integration."""

    def __init__(self, working_dir: Path | None = None):
        self.working_dir = working_dir or Path.cwd()
        self._has_git = shutil.which("git") is not None

    async def _run_git(self, *args: str, check: bool = True) -> tuple[str, str, int]:
        """Run a git command and return stdout, stderr, return code."""
        if not self._has_git:
            return "", "git not found", 1

        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(self.working_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
            proc.returncode or 0,
        )

    async def is_repo(self) -> bool:
        """Check if current directory is a git repo."""
        _, _, rc = await self._run_git("rev-parse", "--is-inside-work-tree")
        return rc == 0

    async def get_branch(self) -> str:
        """Get current branch name."""
        stdout, _, rc = await self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return stdout.strip() if rc == 0 else ""

    async def is_dirty(self) -> bool:
        """Check if there are uncommitted changes."""
        stdout, _, _ = await self._run_git("status", "--porcelain")
        return bool(stdout.strip())

    async def get_staged_files(self) -> list[str]:
        """Get list of staged files."""
        stdout, _, rc = await self._run_git("diff", "--cached", "--name-only")
        if rc != 0:
            return []
        return [f.strip() for f in stdout.strip().split("\n") if f.strip()]

    async def get_unstaged_files(self) -> list[str]:
        """Get list of modified but unstaged files."""
        stdout, _, rc = await self._run_git("diff", "--name-only")
        if rc != 0:
            return []
        return [f.strip() for f in stdout.strip().split("\n") if f.strip()]

    async def get_untracked_files(self) -> list[str]:
        """Get list of untracked files."""
        stdout, _, rc = await self._run_git(
            "ls-files", "--others", "--exclude-standard"
        )
        if rc != 0:
            return []
        return [f.strip() for f in stdout.strip().split("\n") if f.strip()]

    async def get_diff(self, staged: bool = False, file: str | None = None) -> str:
        """Get diff content."""
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file:
            args.extend(["--", file])

        stdout, _, _ = await self._run_git(*args)
        return stdout

    async def get_diff_stat(self, staged: bool = False) -> list[GitDiff]:
        """Get diff statistics for changed files."""
        args = ["diff", "--stat", "--numstat"]
        if staged:
            args.append("--cached")

        stdout, _, rc = await self._run_git(*args)
        if rc != 0:
            return []

        diffs: list[GitDiff] = []
        numstat_section = True

        for line in stdout.strip().split("\n"):
            if not line.strip():
                numstat_section = False
                continue

            if numstat_section:
                parts = line.split("\t")
                if len(parts) >= 3:
                    adds = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    filepath = parts[2]

                    diff_content = await self.get_diff(staged=staged, file=filepath)

                    diffs.append(
                        GitDiff(
                            file=filepath,
                            additions=adds,
                            deletions=dels,
                            content=diff_content,
                        )
                    )

        return diffs

    async def stage_file(self, file: str) -> bool:
        """Stage a file for commit."""
        _, _, rc = await self._run_git("add", file)
        return rc == 0

    async def stage_all(self) -> bool:
        """Stage all changes."""
        _, _, rc = await self._run_git("add", "-A")
        return rc == 0

    async def unstage_file(self, file: str) -> bool:
        """Unstage a file."""
        _, _, rc = await self._run_git("reset", "HEAD", file)
        return rc == 0

    async def commit(
        self, message: str, files: list[str] | None = None
    ) -> CommitResult:
        """Create a commit with the given message."""
        if files:
            for f in files:
                await self.stage_file(f)

        staged = await self.get_staged_files()
        if not staged:
            return CommitResult(success=False, error="Nothing to commit")

        stdout, stderr, rc = await self._run_git("commit", "-m", message)

        if rc != 0:
            return CommitResult(success=False, error=stderr or stdout)

        sha_match = re.search(r"\[.+\s+([a-f0-9]+)\]", stdout)
        sha = sha_match.group(1) if sha_match else None

        return CommitResult(
            success=True,
            sha=sha,
            message=message,
            files_committed=staged,
        )

    async def undo_last_commit(self, keep_changes: bool = True) -> bool:
        """Undo the last commit."""
        mode = "--soft" if keep_changes else "--hard"
        _, _, rc = await self._run_git("reset", mode, "HEAD~1")
        return rc == 0

    async def discard_file(self, file: str) -> bool:
        """Discard changes to a file."""
        _, _, rc = await self._run_git("checkout", "--", file)
        return rc == 0

    async def stash(self, message: str | None = None) -> bool:
        """Stash current changes."""
        args = ["stash", "push"]
        if message:
            args.extend(["-m", message])
        _, _, rc = await self._run_git(*args)
        return rc == 0

    async def stash_pop(self) -> bool:
        """Pop the latest stash."""
        _, _, rc = await self._run_git("stash", "pop")
        return rc == 0

    async def get_recent_commits(self, limit: int = 10) -> list[GitCommit]:
        """Get recent commits."""
        format_str = "%H|%s|%an|%aI"
        stdout, _, rc = await self._run_git(
            "log", f"-{limit}", f"--format={format_str}"
        )
        if rc != 0:
            return []

        commits: list[GitCommit] = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) >= 4:
                commits.append(
                    GitCommit(
                        sha=parts[0],
                        message=parts[1],
                        author=parts[2],
                        date=datetime.fromisoformat(parts[3]),
                        is_ai_generated="[AI]" in parts[1] or "[null]" in parts[1],
                    )
                )

        return commits

    async def generate_commit_message(
        self,
        provider: "LLMProvider",
        context: str = "",
    ) -> str:
        """Generate a commit message using AI based on staged changes."""
        diff = await self.get_diff(staged=True)
        if not diff:
            diff = await self.get_diff(staged=False)

        if not diff:
            return "chore: update files"

        prompt = f"""Generate a concise git commit message for these changes.
Use conventional commit format: <type>(<scope>): <description>

Types: feat, fix, refactor, docs, test, chore, style, perf
Keep the description under 50 characters.
Do not include any explanation, just the commit message.

{f"Context: {context}" if context else ""}

Diff:
{diff[:3000]}
"""

        message = ""
        async for chunk in provider.generate(
            prompt,
            [],
            system_prompt="You are a git commit message generator. Output only the commit message, nothing else.",
        ):
            message += chunk

        message = message.strip().strip('"').strip("'")
        if not message:
            message = "chore: update files"

        return message

    async def auto_commit(
        self,
        provider: "LLMProvider",
        files: list[str] | None = None,
        context: str = "",
    ) -> CommitResult:
        """Automatically stage and commit with AI-generated message."""
        if files:
            for f in files:
                await self.stage_file(f)
        else:
            await self.stage_all()

        staged = await self.get_staged_files()
        if not staged:
            return CommitResult(success=False, error="Nothing to commit")

        message = await self.generate_commit_message(provider, context)

        return await self.commit(message)


async def get_git_manager(path: Path | None = None) -> GitManager:
    """Get a GitManager for the given path."""
    return GitManager(path or Path.cwd())
