from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static

from managers.git import GitCommit, GitDiff


class CommitRevertRequested(Message):
    def __init__(self, commit_sha: str):
        self.commit_sha = commit_sha
        super().__init__()


class CommitBlockWidget(Static):
    """Widget displaying a git commit with actions."""

    DEFAULT_CSS = """
    CommitBlockWidget {
        border: solid $success;
        padding: 1;
        margin: 1 0;
    }

    .commit-header {
        text-style: bold;
    }

    .commit-file {
        padding-left: 2;
        color: $text-muted;
    }

    .commit-file.added {
        color: $success;
    }

    .commit-file.modified {
        color: $warning;
    }

    .commit-file.deleted {
        color: $error;
    }
    """

    def __init__(self, commit: GitCommit, diffs: list[GitDiff] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.commit = commit
        self.diffs = diffs or []

    def compose(self) -> ComposeResult:
        ai_badge = " [AI]" if self.commit.is_ai_generated else ""
        yield Static(
            f"🔄 {self.commit.sha[:7]}: {self.commit.message}{ai_badge}",
            classes="commit-header",
        )

        if self.diffs:
            yield Static(f"Files changed: {len(self.diffs)}")
            for diff in self.diffs:
                prefix = "A" if diff.is_new else "M" if not diff.is_deleted else "D"
                yield Static(
                    f"  {prefix} {diff.file} (+{diff.additions}, -{diff.deletions})",
                    classes="commit-file",
                )

        with Horizontal(classes="commit-actions"):
            yield Button("View Diff", id="view-diff")
            yield Button("Revert", id="revert", variant="error")
