from textual.containers import VerticalScroll


class HistoryViewport(VerticalScroll):
    """Scrollable container for blocks."""

    DEFAULT_CSS = """
    HistoryViewport {
        height: 1fr;
        padding: 1;
        background: $background;
    }
    """

    def on_mount(self):
        self.scroll_end(animate=False)
