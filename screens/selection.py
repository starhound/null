"""Selection list screens."""

from .base import ModalScreen, ComposeResult, Binding, Container, Label, ListView, ListItem, Button


class SelectionListScreen(ModalScreen):
    """Generic screen to select an item from a list."""

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
    """Screen to select an AI model."""

    def __init__(self, models: list[str]):
        super().__init__("Select a Model", models)
