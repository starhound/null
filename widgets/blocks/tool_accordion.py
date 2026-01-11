import json
from typing import ClassVar

from rich.markdown import Markdown
from rich.syntax import Syntax
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Button, Label, ProgressBar, Static

from tools.streaming import ToolProgress, ToolStatus


class ToolHeader(Static):
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
        self._elapsed_timer: Timer | None = None
        self._start_time: float = 0.0

    def compose(self) -> ComposeResult:
        icon = "▼" if self.expanded else "▶"
        icon_classes = "tool-icon expanded" if self.expanded else "tool-icon"
        yield Label(icon, classes=icon_classes, id="tool-icon")
        yield Label(self.tool_name, classes="tool-name")

        status_icon = self._get_status_icon()
        yield Label(status_icon, classes=f"tool-status {self.status}", id="tool-status")

        yield ProgressBar(
            total=100, show_eta=False, classes="tool-progress", id="tool-progress"
        )

        yield Static("", classes="tool-spacer")

        yield Button("✕", id="cancel-btn", classes="tool-cancel-btn", variant="error")

        duration_text = f"{self.duration:.1f}s" if self.duration > 0 else ""
        yield Label(duration_text, classes="tool-duration", id="tool-duration")

    def _get_status_icon(self) -> str:
        icons = {
            "pending": "○",
            "running": self.SPINNER_FRAMES[0],
            "success": "󰄬",
            "error": "✗",
            "cancelled": "⊘",
        }
        return icons.get(self.status, "○")

    def on_mount(self) -> None:
        self.query_one("#tool-progress", ProgressBar).display = False
        self.query_one("#cancel-btn", Button).display = self.status == "running"

        if self.status == "running":
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
            self._start_elapsed_timer()

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

    def _start_elapsed_timer(self) -> None:
        import time

        self._start_time = time.time()
        if self._elapsed_timer:
            self._elapsed_timer.stop()
        self._elapsed_timer = self.set_interval(0.5, self._update_elapsed)

    def _update_elapsed(self) -> None:
        import time

        if self.status != "running":
            if self._elapsed_timer:
                self._elapsed_timer.stop()
            return

        elapsed = time.time() - self._start_time
        try:
            duration_label = self.query_one("#tool-duration", Label)
            duration_label.update(f"{elapsed:.1f}s")
        except Exception:
            pass

    def update_status(self, status: str, duration: float = 0.0) -> None:
        self.status = status
        self.duration = duration
        try:
            status_label = self.query_one("#tool-status", Label)
            status_label.update(self._get_status_icon())
            status_label.remove_class(
                "pending", "running", "success", "error", "cancelled"
            )
            status_label.add_class(status)

            duration_label = self.query_one("#tool-duration", Label)
            duration_label.update(f"{duration:.1f}s" if duration > 0 else "")

            cancel_btn = self.query_one("#cancel-btn", Button)
            cancel_btn.display = status == "running"

            if status == "running":
                if not self._spinner_timer:
                    self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
                self._start_elapsed_timer()
            else:
                if self._spinner_timer:
                    self._spinner_timer.stop()
                if self._elapsed_timer:
                    self._elapsed_timer.stop()

                self.query_one("#tool-progress", ProgressBar).display = False

        except Exception:
            pass

    def update_progress(self, progress: float | None) -> None:
        try:
            bar = self.query_one("#tool-progress", ProgressBar)
            if progress is not None:
                bar.display = True
                bar.progress = progress * 100
            else:
                bar.display = False
        except Exception:
            pass

    def set_expanded(self, expanded: bool) -> None:
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
    streaming = reactive(False)

    def __init__(
        self,
        arguments: str = "",
        output: str = "",
        id: str | None = None,
        streaming: bool = False,
    ):
        super().__init__(id=id)
        self.arguments = arguments
        self.output = output
        self.streaming = streaming
        self._auto_scroll = True

    def compose(self) -> ComposeResult:
        with Container(classes="tool-output-content"):
            if self.arguments:
                try:
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

            if self.output:
                if self.streaming:
                    yield Static(
                        self.output, classes="tool-result streaming", id="tool-result"
                    )
                else:
                    yield Static(
                        Markdown(self.output), classes="tool-result", id="tool-result"
                    )
            else:
                yield Static(
                    "(running...)" if self.streaming else "(no output)",
                    classes="tool-result",
                    id="tool-result",
                )

    def update_output(self, output: str, streaming: bool = False) -> None:
        self.output = output
        self.streaming = streaming

        try:
            result = self.query_one("#tool-result", Static)

            if streaming:
                result.update(output if output else "(running...)")
                result.add_class("streaming")
            else:
                result.remove_class("streaming")
                result.update(Markdown(output) if output else "(no output)")

            if self._auto_scroll and streaming:
                self.scroll_end(animate=False)

        except Exception:
            pass

    def show(self) -> None:
        self.add_class("visible")

    def hide(self) -> None:
        self.remove_class("visible")


class ToolAccordionItem(Static):
    expanded = reactive(False)

    class CancelRequested(Message):
        def __init__(self, tool_id: str):
            self.tool_id = tool_id
            super().__init__()

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
        streaming: bool = False,
    ):
        super().__init__(id=id, classes=classes)
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.output = output
        self.status = status
        self.duration = duration
        self.streaming = streaming
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
            arguments=self.arguments,
            output=self.output,
            id=f"output-{self.tool_id}",
            streaming=self.streaming,
        )
        yield self._output_panel

    def on_click(self, event: Click) -> None:
        if event.y <= 1:
            self.expanded = not self.expanded
            event.stop()

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.CancelRequested(self.tool_id))

    def watch_expanded(self, expanded: bool) -> None:
        if self._header:
            self._header.set_expanded(expanded)
        if self._output_panel:
            if expanded:
                self._output_panel.show()
            else:
                self._output_panel.hide()

    def update_status(self, status: str, duration: float = 0.0) -> None:
        self.status = status
        self.duration = duration
        if self._header:
            self._header.update_status(status, duration)

    def update_output(self, output: str, streaming: bool = False) -> None:
        self.output = output
        self.streaming = streaming
        if self._output_panel:
            self._output_panel.update_output(output, streaming=streaming)

    def update_progress(self, progress: ToolProgress) -> None:
        if self._header:
            self._header.update_progress(progress.progress)

        self.update_status(progress.status.value, progress.elapsed)
        self.update_output(progress.output, streaming=True)


class ToolAccordion(Container):
    def __init__(self, id: str | None = None, classes: str | None = None):
        super().__init__(id=id, classes=classes)
        self._tools: dict[str, ToolAccordionItem] = {}

    def compose(self) -> ComposeResult:
        yield from []

    def add_tool(
        self,
        tool_id: str,
        tool_name: str,
        arguments: str = "",
        status: str = "running",
        streaming: bool = False,
    ) -> ToolAccordionItem:
        if "empty" in self.classes:
            self.remove_class("empty")

        item = ToolAccordionItem(
            tool_id=tool_id,
            tool_name=tool_name,
            arguments=arguments,
            status=status,
            id=f"tool-{tool_id}",
            streaming=streaming,
        )
        self._tools[tool_id] = item
        self.mount(item)

        if streaming:
            item.expanded = True

        return item

    def update_tool(
        self,
        tool_id: str,
        status: str | None = None,
        output: str | None = None,
        duration: float | None = None,
        streaming: bool = False,
    ) -> None:
        item = self._tools.get(tool_id)
        if item:
            if status is not None:
                item.update_status(status, duration or 0.0)
            if output is not None:
                item.update_output(output, streaming=streaming)

    def get_tool(self, tool_id: str) -> ToolAccordionItem | None:
        return self._tools.get(tool_id)

    def clear(self) -> None:
        for item in self._tools.values():
            item.remove()
        self._tools.clear()
        self.add_class("empty")
