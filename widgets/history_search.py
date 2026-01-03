from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static


class HistorySearch(Static, can_focus=True):
    """Overlay widget for searching command history (Ctrl+R style)."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "select_prev", "Previous", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
    ]

    search_query: reactive[str] = reactive("")
    results: reactive[list[str]] = reactive([])
    selected_index: reactive[int] = reactive(0)

    class Selected(Message):
        """Sent when user selects a history item."""

        def __init__(self, command: str):
            self.command = command
            super().__init__()

    class Cancelled(Message):
        """Sent when user cancels search."""

        pass

    def compose(self) -> ComposeResult:
        # Results first (above), then input at bottom
        yield Vertical(id="search-results", classes="search-results")
        yield Input(
            placeholder="Type to search...", id="search-input", classes="search-input"
        )
        yield Label("↑↓ navigate • Enter select • Esc cancel", classes="search-header")

    def show(self):
        """Show the search widget and focus input."""
        self.add_class("visible")
        self.search_query = ""
        self.results = []
        self.selected_index = 0

        # Hide the main input container
        try:
            input_container = self.app.query_one("#input-container")
            input_container.display = False
        except Exception:
            pass

        try:
            input_widget = self.query_one("#search-input", Input)
            input_widget.value = ""
            input_widget.focus()
        except Exception:
            pass

    def hide(self):
        """Hide the search widget."""
        self.remove_class("visible")

        # Show the main input container and focus it
        try:
            input_container = self.app.query_one("#input-container")
            input_container.display = True
            self.app.query_one("#input").focus()
        except Exception:
            pass

        self.post_message(self.Cancelled())

    def on_input_changed(self, event: Input.Changed):
        """Update results when search query changes."""
        self.search_query = event.value
        self._update_results()

    def on_input_submitted(self, event: Input.Submitted):
        """Select current result on Enter."""
        event.stop()
        self._select_current()

    def action_select_prev(self):
        """Move selection up."""
        if self.results and self.selected_index > 0:
            self.selected_index -= 1
            self._render_results()

    def action_select_next(self):
        """Move selection down."""
        if self.results and self.selected_index < len(self.results) - 1:
            self.selected_index += 1
            self._render_results()

    def action_cancel(self):
        """Cancel search."""
        self.hide()

    def action_select(self):
        """Select current result."""
        self._select_current()

    def _update_results(self):
        """Fetch and display search results."""
        from config import Config

        query = self.search_query.strip()
        if not query:
            self.results = []
        else:
            storage = Config._get_storage()
            self.results = storage.search_history(query, limit=10)

        self.selected_index = 0
        self._render_results()

    def _render_results(self):
        """Render the results list."""
        try:
            container = self.query_one("#search-results", Vertical)
            container.remove_children()

            if not self.results:
                if self.search_query:
                    container.mount(Label("No matches found", classes="no-results"))
                return

            for i, cmd in enumerate(self.results):
                label = Label(cmd, classes="search-result")
                if i == self.selected_index:
                    label.add_class("selected")
                container.mount(label)
        except Exception:
            pass

    def _select_current(self):
        """Select the currently highlighted result."""
        if self.results and 0 <= self.selected_index < len(self.results):
            selected = self.results[self.selected_index]
            self.remove_class("visible")

            # Show the main input container
            try:
                input_container = self.app.query_one("#input-container")
                input_container.display = True
            except Exception:
                pass

            self.post_message(self.Selected(selected))
        else:
            self.hide()
