"""Tool approval screen for agent mode."""

from .base import (
    ModalScreen, ComposeResult, Binding,
    Container, Horizontal, Vertical, VerticalScroll,
    Label, Button, Static
)
from rich.syntax import Syntax
from rich.markdown import Markdown
from typing import List, Optional
import json


class ToolPreview(Static):
    """Preview of a tool call for approval."""

    DEFAULT_CSS = """
    ToolPreview {
        width: 100%;
        height: auto;
        padding: 1;
        background: $surface-darken-1;
        border: solid $surface-lighten-1;
        margin-bottom: 1;
    }
    ToolPreview .tool-name {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    ToolPreview .tool-args {
        width: 100%;
        height: auto;
        max-height: 10;
    }
    """

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
                classes="tool-args"
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

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "approve", "Approve"),
        Binding("a", "approve_all", "Approve All"),
        Binding("r", "reject", "Reject"),
    ]

    DEFAULT_CSS = """
    ToolApprovalScreen {
        align: center middle;
    }

    #approval-container {
        width: 80;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #approval-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    #approval-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    #tools-scroll {
        width: 100%;
        height: auto;
        max-height: 20;
        margin-bottom: 1;
    }

    #approval-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #approval-buttons Button {
        margin: 0 1;
    }

    #approval-hint {
        text-align: center;
        color: $text-muted;
        text-style: dim;
        margin-top: 1;
    }
    """

    def __init__(self, tool_calls: List[dict], iteration_number: int = 1):
        """Initialize the approval screen.

        Args:
            tool_calls: List of tool call dicts with 'name' and 'arguments'
            iteration_number: Current iteration number for context
        """
        super().__init__()
        self.tool_calls = tool_calls
        self.iteration_number = iteration_number
        self.result: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Container(id="approval-container"):
            yield Label("Tool Approval Required", id="approval-title")
            yield Label(
                f"Iteration {self.iteration_number} - Agent wants to execute:",
                id="approval-subtitle"
            )

            with VerticalScroll(id="tools-scroll"):
                for tc in self.tool_calls:
                    yield ToolPreview(
                        tool_name=tc.get("name", "Unknown"),
                        arguments=tc.get("arguments", {})
                    )

            with Horizontal(id="approval-buttons"):
                yield Button("Approve", variant="success", id="approve")
                yield Button("Approve All", variant="primary", id="approve-all")
                yield Button("Reject", variant="warning", id="reject")
                yield Button("Cancel", variant="error", id="cancel")

            yield Label(
                "Enter: Approve | A: Approve All | R: Reject | Esc: Cancel",
                id="approval-hint"
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
