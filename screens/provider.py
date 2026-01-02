"""Provider configuration screen."""

from .base import ModalScreen, ComposeResult, Binding, Container, Label, Input, Button


class ProviderConfigScreen(ModalScreen):
    """Screen to configure a provider."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    # Provider-specific field configurations
    PROVIDER_FIELDS = {
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
    }

    def __init__(self, provider: str, current_config: dict):
        super().__init__()
        self.provider = provider
        self.current_config = current_config
        self.inputs = {}

    def compose(self) -> ComposeResult:
        from ai.factory import AIFactory

        provider_info = AIFactory.get_provider_info(self.provider)
        title = provider_info.get("name", self.provider.title())
        description = provider_info.get("description", "")

        with Container(id="config-container"):
            yield Label(f"Configure {title}")
            if description:
                yield Label(description, classes="input-hint")

            # Get fields for this provider
            fields = self.PROVIDER_FIELDS.get(self.provider, {})

            for field_key, (label, placeholder, is_password) in fields.items():
                yield Label(label, classes="input-label")
                inp = Input(
                    placeholder=placeholder,
                    password=is_password,
                    id=field_key,
                    value=self.current_config.get(field_key, "")
                )
                self.inputs[field_key] = inp
                yield inp

            with Container(id="buttons"):
                yield Button("Save", variant="default", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "save":
            result = {}
            for key, widget in self.inputs.items():
                result[key] = widget.value
            self.dismiss(result)
        else:
            self.dismiss(None)

    def action_dismiss(self):
        self.dismiss(None)
