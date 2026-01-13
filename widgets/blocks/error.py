from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

from handlers.error import ErrorSeverity, StructuredError, open_issue_report
from models import BlockState

from .base import BaseBlockWidget


class CopyButton(Button):
    class Pressed(Message, bubble=True):
        def __init__(self, content: str):
            super().__init__()
            self.content = content

    def __init__(self, content: str, id: str | None = None):
        super().__init__("Copy", id=id, classes="error-copy-btn")
        self._content = content

    def on_click(self) -> None:
        self.post_message(self.Pressed(self._content))


class ReportButton(Button):
    class Pressed(Message, bubble=True):
        def __init__(self, error: StructuredError):
            super().__init__()
            self.error = error

    def __init__(self, error: StructuredError, id: str | None = None):
        super().__init__("Report Issue", id=id, classes="error-report-btn")
        self._error = error

    def on_click(self) -> None:
        self.post_message(self.Pressed(self._error))


class StackTraceSection(Static):
    expanded = reactive(False)

    def __init__(self, stack_trace: str, id: str | None = None):
        super().__init__(id=id, classes="stack-trace-section")
        self._stack_trace = stack_trace

    def compose(self) -> ComposeResult:
        with Static(classes="stack-trace-header", id="stack-header"):
            icon = "▼" if self.expanded else "▶"
            yield Label(icon, classes="stack-icon", id="stack-icon")
            yield Label("Stack Trace", classes="stack-label")

        with VerticalScroll(classes="stack-content", id="stack-content"):
            yield Static(self._stack_trace, classes="stack-text")

    def on_mount(self) -> None:
        self._update_visibility()

    def on_click(self, event) -> None:
        if event.y <= 1:
            self.expanded = not self.expanded
            event.stop()

    def watch_expanded(self, expanded: bool) -> None:
        self._update_visibility()
        try:
            icon = self.query_one("#stack-icon", Label)
            icon.update("▼" if expanded else "▶")
        except Exception:
            pass

    def _update_visibility(self) -> None:
        try:
            content = self.query_one("#stack-content", VerticalScroll)
            if self.expanded:
                content.add_class("visible")
            else:
                content.remove_class("visible")
        except Exception:
            pass


class ErrorBlock(BaseBlockWidget):
    DEFAULT_CSS = """
    ErrorBlock {
        height: auto;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, block: BlockState, error: StructuredError | None = None):
        super().__init__(block)
        self._error = error
        self._severity = error.severity if error else ErrorSeverity.ERROR

    def compose(self) -> ComposeResult:
        severity_class = f"error-severity-{self._severity.value}"

        with Container(classes=f"error-block-container {severity_class}"):
            with Static(classes="error-header"):
                yield Label(self._get_severity_icon(), classes="error-icon")
                yield Label(
                    self._error.error_type if self._error else "Error",
                    classes="error-type",
                )
                yield Static("", classes="error-spacer")
                ts_str = self.block.timestamp.strftime("%H:%M:%S")
                yield Label(ts_str, classes="error-timestamp")

            with Vertical(classes="error-body"):
                yield Static(
                    self._error.message if self._error else self.block.content_output,
                    classes="error-message",
                )

                if self._error and self._error.details:
                    with Static(classes="error-details-section"):
                        yield Label("Details", classes="error-section-label")
                        yield Static(self._error.details, classes="error-details")

                if self._error and self._error.suggestion:
                    with Static(classes="error-suggestion-section"):
                        yield Label("💡", classes="suggestion-icon")
                        yield Static(self._error.suggestion, classes="error-suggestion")

                if self._error and self._error.context:
                    with Static(classes="error-context-section"):
                        yield Label("Context", classes="error-section-label")
                        for key, value in self._error.context.items():
                            yield Static(
                                f"{key}: {value}", classes="error-context-item"
                            )

            if self._error and self._error.stack_trace:
                yield StackTraceSection(self._error.stack_trace, id="stack-trace")

            with Static(classes="error-footer"):
                if self._error:
                    yield CopyButton(self._error.to_copyable_text(), id="copy-btn")
                    if self._error.is_unexpected:
                        yield ReportButton(self._error, id="report-btn")

    def _get_severity_icon(self) -> str:
        icons = {
            ErrorSeverity.INFO: "ℹ",
            ErrorSeverity.WARNING: "⚠",
            ErrorSeverity.ERROR: "✗",
            ErrorSeverity.CRITICAL: "⛔",
        }
        return icons.get(self._severity, "✗")

    @on(CopyButton.Pressed)
    def handle_copy(self, event: CopyButton.Pressed) -> None:
        event.stop()
        self.post_message(self.CopyRequested(self.block.id, event.content))

    @on(ReportButton.Pressed)
    def handle_report(self, event: ReportButton.Pressed) -> None:
        event.stop()
        if open_issue_report(event.error):
            self.notify("Opening browser to report issue...")
        else:
            self.notify(
                "Could not open browser. Copy error details instead.",
                severity="warning",
            )

    def update_output(self, new_content: str = "") -> None:
        try:
            message_widget = self.query_one(".error-message", Static)
            message_widget.update(new_content or self.block.content_output)
        except Exception:
            pass


def create_error_block(
    error: StructuredError,
    input_text: str = "",
) -> tuple[BlockState, ErrorBlock]:
    from models import BlockType

    block = BlockState(
        type=BlockType.SYSTEM_MSG,
        content_input=input_text or error.error_type,
        content_output=error.message,
        metadata={
            "error_type": error.error_type,
            "severity": error.severity.value,
            "is_error": True,
        },
    )
    block.is_running = False

    return block, ErrorBlock(block, error)
