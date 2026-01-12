from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from managers.review import DiffHunk, HunkStatus, ProposedChange, ReviewManager


class HunkWidget(Static):
    DEFAULT_CSS = """
    HunkWidget {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid $surface-lighten-2;
    }

    HunkWidget.pending {
        border-left: heavy $warning;
    }

    HunkWidget.accepted {
        border-left: heavy $success;
    }

    HunkWidget.rejected {
        border-left: heavy $error;
    }

    .hunk-header {
        layout: horizontal;
        height: 1;
        margin-bottom: 1;
    }

    .hunk-location {
        color: $text-muted;
        width: 1fr;
    }

    .hunk-status {
        color: $warning;
    }

    .hunk-status.accepted {
        color: $success;
    }

    .hunk-status.rejected {
        color: $error;
    }

    .diff-content {
        height: auto;
    }

    .diff-line-del {
        color: $error;
        background: $error 10%;
    }

    .diff-line-add {
        color: $success;
        background: $success 10%;
    }

    .diff-line-context {
        color: $text-muted;
    }

    .hunk-actions {
        layout: horizontal;
        height: 3;
        margin-top: 1;
        align: right middle;
    }

    .hunk-actions Button {
        margin-left: 1;
        min-width: 10;
    }
    """

    class Accepted(Message):
        def __init__(self, hunk_id: str):
            self.hunk_id = hunk_id
            super().__init__()

    class Rejected(Message):
        def __init__(self, hunk_id: str):
            self.hunk_id = hunk_id
            super().__init__()

    def __init__(self, hunk: DiffHunk, **kwargs):
        super().__init__(**kwargs)
        self.hunk = hunk

    def compose(self) -> ComposeResult:
        with Horizontal(classes="hunk-header"):
            yield Label(
                f"Lines {self.hunk.start_line}-{self.hunk.end_line}",
                classes="hunk-location",
            )
            status_text = self.hunk.status.value.upper()
            yield Label(status_text, classes=f"hunk-status {self.hunk.status.value}")

        with Static(classes="diff-content"):
            for line in self.hunk.context_before:
                yield Label(f"  {line}", classes="diff-line-context")
            for line in self.hunk.original_lines:
                yield Label(f"- {line}", classes="diff-line-del")
            for line in self.hunk.proposed_lines:
                yield Label(f"+ {line}", classes="diff-line-add")
            for line in self.hunk.context_after:
                yield Label(f"  {line}", classes="diff-line-context")

        if self.hunk.status == HunkStatus.PENDING:
            with Horizontal(classes="hunk-actions"):
                yield Button("Accept", id="accept", variant="success")
                yield Button("Reject", id="reject", variant="error")

    def on_mount(self) -> None:
        self.set_class(True, self.hunk.status.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "accept":
            self.post_message(self.Accepted(self.hunk.id))
        elif event.button.id == "reject":
            self.post_message(self.Rejected(self.hunk.id))


class FileChangeWidget(Static):
    DEFAULT_CSS = """
    FileChangeWidget {
        height: auto;
        margin-bottom: 2;
        padding: 1;
        background: $surface;
        border: solid $primary 50%;
    }

    .file-header {
        layout: horizontal;
        height: 2;
        margin-bottom: 1;
    }

    .file-path {
        color: $primary;
        text-style: bold;
        width: 1fr;
    }

    .file-stats {
        color: $text-muted;
    }

    .file-stats-add {
        color: $success;
    }

    .file-stats-del {
        color: $error;
    }

    .file-rationale {
        color: $text-muted;
        text-style: italic;
        margin-bottom: 1;
    }

    .file-actions {
        layout: horizontal;
        height: 3;
        align: right middle;
        margin-top: 1;
    }

    .file-actions Button {
        margin-left: 1;
    }
    """

    def __init__(self, file: str, change: ProposedChange, **kwargs):
        super().__init__(**kwargs)
        self.file = file
        self.change = change

    def compose(self) -> ComposeResult:
        with Horizontal(classes="file-header"):
            yield Label(self.file, classes="file-path")
            yield Label(
                f"+{self.change.total_additions}",
                classes="file-stats file-stats-add",
            )
            yield Label(" / ", classes="file-stats")
            yield Label(
                f"-{self.change.total_deletions}",
                classes="file-stats file-stats-del",
            )

        if self.change.rationale:
            yield Label(self.change.rationale, classes="file-rationale")

        for hunk in self.change.hunks:
            yield HunkWidget(hunk)

        with Horizontal(classes="file-actions"):
            yield Button("Accept All", id="accept-all", variant="success")
            yield Button("Reject All", id="reject-all", variant="error")


class ReviewScreen(ModalScreen[bool]):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "apply", "Apply Changes"),
        Binding("a", "accept_all", "Accept All"),
        Binding("r", "reject_all", "Reject All"),
    ]

    DEFAULT_CSS = """
    ReviewScreen {
        align: center middle;
    }

    #review-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #review-header {
        height: 3;
        dock: top;
    }

    #review-title {
        text-style: bold;
        color: $primary;
    }

    #review-summary {
        color: $text-muted;
    }

    #review-scroll {
        height: 1fr;
        margin: 1 0;
    }

    #review-footer {
        height: 3;
        dock: bottom;
        layout: horizontal;
        align: right middle;
    }

    #review-footer Button {
        margin-left: 1;
    }
    """

    def __init__(self, manager: ReviewManager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager

    def compose(self) -> ComposeResult:
        with Static(id="review-container"):
            with Static(id="review-header"):
                yield Label("Code Review", id="review-title")
                count = len(self.manager.pending_changes)
                yield Label(f"{count} file(s) with changes", id="review-summary")

            with VerticalScroll(id="review-scroll"):
                for file, change in self.manager.pending_changes.items():
                    yield FileChangeWidget(file, change)

            with Horizontal(id="review-footer"):
                yield Button("Cancel", id="cancel", variant="default")
                yield Button("Apply Accepted", id="apply", variant="primary")

    def on_hunk_widget_accepted(self, event: HunkWidget.Accepted) -> None:
        for change in self.manager.pending_changes.values():
            for hunk in change.hunks:
                if hunk.id == event.hunk_id:
                    hunk.status = HunkStatus.ACCEPTED
                    self._refresh_hunk(event.hunk_id)
                    return

    def on_hunk_widget_rejected(self, event: HunkWidget.Rejected) -> None:
        for change in self.manager.pending_changes.values():
            for hunk in change.hunks:
                if hunk.id == event.hunk_id:
                    hunk.status = HunkStatus.REJECTED
                    self._refresh_hunk(event.hunk_id)
                    return

    def _refresh_hunk(self, hunk_id: str) -> None:
        for widget in self.query(HunkWidget):
            if widget.hunk.id == hunk_id:
                widget.remove_class("pending", "accepted", "rejected")
                widget.add_class(widget.hunk.status.value)
                widget.refresh()
                break

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "apply":
            self.dismiss(True)
        elif event.button.id == "accept-all":
            parent = event.button.parent
            while parent and not isinstance(parent, FileChangeWidget):
                parent = parent.parent
            if isinstance(parent, FileChangeWidget):
                self.manager.accept_file(parent.file)
                self._refresh_file(parent.file)
        elif event.button.id == "reject-all":
            parent = event.button.parent
            while parent and not isinstance(parent, FileChangeWidget):
                parent = parent.parent
            if isinstance(parent, FileChangeWidget):
                self.manager.reject_file(parent.file)
                self._refresh_file(parent.file)

    def _refresh_file(self, file: str) -> None:
        for widget in self.query(FileChangeWidget):
            if widget.file == file:
                for hunk_widget in widget.query(HunkWidget):
                    hunk_widget.remove_class("pending", "accepted", "rejected")
                    hunk_widget.add_class(hunk_widget.hunk.status.value)
                    hunk_widget.refresh()
                break

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_apply(self) -> None:
        self.dismiss(True)

    def action_accept_all(self) -> None:
        self.manager.accept_all()
        for widget in self.query(HunkWidget):
            widget.remove_class("pending", "accepted", "rejected")
            widget.add_class("accepted")
            widget.refresh()

    def action_reject_all(self) -> None:
        self.manager.reject_all()
        for widget in self.query(HunkWidget):
            widget.remove_class("pending", "accepted", "rejected")
            widget.add_class("rejected")
            widget.refresh()
