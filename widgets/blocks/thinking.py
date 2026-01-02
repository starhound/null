from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static, Label
from textual.reactive import reactive
from textual.timer import Timer

from models import BlockState


class ThinkingWidget(Static):
    """Animated widget for AI response with peek preview and expand toggle."""

    SPINNER_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    thinking_text = reactive("")
    is_loading = reactive(True)
    is_expanded = reactive(False)

    # Common reasoning tags used by models (DeepSeek-R1, QwQ, etc.)
    REASONING_PATTERNS = ("<think>", "<thinking>", "<reasoning>", "<thought>")

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block
        self._last_rendered_len = 0
        self._render_threshold = 40
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None
        self._detected_reasoning = False
        # Initialize loading state from block
        self.is_loading = block.is_running
        # Initialize content if block has output
        if block.content_output:
            self.thinking_text = block.content_output
            self._check_for_reasoning(block.content_output)

    def _check_for_reasoning(self, text: str) -> bool:
        """Detect if output contains reasoning tags."""
        if self._detected_reasoning:
            return True
        text_lower = text.lower()
        for pattern in self.REASONING_PATTERNS:
            if pattern in text_lower:
                self._detected_reasoning = True
                self._update_label_for_reasoning()
                return True
        return False

    def _update_label_for_reasoning(self):
        """Update the status label when reasoning is detected."""
        try:
            status = self.query_one("#status-label", Label)
            if self.is_loading:
                status.update("Thinking...")
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        header_classes = "thinking-header loading" if self.is_loading else "thinking-header"
        with Static(classes=header_classes, id="thinking-header"):
            yield Label(self.SPINNER_FRAMES[0], classes="spinner", id="spinner")
            yield Label("Generating...", classes="thinking-label", id="status-label")
            yield Label("expand", classes="toggle-hint", id="toggle-hint")

        with VerticalScroll(classes="peek-window empty", id="peek-window"):
            yield Static("", classes="peek-content", id="peek-content")

    def on_mount(self):
        """Start the spinner animation if loading."""
        if self.is_loading:
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
            self._show_header(True)
        else:
            self._show_header(False)
            if self.thinking_text:
                self.call_later(self._init_complete_state)

    def _show_header(self, show: bool):
        """Show or hide the thinking header."""
        try:
            header = self.query_one("#thinking-header", Static)
            if show:
                header.add_class("loading")
            else:
                header.remove_class("loading")
        except Exception:
            pass

    def _init_complete_state(self):
        """Initialize UI for completed state."""
        try:
            spinner = self.query_one("#spinner", Label)
            status = self.query_one("#status-label", Label)
            spinner.add_class("complete")
            spinner.update("✓")
            status.update("Response complete")
            # Force render the content
            if self.thinking_text:
                self.force_render()
        except Exception:
            pass

    def start_loading(self):
        """Start the loading animation (for retry)."""
        self.is_loading = True
        if not self._spinner_timer:
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
                label = "Thinking..." if self._detected_reasoning else "Generating..."
                status.update(label)
            else:
                spinner.add_class("complete")
                spinner.update("✓")
                label = "Thought complete" if self._detected_reasoning else "Response complete"
                status.update(label)
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
                hint.update("collapse")
            else:
                peek.remove_class("expanded")
                hint.update("expand")
                peek.scroll_end(animate=False)
        except Exception:
            pass

    def watch_thinking_text(self, new_text: str):
        """Update the peek window with new content."""
        try:
            peek = self.query_one("#peek-window", VerticalScroll)

            # Remove empty state when we have content
            if new_text:
                if "empty" in peek.classes:
                    peek.remove_class("empty")
                # Check for reasoning patterns in new content
                self._check_for_reasoning(new_text)

            # Throttle rendering for performance
            current_len = len(new_text)
            delta = current_len - self._last_rendered_len
            if delta < self._render_threshold and not new_text.endswith('\n'):
                return

            self._last_rendered_len = current_len
            content = self.query_one("#peek-content", Static)
            from rich.markdown import Markdown
            content.update(Markdown(new_text, code_theme="monokai"))

            # Auto-scroll to bottom to follow content
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
            content.update(Markdown(self.thinking_text, code_theme="monokai"))
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
