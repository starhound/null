from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static, Label
from textual.reactive import reactive
from textual.timer import Timer

from models import BlockState


class ThinkingWidget(Static):
    """Animated widget for AI response with peek preview and expand toggle."""

    DEFAULT_CSS = """
    ThinkingWidget {
        height: auto;
        padding: 1 1 0 1;
        margin: 0;
    }

    /* Header row with spinner and status */
    .thinking-header {
        layout: horizontal;
        height: 1;
        width: 100%;
        padding: 0 1;
        margin-bottom: 1;
        background: $surface-darken-1;
    }

    .spinner {
        color: $primary;
        min-width: 2;
        text-style: bold;
    }

    .spinner.complete {
        color: $success;
    }

    .thinking-label {
        color: $text-muted;
        text-style: italic;
        padding-left: 1;
        width: 1fr;
    }

    .toggle-hint {
        color: $text-muted;
        text-style: dim;
    }

    .toggle-hint:hover {
        color: $primary;
        text-style: bold;
    }

    /* Peek window - scrolling preview */
    .peek-window {
        height: 4;
        max-height: 4;
        margin: 0 1;
        padding: 1;
        border-left: wide $primary 50%;
        background: $surface-darken-2;
        scrollbar-size: 1 1;
    }

    .peek-window:focus {
        border-left: wide $primary;
    }

    .peek-window.expanded {
        height: auto;
        min-height: 4;
        max-height: 25;
    }

    .peek-content {
        width: 100%;
        padding: 0;
    }

    /* Empty state */
    .peek-window.empty {
        height: 2;
        max-height: 2;
    }

    .empty-hint {
        color: $text-muted;
        text-style: italic dim;
        padding: 0 1;
    }
    """

    SPINNER_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    thinking_text = reactive("")
    is_loading = reactive(True)
    is_expanded = reactive(False)

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block
        self._last_rendered_len = 0
        self._render_threshold = 40
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Static(classes="thinking-header"):
            yield Label(self.SPINNER_FRAMES[0], classes="spinner", id="spinner")
            yield Label("Generating response...", classes="thinking-label", id="status-label")
            yield Label("click to expand", classes="toggle-hint", id="toggle-hint")

        with VerticalScroll(classes="peek-window empty", id="peek-window"):
            yield Label("Waiting for response...", classes="empty-hint", id="empty-hint")
            yield Static("", classes="peek-content", id="peek-content")

    def on_mount(self):
        """Start the spinner animation."""
        self._spinner_timer = self.set_interval(0.08, self._animate_spinner)

    def _animate_spinner(self):
        """Animate the spinner."""
        if not self.is_loading:
            return

        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            spinner = self.query_one("#spinner", Label)
            spinner.update(self.SPINNER_FRAMES[self._spinner_index])
        except Exception:
            pass

    def watch_is_loading(self, loading: bool):
        """Update UI when loading state changes."""
        try:
            spinner = self.query_one("#spinner", Label)
            status = self.query_one("#status-label", Label)

            if loading:
                spinner.remove_class("complete")
                spinner.update(self.SPINNER_FRAMES[0])
                status.update("Generating response...")
            else:
                spinner.add_class("complete")
                spinner.update("✓")
                status.update("Response complete")
                if self._spinner_timer:
                    self._spinner_timer.stop()
        except Exception:
            pass

    def watch_is_expanded(self, expanded: bool):
        """Toggle between peek and expanded view."""
        try:
            peek = self.query_one("#peek-window", VerticalScroll)
            hint = self.query_one("#toggle-hint", Label)

            if expanded:
                peek.add_class("expanded")
                hint.update("click to collapse")
            else:
                peek.remove_class("expanded")
                hint.update("click to expand")
                # Scroll to bottom when collapsing
                peek.scroll_end(animate=False)
        except Exception:
            pass

    def watch_thinking_text(self, new_text: str):
        """Update the peek window with new content."""
        try:
            peek = self.query_one("#peek-window", VerticalScroll)
            empty_hint = self.query_one("#empty-hint", Label)

            # Remove empty state when we have content
            if new_text:
                if "empty" in peek.classes:
                    peek.remove_class("empty")
                    empty_hint.display = False

            # Throttle rendering for performance
            current_len = len(new_text)
            delta = current_len - self._last_rendered_len
            if delta < self._render_threshold and not new_text.endswith('\n'):
                return

            self._last_rendered_len = current_len
            content = self.query_one("#peek-content", Static)
            from rich.markdown import Markdown
            content.update(Markdown(new_text))

            # Auto-scroll to bottom in peek mode
            if not self.is_expanded:
                peek.scroll_end(animate=False)
        except Exception:
            pass

    def force_render(self):
        """Force a full render of current content."""
        try:
            self._last_rendered_len = len(self.thinking_text)
            content = self.query_one("#peek-content", Static)
            from rich.markdown import Markdown
            content.update(Markdown(self.thinking_text))
        except Exception:
            pass

    def on_click(self, event):
        """Handle clicks to toggle expand/collapse."""
        # Toggle if clicking header area (first row)
        if event.y <= 1:
            self.is_expanded = not self.is_expanded
            self.force_render()

    def stop_loading(self):
        """Call when generation is complete."""
        self.is_loading = False
