from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem
from textual.events import Click


class CommandItem(ListItem):
    """List item for command suggestions."""

    def __init__(self, label_text: str, value: str):
        super().__init__(Label(label_text))
        self.value = value


class CommandSuggester(Static):
    """Popup for command suggestions."""

    can_focus = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_index = 0

    def on_click(self, event: Click) -> None:
        """Handle clicks on suggester items."""
        # Find if we clicked on a CommandItem
        for i, widget in enumerate(self.query(CommandItem)):
            if widget.region.contains(event.x, event.y):
                self._selected_index = i
                self._update_highlight()
                self._apply_selection()
                event.stop()
                return

    def _update_highlight(self):
        """Update visual highlight on selected item."""
        items = list(self.query(CommandItem))
        for i, item in enumerate(items):
            if i == self._selected_index:
                item.add_class("--highlight")
            else:
                item.remove_class("--highlight")

    def _apply_selection(self):
        """Apply the current selection to the input."""
        try:
            input_ctrl = self.app.query_one("#input")
            complete = self.get_selected()
            if complete:
                parts = input_ctrl.text.split(" ")
                if len(parts) == 1:
                    input_ctrl.text = complete + " "
                else:
                    input_ctrl.text = parts[0] + " " + complete + " "
                self.display = False
                input_ctrl.move_cursor((len(input_ctrl.text), 0))
        except Exception:
            pass

    @property
    def commands_data(self):
        """Command definitions with dynamic provider list."""
        from ai.factory import AIFactory
        providers = AIFactory.list_providers()

        return {
            "/help": {"desc": "Show help screen", "args": []},
            "/config": {"desc": "Open settings", "args": []},
            "/settings": {"desc": "Open settings", "args": []},
            "/provider": {"desc": "Select AI provider", "args": providers},
            "/model": {"desc": "Select AI model", "args": []},
            "/theme": {"desc": "Change UI theme", "args": ["null-dark", "null-warm", "null-mono", "null-light", "dracula", "nord", "monokai"]},
            "/ai": {"desc": "Toggle AI Mode", "args": []},
            "/chat": {"desc": "Toggle AI Mode", "args": []},
            "/prompts": {"desc": "Manage system prompts", "args": ["list", "reload", "show", "dir"]},
            "/export": {"desc": "Export conversation", "args": ["md", "json"]},
            "/session": {"desc": "Manage sessions", "args": ["save", "load", "list", "new"]},
            "/mcp": {"desc": "Manage MCP servers", "args": ["list", "tools", "add", "edit", "remove", "enable", "disable", "reconnect"]},
            "/status": {"desc": "Show current status", "args": []},
            "/clear": {"desc": "Clear history", "args": []},
            "/compact": {"desc": "Summarize context", "args": []},
            "/quit": {"desc": "Exit application", "args": []}
        }

    def compose(self) -> ComposeResult:
        lv = ListView(id="suggestions")
        lv.can_focus = False
        yield lv

    def update_filter(self, text: str):
        if not text.startswith("/"):
            self.display = False
            return

        lv = self.query_one(ListView)
        lv.clear()

        parts = text.split(" ")
        base_cmd = parts[0]

        candidates = []

        if len(parts) > 1 and base_cmd in self.commands_data:
            # Args mode
            prefix = " ".join(parts[1:])
            args = self.commands_data[base_cmd]["args"]
            for arg in args:
                if arg.startswith(prefix):
                    candidates.append((arg, ""))
        else:
            # Command mode
            for cmd, data in self.commands_data.items():
                if cmd.startswith(base_cmd):
                    candidates.append((cmd, data["desc"]))

        if not candidates:
            self.display = False
            return

        self.display = True
        self._selected_index = 0

        for text_val, desc in candidates:
            label_str = f"{text_val:<15} {desc}" if desc else text_val
            lv.append(CommandItem(label_str, text_val))

        self._update_highlight()

    def select_next(self):
        """Move selection down."""
        items = list(self.query(CommandItem))
        if items and self._selected_index < len(items) - 1:
            self._selected_index += 1
            self._update_highlight()

    def select_prev(self):
        """Move selection up."""
        if self._selected_index > 0:
            self._selected_index -= 1
            self._update_highlight()

    def get_selected(self) -> str:
        """Get the currently selected command value."""
        items = list(self.query(CommandItem))
        if items and 0 <= self._selected_index < len(items):
            return items[self._selected_index].value
        return ""
