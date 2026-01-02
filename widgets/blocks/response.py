from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Label
from textual.reactive import reactive

from models import BlockState
from .code_block import CodeBlockWidget

class ResponseWidget(Static):
    """Widget for the final AI response content."""

    content_text = reactive("")

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        with Container(classes="response-container"):
            with Static(classes="response-header"):
                yield Label("◆", classes="response-icon")
                yield Label("Final Answer", classes="response-title")
            
            yield Static(id="response-content")

    def watch_content_text(self, new_text: str):
        try:
            content = self.query_one("#response-content", Static)
            if new_text:
                self.remove_class("hidden")
                from rich.markdown import Markdown
                content.update(Markdown(new_text, code_theme="monokai"))
            else:
                self.add_class("hidden")
                content.update("")
        except Exception:
            pass

    def set_simple(self, simple: bool):
        """Toggle simple display mode (no header/border)."""
        try:
            container = self.query_one(".response-container")
            if simple:
                container.add_class("simple")
            else:
                container.remove_class("simple")
        except Exception:
            pass
