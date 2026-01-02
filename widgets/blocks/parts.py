import re
from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.reactive import reactive
from rich.text import Text

from models import BlockState, BlockType


# URL pattern for making links clickable in plain text output
URL_PATTERN = re.compile(
    r'(https?://|ftp://)[^\s<>\[\]\"\'`\)]+',
    re.IGNORECASE
)


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
    """Metadata bar for AI responses showing provider, model, tokens, context."""

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        meta = self.block.metadata or {}
        parts = []

        # Provider
        provider = meta.get("provider", "")
        if provider:
            parts.append(provider)

        # Model
        model = meta.get("model", "")
        if model:
            if "/" in model:
                model = model.split("/")[-1]
            parts.append(model)

        # Tokens (input/output)
        tokens = meta.get("tokens", "")
        if tokens:
            parts.append(tokens)

        # Cost if available
        cost = meta.get("cost", "")
        if cost:
            parts.append(cost)

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
            yield Label("edit", id="edit-btn", classes="meta-action")
            yield Label("retry", id="retry-btn", classes="meta-action")

    def on_click(self, event) -> None:
        """Handle clicks on action buttons."""
        # Check if we clicked on edit or retry buttons
        try:
            edit_btn = self.query_one("#edit-btn")
            retry_btn = self.query_one("#retry-btn")
            
            # Check which button was clicked by position
            if edit_btn.region.contains(event.x, event.y):
                from widgets.blocks.base import BaseBlockWidget
                self.post_message(BaseBlockWidget.EditRequested(self.block.id, self.block.content_input))
                event.stop()
            elif retry_btn.region.contains(event.x, event.y):
                from widgets.blocks.base import BaseBlockWidget
                self.post_message(BaseBlockWidget.RetryRequested(self.block.id))
                event.stop()
        except Exception:
            pass


class BlockBody(Static):
    """Body containing simple text content (e.g. command output)."""

    content_text = reactive("")

    def __init__(self, text: str = ""):
        super().__init__()
        self._initial_text = text or ""
        self.content_text = self._initial_text

    def compose(self) -> ComposeResult:
        yield Static(self._make_links_clickable(self._initial_text), id="body-content")

    def watch_content_text(self, new_text: str):
        try:
            content = self.query_one("#body-content", Static)
            content.update(self._make_links_clickable(new_text))
        except Exception:
            pass

    def _make_links_clickable(self, text: str) -> Text:
        """Convert plain text with URLs to Rich Text with clickable links.

        Also handles command separators and prompts with styling.
        """
        if not text:
            return Text("")

        result = Text()
        last_end = 0

        # First, handle URLs
        for match in URL_PATTERN.finditer(text):
            # Add text before the URL (with separator styling)
            if match.start() > last_end:
                segment = text[last_end:match.start()]
                self._append_styled_segment(result, segment)

            # Add the URL as a clickable link
            url = match.group(0)
            result.append(url, style=f"link {url} underline cyan")
            last_end = match.end()

        # Add remaining text after last URL
        if last_end < len(text):
            segment = text[last_end:]
            self._append_styled_segment(result, segment)

        return result

    def _append_styled_segment(self, result: Text, segment: str):
        """Append a text segment with appropriate styling for separators and prompts."""
        # Split by lines to handle separators and prompts
        lines = segment.split('\n')
        for i, line in enumerate(lines):
            if i > 0:
                result.append('\n')

            # Style command separators (dim)
            if line.startswith('┄') or line.startswith('─'):
                result.append(line, style="dim")
            # Style command prompts (bold green)
            elif line.startswith('❯ '):
                result.append('❯ ', style="bold green")
                result.append(line[2:], style="bold")
            elif line.startswith('$ '):
                result.append('$ ', style="bold green")
                result.append(line[2:], style="bold")
            else:
                result.append(line)


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
