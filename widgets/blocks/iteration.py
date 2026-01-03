"""Iteration widget for agent mode think -> tool -> response cycles."""

from typing import ClassVar

from rich.markdown import Markdown
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Click
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Label, Static

from models import AgentIteration, ToolCallState


class IterationHeader(Static):
    """Header showing iteration number and status."""

    SPINNER_FRAMES: ClassVar[list[str]] = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    def __init__(self, iteration: AgentIteration):
        super().__init__()
        self.iteration = iteration
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        status_class = f"iter-status {self.iteration.status}"
        yield Label(self._get_status_icon(), classes=status_class, id="status-icon")
        yield Label(
            f"Iteration {self.iteration.iteration_number}", classes="iter-label"
        )
        duration_text = (
            f"{self.iteration.duration:.1f}s" if self.iteration.duration > 0 else ""
        )
        yield Label(duration_text, classes="iter-duration", id="duration")

    def _get_status_icon(self) -> str:
        icons = {
            "pending": "○",
            "thinking": self.SPINNER_FRAMES[0],
            "executing": "◐",
            "waiting_approval": "⏸",
            "complete": "●",
        }
        return icons.get(self.iteration.status, "○")

    def on_mount(self) -> None:
        if self.iteration.status in ("thinking", "executing"):
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)

    def _animate_spinner(self) -> None:
        if self.iteration.status not in ("thinking", "executing"):
            if self._spinner_timer:
                self._spinner_timer.stop()
            return

        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            icon = self.query_one("#status-icon", Label)
            icon.update(self.SPINNER_FRAMES[self._spinner_index])
        except Exception:
            pass

    def update_status(self, status: str, duration: float = 0.0) -> None:
        """Update the iteration status."""
        self.iteration.status = status
        self.iteration.duration = duration
        try:
            icon = self.query_one("#status-icon", Label)
            icon.update(self._get_status_icon())
            icon.remove_class("pending", "thinking", "executing", "complete", "waiting")
            icon.add_class(status)

            duration_label = self.query_one("#duration", Label)
            duration_label.update(f"{duration:.1f}s" if duration > 0 else "")

            if status in ("thinking", "executing") and not self._spinner_timer:
                self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
            elif status not in ("thinking", "executing") and self._spinner_timer:
                self._spinner_timer.stop()
        except Exception:
            pass


class ThinkingSection(Static):
    """Collapsible thinking/reasoning content."""

    collapsed = reactive(True)

    def __init__(self, content: str = "", collapsed: bool = True):
        super().__init__()
        self.content = content
        self.collapsed = collapsed

    def compose(self) -> ComposeResult:
        icon = "▶" if self.collapsed else "▼"
        icon_class = "thinking-icon" if self.collapsed else "thinking-icon expanded"

        with Container(classes="thinking-toggle", id="toggle"):
            yield Label(icon, classes=icon_class, id="toggle-icon")
            yield Label("Reasoning...", classes="thinking-title")

        content_class = (
            "thinking-content" if self.collapsed else "thinking-content visible"
        )
        yield Static(
            Markdown(self.content) if self.content else "(no reasoning)",
            classes=content_class,
            id="content",
        )

    def watch_collapsed(self, collapsed: bool) -> None:
        try:
            icon = self.query_one("#toggle-icon", Label)
            content = self.query_one("#content", Static)

            if collapsed:
                icon.update("▶")
                icon.remove_class("expanded")
                content.remove_class("visible")
            else:
                icon.update("▼")
                icon.add_class("expanded")
                content.add_class("visible")
        except Exception:
            pass

    def on_click(self, event: Click) -> None:
        # Toggle on header click - use first line detection
        # The toggle container is the first row (height=1)
        if event.y <= 0:
            self.collapsed = not self.collapsed
            event.stop()

    def update_content(self, content: str) -> None:
        """Update the thinking content."""
        # Don't clear existing content with empty string
        if not content and self.content:
            return
        self.content = content
        try:
            static = self.query_one("#content", Static)
            static.update(Markdown(content) if content else "(no reasoning)")
        except Exception:
            pass


class ToolCallItem(Static):
    """Compact display of a single tool call within an iteration."""

    SPINNER_FRAMES: ClassVar[list[str]] = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    def __init__(self, tool_call: ToolCallState):
        super().__init__()
        self.tool_call = tool_call
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        icon = self._get_status_icon()
        icon_class = f"tool-icon {self.tool_call.status}"
        with Container(classes="tool-row"):
            yield Label(icon, classes=icon_class, id="icon")
            yield Label(self.tool_call.tool_name, classes="tool-name")
            duration = (
                f"{self.tool_call.duration:.1f}s" if self.tool_call.duration > 0 else ""
            )
            yield Label(duration, classes="tool-duration", id="duration")

    def _get_status_icon(self) -> str:
        icons = {
            "pending": "○",
            "running": self.SPINNER_FRAMES[0],
            "success": "✓",
            "error": "✗",
        }
        return icons.get(self.tool_call.status, "○")

    def on_mount(self) -> None:
        if self.tool_call.status == "running":
            self._spinner_timer = self.set_interval(0.08, self._animate)

    def _animate(self) -> None:
        if self.tool_call.status != "running":
            if self._spinner_timer:
                self._spinner_timer.stop()
            return

        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            icon = self.query_one("#icon", Label)
            icon.update(self.SPINNER_FRAMES[self._spinner_index])
        except Exception:
            pass

    def update_status(self, status: str, duration: float = 0.0) -> None:
        """Update tool call status."""
        self.tool_call.status = status
        self.tool_call.duration = duration
        try:
            icon = self.query_one("#icon", Label)
            icon.update(self._get_status_icon())
            icon.remove_class("pending", "running", "success", "error")
            icon.add_class(status)

            dur = self.query_one("#duration", Label)
            dur.update(f"{duration:.1f}s" if duration > 0 else "")

            if status == "running" and not self._spinner_timer:
                self._spinner_timer = self.set_interval(0.08, self._animate)
            elif status != "running" and self._spinner_timer:
                self._spinner_timer.stop()
        except Exception:
            pass


class IterationSeparator(Static):
    """Visual separator between iterations."""

    def __init__(self, iteration_number: int):
        super().__init__()
        self.iteration_number = iteration_number

    def compose(self) -> ComposeResult:
        yield Label(f"─── Iteration {self.iteration_number} ───", id="sep-label")


class IterationWidget(Static):
    """Complete widget displaying a single agent iteration.

    Contains:
    - IterationHeader (number, status, duration)
    - ThinkingSection (collapsible reasoning)
    - Tool calls list
    - Optional response fragment
    """

    def __init__(self, iteration: AgentIteration, show_thinking: bool = True):
        super().__init__()
        self.iteration = iteration
        self.show_thinking = show_thinking
        self._header: IterationHeader | None = None
        self._thinking: ThinkingSection | None = None
        self._tool_widgets: dict[str, ToolCallItem] = {}

    def compose(self) -> ComposeResult:
        self._header = IterationHeader(self.iteration)
        yield self._header

        if self.show_thinking and self.iteration.thinking:
            self._thinking = ThinkingSection(
                content=self.iteration.thinking, collapsed=True
            )
            yield self._thinking

        with Container(classes="iter-tools", id="tools-container"):
            for tc in self.iteration.tool_calls:
                widget = ToolCallItem(tc)
                self._tool_widgets[tc.id] = widget
                yield widget

        if self.iteration.response_fragment:
            yield Static(
                Markdown(self.iteration.response_fragment),
                classes="iter-response",
                id="response",
            )

    def update_status(self, status: str, duration: float = 0.0) -> None:
        """Update iteration status."""
        self.iteration.status = status
        self.iteration.duration = duration
        if self._header:
            self._header.update_status(status, duration)

    def update_thinking(self, thinking: str) -> None:
        """Update thinking content."""
        self.iteration.thinking = thinking
        if self._thinking:
            self._thinking.update_content(thinking)
        elif self.show_thinking and thinking:
            # Mount thinking section if it doesn't exist
            self._thinking = ThinkingSection(content=thinking, collapsed=True)
            try:
                self.mount(self._thinking, after=self._header)
            except Exception:
                pass

    def add_tool_call(self, tool_call: ToolCallState) -> ToolCallItem:
        """Add a tool call UI widget to this iteration.

        Note: This only creates the UI widget. The data model
        (iteration.tool_calls) should be updated by the caller.
        """
        widget = ToolCallItem(tool_call)
        self._tool_widgets[tool_call.id] = widget
        try:
            container = self.query_one("#tools-container", Container)
            container.mount(widget)
        except Exception:
            pass
        return widget

    def update_tool_call(
        self, tool_id: str, status: str | None = None, duration: float | None = None
    ) -> None:
        """Update a tool call within this iteration."""
        widget = self._tool_widgets.get(tool_id)
        if widget and status:
            widget.update_status(status, duration or 0.0)

    def update_response(self, response: str) -> None:
        """Update the response fragment."""
        self.iteration.response_fragment = response
        try:
            resp = self.query_one("#response", Static)
            resp.update(Markdown(response))
        except Exception:
            # Mount new response widget
            try:
                self.mount(
                    Static(Markdown(response), classes="iter-response", id="response")
                )
            except Exception:
                pass
