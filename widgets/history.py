from textual.containers import VerticalScroll


class HistoryViewport(VerticalScroll):
    """Scrollable container for blocks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auto_scroll = True
        self._pending_scroll = False

    def on_mount(self):
        """Initial scroll to bottom."""
        self.call_later(self._do_scroll_end)

    def _do_scroll_end(self):
        """Perform scroll to end after layout."""
        if self._auto_scroll:
            self.scroll_end(animate=False)

    def _is_at_bottom(self) -> bool:
        """Check if currently scrolled to bottom (with tolerance)."""
        # Allow some tolerance for rounding errors
        return self.scroll_y >= self.max_scroll_y - 5

    def on_mouse_scroll_up(self, event) -> None:
        """User scrolled up with mouse wheel."""
        self._auto_scroll = False

    def on_mouse_scroll_down(self, event) -> None:
        """User scrolled down with mouse wheel."""
        # Re-enable auto-scroll if we reach bottom
        self.call_later(self._check_at_bottom)

    def on_key(self, event) -> None:
        """Handle keyboard scrolling."""
        if event.key in ("up", "pageup", "home"):
            self._auto_scroll = False
        elif event.key in ("down", "pagedown", "end"):
            self.call_later(self._check_at_bottom)

    def _check_at_bottom(self):
        """Check if at bottom and re-enable auto-scroll."""
        if self._is_at_bottom():
            self._auto_scroll = True

    def on_resize(self, event) -> None:
        """Handle resize events."""
        if self._auto_scroll:
            self.call_later(self._do_scroll_end)

    def watch_virtual_size(self, virtual_size) -> None:
        """Called when content size changes."""
        if self._auto_scroll and not self._pending_scroll:
            self._pending_scroll = True
            self.call_later(self._delayed_scroll)

    def _delayed_scroll(self):
        """Delayed scroll to allow layout to complete."""
        self._pending_scroll = False
        if self._auto_scroll:
            self.scroll_end(animate=False)

    def scroll_to_bottom(self):
        """Force scroll to bottom and enable auto-scroll."""
        self._auto_scroll = True
        self.scroll_end(animate=False)

    async def mount(self, *widgets, **kwargs):
        """Override mount to scroll after adding widgets."""
        result = await super().mount(*widgets, **kwargs)
        if self._auto_scroll:
            self.call_later(self._do_scroll_end)
        return result
