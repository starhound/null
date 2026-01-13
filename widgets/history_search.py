from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static


class HistorySearch(Static, can_focus=True):
    """Overlay widget for searching command history (Ctrl+R style).

    Features:
    - Live search as you type
    - Up/Down navigation through results
    - Match highlighting
    - Shows result count
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("up", "select_prev", "Previous", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("ctrl+r", "select_prev", "Previous", show=False),  # Bash-like cycling
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
        yield Label("", id="search-status", classes="search-status")
        yield Vertical(id="search-results", classes="search-results")
        yield Input(
            placeholder="(reverse-i-search): type to filter...", id="search-input", classes="search-input"
        )
        yield Label("↑↓/Ctrl+R navigate | Enter select | Esc cancel", classes="search-header")

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

        # Load initial history (show recent commands before typing)
        self._load_recent_history()

        try:
            input_widget = self.query_one("#search-input", Input)
            input_widget.value = ""
            input_widget.focus()
        except Exception:
            pass

    def _load_recent_history(self):
        """Load recent history to show before user starts typing."""
        from config import Config

        storage = Config._get_storage()
        # Show last 10 commands when opened
        self.results = storage.get_last_history(limit=10)[::-1]  # Reverse for newest first
        self._update_status()
        self._render_results()

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
        """Move selection up (or cycle through results with Ctrl+R)."""
        if self.results:
            if self.selected_index > 0:
                self.selected_index -= 1
            else:
                # Wrap to bottom
                self.selected_index = len(self.results) - 1
            self._render_results()

    def action_select_next(self):
        """Move selection down."""
        if self.results:
            if self.selected_index < len(self.results) - 1:
                self.selected_index += 1
            else:
                # Wrap to top
                self.selected_index = 0
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
            # Show recent history when query is empty
            self._load_recent_history()
            return

        storage = Config._get_storage()
        self.results = storage.search_history(query, limit=15)

        self.selected_index = 0
        self._update_status()
        self._render_results()

    def _update_status(self):
        """Update the status line showing match count."""
        try:
            status = self.query_one("#search-status", Label)
            if self.search_query:
                if self.results:
                    status.update(f"[{len(self.results)} matches for '{self.search_query}']")
                else:
                    status.update(f"[No matches for '{self.search_query}']")
            else:
                from config import Config
                count = Config._get_storage().get_history_count()
                status.update(f"[{count} commands in history]")
        except Exception:
            pass

    def _render_results(self):
        """Render the results list with highlighting."""
        try:
            container = self.query_one("#search-results", Vertical)
            container.remove_children()

            if not self.results:
                if self.search_query:
                    container.mount(Label("No matches found", classes="no-results"))
                return

            for i, cmd in enumerate(self.results):
                # Highlight matching portion if there's a query
                display_cmd = cmd
                if self.search_query:
                    # Simple highlight by wrapping match in markup
                    query_lower = self.search_query.lower()
                    cmd_lower = cmd.lower()
                    idx = cmd_lower.find(query_lower)
                    if idx >= 0:
                        before = cmd[:idx]
                        match = cmd[idx:idx + len(self.search_query)]
                        after = cmd[idx + len(self.search_query):]
                        display_cmd = f"{before}[bold cyan]{match}[/bold cyan]{after}"

                label = Label(display_cmd, classes="search-result", markup=True)
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
