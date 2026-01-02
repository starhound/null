from textual.containers import VerticalScroll
from textual.events import Resize


class HistoryViewport(VerticalScroll):
    """Scrollable container for blocks."""

    DEFAULT_CSS = """
    HistoryViewport {
        padding: 1;
        background: $background;
        scrollbar-gutter: stable;
        min-height: 10;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auto_scroll = True
        self._last_max_scroll = 0

    def on_mount(self):
        self.scroll_end(animate=False)
        # Watch for content changes
        self.set_interval(0.1, self._check_scroll)

    def _check_scroll(self):
        """Check if we need to auto-scroll to bottom."""
        if not self._auto_scroll:
            return

        # If max scroll position changed (content grew), scroll to bottom
        if self.max_scroll_y > self._last_max_scroll:
            self._last_max_scroll = self.max_scroll_y
            self.scroll_end(animate=False)

    def on_scroll_up(self, event=None):
        """User scrolled up, disable auto-scroll."""
        self._auto_scroll = False

    def on_scroll_down(self, event=None):
        """Check if user scrolled to bottom to re-enable auto-scroll."""
        # Re-enable if at or near bottom
        if self.scroll_y >= self.max_scroll_y - 2:
            self._auto_scroll = True

    def watch_scroll_y(self, scroll_y: float):
        """Track scroll position to manage auto-scroll."""
        # If user is at bottom, enable auto-scroll
        if scroll_y >= self.max_scroll_y - 2:
            self._auto_scroll = True
        elif scroll_y < self.max_scroll_y - 10:
            # If user scrolled significantly up, disable
            self._auto_scroll = False

    def scroll_to_bottom(self):
        """Force scroll to bottom and enable auto-scroll."""
        self._auto_scroll = True
        self.scroll_end(animate=False)
        self._last_max_scroll = self.max_scroll_y
