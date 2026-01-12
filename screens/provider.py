"""Provider configuration screen."""

from typing import Any, ClassVar

from textual.binding import BindingType
from textual.reactive import reactive
from textual.timer import Timer

from .base import Binding, Button, ComposeResult, Container, Input, Label, ModalScreen


class ProviderConfigScreen(ModalScreen):
    """Screen to configure a provider with connection validation."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "dismiss", "Close")]
    SPINNER_FRAMES: ClassVar[list[str]] = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    is_connecting = reactive(False)

    # Provider-specific field configurations
    PROVIDER_FIELDS: ClassVar[dict[str, Any]] = {
        # Local providers
        "ollama": {
            "endpoint": ("Endpoint URL", "http://localhost:11434", False),
        },
        "lm_studio": {
            "endpoint": ("Endpoint URL", "http://localhost:1234/v1", False),
        },
        # Cloud providers requiring API key
        "openai": {
            "api_key": ("API Key", "sk-...", True),
        },
        "anthropic": {
            "api_key": ("API Key", "sk-ant-...", True),
        },
        "google": {
            "api_key": ("API Key (Gemini)", "AI...", True),
            "model": ("Model Name", "gemini-2.0-flash", False),
            "project_id": ("Project ID (optional)", "my-project", False),
        },
        "azure": {
            "api_key": ("API Key", "", True),
            "endpoint": ("Endpoint URL", "https://xxx.openai.azure.com", False),
            "api_version": ("API Version", "2024-02-01", False),
        },
        "bedrock": {
            "region": ("AWS Region", "us-east-1", False),
        },
        "groq": {
            "api_key": ("API Key", "gsk_...", True),
        },
        "mistral": {
            "api_key": ("API Key", "", True),
        },
        "together": {
            "api_key": ("API Key", "", True),
        },
        "nvidia": {
            "api_key": ("API Key", "nvapi-...", True),
        },
        "cohere": {
            "api_key": ("API Key", "", True),
        },
        "xai": {
            "api_key": ("API Key", "xai-...", True),
        },
        "openrouter": {
            "api_key": ("API Key", "sk-or-...", True),
        },
        "fireworks": {
            "api_key": ("API Key", "fw_...", True),
        },
        "deepseek": {
            "api_key": ("API Key", "sk-...", True),
        },
        "perplexity": {
            "api_key": ("API Key", "pplx-...", True),
        },
        "custom": {
            "api_key": ("API Key (Optional)", "", True),
            "endpoint": ("Base URL", "http://localhost:8000/v1", False),
            "model": ("Model Name", "my-model", False),
        },
        "cloudflare": {
            "api_key": ("API Token", "", True),
            "account_id": ("Account ID", "", False),
            "model": ("Model Name", "@cf/meta/llama-3-8b-instruct", False),
        },
        "huggingface": {
            "api_key": ("HF Token", "hf_...", True),
            "model": ("Model ID", "meta-llama/Meta-Llama-3-8B-Instruct", False),
        },
        "llama_cpp": {
            "endpoint": ("Server URL", "http://localhost:8000/v1", False),
        },
    }

    # OAuth providers that need browser login flow instead of form fields
    OAUTH_PROVIDERS: ClassVar[set[str]] = {"claude_oauth", "antigravity"}

    def __init__(self, provider: str, current_config: dict[str, Any]):
        super().__init__()
        self.provider = provider
        self.current_config = current_config
        self.inputs: dict[str, Input] = {}
        self._spinner_index = 0
        self._spinner_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        from ai.factory import AIFactory

        provider_info = AIFactory.get_provider_info(self.provider)
        title = provider_info.get("name", self.provider.title())
        description = provider_info.get("description", "")
        is_oauth = self.provider in self.OAUTH_PROVIDERS

        with Container(id="config-container"):
            yield Label(f"Configure {title}", id="config-title")
            if description:
                yield Label(description, classes="input-hint")

            if is_oauth:
                yield Label(
                    "This provider uses browser-based OAuth authentication.",
                    classes="input-hint",
                )
                yield Label("", id="connection-status", classes="connection-status")
                with Container(id="buttons"):
                    yield Button(
                        "Login with Browser", variant="default", id="oauth-login"
                    )
                    yield Button("Cancel", variant="default", id="cancel")
            else:
                fields = self.PROVIDER_FIELDS.get(self.provider, {})

                for field_key, (label, placeholder, is_password) in fields.items():
                    yield Label(label, classes="input-label")
                    current_value = self.current_config.get(field_key, "")
                    initial_value = current_value if current_value else placeholder
                    inp = Input(
                        placeholder=placeholder,
                        password=is_password,
                        id=field_key,
                        value=initial_value if not is_password else current_value,
                    )
                    self.inputs[field_key] = inp
                    yield inp

                yield Label("", id="connection-status", classes="connection-status")

                with Container(id="buttons"):
                    yield Button("Save & Connect", variant="default", id="save")
                    yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        if self.inputs:
            first_key = next(iter(self.inputs.keys()))
            self.inputs[first_key].focus()

    def on_unmount(self) -> None:
        self._stop_spinner()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#save", Button).press()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            if not self.is_connecting:
                self._test_connection()
        elif event.button.id == "oauth-login":
            if not self.is_connecting:
                self._start_oauth_login()
        else:
            self.dismiss(None)

    def _start_oauth_login(self):
        self.is_connecting = True
        self._start_spinner()
        try:
            status = self.query_one("#connection-status", Label)
            status.update("Opening browser for authentication...")
            status.remove_class("error", "success")
        except Exception:
            pass
        self.run_worker(self._do_oauth_login())

    def _test_connection(self):
        """Test connection to the provider."""
        self.is_connecting = True
        self._start_spinner()
        self.run_worker(self._do_connection_test())

    def _start_spinner(self):
        """Start the connecting spinner animation."""
        try:
            status = self.query_one("#connection-status", Label)
            status.update(f"{self.SPINNER_FRAMES[0]} Connecting...")
            status.remove_class("error", "success")
            self._spinner_timer = self.set_interval(0.08, self._animate_spinner)

            # Disable save button during connection
            save_btn = self.query_one("#save", Button)
            save_btn.disabled = True
        except Exception:
            pass

    def _stop_spinner(self):
        """Stop the spinner."""
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None
        try:
            save_btn = self.query_one("#save", Button)
            save_btn.disabled = False
        except Exception:
            pass

    def _animate_spinner(self):
        """Animate the spinner frame."""
        self._spinner_index = (self._spinner_index + 1) % len(self.SPINNER_FRAMES)
        try:
            status = self.query_one("#connection-status", Label)
            status.update(f"{self.SPINNER_FRAMES[self._spinner_index]} Connecting...")
        except Exception:
            pass

    async def _do_connection_test(self):
        """Perform the actual connection test."""
        from ai.factory import AIFactory

        # Collect current input values
        result = {}
        for key, widget in self.inputs.items():
            result[key] = widget.value

        try:
            # Build provider config
            provider_config = {"provider": self.provider, **result}

            # Create provider instance
            provider = AIFactory.get_provider(provider_config)

            # Test connection
            is_valid = await provider.validate_connection()

            self._stop_spinner()
            self.is_connecting = False

            status = self.query_one("#connection-status", Label)

            if is_valid:
                status.update("✓ Connected successfully!")
                status.add_class("success")
                status.remove_class("error")

                # Small delay to show success, then dismiss
                await self._delay_and_dismiss(result)
            else:
                status.update("✗ Connection failed. Check your settings.")
                status.add_class("error")
                status.remove_class("success")

        except Exception as e:
            self._stop_spinner()
            self.is_connecting = False

            try:
                status = self.query_one("#connection-status", Label)
                error_msg = str(e)
                if len(error_msg) > 50:
                    error_msg = error_msg[:50] + "..."
                status.update(f"✗ Error: {error_msg}")
                status.add_class("error")
                status.remove_class("success")
            except Exception:
                pass

    async def _do_oauth_login(self):
        from ai.factory import AIFactory

        try:
            provider_config = {"provider": self.provider}
            provider = AIFactory.get_provider(provider_config)

            if hasattr(provider, "login"):
                success = await provider.login()

                self._stop_spinner()
                self.is_connecting = False

                status = self.query_one("#connection-status", Label)

                if success:
                    status.update("✓ Authenticated successfully!")
                    status.add_class("success")
                    status.remove_class("error")
                    await self._delay_and_dismiss({})
                else:
                    status.update("✗ Authentication failed or cancelled.")
                    status.add_class("error")
                    status.remove_class("success")
            else:
                self._stop_spinner()
                self.is_connecting = False
                status = self.query_one("#connection-status", Label)
                status.update("✗ Provider does not support OAuth.")
                status.add_class("error")

        except Exception as e:
            self._stop_spinner()
            self.is_connecting = False

            try:
                status = self.query_one("#connection-status", Label)
                error_msg = str(e)
                if len(error_msg) > 50:
                    error_msg = error_msg[:50] + "..."
                status.update(f"✗ Error: {error_msg}")
                status.add_class("error")
                status.remove_class("success")
            except Exception:
                pass

    async def _delay_and_dismiss(self, result: dict):
        import asyncio

        await asyncio.sleep(0.5)
        self.dismiss(result)

    async def action_dismiss(self, result: object = None) -> None:
        if not self.is_connecting:
            self.dismiss(None)
