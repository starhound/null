from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem


class CommandItem(ListItem):
    """List item for command suggestions."""

    def __init__(self, label_text: str, value: str):
        super().__init__(Label(label_text))
        self.value = value


class CommandSuggester(Static):
    """Popup for command suggestions."""

    DEFAULT_CSS = """
    CommandSuggester {
        layer: overlay;
        dock: bottom;
        margin-bottom: 4;
        margin-left: 1;
        margin-right: 1;
        width: auto;
        max-width: 50;
        height: auto;
        max-height: 12;
        background: $surface;
        border: round $accent;
        display: none;
        padding: 0;
    }

    ListView {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0;
        background: transparent;
    }

    ListItem {
        padding: 0 1;
        height: 1;
    }

    ListItem:hover {
        background: $surface-lighten-1;
    }

    ListView > ListItem.-highlight {
        background: $primary 30%;
    }
    """

    can_focus = False

    commands_data = {
        "/help": {"desc": "Show help screen", "args": []},
        "/provider": {"desc": "Select AI provider", "args": ["ollama", "openai", "lm_studio", "azure", "bedrock", "xai"]},
        "/model": {"desc": "Select AI model", "args": []},
        "/theme": {"desc": "Change UI theme", "args": ["monokai", "dracula", "nord", "solarized-light", "solarized-dark"]},
        "/ai": {"desc": "Toggle AI Mode", "args": []},
        "/chat": {"desc": "Toggle AI Mode", "args": []},
        "/prompts": {"desc": "Select System Persona", "args": ["default", "pirate", "concise", "agent"]},
        "/clear": {"desc": "Clear history", "args": []},
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

        for text_val, desc in candidates:
            label_str = f"{text_val:<15} {desc}" if desc else text_val
            lv.append(CommandItem(label_str, text_val))

        if len(lv.children) > 0:
            lv.index = 0

    def select_next(self):
        self.query_one(ListView).action_cursor_down()

    def select_prev(self):
        self.query_one(ListView).action_cursor_up()

    def get_selected(self) -> str:
        lv = self.query_one(ListView)
        if lv.index is not None and 0 <= lv.index < len(lv.children):
            item = lv.children[lv.index]
            if isinstance(item, CommandItem):
                return item.value
        return ""
