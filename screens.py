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
        height: 60%;
        background: $surface;
        border: solid $accent;
        padding: 1;
    }
    
    DataTable {
        height: 1fr;
    }
    """
    
    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Label("[bold]Available Commands[/bold]")
            yield DataTable()
            yield Button("Close", variant="primary", id="close_btn")

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
        width: 50%;
        height: 50%;
        background: $surface;
        border: solid $accent;
        layout: vertical;
    }
    
    ListView {
        height: 1fr;
        margin: 1;
        border: solid $surface-lighten-2;
    }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, title: str, items: list[str]):
        super().__init__()
        self.title = title
        self.items = items

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label(f"[bold]{self.title}[/bold]")
            if not self.items:
                yield Label("No items found.")
            else:
                yield ListView(*[ListItem(Label(m)) for m in self.items], id="item_list")
            yield Button("Cancel", variant="error", id="cancel_btn")

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
        width: 60%;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 1;
        layout: vertical;
    }
    
    .input-label {
        margin-top: 1;
        text-style: bold;
    }
    
    #buttons {
        layout: horizontal;
        align: center middle;
        margin-top: 1;
        height: 3;
    }
    
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, provider: str, current_config: dict):
        super().__init__()
        self.provider = provider
        self.current_config = current_config
        self.inputs = {}

    def compose(self) -> ComposeResult:
        with Container(id="config-container"):
            yield Label(f"[bold]Configure {self.provider.title()}[/bold]")
            
            # Dynamic fields based on provider
            if self.provider in ["openai", "xai", "azure", "lm_studio", "bedrock"]:
                yield Label("API Key:", classes="input-label")
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
                yield Label("Endpoint URL (Optional if default):", classes="input-label")
                default_url = "http://localhost:11434" if self.provider == "ollama" else ""
                if self.provider == "lm_studio": default_url = "http://localhost:1234/v1"
                
                inp = Input(
                    placeholder=f"Default: {default_url}" if default_url else "https://...", 
                    id="endpoint",
                    value=self.current_config.get("endpoint", default_url)
                )
                self.inputs["endpoint"] = inp
                yield inp
                
            if self.provider == "bedrock":
                yield Label("AWS Region:", classes="input-label")
                inp = Input(
                    placeholder="us-east-1", 
                    id="region",
                    value=self.current_config.get("region", "us-east-1")
                )
                self.inputs["region"] = inp
                yield inp
            
            # Removed "Default Model" field to simplify config. 
            # Users should use /model to select from available list after auth.
            
            with Container(id="buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            # Collect values
            result = {}
            for key, widget in self.inputs.items():
                result[key] = widget.value
            self.dismiss(result)
        else:
            self.dismiss(None)
