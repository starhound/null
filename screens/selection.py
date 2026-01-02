"""Selection list screens."""

from typing import Callable, Coroutine, Any, Optional
from textual.timer import Timer
from textual.reactive import reactive

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


class ModelListScreen(ModalScreen):
    """Screen to select an AI model with async loading support."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]
    SPINNER_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    is_loading = reactive(True)

    def __init__(
        self,
        models: Optional[dict[str, list[str]]] = None,
        fetch_func: Optional[Callable[[], Coroutine[Any, Any, dict[str, list[str]]]]] = None
    ):
        """Initialize model list screen.

        Args:
            models: Pre-fetched dict of models {provider: [models]}
            fetch_func: Async function to fetch models
        """
        super().__init__()
        self.items = models or {}
        self.fetch_func = fetch_func
        self._spinner_index = 0
        self._spinner_timer: Optional[Timer] = None
        self.is_loading = not bool(models)
        self._flattened_items = []  # Map index to (provider, model) or just model string

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label("Select a Model", id="model-title")
            yield Label("", id="loading-indicator", classes="loading-spinner")
            yield ListView(id="item_list")
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_mount(self):
        """Start loading models if needed."""
        if self.is_loading and self.fetch_func:
            self._start_spinner()
            self.run_worker(self._fetch_models())
        elif self.items:
            self._populate_list()

    def _start_spinner(self):
        """Start the loading spinner animation."""
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update(f"{self.SPINNER_FRAMES[0]} Loading models from all providers...")
            indicator.display = True
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
        except Exception:
            pass

    def _stop_spinner(self):
        """Stop the loading spinner."""
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.display = False
        except Exception:
            pass

    def _animate_spinner(self):
        """Animate the spinner frame."""
        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update(f"{self.SPINNER_FRAMES[self._spinner_index]} Loading models from all providers...")
        except Exception:
            pass

    async def _fetch_models(self):
        """Fetch models using the provided function."""
        try:
            if self.fetch_func:
                self.items = await self.fetch_func()
        except Exception as e:
            self.notify(f"Failed to fetch models: {e}", severity="error")
            self.items = {}
        finally:
            self.is_loading = False
            self._stop_spinner()
            self._populate_list()

    def _populate_list(self):
        """Populate the list view with models."""
        try:
            listview = self.query_one("#item_list", ListView)
            listview.clear()
            self._flattened_items = []

            if not self.items:
                listview.mount(ListItem(Label("No models found from configured providers")))
            else:
                for provider, models in self.items.items():
                    if not models:
                        continue
                    
                    # Provider Header
                    header = ListItem(Label(f"[{provider.upper()}]"), disabled=True)
                    header.add_class("list-header")
                    listview.mount(header)
                    self._flattened_items.append(None) # Header placeholder

                    # Models
                    for model in models:
                        item = ListItem(Label(f"  {model}"))
                        listview.mount(item)
                        # Store full info: (provider, model_name)
                        self._flattened_items.append((provider, model))

            # Focus the list
            listview.focus()
        except Exception:
            pass

    def on_list_view_selected(self, message: ListView.Selected):
        if self.is_loading:
            return
            
        index = self.query_one("#item_list", ListView).index
        
        # Map ListView index to our flattened items
        if index is not None and 0 <= index < len(self._flattened_items):
            selection = self._flattened_items[index]
            if selection:
                provider, model = selection
                self.dismiss((provider, model))
                return
        
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)

    def action_dismiss(self):
        self.dismiss(None)
