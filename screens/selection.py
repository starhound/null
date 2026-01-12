"""Selection list screens."""

from collections.abc import Callable
from typing import ClassVar

from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Collapsible, Input, Static

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Label,
    ListItem,
    ListView,
    ModalScreen,
)


class ThemeSelectionScreen(ModalScreen):
    """Screen to select a theme with live preview on highlight."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "dismiss", "Close")]

    def __init__(self, title: str, items: list[str]):
        super().__init__()
        self._screen_title = title
        self.items = items
        self._original_theme: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label(self._screen_title)
            if not self.items:
                yield Label("No themes found.", classes="empty-msg")
            else:
                yield ListView(
                    *[ListItem(Label(m)) for m in self.items], id="item_list"
                )
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

    async def action_dismiss(self, result: object = None) -> None:
        """Restore original theme on escape."""
        if self._original_theme:
            self.app.theme = self._original_theme
        self.dismiss(None)


class SelectionListScreen(ModalScreen):
    """Generic screen to select an item from a list."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "dismiss", "Close")]

    def __init__(self, title: str, items: list[str]):
        super().__init__()
        self._screen_title = title
        self.items = items

    def compose(self) -> ComposeResult:
        with Container(id="selection-container"):
            yield Label(self._screen_title)
            if not self.items:
                yield Label("No items found.", classes="empty-msg")
            else:
                yield ListView(
                    *[ListItem(Label(m)) for m in self.items], id="item_list"
                )
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_list_view_selected(self, message: ListView.Selected):
        index = self.query_one(ListView).index
        if index is not None and 0 <= index < len(self.items):
            self.dismiss(str(self.items[index]))
        else:
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    async def action_dismiss(self, result: object = None) -> None:
        self.dismiss(None)


class ModelItem(Static):
    can_focus = True

    class Selected(Message):
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
        self.post_message(self.Selected(self.provider, self.model))

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.post_message(self.Selected(self.provider, self.model))
            event.stop()


class ModelListScreen(ModalScreen):
    """Screen to select a model from available providers."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("up", "focus_prev", "Previous", show=False),
        Binding("down", "focus_next", "Next", show=False),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_prev", "Previous", show=False),
    ]

    def action_focus_prev(self):
        self.focus_previous()

    def action_focus_next(self):
        self.focus_next()

    SPINNER_FRAMES: ClassVar[list[str]] = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    is_loading: reactive[bool] = reactive(True)
    search_query: reactive[str] = reactive("")

    def __init__(self, fetch_func: Callable | None = None):
        """Initialize model list screen."""
        super().__init__()
        self.ai_manager = fetch_func
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None
        self._models_by_provider: dict[str, list[str]] = {}
        self._total_providers = 0
        self._completed_providers = 0
        self._fetch_task: object | None = None

    def compose(self) -> ComposeResult:
        with Container(id="model-selection-container"):
            yield Label("Select a Model", id="model-title")
            yield Input(placeholder="Search models...", id="model-search")
            yield Label("", id="loading-indicator")
            with VerticalScroll(id="model-scroll"):
                yield Static("", id="model-content")
            yield Button("Cancel [Esc]", variant="default", id="cancel_btn")

    def on_mount(self):
        self._start_spinner()
        self._fetch_task = self.run_worker(self._fetch_models_streaming, exclusive=True)

    def on_unmount(self) -> None:
        self._stop_spinner()
        if self._fetch_task:
            try:
                self._fetch_task.cancel()
            except Exception:
                pass

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "model-search":
            self.search_query = event.value.lower()
            if not self.is_loading:
                self._update_collapsibles()

    async def _fetch_models_streaming(self) -> None:
        try:
            if not hasattr(self.app, "ai_manager"):
                self._show_no_providers()
                return

            manager = self.app.ai_manager
            usable = manager.get_usable_providers()

            if not usable:
                self._show_no_providers()
                return

            self._total_providers = len(usable)
            self._completed_providers = 0

            async for (
                provider_name,
                models,
                _error,
                completed,
                _total,
            ) in manager.list_all_models_streaming():
                self._completed_providers = completed
                self._update_progress_text()

                if models:
                    self._models_by_provider[provider_name] = models
                    self._update_collapsibles()

            self._stop_spinner()
            self.is_loading = False
            self._finalize_list()

        except Exception as e:
            self._stop_spinner()
            self.is_loading = False
            self._show_error(str(e)[:50])

    def _update_progress_text(self):
        try:
            indicator = self.query_one("#loading-indicator", Label)
            spinner = self.SPINNER_FRAMES[self._spinner_index]
            if self._total_providers > 0:
                indicator.update(
                    f"{spinner} Loading... ({self._completed_providers}/{self._total_providers} providers)"
                )
            else:
                indicator.update(f"{spinner} Checking providers...")
        except Exception:
            pass

    def _start_spinner(self):
        try:
            indicator = self.query_one("#loading-indicator", Label)
            indicator.update(f"{self.SPINNER_FRAMES[0]} Checking providers...")
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)
        except Exception:
            pass

    def _stop_spinner(self):
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None

    def _animate_spinner(self):
        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        self._update_progress_text()

    def _update_collapsibles(self):
        """Update the collapsible sections with models (incremental)."""
        try:
            scroll = self.query_one("#model-scroll", VerticalScroll)

            from config import Config

            active_provider = Config.get("ai.provider")

            # Get existing provider IDs to avoid re-creating
            existing_ids = {child.id for child in scroll.children if child.id}

            # Only process providers that don't already have a collapsible
            # (unless we're filtering by search, then rebuild is needed)
            if self.search_query:
                # When searching, do a full rebuild for accurate filtering
                for child in list(scroll.children):
                    child.remove()
                existing_ids = set()

            # Get sorted providers: active first, then alphabetically
            sorted_providers = sorted(
                self._models_by_provider.keys(),
                key=lambda p: (0 if p == active_provider else 1, p),
            )

            # Create collapsibles for each provider
            for provider in sorted_providers:
                provider_id = f"provider-{provider}"

                # Skip if already exists (incremental update)
                if provider_id in existing_ids:
                    continue

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
                model_widgets: list[ModelItem | Static] = []
                for model in filtered[:100]:  # Limit to 100 per provider
                    model_widgets.append(ModelItem(provider, model))

                if len(filtered) > 100:
                    model_widgets.append(
                        Static(
                            f"  ... and {len(filtered) - 100} more",
                            classes="more-label",
                        )
                    )

                # Create collapsible WITH the children
                collapsible = Collapsible(
                    *model_widgets,
                    title=title,
                    collapsed=collapsed,
                    id=provider_id,
                )
                scroll.mount(collapsible)

        except Exception as e:
            try:
                self.log.error(f"Failed to update model list: {e}")
            except Exception:
                pass
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
                indicator.update(
                    f"✓ Found {total_models} models from {provider_count} provider(s)"
                )
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    async def action_dismiss(self, result: object = None) -> None:
        self.dismiss(None)
