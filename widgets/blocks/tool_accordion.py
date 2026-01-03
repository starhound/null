"""Tool accordion widget for agent mode tool calls."""

import json
from typing import ClassVar

from rich.markdown import Markdown
from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Click
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Label, Static


class ToolHeader(Static):
    """Header line for a tool call item."""

    SPINNER_FRAMES: ClassVar[list[str]] = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    def __init__(
        self,
        tool_name: str,
        status: str = "pending",
        duration: float = 0.0,
        expanded: bool = False,
        id: str | None = None,
    ):
        super().__init__(id=id)
        self.tool_name = tool_name
        self.status = status
        self.duration = duration
        self.expanded = expanded
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        icon = "▼" if self.expanded else "▶"
        icon_classes = "tool-icon expanded" if self.expanded else "tool-icon"
        yield Label(icon, classes=icon_classes, id="tool-icon")
        yield Label(self.tool_name, classes="tool-name")

        # Status indicator
        status_icon = self._get_status_icon()
        yield Label(status_icon, classes=f"tool-status {self.status}", id="tool-status")

        # Spacer with decorative line
        yield Static("", classes="tool-spacer")

        # Duration (only show if > 0)
        duration_text = f"{self.duration:.1f}s" if self.duration > 0 else ""
        yield Label(duration_text, classes="tool-duration", id="tool-duration")

    def _get_status_icon(self) -> str:
        icons = {
            "pending": "○",
            "running": self.SPINNER_FRAMES[0],
            "success": "[✓]",
            "error": "[✗]",
        }
        return icons.get(self.status, "○")

    def on_mount(self) -> None:
        if self.status == "running":
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)

    def _animate_spinner(self) -> None:
        if self.status != "running":
            if self._spinner_timer:
                self._spinner_timer.stop()
            return

        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            status_label = self.query_one("#tool-status", Label)
            status_label.update(self.SPINNER_FRAMES[self._spinner_index])
        except Exception:
            pass

    def update_status(self, status: str, duration: float = 0.0) -> None:
        """Update the tool status and duration."""
        self.status = status
        self.duration = duration
        try:
            status_label = self.query_one("#tool-status", Label)
            status_label.update(self._get_status_icon())
            status_label.remove_class("pending", "running", "success", "error")
            status_label.add_class(status)

            duration_label = self.query_one("#tool-duration", Label)
            duration_label.update(f"{duration:.1f}s" if duration > 0 else "")

            if status == "running" and not self._spinner_timer:
                self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
            elif status != "running" and self._spinner_timer:
                self._spinner_timer.stop()
        except Exception:
            pass

    def set_expanded(self, expanded: bool) -> None:
        """Update the expand/collapse icon."""
        self.expanded = expanded
        try:
            icon_label = self.query_one("#tool-icon", Label)
            icon_label.update("▼" if expanded else "▶")
            if expanded:
                icon_label.add_class("expanded")
            else:
                icon_label.remove_class("expanded")
        except Exception:
            pass


class ToolOutput(VerticalScroll):
    """Collapsible output container for tool results."""

    def __init__(self, arguments: str = "", output: str = "", id: str | None = None):
        super().__init__(id=id)
        self.arguments = arguments
        self.output = output

    def compose(self) -> ComposeResult:
        with Container(classes="tool-output-content"):
            # Show arguments if present
            if self.arguments:
                try:
                    # Try to parse and pretty-print JSON arguments
                    args_dict = json.loads(self.arguments)
                    args_formatted = json.dumps(args_dict, indent=2)
                    yield Static(
                        Syntax(
                            args_formatted, "json", theme="monokai", line_numbers=False
                        ),
                        classes="tool-args",
                    )
                except (json.JSONDecodeError, TypeError):
                    yield Static(f"Args: {self.arguments}", classes="tool-args")

            # Show output
            if self.output:
                yield Static(
                    Markdown(self.output), classes="tool-result", id="tool-result"
                )
            else:
                yield Static("(no output)", classes="tool-result", id="tool-result")

    def update_output(self, output: str) -> None:
        """Update the output content."""
        self.output = output
        try:
            result = self.query_one("#tool-result", Static)
            result.update(Markdown(output) if output else "(no output)")
        except Exception:
            pass

    def show(self) -> None:
        """Show the output panel."""
        self.add_class("visible")

    def hide(self) -> None:
        """Hide the output panel."""
        self.remove_class("visible")


class ToolAccordionItem(Static):
    """Single collapsible tool call in the accordion."""

    expanded = reactive(False)

    def __init__(
        self,
        tool_id: str,
        tool_name: str,
        arguments: str = "",
        output: str = "",
        status: str = "pending",
        duration: float = 0.0,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.output = output
        self.status = status
        self.duration = duration
        self._header: ToolHeader | None = None
        self._output_panel: ToolOutput | None = None

    def compose(self) -> ComposeResult:
        self._header = ToolHeader(
            tool_name=self.tool_name,
            status=self.status,
            duration=self.duration,
            expanded=self.expanded,
            id=f"header-{self.tool_id}",
        )
        yield self._header

        self._output_panel = ToolOutput(
            arguments=self.arguments, output=self.output, id=f"output-{self.tool_id}"
        )
        yield self._output_panel

    def on_click(self, event: Click) -> None:
        """Toggle expand/collapse on click."""
        # Only toggle if clicking the header area
        if event.y <= 1:
            self.expanded = not self.expanded
            event.stop()

    def watch_expanded(self, expanded: bool) -> None:
        """Update UI when expanded state changes."""
        if self._header:
            self._header.set_expanded(expanded)
        if self._output_panel:
            if expanded:
                self._output_panel.show()
            else:
                self._output_panel.hide()

    def update_status(self, status: str, duration: float = 0.0) -> None:
        """Update the tool status."""
        self.status = status
        self.duration = duration
        if self._header:
            self._header.update_status(status, duration)

    def update_output(self, output: str) -> None:
        """Update the tool output."""
        self.output = output
        if self._output_panel:
            self._output_panel.update_output(output)


class ToolAccordion(Container):
    """Stack of collapsible tool calls for agent mode."""

    def __init__(self, id: str | None = None, classes: str | None = None):
        super().__init__(id=id, classes=classes)
        self._tools: dict[str, ToolAccordionItem] = {}

    def compose(self) -> ComposeResult:
        # Empty by default - tools added dynamically
        # Using "yield from []" to create an empty generator
        yield from []

    def add_tool(
        self, tool_id: str, tool_name: str, arguments: str = "", status: str = "running"
    ) -> ToolAccordionItem:
        """Add a new tool call to the accordion."""
        # Remove empty class if this is the first tool
        if "empty" in self.classes:
            self.remove_class("empty")

        item = ToolAccordionItem(
            tool_id=tool_id,
            tool_name=tool_name,
            arguments=arguments,
            status=status,
            id=f"tool-{tool_id}",
        )
        self._tools[tool_id] = item
        self.mount(item)
        return item

    def update_tool(
        self,
        tool_id: str,
        status: str | None = None,
        output: str | None = None,
        duration: float | None = None,
    ) -> None:
        """Update an existing tool call."""
        item = self._tools.get(tool_id)
        if item:
            if status is not None:
                item.update_status(status, duration or 0.0)
            if output is not None:
                item.update_output(output)

    def get_tool(self, tool_id: str) -> ToolAccordionItem | None:
        """Get a tool item by ID."""
        return self._tools.get(tool_id)

    def clear(self) -> None:
        """Remove all tool items."""
        for item in self._tools.values():
            item.remove()
        self._tools.clear()
        self.add_class("empty")
