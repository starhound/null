from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Label, Static, Markdown
from textual.screen import ModalScreen

from context import ContextManager


class ContextScreen(ModalScreen):
    DEFAULT_CSS = """
    ContextScreen {
        align: center middle;
    }
    #context-dialog {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    #context-header {
        dock: top;
        height: 1;
        border-bottom: solid $primary;
        text-align: center;
        text-style: bold;
    }
    #context-stats {
        dock: bottom;
        height: 3;
        border-top: solid $primary;
        color: $text-muted;
    }
    .msg-item {
        margin-bottom: 1;
        padding: 1;
        background: $surface-lighten-1;
    }
    .msg-role {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="context-dialog"):
            yield Label("Context Inspector", id="context-header")
            yield VerticalScroll(id="context-list")
            yield Static(id="context-stats")

    def on_mount(self):
        self._load_context()

    def _load_context(self):
        ai_provider = self.app.ai_provider
        max_tokens = 4000
        if ai_provider:
            info = ai_provider.get_model_info()
            max_tokens = info.context_window

        context_info = ContextManager.build_messages(
            self.app.blocks, max_tokens=max_tokens
        )

        stats = self.query_one("#context-stats", Static)
        stats.update(
            f"Messages: {context_info.message_count}\n"
            f"Est. Tokens: {context_info.estimated_tokens} / {max_tokens}\n"
            f"Truncated: {'Yes' if context_info.truncated else 'No'}"
        )

        container = self.query_one("#context-list", VerticalScroll)

        widgets = []
        for msg in context_info.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            item = Container(classes="msg-item")
            item.mount(Label(role.upper(), classes="msg-role"))
            item.mount(Static(str(content)))
            widgets.append(item)

        container.mount_all(widgets)
