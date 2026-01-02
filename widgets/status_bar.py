from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive


class StatusBar(Static):
    """Status bar showing mode, context size, and provider status."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface-darken-1;
        layout: horizontal;
        padding: 0 1;
    }

    .status-section {
        margin-right: 3;
    }

    .status-label {
        color: $text-muted;
    }

    .status-value {
        color: $primary;
    }

    .mode-cli {
        color: $success;
        text-style: bold;
    }

    .mode-ai {
        color: $warning;
        text-style: bold;
    }

    .context-low {
        color: $success;
    }

    .context-medium {
        color: $warning;
    }

    .context-high {
        color: $error;
    }

    .provider-connected {
        color: $success;
    }

    .provider-disconnected {
        color: $error;
    }

    .provider-checking {
        color: $warning;
        text-style: italic;
    }
    """

    mode = reactive("CLI")
    context_chars = reactive(0)
    context_limit = reactive(4000)
    provider_name = reactive("")
    provider_status = reactive("unknown")  # connected, disconnected, checking

    def compose(self) -> ComposeResult:
        yield Label("", id="mode-indicator", classes="status-section")
        yield Label("", id="context-indicator", classes="status-section")
        yield Label("", id="provider-indicator", classes="status-section")

    def on_mount(self):
        """Initialize display."""
        self._update_mode_display()
        self._update_context_display()
        self._update_provider_display()

    def watch_mode(self, mode: str):
        """Update mode display when mode changes."""
        self._update_mode_display()

    def watch_context_chars(self, chars: int):
        """Update context display when size changes."""
        self._update_context_display()

    def watch_provider_status(self, status: str):
        """Update provider display when status changes."""
        self._update_provider_display()

    def watch_provider_name(self, name: str):
        """Update provider display when name changes."""
        self._update_provider_display()

    def _update_mode_display(self):
        try:
            indicator = self.query_one("#mode-indicator", Label)
            indicator.remove_class("mode-cli", "mode-ai")

            if self.mode == "CLI":
                indicator.update("Mode: CLI")
                indicator.add_class("mode-cli")
            else:
                indicator.update("Mode: AI")
                indicator.add_class("mode-ai")
        except Exception:
            pass

    def _update_context_display(self):
        try:
            indicator = self.query_one("#context-indicator", Label)
            indicator.remove_class("context-low", "context-medium", "context-high")

            # Calculate percentage
            pct = (self.context_chars / self.context_limit * 100) if self.context_limit > 0 else 0
            tokens = self.context_chars // 4  # Rough estimate

            indicator.update(f"Context: ~{tokens} tokens ({pct:.0f}%)")

            if pct < 50:
                indicator.add_class("context-low")
            elif pct < 80:
                indicator.add_class("context-medium")
            else:
                indicator.add_class("context-high")
        except Exception:
            pass

    def _update_provider_display(self):
        try:
            indicator = self.query_one("#provider-indicator", Label)
            indicator.remove_class("provider-connected", "provider-disconnected", "provider-checking")

            name = self.provider_name or "None"

            if self.provider_status == "connected":
                indicator.update(f"AI: {name} (connected)")
                indicator.add_class("provider-connected")
            elif self.provider_status == "disconnected":
                indicator.update(f"AI: {name} (offline)")
                indicator.add_class("provider-disconnected")
            else:
                indicator.update(f"AI: {name}")
                indicator.add_class("provider-checking")
        except Exception:
            pass

    def set_mode(self, mode: str):
        """Set current mode (CLI or AI)."""
        self.mode = mode

    def set_context(self, chars: int, limit: int = 4000):
        """Set current context size."""
        self.context_chars = chars
        self.context_limit = limit

    def set_provider(self, name: str, status: str = "unknown"):
        """Set provider name and status."""
        self.provider_name = name
        self.provider_status = status
