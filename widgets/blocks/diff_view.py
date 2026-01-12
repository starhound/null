from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static


class DiffViewWidget(Static):
    """Widget displaying a git diff with syntax highlighting."""

    DEFAULT_CSS = """
    DiffViewWidget {
        border: solid $primary;
        padding: 1;
    }

    .diff-header {
        background: $primary-darken-3;
        padding: 0 1;
    }

    .diff-add {
        color: $success;
        background: $success-darken-3;
    }

    .diff-del {
        color: $error;
        background: $error-darken-3;
    }

    .diff-context {
        color: $text-muted;
    }

    .diff-hunk {
        color: $primary;
        text-style: bold;
    }
    """

    def __init__(self, file: str, diff_content: str, **kwargs):
        super().__init__(**kwargs)
        self.file = file
        self.diff_content = diff_content

    def compose(self) -> ComposeResult:
        yield Static(f"📄 {self.file}", classes="diff-header")

        with ScrollableContainer():
            for line in self.diff_content.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    yield Static(line, classes="diff-add")
                elif line.startswith("-") and not line.startswith("---"):
                    yield Static(line, classes="diff-del")
                elif line.startswith("@@"):
                    yield Static(line, classes="diff-hunk")
                else:
                    yield Static(line, classes="diff-context")
