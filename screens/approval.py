"""Tool approval screen for agent mode."""

import json
from typing import ClassVar

from rich.syntax import Syntax
from textual.binding import BindingType

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
            yield Static(
                Syntax(args_json, "json", theme="monokai", line_numbers=False),
                classes="tool-args",
            )
        except (TypeError, ValueError):
            yield Static(str(self.arguments), classes="tool-args")


class ToolApprovalScreen(ModalScreen):
    """Modal for approving tool execution in agent mode.

    Presents the pending tool calls and allows the user to:
    - Approve: Execute this tool
    - Approve All: Execute all remaining tools without asking
    - Reject: Skip this tool
    - Cancel: Stop the entire agent loop
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "approve", "Approve"),
        Binding("a", "approve_all", "Approve All"),
        Binding("r", "reject", "Reject"),
    ]

    def __init__(self, tool_calls: list[dict], iteration_number: int = 1):
        """Initialize the approval screen.

        Args:
            tool_calls: List of tool call dicts with 'name' and 'arguments'
            iteration_number: Current iteration number for context
        """
        super().__init__()
        self.tool_calls = tool_calls
        self.iteration_number = iteration_number
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="approval-container"):
            yield Label("Tool Approval Required", id="approval-title")
            yield Label(
                f"Iteration {self.iteration_number} - Agent wants to execute:",
                id="approval-subtitle",
            )

            with VerticalScroll(id="tools-scroll"):
                for tc in self.tool_calls:
                    yield ToolPreview(
                        tool_name=tc.get("name", "Unknown"),
                        arguments=tc.get("arguments", {}),
                    )

            with Horizontal(id="approval-buttons"):
                yield Button("Approve", variant="success", id="approve")
                yield Button("Approve All", variant="primary", id="approve-all")
                yield Button("Reject", variant="warning", id="reject")
                yield Button("Cancel", variant="error", id="cancel")

            yield Label(
                "Enter: Approve | A: Approve All | R: Reject | Esc: Cancel",
                id="approval-hint",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        self.result = event.button.id
        self.dismiss(self.result)

    def action_approve(self) -> None:
        """Approve the current tool(s)."""
        self.result = "approve"
        self.dismiss(self.result)

    def action_approve_all(self) -> None:
        """Approve all remaining tools without asking."""
        self.result = "approve-all"
        self.dismiss(self.result)

    def action_reject(self) -> None:
        """Reject the current tool(s)."""
        self.result = "reject"
        self.dismiss(self.result)

    def action_cancel(self) -> None:
        """Cancel the entire agent loop."""
        self.result = "cancel"
        self.dismiss(self.result)
