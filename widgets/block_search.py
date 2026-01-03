"""Block content search widget (Ctrl+F)."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static


class BlockSearch(Static, can_focus=True):
    """Overlay widget for searching within block content."""

    BINDINGS = [
        Binding("up", "select_prev", "Previous", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("f3", "select_next", "Next", show=False),
        Binding("shift+f3", "select_prev", "Previous", show=False),
    ]

    search_query = reactive("")
    results = reactive([])
    selected_index = reactive(0)

    class Selected(Message):
        """Sent when user selects a search result."""

        def __init__(self, block_id: str, match_text: str):
            self.block_id = block_id
            self.match_text = match_text
            super().__init__()

    class Cancelled(Message):
        """Sent when user cancels search."""

        pass

    def compose(self) -> ComposeResult:
        yield Vertical(id="block-search-results", classes="search-results")
        yield Input(
            placeholder="Search blocks...",
            id="block-search-input",
            classes="search-input",
        )
        yield Label(
            "↑↓ navigate • Enter jump to block • Esc cancel", classes="search-header"
        )

    def show(self):
        """Show the search widget and focus input."""
        self.add_class("visible")
        self.search_query = ""
        self.results = []
        self.selected_index = 0

        try:
            input_widget = self.query_one("#block-search-input", Input)
            input_widget.value = ""
            input_widget.focus()
        except Exception:
            pass

    def hide(self):
        """Hide the search widget."""
        self.remove_class("visible")
        # Clear any highlights
        self._clear_highlights()

        try:
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
            self._scroll_to_current()

    def action_select_next(self):
        """Move selection down."""
        if self.results and self.selected_index < len(self.results) - 1:
            self.selected_index += 1
            self._render_results()
            self._scroll_to_current()

    def action_cancel(self):
        """Cancel search."""
        self.hide()

    def action_select(self):
        """Select current result."""
        self._select_current()

    def _update_results(self):
        """Search through blocks and display results."""
        query = self.search_query.strip().lower()

        if not query:
            self.results = []
            self._clear_highlights()
        else:
            self.results = self._search_blocks(query)
            self._highlight_matches(query)

        self.selected_index = 0
        self._render_results()

        if self.results:
            self._scroll_to_current()

    def _search_blocks(self, query: str) -> list:
        """Search through all blocks for matching text."""
        results = []

        try:
            blocks = getattr(self.app, "blocks", [])

            for block in blocks:
                matches = []

                # Search in input
                if block.content_input and query in block.content_input.lower():
                    matches.append(("input", block.content_input))

                # Search in output
                if block.content_output and query in block.content_output.lower():
                    # Find the specific lines that match
                    for line in block.content_output.split("\n"):
                        if query in line.lower():
                            matches.append(("output", line.strip()[:100]))

                for match_type, match_text in matches:
                    results.append(
                        {
                            "block_id": block.id,
                            "type": match_type,
                            "text": match_text,
                            "block_type": block.type.value
                            if hasattr(block.type, "value")
                            else str(block.type),
                        }
                    )

        except Exception:
            pass

        return results[:50]  # Limit results

    def _render_results(self):
        """Render the results list."""
        try:
            container = self.query_one("#block-search-results", Vertical)
            container.remove_children()

            if not self.results:
                if self.search_query:
                    container.mount(Label("No matches found", classes="no-results"))
                return

            for i, result in enumerate(self.results[:10]):  # Show top 10
                prefix = ">" if result["type"] == "input" else "<"
                text = (
                    result["text"][:60] + "..."
                    if len(result["text"]) > 60
                    else result["text"]
                )
                display = f"{prefix} {text}"

                label = Label(display, classes="search-result")
                if i == self.selected_index:
                    label.add_class("selected")
                container.mount(label)

            if len(self.results) > 10:
                container.mount(
                    Label(
                        f"... and {len(self.results) - 10} more", classes="no-results"
                    )
                )

        except Exception:
            pass

    def _scroll_to_current(self):
        """Scroll the history viewport to show the current match."""
        if not self.results or self.selected_index >= len(self.results):
            return

        try:
            result = self.results[self.selected_index]
            block_id = result["block_id"]

            # Find the block widget
            from widgets.block import BaseBlockWidget

            history = self.app.query_one("#history")

            for widget in history.query(BaseBlockWidget):
                if widget.block.id == block_id:
                    widget.scroll_visible()
                    widget.add_class("search-highlight")
                    break

        except Exception:
            pass

    def _highlight_matches(self, query: str):
        """Highlight matching blocks."""
        if not self.results:
            return

        try:
            from widgets.block import BaseBlockWidget

            history = self.app.query_one("#history")

            # Get unique block IDs that have matches
            matching_ids = {r["block_id"] for r in self.results}

            for widget in history.query(BaseBlockWidget):
                if widget.block.id in matching_ids:
                    widget.add_class("search-match")
                else:
                    widget.remove_class("search-match")

        except Exception:
            pass

    def _clear_highlights(self):
        """Clear all search highlights."""
        try:
            from widgets.block import BaseBlockWidget

            history = self.app.query_one("#history")

            for widget in history.query(BaseBlockWidget):
                widget.remove_class("search-match")
                widget.remove_class("search-highlight")

        except Exception:
            pass

    def _select_current(self):
        """Select the currently highlighted result and jump to it."""
        if self.results and 0 <= self.selected_index < len(self.results):
            result = self.results[self.selected_index]
            self._scroll_to_current()
            # Keep search open to allow F3 navigation
        else:
            self.hide()
