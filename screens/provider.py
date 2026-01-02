"""Provider configuration screen."""

from .base import ModalScreen, ComposeResult, Binding, Container, Label, Input, Button


class ProviderConfigScreen(ModalScreen):
    """Screen to configure a provider."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, provider: str, current_config: dict):
        super().__init__()
        self.provider = provider
        self.current_config = current_config
        self.inputs = {}

    def compose(self) -> ComposeResult:
        with Container(id="config-container"):
            yield Label(f"Configure {self.provider.title()}")

            # Dynamic fields based on provider
            if self.provider in ["openai", "xai", "azure", "lm_studio", "bedrock"]:
                yield Label("API Key", classes="input-label")
                inp = Input(
                    placeholder="sk-...",
                    password=True,
                    id="api_key",
                    value=self.current_config.get("api_key", "")
                )
                self.inputs["api_key"] = inp
                yield inp

            # Custom Endpoint providers
            if self.provider in ["ollama", "lm_studio", "azure"]:
                yield Label("Endpoint URL", classes="input-label")
                default_url = "http://localhost:11434" if self.provider == "ollama" else ""
                if self.provider == "lm_studio":
                    default_url = "http://localhost:1234/v1"

                inp = Input(
                    placeholder=default_url if default_url else "https://...",
                    id="endpoint",
                    value=self.current_config.get("endpoint", default_url)
                )
                self.inputs["endpoint"] = inp
                yield inp

            if self.provider == "bedrock":
                yield Label("AWS Region", classes="input-label")
                inp = Input(
                    placeholder="us-east-1",
                    id="region",
                    value=self.current_config.get("region", "us-east-1")
                )
                self.inputs["region"] = inp
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
