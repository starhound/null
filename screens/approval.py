"""Tool approval screen for agent mode."""

import json
from typing import ClassVar

from rich.syntax import Syntax
from textual.binding import BindingType
from textual.timer import Timer

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    Label,
    ModalScreen,
    Static,
    VerticalScroll,
)


class ToolPreview(Static):
    """Preview of a tool call for approval."""

    def __init__(self, tool_name: str, arguments: dict):
        super().__init__()
        self.tool_name = tool_name
        self.arguments = arguments

    def compose(self) -> ComposeResult:
        yield Label(f"Tool: {self.tool_name}", classes="tool-name")

        # Format arguments as JSON
        try:
            args_json = json.dumps(self.arguments, indent=2)
            # Get theme safely - may not have app context during testing
            try:
                theme = getattr(self.app, "theme", "monokai")
            except Exception:
                theme = "monokai"
            yield Static(
                Syntax(
                    args_json,
                    "json",
                    theme=theme,
                    line_numbers=False,
                ),
                classes="tool-args",
            )
        except (TypeError, ValueError):
            yield Static(str(self.arguments), classes="tool-args")


class ToolApprovalScreen(ModalScreen):
    """Modal for approving tool execution in agent mode.

    Presents the pending tool calls and allows the user to:
    - Approve: Execute this tool
    - Approve All: Execute all remaining tools without asking
    - Approve for Session: Remember these tools as approved for the session
    - Reject: Skip this tool
    - Cancel: Stop the entire agent loop

    Supports configurable timeout that auto-rejects if no response.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "approve", "Approve"),
        Binding("a", "approve_all", "Approve All"),
        Binding("s", "approve_session", "Approve for Session"),
        Binding("r", "reject", "Reject"),
    ]

    def __init__(
        self,
        tool_calls: list[dict],
        iteration_number: int = 1,
        timeout_seconds: int | None = None,
    ):
        """Initialize the approval screen.

        Args:
            tool_calls: List of tool call dicts with 'name' and 'arguments'
            iteration_number: Current iteration number for context
            timeout_seconds: Seconds before auto-reject (None = no timeout)
        """
        super().__init__()
        self.tool_calls = tool_calls
        self.iteration_number = iteration_number
        self.timeout_seconds = timeout_seconds
        self.result: str | None = None
        self._timeout_timer: Timer | None = None
        self._countdown_timer: Timer | None = None
        self._remaining_seconds: int = timeout_seconds or 0

    def compose(self) -> ComposeResult:
        with Container(id="approval-container"):
            yield Label("Tool Approval Required", id="approval-title")

            subtitle = f"Iteration {self.iteration_number} - Agent wants to execute:"
            if self.timeout_seconds:
                subtitle += f" (auto-reject in {self.timeout_seconds}s)"
            yield Label(subtitle, id="approval-subtitle")

            with VerticalScroll(id="tools-scroll"):
                for tc in self.tool_calls:
                    yield ToolPreview(
                        tool_name=tc.get("name", "Unknown"),
                        arguments=tc.get("arguments", {}),
                    )

            with Horizontal(id="approval-buttons"):
                yield Button("Approve", variant="success", id="approve")
                yield Button("Approve All", variant="primary", id="approve-all")
                yield Button("Session", variant="default", id="approve-session")
                yield Button("Reject", variant="warning", id="reject")
                yield Button("Cancel", variant="error", id="cancel")

            yield Label(
                "Enter: Approve | A: All | S: Session | R: Reject | Esc: Cancel",
                id="approval-hint",
            )

    def on_mount(self) -> None:
        if self.timeout_seconds and self.timeout_seconds > 0:
            self._remaining_seconds = self.timeout_seconds
            self._timeout_timer = self.set_timer(self.timeout_seconds, self._on_timeout)
            self._countdown_timer = self.set_interval(1.0, self._update_countdown)

    def _on_timeout(self) -> None:
        self._stop_timers()
        self.result = "timeout"
        self.dismiss(self.result)

    def _update_countdown(self) -> None:
        self._remaining_seconds -= 1
        if self._remaining_seconds > 0:
            try:
                subtitle = self.query_one("#approval-subtitle", Label)
                subtitle.update(
                    f"Iteration {self.iteration_number} - Agent wants to execute: "
                    f"(auto-reject in {self._remaining_seconds}s)"
                )
            except Exception:
                pass

    def _stop_timers(self) -> None:
        if self._timeout_timer:
            self._timeout_timer.stop()
            self._timeout_timer = None
        if self._countdown_timer:
            self._countdown_timer.stop()
            self._countdown_timer = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._stop_timers()
        self.result = event.button.id
        self.dismiss(self.result)

    def action_approve(self) -> None:
        self._stop_timers()
        self.result = "approve"
        self.dismiss(self.result)

    def action_approve_all(self) -> None:
        self._stop_timers()
        self.result = "approve-all"
        self.dismiss(self.result)

    def action_approve_session(self) -> None:
        self._stop_timers()
        self.result = "approve-session"
        self.dismiss(self.result)

    def action_reject(self) -> None:
        self._stop_timers()
        self.result = "reject"
        self.dismiss(self.result)

    def action_cancel(self) -> None:
        self._stop_timers()
        self.result = "cancel"
        self.dismiss(self.result)

    def get_tool_names(self) -> list[str]:
        return [tc.get("name", "") for tc in self.tool_calls if tc.get("name")]
