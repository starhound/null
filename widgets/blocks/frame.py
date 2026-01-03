"""Block frame widget with chat/agent mode styling."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Label, Static


class BlockFrame(Container):
    """Container that provides mode-specific framing for AI blocks.

    Modes:
    - 'chat': Simple responses, single-line border, subtle styling
    - 'agent': Tool-using responses, double-line border, accent colors
    """

    DEFAULT_CSS = """
    BlockFrame {
        width: 100%;
        height: auto;
        padding: 0;
    }

    /* Chat mode - subtle single border */
    BlockFrame.mode-chat {
        border: round $surface-lighten-1;
        background: $surface;
    }

    BlockFrame.mode-chat .block-mode-tag {
        color: $text-muted;
        text-style: dim;
    }

    /* Agent mode - bold double border */
    BlockFrame.mode-agent {
        border: double $accent;
        background: $surface;
    }

    BlockFrame.mode-agent .block-mode-tag {
        color: $accent;
        text-style: bold;
    }

    /* Header styling */
    BlockFrame .frame-header {
        width: 100%;
        height: 1;
        padding: 0 1;
        background: $surface-darken-1;
    }

    BlockFrame .frame-header .block-mode-tag {
        width: auto;
    }

    BlockFrame .frame-header .block-input-preview {
        color: $text;
        margin-left: 1;
        width: 1fr;
    }

    /* Separator between sections */
    BlockFrame .frame-separator {
        width: 100%;
        height: 1;
        background: $surface-lighten-1 50%;
    }

    BlockFrame.mode-agent .frame-separator {
        background: $accent 30%;
    }
    """

    mode = reactive("chat")  # "chat" or "agent"

    # Box drawing characters for each mode
    CHARS = {
        "chat": {
            "tl": "┌",
            "tr": "┐",
            "bl": "└",
            "br": "┘",
            "h": "─",
            "v": "│",
            "lt": "├",
            "rt": "┤",
        },
        "agent": {
            "tl": "╔",
            "tr": "╗",
            "bl": "╚",
            "br": "╝",
            "h": "═",
            "v": "║",
            "lt": "╠",
            "rt": "╣",
        },
    }

    def __init__(
        self,
        mode: str = "chat",
        input_preview: str = "",
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.mode = mode
        self.input_preview = input_preview
        self.add_class(f"mode-{mode}")

    def compose(self) -> ComposeResult:
        # Mode tag in header
        tag = "[ AGENT ]" if self.mode == "agent" else "[ CHAT ]"

        with Container(classes="frame-header"):
            yield Label(tag, classes="block-mode-tag", id="mode-tag")
            if self.input_preview:
                # Truncate long inputs
                preview = (
                    self.input_preview[:60] + "..."
                    if len(self.input_preview) > 60
                    else self.input_preview
                )
                preview = f"> {preview}"
                yield Label(preview, classes="block-input-preview")

    def watch_mode(self, old_mode: str, new_mode: str) -> None:
        """Update styling when mode changes."""
        self.remove_class(f"mode-{old_mode}")
        self.add_class(f"mode-{new_mode}")

        try:
            tag_label = self.query_one("#mode-tag", Label)
            tag = "[ AGENT ]" if new_mode == "agent" else "[ CHAT ]"
            tag_label.update(tag)
        except Exception:
            pass

    def set_mode(self, mode: str) -> None:
        """Explicitly set the mode."""
        self.mode = mode


class FrameSeparator(Static):
    """Horizontal separator for frame sections."""

    DEFAULT_CSS = """
    FrameSeparator {
        width: 100%;
        height: 1;
        background: $surface-lighten-1 50%;
        margin: 0;
        padding: 0;
    }
    FrameSeparator.agent {
        background: $accent 30%;
    }
    """

    def __init__(self, mode: str = "chat", id: str | None = None):
        super().__init__("", id=id)
        if mode == "agent":
            self.add_class("agent")
