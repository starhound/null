import re
from pathlib import Path

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
        self.cmd_history: list[str] = []
        self.cmd_history_index: int = -1
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
        if command and (not self.cmd_history or self.cmd_history[-1] != command):
            self.cmd_history.append(command)
        self.cmd_history_index = -1

    def action_history_up(self):
        if not self.cmd_history:
            return

        if self.cmd_history_index == -1:
            self.current_input = self.text
            self.cmd_history_index = len(self.cmd_history) - 1
        elif self.cmd_history_index > 0:
            self.cmd_history_index -= 1

        self.text = self.cmd_history[self.cmd_history_index]
        # Move cursor to end
        self.move_cursor((len(self.text), 0))

    def action_history_down(self):
        if self.cmd_history_index == -1:
            return

        if self.cmd_history_index < len(self.cmd_history) - 1:
            self.cmd_history_index += 1
            self.text = self.cmd_history[self.cmd_history_index]
        else:
            self.cmd_history_index = -1
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

    def _get_current_word(self) -> str:
        """Get the word at the current cursor position."""
        text = self.text
        words = text.split()
        if not words:
            return ""
        return words[-1]

    def _is_path_context(self) -> bool:
        """Check if current word looks like a path."""
        last_word = self._get_current_word()
        if not last_word:
            return False
        # Detect: /path, ./path, ../path, ~/path
        return bool(re.match(r'^[~./]|^\.\./', last_word))

    def _get_path_completions(self, partial: str) -> list[str]:
        """Get filesystem completions for partial path."""
        try:
            # Handle home directory
            if partial.startswith("~"):
                base = Path.home()
                if len(partial) > 1 and partial[1] == "/":
                    partial = partial[2:]
                else:
                    partial = partial[1:]
                full_path = base / partial if partial else base
            elif partial.startswith("/"):
                base = Path("/")
                partial = partial[1:]
                full_path = base / partial if partial else base
            else:
                base = Path.cwd()
                full_path = base / partial if partial else base

            # Get parent and pattern
            if full_path.exists() and full_path.is_dir():
                parent = full_path
                pattern = "*"
            else:
                parent = full_path.parent
                pattern = full_path.name + "*"

            if not parent.exists():
                return []

            matches = []
            for p in parent.glob(pattern):
                # Get relative path from current dir or show full if needed
                try:
                    if partial.startswith("~"):
                        rel = "~/" + str(p.relative_to(Path.home()))
                    elif partial.startswith("/"):
                        rel = str(p)
                    else:
                        rel = str(p.relative_to(Path.cwd()))
                except ValueError:
                    rel = str(p)

                if p.is_dir():
                    rel += "/"
                matches.append(rel)

            return sorted(matches)[:10]
        except Exception:
            return []

    def _complete_path(self, completions: list[str]):
        """Complete the current path with the given completion."""
        if not completions:
            return

        text = self.text
        words = text.split()

        if len(words) == 0:
            return

        if len(completions) == 1:
            # Single match - complete it
            words[-1] = completions[0]
            self.text = " ".join(words)
            self.move_cursor((len(self.text), 0))
        else:
            # Multiple matches - find common prefix
            common = completions[0]
            for c in completions[1:]:
                while not c.startswith(common) and common:
                    common = common[:-1]
            if common and len(common) > len(words[-1]):
                words[-1] = common
                self.text = " ".join(words)
                self.move_cursor((len(self.text), 0))

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
            # First check slash commands
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
            # Then check path completion (only in CLI mode)
            elif not self.is_ai_mode and self._is_path_context():
                partial = self._get_current_word()
                completions = self._get_path_completions(partial)
                if completions:
                    self._complete_path(completions)
                    event.stop()
                    return

        elif event.key == "escape":
            suggester = self.app.query_one("CommandSuggester")
            if suggester.display:
                suggester.display = False
                event.stop()
