from textual.screen import ModalScreen
from textual.widgets import DataTable, Button, Label, ListView, ListItem
from textual.containers import Container, Grid, Vertical
from textual.app import ComposeResult
from textual.binding import Binding

class HelpScreen(ModalScreen):
    """Screen to show available commands."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        background: $background 80%;
    }

    #help-container {
        width: 60%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }

    #help-container > Label {
        margin-bottom: 1;
        text-style: bold;
        color: $primary;
    }

    DataTable {
        height: auto;
        max-height: 20;
        margin-bottom: 1;
    }

    #close_btn {
        width: 100%;
        height: 1;
        min-width: 8;
        border: none;
        background: $surface-lighten-2;
        color: $text;
        margin-top: 1;
    }

    #close_btn:hover {
        background: $primary;
        color: $text;
    }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Label("Help - Available Commands")
            yield DataTable()
            yield Button("Close [Esc]", variant="default", id="close_btn")

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("Command", "Description")
        table.add_rows([
            ("/help", "Show this help screen"),
            ("/provider", "Select and configure AI provider"),
            ("/theme <name>", "Change the UI theme (e.g. monokai, dracula)"),
            ("/model", "List available AI models"),
            ("/model <provider> <name>", "Set AI provider and model"),
            ("/quit", "Exit the application"),
        ])
        table.cursor_type = "row"

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close_btn":
            self.dismiss()
    
    def action_dismiss(self):
        self.dismiss()

class SelectionListScreen(ModalScreen):
    """Generic screen to select an item from a list."""

    DEFAULT_CSS = """
    SelectionListScreen {
        align: center middle;
        background: $background 80%;
    }

    #selection-container {
        width: 40%;
        min-width: 30;
        height: auto;
        max-height: 60%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
        layout: vertical;
    }

    #selection-container > Label {
        margin-bottom: 1;
        text-style: bold;
        color: $primary;
    }

    ListView {
        height: auto;
        max-height: 15;
        margin: 0;
        padding: 0;
        background: $surface-darken-1;
    }

    ListItem {
        padding: 0 1;
        height: 1;
    }

    ListItem:hover {
        background: $surface-lighten-1;
    }

    #cancel_btn {
        width: 100%;
        height: 1;
        border: none;
        background: $surface-lighten-2;
        color: $text-muted;
        margin-top: 1;
    }

    #cancel_btn:hover {
        background: $error;
        color: $text;
    }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, title: str, items: list[str]):
        super().__init__()
        self.title = title
        self.items = items

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label(self.title)
            if not self.items:
                yield Label("No items found.", classes="empty-msg")
            else:
                yield ListView(*[ListItem(Label(m)) for m in self.items], id="item_list")
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_list_view_selected(self, message: ListView.Selected):
        # Robustly get selected item value via index
        # message.item is the selected ListItem
        # We can find its index in the list view to map back to self.items
        index = self.query_one(ListView).index
        if index is not None and 0 <= index < len(self.items):
             self.dismiss(str(self.items[index]))
        else:
             self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)
    
    def action_dismiss(self):
        self.dismiss(None)

class ModelListScreen(SelectionListScreen):
    def __init__(self, models: list[str]):
        super().__init__("Select a Model", models)

from textual.widgets import Input

class ProviderConfigScreen(ModalScreen):
    """Screen to configure a provider."""

    DEFAULT_CSS = """
    ProviderConfigScreen {
        align: center middle;
        background: $background 80%;
    }

    #config-container {
        width: 50%;
        min-width: 40;
        height: auto;
        background: $surface;
        border: round $primary;
        padding: 1 2;
        layout: vertical;
    }

    #config-container > Label:first-child {
        margin-bottom: 1;
        text-style: bold;
        color: $primary;
    }

    .input-label {
        margin-top: 1;
        margin-bottom: 0;
        color: $text-muted;
    }

    Input {
        margin-bottom: 0;
    }

    #buttons {
        layout: horizontal;
        align: center middle;
        margin-top: 1;
        height: 1;
        width: 100%;
    }

    #save {
        width: 1fr;
        height: 1;
        border: none;
        background: $success;
        color: $text;
        margin-right: 1;
    }

    #save:hover {
        background: $success-lighten-1;
    }

    #cancel {
        width: 1fr;
        height: 1;
        border: none;
        background: $surface-lighten-2;
        color: $text-muted;
    }

    #cancel:hover {
        background: $error;
        color: $text;
    }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, provider: str, current_config: dict):
        super().__init__()
        self.provider = provider
        self.current_config = current_config
        self.inputs = {}

    def compose(self) -> ComposeResult:
        with Container(id="config-container"):
            yield Label(f"Configure {self.provider.title()}")

            # Dynamic fields based on provider
            if self.provider in ["openai", "xai", "azure", "lm_studio", "bedrock"]:
                yield Label("API Key", classes="input-label")
                inp = Input(
                    placeholder="sk-...",
                    password=True,
                    id="api_key",
                    value=self.current_config.get("api_key", "")
                )
                self.inputs["api_key"] = inp
                yield inp

            # Custom Endpoint providers
            if self.provider in ["ollama", "lm_studio", "azure"]:
                yield Label("Endpoint URL", classes="input-label")
                default_url = "http://localhost:11434" if self.provider == "ollama" else ""
                if self.provider == "lm_studio":
                    default_url = "http://localhost:1234/v1"

                inp = Input(
                    placeholder=default_url if default_url else "https://...",
                    id="endpoint",
                    value=self.current_config.get("endpoint", default_url)
                )
                self.inputs["endpoint"] = inp
                yield inp

            if self.provider == "bedrock":
                yield Label("AWS Region", classes="input-label")
                inp = Input(
                    placeholder="us-east-1",
                    id="region",
                    value=self.current_config.get("region", "us-east-1")
                )
                self.inputs["region"] = inp
                yield inp

            with Container(id="buttons"):
                yield Button("Save", variant="default", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            # Collect values
            result = {}
            for key, widget in self.inputs.items():
                result[key] = widget.value
            self.dismiss(result)
        else:
            self.dismiss(None)

    def action_dismiss(self):
        self.dismiss(None)
