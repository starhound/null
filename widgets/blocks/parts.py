from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive

from models import BlockState, BlockType


class BlockHeader(Static):
    """Header for a block showing prompt, timestamp, etc."""

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        if self.block.type == BlockType.COMMAND:
            icon = "❯"
            icon_class = "prompt-symbol prompt-symbol-cli"
            text_class = "header-text-cli"
            display_text = self.block.content_input
        elif self.block.type == BlockType.AI_QUERY:
            icon = "◇"
            icon_class = "prompt-symbol prompt-symbol-query"
            text_class = "header-text-ai"
            display_text = self.block.content_input
        elif self.block.type == BlockType.AI_RESPONSE:
            icon = "◆"
            icon_class = "prompt-symbol prompt-symbol-response"
            text_class = "header-text-ai"
            display_text = self.block.content_input if self.block.content_input else ""
        elif self.block.type == BlockType.SYSTEM_MSG:
            icon = "◈"
            icon_class = "prompt-symbol prompt-symbol-system"
            text_class = "header-text-system"
            display_text = self.block.content_input if self.block.content_input else "System"
        else:
            icon = "▸"
            icon_class = "prompt-symbol prompt-symbol-cli"
            text_class = "header-text"
            display_text = self.block.content_input or ""

        yield Label(icon, classes=icon_class)
        yield Label(display_text, classes=text_class)

        ts_str = self.block.timestamp.strftime("%H:%M")
        yield Label(ts_str, classes="timestamp")


class BlockMeta(Static):
    """Metadata bar for AI responses showing model, tokens, context."""

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        meta = self.block.metadata or {}
        parts = []

        # Model
        model = meta.get("model", "")
        if model:
            if "/" in model:
                model = model.split("/")[-1]
            parts.append(model)

        # Tokens
        tokens = meta.get("tokens", "")
        if tokens:
            parts.append(tokens)

        # Context
        ctx = meta.get("context", "")
        if ctx and ctx != "0 chars":
            parts.append(ctx)

        # Persona
        persona = meta.get("persona", "")
        if persona and persona != "default":
            parts.append(f"@{persona}")

        # Render parts with separators
        for i, part in enumerate(parts):
            if i > 0:
                yield Label("·", classes="meta-sep")
            yield Label(part, classes="meta-value")

        # Spacer to push actions to right
        yield Label("", classes="meta-spacer")

        # Action labels for AI responses
        if self.block.type == BlockType.AI_RESPONSE and not self.block.is_running:
            yield Static("edit", id="edit-btn", classes="meta-action")
            yield Static("retry", id="retry-btn", classes="meta-action")


class BlockBody(Static):
    """Body containing simple text content (e.g. command output)."""

    content_text = reactive("")

    def __init__(self, text: str = ""):
        super().__init__()
        self._initial_text = text or ""
        self.content_text = self._initial_text

    def compose(self) -> ComposeResult:
        yield Static(self._initial_text, id="body-content")

    def watch_content_text(self, new_text: str):
        try:
            content = self.query_one("#body-content", Static)
            content.update(new_text)
        except Exception:
            pass


class BlockFooter(Static):
    """Footer showing exit code/status."""

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block
        if not self._has_content():
            self.add_class("empty-footer")

    def _has_content(self) -> bool:
        """Check if footer should show content."""
        if self.block.exit_code is not None and self.block.exit_code != 0:
            return True
        if self.block.is_running:
            return True
        return False

    def compose(self) -> ComposeResult:
        if self.block.exit_code is not None and self.block.exit_code != 0:
            yield Label(f"Exit Code: {self.block.exit_code}", classes="exit-error")
        elif self.block.is_running:
            yield Label("Running...", classes="running-spinner")
