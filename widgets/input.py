from textual.widgets import TextArea
from textual.message import Message
from textual.binding import Binding


class InputController(TextArea):
    """
    Multi-line input widget with history and mode toggling.
    Supports Shift+Enter for newlines, Enter to submit.
    """

    DEFAULT_CSS = """
    InputController {
        height: auto;
        min-height: 1;
        max-height: 5;
        border: solid $accent;
        padding: 0 1;
    }

    InputController:focus {
        border: solid $primary;
    }

    InputController.ai-mode {
        border: solid $warning;
    }

    InputController.ai-mode:focus {
        border: solid $warning-lighten-1;
    }
    """

    BINDINGS = [
        Binding("enter", "submit", "Submit", priority=True),
        Binding("shift+enter", "newline", "New Line", priority=True),
    ]

    class Submitted(Message):
        """Sent when user submits input."""
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    class Toggled(Message):
        """Sent when input mode is toggled."""
        def __init__(self, mode: str):
            self.mode = mode
            super().__init__()

    def __init__(self, placeholder: str = "", **kwargs):
        # TextArea doesn't have placeholder, but we store it for reference
        super().__init__(**kwargs)
        self._placeholder = placeholder
        self.history: list[str] = []
        self.history_index: int = -1
        self.current_input: str = ""
        self.mode: str = "CLI"  # "CLI" or "AI"
        self.show_line_numbers = False
        self.tab_behavior = "indent"

    @property
    def value(self) -> str:
        """Compatibility property for Input-like API."""
        return self.text

    @value.setter
    def value(self, new_value: str):
        """Compatibility setter for Input-like API."""
        self.text = new_value

    @property
    def placeholder(self) -> str:
        return self._placeholder

    @placeholder.setter
    def placeholder(self, value: str):
        self._placeholder = value

    @property
    def is_ai_mode(self) -> bool:
        return self.mode == "AI"

    def action_submit(self):
        """Handle Enter key - submit input."""
        text = self.text.strip()
        if text:
            self.post_message(self.Submitted(text))

    def action_newline(self):
        """Handle Shift+Enter - insert newline."""
        self.insert("\n")

    def add_to_history(self, command: str):
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
        self.history_index = -1

    def action_history_up(self):
        if not self.history:
            return

        if self.history_index == -1:
            self.current_input = self.text
            self.history_index = len(self.history) - 1
        elif self.history_index > 0:
            self.history_index -= 1

        self.text = self.history[self.history_index]
        # Move cursor to end
        self.move_cursor((len(self.text), 0))

    def action_history_down(self):
        if self.history_index == -1:
            return

        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.text = self.history[self.history_index]
        else:
            self.history_index = -1
            self.text = self.current_input

        # Move cursor to end
        self.move_cursor((len(self.text), 0))

    def toggle_mode(self):
        if self.mode == "CLI":
            self.mode = "AI"
            self.add_class("ai-mode")
            self._placeholder = "Ask AI..."
        else:
            self.mode = "CLI"
            self.remove_class("ai-mode")
            self._placeholder = "Type a command..."
        self.post_message(self.Toggled(self.mode))

    def _on_cursor_first_line(self) -> bool:
        """Check if cursor is on first line."""
        row, _ = self.cursor_location
        return row == 0

    def _on_cursor_last_line(self) -> bool:
        """Check if cursor is on last line."""
        row, _ = self.cursor_location
        return row >= self.document.line_count - 1

    async def on_key(self, event):
        # Handle navigation keys manually to support both Suggester and History
        if event.key == "up":
            if self.text.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    suggester.select_prev()
                    event.stop()
                    return
            # Only navigate history if on first line
            if self._on_cursor_first_line():
                self.action_history_up()
                event.stop()

        elif event.key == "down":
            if self.text.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    suggester.select_next()
                    event.stop()
                    return
            # Only navigate history if on last line
            if self._on_cursor_last_line():
                self.action_history_down()
                event.stop()

        elif event.key == "tab":
            if self.text.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    complete = suggester.get_selected()
                    if complete:
                        parts = self.text.split(" ")
                        if len(parts) == 1:
                            self.text = complete + " "
                        else:
                            self.text = " ".join(parts[:-1]) + " " + complete
                        suggester.display = False
                        self.move_cursor((len(self.text), 0))
                        event.stop()
                        return

        elif event.key == "escape":
            suggester = self.app.query_one("CommandSuggester")
            if suggester.display:
                suggester.display = False
                event.stop()
