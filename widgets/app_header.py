"""Custom app header widget with provider info and connectivity status."""

from datetime import datetime

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Label, Static


class AppHeader(Static):
    """Custom header showing provider/model, app title, and clock."""

    DEFAULT_CSS = """
    AppHeader {
        dock: top;
        width: 100%;
        height: 1;
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr auto 1fr;
        background: $panel;
        color: $text;
    }

    AppHeader .header-left {
        column-span: 1;
        width: 100%;
        height: 1;
        padding: 0 0 0 1;
    }

    AppHeader .header-icon {
        color: $success;
        text-style: bold;
    }

    AppHeader.-disconnected .header-icon {
        color: $warning;
    }

    AppHeader .header-title {
        column-span: 1;
        width: 100%;
        height: 1;
        text-align: center;
        text-style: bold;
        color: $text;
    }

    AppHeader .header-right {
        column-span: 1;
        width: 100%;
        height: 1;
        text-align: right;
        padding: 0 1 0 0;
        color: $text-muted;
    }
    """

    # Reactive properties
    provider_text: reactive[str] = reactive("", layout=True)
    connected: reactive[bool] = reactive(True)

    def __init__(
        self,
        title: str = "Null Terminal",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._title = title

    def compose(self) -> ComposeResult:
        yield Label("● ", classes="header-left header-icon")
        yield Label(self._title, classes="header-title")
        yield Label(self._get_time(), classes="header-right", id="header-clock")

    def on_mount(self) -> None:
        """Start the clock update interval."""
        self.set_interval(1, self._update_clock)

    def _get_time(self) -> str:
        """Get current time as string."""
        return datetime.now().strftime("%H:%M:%S")

    def _update_clock(self) -> None:
        """Update the clock display."""
        try:
            clock = self.query_one("#header-clock", Label)
            clock.update(self._get_time())
        except Exception:
            pass

    def _update_left_label(self) -> None:
        """Update the left label with icon and provider text."""
        try:
            left_label = self.query_one(".header-left", Label)
            icon = "●" if self.connected else "○"
            if self.provider_text:
                left_label.update(f"{icon} {self.provider_text}")
            else:
                left_label.update(f"{icon} ")
        except Exception:
            pass

    def watch_provider_text(self, value: str) -> None:
        """Update left label when provider text changes."""
        self._update_left_label()

    def watch_connected(self, value: bool) -> None:
        """Update icon and class when connection status changes."""
        if value:
            self.remove_class("-disconnected")
        else:
            self.add_class("-disconnected")
        self._update_left_label()

    def set_provider(self, provider: str, model: str = "", connected: bool = True):
        """Update the provider/model display and connectivity status."""
        # Build display text
        if model:
            # Shorten long model names
            display_model = model
            if "/" in display_model:
                display_model = display_model.split("/")[-1]
            if len(display_model) > 25:
                display_model = display_model[:22] + "..."
            self.provider_text = f"{provider} · {display_model}"
        else:
            self.provider_text = provider

        self.connected = connected
