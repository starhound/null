from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Static, Label, Button
from textual.reactive import reactive
from textual import on

try:
    import pyperclip
except ImportError:
    pyperclip = None

from models import BlockState


class ExecutionWidget(Static):
    """Widget for command execution output with copy button."""

    DEFAULT_CSS = """
    ExecutionWidget {
        height: auto;
        padding: 0 1;
        margin-top: 1;
        background: transparent;
    }

    .hidden {
        display: none;
    }

    #exec-container {
        padding: 0;
    }

    /* Header with title and copy button */
    .exec-header {
        layout: horizontal;
        height: 1;
        width: 100%;
        padding: 0 1;
        margin-bottom: 1;
        background: $surface-darken-1;
    }

    .exec-title {
        color: $success;
        width: 1fr;
        text-style: bold;
    }

    .exec-icon {
        color: $success;
        min-width: 2;
        margin-right: 1;
    }

    .copy-btn {
        min-width: 6;
        height: 1;
        border: none;
        padding: 0;
        background: transparent;
        color: $text-muted;
        text-style: dim;
    }

    .copy-btn:hover {
        color: $primary;
        text-style: bold;
    }

    /* Output content area */
    .exec-scroll {
        height: auto;
        max-height: 15;
        margin: 0 1;
        padding: 1;
        background: $surface-darken-2;
        border-left: wide $success 50%;
        scrollbar-size: 1 1;
    }

    #exec-content {
        width: 100%;
        padding: 0;
    }
    """

    exec_output = reactive("")

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        with Container(id="exec-container", classes="hidden"):
            with Static(classes="exec-header"):
                yield Label("⚡", classes="exec-icon")
                yield Label("Command Output", classes="exec-title")
                yield Button("[copy]", classes="copy-btn", id="copy-btn")
            with VerticalScroll(classes="exec-scroll"):
                yield Static(id="exec-content")

    def watch_exec_output(self, new_text: str):
        try:
            container = self.query_one("#exec-container")
            content = self.query_one("#exec-content", Static)

            if new_text:
                container.remove_class("hidden")
                from rich.markdown import Markdown
                content.update(Markdown(new_text))
            else:
                container.add_class("hidden")
                content.update("")
        except Exception:
            pass

    @on(Button.Pressed, "#copy-btn")
    def copy_output(self):
        text = self.block.content_exec_output
        try:
            if text.startswith("\n```text\n") and text.endswith("\n```\n"):
                text = text[7:-5]

            if pyperclip:
                pyperclip.copy(text)
                self.notify("Copied to clipboard!")
            else:
                self.notify("pyperclip not installed", severity="error")
        except Exception as e:
            self.notify(f"Clipboard error: {e}", severity="error")
