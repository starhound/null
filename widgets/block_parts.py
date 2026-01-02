from textual.app import ComposeResult
from textual.widgets import Static, Label, Button
from textual.reactive import reactive
from textual import on

from models import BlockState, BlockType


class BlockHeader(Static):
    """Header for a block showing prompt, timestamp, etc."""

    DEFAULT_CSS = """
    BlockHeader {
        layout: horizontal;
        height: 1;
        dock: top;
        background: $surface;
        color: $text;
        padding: 0 1;
    }

    /* CLI command symbol - green */
    .prompt-symbol-cli {
        color: $success;
        margin-right: 1;
        text-style: bold;
    }

    /* AI query symbol - amber */
    .prompt-symbol-query {
        color: $warning;
        margin-right: 1;
    }

    /* AI response symbol - blue/primary */
    .prompt-symbol-response {
        color: $primary;
        margin-right: 1;
    }

    /* System message symbol - cyan/secondary */
    .prompt-symbol-system {
        color: $secondary;
        margin-right: 1;
        text-style: bold;
    }

    .header-text {
        color: $text;
        width: 1fr;
    }

    .header-text-cli {
        color: $success-lighten-2;
        text-style: bold;
        width: 1fr;
    }

    .header-text-ai {
        color: $text;
        width: 1fr;
    }

    .header-text-system {
        color: $secondary;
        width: 1fr;
    }

    .timestamp {
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        if self.block.type == BlockType.COMMAND:
            icon = "$"
            icon_class = "prompt-symbol-cli"
            text_class = "header-text-cli"
            display_text = self.block.content_input
        elif self.block.type == BlockType.AI_QUERY:
            icon = "?"
            icon_class = "prompt-symbol-query"
            text_class = "header-text-ai"
            display_text = self.block.content_input
        elif self.block.type == BlockType.AI_RESPONSE:
            icon = "◆"
            icon_class = "prompt-symbol-response"
            text_class = "header-text-ai"
            # Show the original query if available
            display_text = self.block.content_input if self.block.content_input else "AI Response"
        elif self.block.type == BlockType.SYSTEM_MSG:
            icon = "●"
            icon_class = "prompt-symbol-system"
            text_class = "header-text-system"
            display_text = self.block.content_input if self.block.content_input else "System"
        else:
            icon = ">"
            icon_class = "prompt-symbol-cli"
            text_class = "header-text"
            display_text = self.block.content_input or "..."

        yield Label(icon, classes=icon_class)
        yield Label(display_text, classes=text_class)

        ts_str = self.block.timestamp.strftime("%H:%M:%S")
        yield Label(ts_str, classes="timestamp")


class BlockMeta(Static):
    """Metadata bar for AI responses showing model, tokens, context."""

    DEFAULT_CSS = """
    BlockMeta {
        layout: horizontal;
        height: 1;
        padding: 0 2;
        background: $surface-darken-1;
        color: $text-muted;
    }

    .meta-item {
        margin-right: 2;
        text-style: dim;
    }

    .meta-label {
        color: $text-muted;
    }

    .meta-value {
        color: $primary;
        text-style: italic;
    }

    .meta-value-success {
        color: $success;
        text-style: italic;
    }

    .meta-value-warning {
        color: $warning;
        text-style: italic;
    }

    .meta-spacer {
        width: 1fr;
    }

    .meta-action {
        min-width: 8;
        width: auto;
        height: 1;
        border: none;
        padding: 0 1;
        margin: 0;
        background: $surface;
        color: $text-muted;
        text-style: none;
    }

    .meta-action:hover {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    .meta-action:focus {
        background: $primary;
        color: $text;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        meta = self.block.metadata or {}

        # Model
        model = meta.get("model", "")
        if model:
            if "/" in model:
                model = model.split("/")[-1]
            yield Label(f"model: ", classes="meta-label")
            yield Label(f"{model}", classes="meta-value")
            yield Label("  ", classes="meta-item")

        # Context
        ctx = meta.get("context", "")
        if ctx and ctx != "0 chars":
            yield Label(f"context: ", classes="meta-label")
            yield Label(f"{ctx}", classes="meta-value-warning")
            yield Label("  ", classes="meta-item")

        # Tokens (if available)
        tokens = meta.get("tokens", "")
        if tokens:
            yield Label(f"tokens: ", classes="meta-label")
            yield Label(f"{tokens}", classes="meta-value-success")
            yield Label("  ", classes="meta-item")

        # Persona
        persona = meta.get("persona", "")
        if persona and persona != "default":
            yield Label(f"persona: ", classes="meta-label")
            yield Label(f"{persona}", classes="meta-value")

        # Spacer to push actions to right
        yield Label("", classes="meta-spacer")

        # Action buttons for AI responses
        if self.block.type == BlockType.AI_RESPONSE and not self.block.is_running:
            yield Button("[edit]", id="edit-btn", classes="meta-action")
            yield Button("[retry]", id="retry-btn", classes="meta-action")


class BlockBody(Static):
    """Body containing simple text content (e.g. command output)."""

    DEFAULT_CSS = """
    BlockBody {
        padding: 1 2;
        color: $text;
        min-height: 1;
    }
    """

    content_text = reactive("")

    def __init__(self, text: str = ""):
        super().__init__()
        self.content_text = text

    def compose(self) -> ComposeResult:
        yield Static(id="body-content")

    def watch_content_text(self, new_text: str):
        try:
            content = self.query_one("#body-content", Static)
            content.update(new_text)
        except Exception:
            pass


class BlockFooter(Static):
    """Footer showing exit code/status."""

    DEFAULT_CSS = """
    BlockFooter {
        height: auto;
        padding: 0 2;
        color: $text-muted;
    }

    BlockFooter.empty-footer {
        display: none;
    }

    .exit-error {
        color: $error;
        text-style: bold;
    }

    .running-spinner {
        color: $warning;
        text-style: italic;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        if self.block.exit_code is not None and self.block.exit_code != 0:
            yield Label(f"Exit Code: {self.block.exit_code}", classes="exit-error")
        elif self.block.is_running:
            yield Label("Running...", classes="running-spinner")
        else:
            self.add_class("empty-footer")
