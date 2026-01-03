"""Providers management screen."""

from ai.factory import AIFactory
from config import Config

from .base import (
    Binding,
    Button,
    ComposeResult,
    Container,
    Horizontal,
    Label,
    ModalScreen,
    VerticalScroll,
)


class ProviderRow(Horizontal):
    """A single provider row with status and actions."""

    can_focus = True

    def __init__(
        self, provider_name: str, info: dict, is_active: bool, is_configured: bool
    ):
        super().__init__()
        self.provider_name = provider_name
        self.info = info
        self.is_active = is_active
        self.is_configured = is_configured
        self.add_class("provider-row")

    def compose(self) -> ComposeResult:
        # Status indicator
        if self.is_active:
            status = "[●]"
            status_class = "active"
        elif self.is_configured:
            status = "[○]"
            status_class = "configured"
        else:
            status = "[ ]"
            status_class = "unconfigured"

        yield Label(status, classes=f"provider-status {status_class}")
        yield Label(self.info.get("name", self.provider_name), classes="provider-name")
        yield Label(self.info.get("description", ""), classes="provider-desc")

        # Configure button
        yield Button(
            "Configure", id=f"config-{self.provider_name}", classes="provider-btn"
        )

        # Set Active button (only if configured and not already active)
        if self.is_configured and not self.is_active:
            yield Button(
                "Set Active",
                id=f"activate-{self.provider_name}",
                classes="provider-btn-active",
            )

        # Unconfigure button (only if configured and not active)
        if self.is_configured and not self.is_active:
            yield Button(
                "Remove",
                id=f"unconfigure-{self.provider_name}",
                classes="provider-btn-remove",
            )


class ProvidersScreen(ModalScreen):
    """Screen to manage AI providers."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("up", "focus_prev", "Previous", show=False),
        Binding("down", "focus_next", "Next", show=False),
        Binding("enter", "configure_focused", "Configure", show=False),
    ]

    def __init__(self):
        super().__init__()
        self._active_provider = Config.get("ai.provider")

    def action_focus_prev(self):
        """Move focus to previous provider row."""
        self.focus_previous()

    def action_focus_next(self):
        """Move focus to next provider row."""
        self.focus_next()

    def action_configure_focused(self):
        """Configure the currently focused provider."""
        focused = self.focused
        if isinstance(focused, ProviderRow):
            self.dismiss(("configure", focused.provider_name))

    def compose(self) -> ComposeResult:
        with Container(id="providers-container"):
            yield Label("AI Providers", id="providers-title")
            yield Label(
                f"Active: {self._active_provider or 'None'}", id="active-provider-label"
            )

            with VerticalScroll(id="providers-list"):
                # Group providers
                local_providers = ["ollama", "lm_studio"]
                cloud_providers = []
                other_providers = []

                for p_name in AIFactory.list_providers():
                    info = AIFactory.get_provider_info(p_name)
                    if p_name in local_providers:
                        continue  # Handle separately
                    elif info.get("requires_api_key"):
                        cloud_providers.append(p_name)
                    else:
                        other_providers.append(p_name)

                # Local providers section
                yield Label("── Local ──", classes="section-header")
                for p_name in local_providers:
                    info = AIFactory.get_provider_info(p_name)
                    is_active = p_name == self._active_provider
                    is_configured = self._is_provider_configured(p_name, info)
                    yield ProviderRow(p_name, info, is_active, is_configured)

                # Cloud providers section
                yield Label("── Cloud ──", classes="section-header")
                for p_name in sorted(cloud_providers):
                    info = AIFactory.get_provider_info(p_name)
                    is_active = p_name == self._active_provider
                    is_configured = self._is_provider_configured(p_name, info)
                    yield ProviderRow(p_name, info, is_active, is_configured)

                # Other providers (like bedrock)
                if other_providers:
                    yield Label("── Other ──", classes="section-header")
                    for p_name in sorted(other_providers):
                        info = AIFactory.get_provider_info(p_name)
                        is_active = p_name == self._active_provider
                        is_configured = self._is_provider_configured(p_name, info)
                        yield ProviderRow(p_name, info, is_active, is_configured)

            yield Button("Close [Esc]", variant="default", id="close_btn")

    def _is_provider_configured(self, provider_name: str, info: dict) -> bool:
        """Check if a provider has the required configuration."""
        if info.get("requires_api_key"):
            return bool(Config.get(f"ai.{provider_name}.api_key"))
        elif info.get("requires_endpoint"):
            # Local providers - check if endpoint is explicitly set
            return bool(Config.get(f"ai.{provider_name}.endpoint"))
        return False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "close_btn":
            self.dismiss(None)
            return

        if button_id and button_id.startswith("config-"):
            provider_name = button_id.replace("config-", "")
            # Dismiss and return the provider to configure
            self.dismiss(("configure", provider_name))
            return

        if button_id and button_id.startswith("activate-"):
            provider_name = button_id.replace("activate-", "")
            # Set as active provider
            Config.set("ai.provider", provider_name)
            self.dismiss(("activated", provider_name))
            return

        if button_id and button_id.startswith("unconfigure-"):
            provider_name = button_id.replace("unconfigure-", "")
            # Remove provider configuration from database
            self._unconfigure_provider(provider_name)
            self.dismiss(("unconfigured", provider_name))
            return

    def _unconfigure_provider(self, provider_name: str):
        """Remove all configuration for a provider from the database."""
        sm = Config._get_storage()
        # Delete all keys starting with ai.<provider_name>.
        sm.delete_config_prefix(f"ai.{provider_name}.")

    def action_dismiss(self):
        self.dismiss(None)
