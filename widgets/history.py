from textual.containers import VerticalScroll


class HistoryViewport(VerticalScroll):
    """Scrollable container for blocks."""

    DEFAULT_CSS = """
    HistoryViewport {
        padding: 1;
        background: $background;
        scrollbar-gutter: stable;
    }
    """

    def on_mount(self):
        self.scroll_end(animate=False)
