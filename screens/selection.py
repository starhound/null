"""Selection list screens."""

from typing import Callable, Coroutine, Any, Optional, Dict, List, Tuple
from textual.timer import Timer
from textual.reactive import reactive
from textual.widgets import Static, Input, Collapsible
from textual.containers import VerticalScroll
from textual.message import Message

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


class ModelItem(Static):
    """A clickable model item."""

    class Selected(Message):
        """Message sent when a model is selected."""
        def __init__(self, provider: str, model: str):
            super().__init__()
            self.provider = provider
            self.model = model

    def __init__(self, provider: str, model: str):
        super().__init__(f"  {model}")
        self.provider = provider
        self.model = model
        self.add_class("model-item")

    def on_click(self):
        """Handle click on model item."""
        self.post_message(self.Selected(self.provider, self.model))


class ModelListScreen(ModalScreen):
    """Screen to select an AI model with collapsible provider sections."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]
    SPINNER_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    is_loading = reactive(True)
    search_query = reactive("")

    def __init__(self, fetch_func: Optional[Callable] = None):
        """Initialize model list screen."""
        super().__init__()
        self.ai_manager = fetch_func
        self._spinner_index = 0
        self._spinner_timer: Optional[Timer] = None
        self._models_by_provider: Dict[str, List[str]] = {}
        self._total_providers = 0

    def compose(self) -> ComposeResult:
        with Container(id="model-selection-container"):
            yield Label("Select a Model", id="model-title")
            yield Input(placeholder="Search models...", id="model-search")
            yield Label("", id="loading-indicator")
            with VerticalScroll(id="model-scroll"):
                yield Static("", id="model-content")
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_mount(self):
        """Start loading models after screen is rendered."""
        self._start_spinner()
        self.set_timer(0.1, self._start_loading)

    def on_input_changed(self, event: Input.Changed):
        """Handle search input changes."""
        if event.input.id == "model-search":
            self.search_query = event.value.lower()
            if not self.is_loading:
                self._update_collapsibles()

    def _start_loading(self):
        """Start the model loading worker in a thread."""
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
                    f"Loading models..."
                )
            else:
                indicator.update(f"{self.SPINNER_FRAMES[self._spinner_index]} Checking providers...")
        except Exception:
            pass

    def _fetch_models_in_thread(self) -> Tuple[Dict[str, List[str]], int]:
        """Synchronous model fetching - runs in a separate thread."""
        import asyncio

        try:
            if not hasattr(self.app, 'ai_manager'):
                return {}, 0

            manager = self.app.ai_manager
            usable = manager.get_usable_providers()
            if not usable:
                return {}, 0

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(manager.list_all_models())
                return result, len(usable)
            finally:
                loop.close()

        except Exception:
            return {}, 0

    def on_worker_state_changed(self, event) -> None:
        """Handle worker completion - update UI with results."""
        from textual.worker import WorkerState

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

                self._update_collapsibles()
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

    def _update_collapsibles(self):
        """Update the collapsible sections with models."""
        try:
            scroll = self.query_one("#model-scroll", VerticalScroll)

            # Remove ALL children from scroll (including old collapsibles)
            for child in list(scroll.children):
                child.remove()

            # Get sorted providers: active first, then alphabetically
            from config import Config
            active_provider = Config.get("ai.provider")

            sorted_providers = sorted(
                self._models_by_provider.keys(),
                key=lambda p: (0 if p == active_provider else 1, p)
            )

            # Create collapsibles for each provider
            for provider in sorted_providers:
                models = self._models_by_provider[provider]
                if not models:
                    continue

                # Filter by search query
                if self.search_query:
                    filtered = [m for m in models if self.search_query in m.lower()]
                else:
                    filtered = models

                if not filtered and self.search_query:
                    continue  # Skip provider if no matches

                # Create collapsible with count
                is_active = provider == active_provider
                title = f"{provider.upper()} ({len(filtered)}{'+' if len(filtered) < len(models) else ''} models)"
                if is_active:
                    title = f"● {title}"

                # Expand active provider or first provider, or if searching
                collapsed = not is_active and not self.search_query

                # Build list of model widgets to pass to Collapsible
                model_widgets = []
                for model in filtered[:100]:  # Limit to 100 per provider
                    model_widgets.append(ModelItem(provider, model))
                
                if len(filtered) > 100:
                    model_widgets.append(Static(f"  ... and {len(filtered) - 100} more", classes="more-label"))

                # Create collapsible WITH the children
                collapsible = Collapsible(*model_widgets, title=title, collapsed=collapsed, id=f"provider-{provider}")
                scroll.mount(collapsible)

        except Exception as e:
            self.log.error(f"Failed to update model list: {e}")
            self._show_error(f"Failed to display models: {str(e)[:50]}")

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

            # Focus the search input
            search = self.query_one("#model-search", Input)
            search.focus()

        except Exception:
            pass

    def _show_no_providers(self):
        """Show message when no providers are configured."""
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update("No providers configured")
            indicator.add_class("error")

            scroll = self.query_one("#model-scroll", VerticalScroll)
            scroll.mount(Static("No providers configured. Use /providers to add one."))
            scroll.mount(Static("Local: ollama, lm_studio (no API key needed)"))
            scroll.mount(Static("Cloud: openai, anthropic, nvidia, groq..."))
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

    def on_model_item_selected(self, message: ModelItem.Selected):
        """Handle model selection from ModelItem."""
        self.dismiss((message.provider, message.model))

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(None)

    def action_dismiss(self):
        self.dismiss(None)
