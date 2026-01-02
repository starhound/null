"""Selection list screens."""

from typing import Callable, Coroutine, Any, Optional, Dict, List, Tuple
from textual.timer import Timer
from textual.reactive import reactive
from textual.widgets import Static

from .base import ModalScreen, ComposeResult, Binding, Container, Label, ListView, ListItem, Button


class ThemeSelectionScreen(ModalScreen):
    """Screen to select a theme with live preview on highlight."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, title: str, items: list[str]):
        super().__init__()
        self.title = title
        self.items = items
        self._original_theme: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label(self.title)
            if not self.items:
                yield Label("No themes found.", classes="empty-msg")
            else:
                yield ListView(*[ListItem(Label(m)) for m in self.items], id="item_list")
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_mount(self):
        """Store the original theme when screen opens."""
        self._original_theme = self.app.theme

    def on_list_view_highlighted(self, message: ListView.Highlighted):
        """Preview theme when item is highlighted."""
        if message.item is None:
            return

        listview = self.query_one("#item_list", ListView)
        index = listview.index

        if index is not None and 0 <= index < len(self.items):
            theme_name = self.items[index]
            # Apply theme for preview (don't save to config)
            try:
                self.app.theme = theme_name
            except Exception:
                pass

    def on_list_view_selected(self, message: ListView.Selected):
        """Apply theme permanently when selected."""
        index = self.query_one("#item_list", ListView).index
        if index is not None and 0 <= index < len(self.items):
            self.dismiss(str(self.items[index]))
        else:
            # Restore original on invalid selection
            if self._original_theme:
                self.app.theme = self._original_theme
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed):
        """Restore original theme on cancel."""
        if self._original_theme:
            self.app.theme = self._original_theme
        self.dismiss(None)

    def action_dismiss(self):
        """Restore original theme on escape."""
        if self._original_theme:
            self.app.theme = self._original_theme
        self.dismiss(None)


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
    """Screen to select an AI model with streaming async loading."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]
    SPINNER_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    is_loading = reactive(True)

    def __init__(self, fetch_func: Optional[Callable] = None):
        """Initialize model list screen.

        Args:
            fetch_func: The AIManager instance to fetch models from
        """
        super().__init__()
        self.ai_manager = fetch_func  # Actually receives the manager's method
        self._spinner_index = 0
        self._spinner_timer: Optional[Timer] = None
        self._flattened_items: List[Optional[tuple]] = []
        self._models_by_provider: Dict[str, List[str]] = {}
        self._completed_providers = 0
        self._total_providers = 0

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label("Select a Model", id="model-title")
            yield Label("", id="loading-indicator")
            yield ListView(id="item_list")
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_mount(self):
        """Start loading models after screen is rendered."""
        self._start_spinner()
        # Use set_timer to ensure screen fully renders first
        self.set_timer(0.1, self._start_loading)

    def _start_loading(self):
        """Start the model loading worker in a thread."""
        # Use thread=True to run in a separate thread, not the event loop
        self.run_worker(self._fetch_models_in_thread, thread=True)

    def _start_spinner(self):
        """Start the loading spinner animation."""
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update(f"{self.SPINNER_FRAMES[0]} Checking providers...")
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
        except Exception:
            pass

    def _stop_spinner(self):
        """Stop the spinner."""
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None

    def _animate_spinner(self):
        """Animate the spinner frame."""
        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            indicator = self.query_one("#loading-indicator", Label)
            if self._total_providers > 0:
                indicator.update(
                    f"{self.SPINNER_FRAMES[self._spinner_index]} "
                    f"Loading models ({self._completed_providers}/{self._total_providers} providers)..."
                )
            else:
                indicator.update(f"{self.SPINNER_FRAMES[self._spinner_index]} Checking providers...")
        except Exception:
            pass

    def _fetch_models_in_thread(self) -> Tuple[Dict[str, List[str]], int]:
        """Synchronous model fetching - runs in a separate thread via run_worker(thread=True).

        Returns: (models_by_provider dict, total_provider_count)
        """
        import asyncio

        try:
            # Get reference to app's ai_manager
            if not hasattr(self.app, 'ai_manager'):
                return {}, 0

            manager = self.app.ai_manager

            # Get usable providers (this does sync SQLite calls)
            usable = manager.get_usable_providers()
            if not usable:
                return {}, 0

            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Run the async fetch in this thread's event loop
                result = loop.run_until_complete(manager.list_all_models())
                return result, len(usable)
            finally:
                loop.close()

        except Exception as e:
            # Log error but don't crash
            return {}, 0

    def on_worker_state_changed(self, event) -> None:
        """Handle worker completion - update UI with results."""
        from textual.worker import WorkerState

        # Only handle model fetch workers (name contains our method name)
        if "_fetch_models" not in str(event.worker.name):
            return

        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if result and isinstance(result, tuple) and len(result) == 2:
                self._models_by_provider, self._total_providers = result

                if not self._models_by_provider:
                    self._stop_spinner()
                    self.is_loading = False
                    self._show_no_providers()
                    return

                # Update UI with results
                self._update_list()
                self._stop_spinner()
                self.is_loading = False
                self._finalize_list()
            else:
                self._stop_spinner()
                self.is_loading = False
                self._show_no_providers()

        elif event.state == WorkerState.ERROR:
            self._stop_spinner()
            self.is_loading = False
            self._show_error(str(event.worker.error) if event.worker.error else "Unknown error")

        elif event.state == WorkerState.CANCELLED:
            self._stop_spinner()
            self.is_loading = False

    def _update_list(self):
        """Update the list view with current models."""
        try:
            listview = self.query_one("#item_list", ListView)
            listview.clear()
            self._flattened_items = []

            # Sort providers: active first, then alphabetically
            from config import Config
            active_provider = Config.get("ai.provider")

            sorted_providers = sorted(
                self._models_by_provider.keys(),
                key=lambda p: (0 if p == active_provider else 1, p)
            )

            for provider in sorted_providers:
                models = self._models_by_provider[provider]
                if not models:
                    continue

                # Provider header with model count
                header_text = f"[{provider.upper()}] ({len(models)} models)"
                header = ListItem(Label(header_text), disabled=True)
                header.add_class("list-header")
                listview.mount(header)
                self._flattened_items.append(None)

                # Models (limit display for very long lists)
                display_models = models[:50]  # Show first 50
                for model in display_models:
                    item = ListItem(Label(f"  {model}"))
                    listview.mount(item)
                    self._flattened_items.append((provider, model))

                if len(models) > 50:
                    more = ListItem(Label(f"  ... and {len(models) - 50} more"), disabled=True)
                    listview.mount(more)
                    self._flattened_items.append(None)

        except Exception:
            pass

    def _finalize_list(self):
        """Finalize the list after loading completes."""
        try:
            indicator = self.query_one("#loading-indicator", Label)

            if not self._models_by_provider:
                indicator.update("No models found from any provider")
                indicator.add_class("error")
            else:
                total_models = sum(len(m) for m in self._models_by_provider.values())
                provider_count = len(self._models_by_provider)
                indicator.update(f"✓ Found {total_models} models from {provider_count} provider(s)")
                indicator.add_class("success")

            # Focus the list
            listview = self.query_one("#item_list", ListView)
            listview.focus()

        except Exception:
            pass

    def _show_no_providers(self):
        """Show message when no providers are configured."""
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update("No providers configured")
            indicator.add_class("error")

            listview = self.query_one("#item_list", ListView)
            listview.clear()
            listview.mount(ListItem(Label("No providers configured. Use F4 to add one.")))
            listview.mount(ListItem(Label("Local: ollama, lm_studio (no API key needed)")))
            listview.mount(ListItem(Label("Cloud: openai, anthropic, nvidia, groq...")))
        except Exception:
            pass

    def _show_error(self, message: str):
        """Show error message."""
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update(f"✗ Error: {message}")
            indicator.add_class("error")
        except Exception:
            pass

    def on_list_view_selected(self, message: ListView.Selected):
        if self.is_loading:
            return

        index = self.query_one("#item_list", ListView).index

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
