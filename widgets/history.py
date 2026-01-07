from textual.widgets import ListView, ListItem
from textual.widget import Widget


class HistoryViewport(ListView):
    """Scrollable container for blocks using ListView."""

    DEFAULT_CSS = """
    HistoryViewport {
        height: 1fr;
        width: 1fr;
    }
    HistoryViewport > ListItem {
        height: auto;
        padding: 0;
        margin: 0;
        background: transparent;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auto_scroll = True

    async def add_block(self, widget: Widget):
        await self.mount(ListItem(widget))
        if self._auto_scroll:
            self.scroll_end(animate=False)

    def on_mount(self):
        self.call_later(self.scroll_end, animate=False)

    def on_key(self, event) -> None:
        if event.key in ("pageup", "home"):
            self._auto_scroll = False
        elif event.key in ("down", "pagedown", "end"):
            if self.index == len(self.children) - 1:
                self._auto_scroll = True
