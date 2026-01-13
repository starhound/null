"""Providers management screen."""

from typing import ClassVar

from textual.binding import BindingType

from ai.base import HealthStatus, ProviderHealth
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
        self,
        provider_name: str,
        info: dict,
        is_active: bool,
        is_configured: bool,
        health: ProviderHealth | None = None,
    ):
        super().__init__()
        self.provider_name = provider_name
        self.info = info
        self.is_active = is_active
        self.is_configured = is_configured
        self.health = health or ProviderHealth()
        self.add_class("provider-row")

    def compose(self) -> ComposeResult:
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

        health_indicator = self._get_health_indicator()
        yield Label(
            health_indicator, classes=f"provider-health {self._get_health_class()}"
        )

        yield Label(self.info.get("description", ""), classes="provider-desc")

        yield Button(
            "Configure", id=f"config-{self.provider_name}", classes="provider-btn"
        )

        if self.is_configured and not self.is_active:
            yield Button(
                "Set Active",
                id=f"activate-{self.provider_name}",
                classes="provider-btn-active",
            )

        if self.is_configured and not self.is_active:
            yield Button(
                "Remove",
                id=f"unconfigure-{self.provider_name}",
                classes="provider-btn-remove",
            )

    def _get_health_indicator(self) -> str:
        if not self.is_configured:
            return ""

        status = self.health.status
        latency = self.health.latency_display

        if status == HealthStatus.CONNECTED:
            icon = "●"
            return f"{icon} {latency}" if latency else icon
        elif status == HealthStatus.DISCONNECTED:
            return "○ offline"
        elif status == HealthStatus.ERROR:
            return "✗ error"
        elif status == HealthStatus.CHECKING:
            return "◌ ..."
        return ""

    def _get_health_class(self) -> str:
        if not self.is_configured:
            return "health-none"

        status = self.health.status
        if status == HealthStatus.CONNECTED:
            category = self.health.latency_category
            if category == "fast":
                return "health-good"
            elif category == "normal":
                return "health-slow"
            return "health-bad"
        elif status == HealthStatus.DISCONNECTED:
            return "health-offline"
        elif status == HealthStatus.ERROR:
            return "health-error"
        elif status == HealthStatus.CHECKING:
            return "health-checking"
        return "health-none"


class ProvidersScreen(ModalScreen):
    """Screen to manage AI providers."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("up", "focus_prev", "Previous", show=False),
        Binding("down", "focus_next", "Next", show=False),
        Binding("enter", "configure_focused", "Configure", show=False),
        Binding("r", "refresh_health", "Refresh", show=True),
    ]

    def __init__(self):
        super().__init__()
        self._active_provider = Config.get("ai.provider")
        self._health_cache: dict[str, ProviderHealth] = {}

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

    def action_refresh_health(self):
        self.run_worker(self._check_all_health(), exclusive=True)

    async def _check_all_health(self):
        if not hasattr(self.app, "ai_manager"):
            return

        health_map = await self.app.ai_manager.check_all_health()
        self._health_cache = health_map
        self._refresh_provider_rows()

    def _refresh_provider_rows(self):
        for row in self.query(ProviderRow):
            health = self._health_cache.get(row.provider_name)
            if health:
                row.health = health
                health_label = row.query_one(".provider-health", Label)
                health_label.update(row._get_health_indicator())
                health_label.remove_class(
                    "health-good",
                    "health-slow",
                    "health-bad",
                    "health-offline",
                    "health-error",
                    "health-checking",
                    "health-none",
                )
                health_label.add_class(row._get_health_class())

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

                yield Label("── Local ──", classes="section-header")
                for p_name in local_providers:
                    info = AIFactory.get_provider_info(p_name)
                    is_active = p_name == self._active_provider
                    is_configured = self._is_provider_configured(p_name, info)
                    health = self._health_cache.get(p_name)
                    yield ProviderRow(p_name, info, is_active, is_configured, health)

                yield Label("── Cloud ──", classes="section-header")
                for p_name in sorted(cloud_providers):
                    info = AIFactory.get_provider_info(p_name)
                    is_active = p_name == self._active_provider
                    is_configured = self._is_provider_configured(p_name, info)
                    health = self._health_cache.get(p_name)
                    yield ProviderRow(p_name, info, is_active, is_configured, health)

                if other_providers:
                    yield Label("── Other ──", classes="section-header")
                    for p_name in sorted(other_providers):
                        info = AIFactory.get_provider_info(p_name)
                        is_active = p_name == self._active_provider
                        is_configured = self._is_provider_configured(p_name, info)
                        health = self._health_cache.get(p_name)
                        yield ProviderRow(
                            p_name, info, is_active, is_configured, health
                        )

            yield Button("Close [Esc]", variant="default", id="close_btn")

    async def on_mount(self) -> None:
        self.run_worker(self._check_all_health(), exclusive=True)

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
            # Also sync to JSON settings
            from config import SettingsManager

            SettingsManager().set("ai", "provider", provider_name)
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

    async def action_dismiss(self, result: object = None) -> None:
        self.dismiss(None)
