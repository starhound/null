from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, LoadingIndicator, Static

from managers.nl2shell import CommandSuggestion


class NL2ShellPreview(Static):
    """
    Inline preview for Natural Language to Shell translation.
    Appears below the input box when a natural language pattern is detected.
    """

    DEFAULT_CSS = """
    NL2ShellPreview {
        layout: vertical;
        background: $surface;
        border-top: solid $primary 50%;
        height: auto;
        display: none;
        padding: 0 1;
        margin-bottom: 1;
    }

    NL2ShellPreview.--visible {
        display: block;
    }

    NL2ShellPreview .preview-container {
        layout: horizontal;
        height: auto;
        align-vertical: middle;
        padding: 1 0;
    }

    NL2ShellPreview .command-text {
        color: $accent;
        text-style: bold;
        width: 1fr;
    }

    NL2ShellPreview .confidence-badge {
        background: $success 20%;
        color: $success;
        padding: 0 1;
        text-style: bold;
    }

    NL2ShellPreview .confidence-badge.low {
        background: $warning 20%;
        color: $warning;
    }

    NL2ShellPreview .explanation {
        color: $text-muted;
        text-style: italic;
        padding-bottom: 1;
    }

    NL2ShellPreview .controls {
        color: $text-disabled;
        text-style: dim;
    }

    NL2ShellPreview .loading-container {
        height: 3;
        align: center middle;
    }

    NL2ShellPreview LoadingIndicator {
        color: $primary;
        height: 1;
    }
    """

    suggestion: reactive[CommandSuggestion | None] = reactive(None)
    is_loading: reactive[bool] = reactive(False)
    current_alternative_index: reactive[int] = reactive(-1)

    class Accepted(Message):
        """Sent when the user accepts the translation."""

        def __init__(self, command: str):
            self.command = command
            super().__init__()

    class Rejected(Message):
        """Sent when the user rejects the translation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._alternatives: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="content-area"):
            with Horizontal(classes="preview-container"):
                yield Label("", classes="command-text", id="command-preview")
                yield Label("", classes="confidence-badge", id="confidence")

            yield Label("", classes="explanation", id="explanation")

            with Horizontal(classes="controls"):
                yield Label("↹ Cycle Alternatives • ↵ Accept • Esc Reject")

        with Vertical(classes="loading-container", id="loading-area"):
            yield Label("Translating...", classes="loading-text")
            yield LoadingIndicator()

    def watch_is_loading(self, loading: bool) -> None:
        self.set_class(loading or self.suggestion is not None, "--visible")

        content = self.query_one("#content-area")
        loader = self.query_one("#loading-area")

        if loading:
            content.display = False
            loader.display = True
        else:
            content.display = True
            loader.display = False

    def watch_suggestion(self, suggestion: CommandSuggestion | None) -> None:
        self.set_class(self.is_loading or suggestion is not None, "--visible")

        if not suggestion:
            return

        self._alternatives = [suggestion.command, *suggestion.alternatives]
        self.current_alternative_index = 0
        self._update_display()

    def _update_display(self) -> None:
        if not self.suggestion or not self._alternatives:
            return

        command = self._alternatives[self.current_alternative_index]

        self.query_one("#command-preview", Label).update(f"> {command}")

        conf_label = self.query_one("#confidence", Label)
        conf_label.update(f"{int(self.suggestion.confidence * 100)}%")

        conf_label.set_class(self.suggestion.confidence < 0.7, "low")

        expl_label = self.query_one("#explanation", Label)
        if self.current_alternative_index == 0:
            expl_label.update(self.suggestion.explanation)
        else:
            expl_label.update("Alternative command")

        controls = self.query_one(".controls", Label)
        if len(self._alternatives) > 1:
            controls.update(
                f"↹ Cycle ({self.current_alternative_index + 1}/{len(self._alternatives)}) • ↵ Accept • Esc Reject"
            )
        else:
            controls.update("↵ Accept • Esc Reject")

    def action_cycle(self) -> None:
        """Cycle through available alternatives."""
        if not self._alternatives:
            return

        self.current_alternative_index = (self.current_alternative_index + 1) % len(
            self._alternatives
        )
        self._update_display()

    def action_accept(self) -> None:
        """Accept the current suggestion."""
        if self._alternatives:
            command = self._alternatives[self.current_alternative_index]
            self.post_message(self.Accepted(command))
            self.suggestion = None

    def action_reject(self) -> None:
        """Reject the suggestion."""
        self.suggestion = None
        self.post_message(self.Rejected())
