import json

from rich.json import JSON
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from models import BlockState

from .base import BaseBlockWidget
from .parts import BlockBody, BlockFooter, BlockHeader


class VizBlockWidget(BaseBlockWidget):
    """Widget for visualizing structured data (JSON, Tables)."""

    def __init__(self, block: BlockState, view_type: str = "json"):
        super().__init__(block)
        self.view_type = view_type
        self.header = BlockHeader(block)
        self.footer = BlockFooter(block)
        self.body_content: Static | BlockBody | None = None

    def compose(self) -> ComposeResult:
        yield self.header

        # Render body based on view type
        if self.view_type == "json":
            try:
                data = json.loads(self.block.content_output)
                self.body_content = Static(JSON.from_data(data), classes="viz-body")
            except Exception:
                self.body_content = Static("Error parsing JSON", classes="error")
        elif self.view_type == "table":
            # Heuristic table rendering (simple CSV or list of dicts)
            self.body_content = Static(self._render_table(), classes="viz-body")
        else:
            self.body_content = BlockBody(self.block.content_output)

        yield self.body_content
        yield self.footer

    def _render_table(self):
        try:
            data = json.loads(self.block.content_output)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                table = Table(show_header=True, header_style="bold magenta")
                keys = list(data[0].keys())
                for key in keys:
                    table.add_column(str(key))
                for item in data:
                    table.add_row(*[str(item.get(k, "")) for k in keys])
                return table
        except Exception:
            pass
        return Text("Cannot render table", style="red")
