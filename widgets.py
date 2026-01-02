from datetime import datetime
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Input, Static, Label
from textual.reactive import reactive
from textual.message import Message
from rich.syntax import Syntax
from rich.text import Text

from models import BlockState, BlockType

class InputController(Input):
    """
    Detached input widget.
    State management (history cycling) will be handled by the main App or a controller class
    wrapping this, for simplicity we just emit events on submit.
    """
    BINDINGS = [
        ("up", "history_up", "Previous Command"),
        ("down", "history_down", "Next Command"),
    ]

    class Toggled(Message):
        """Sent when input mode is toggled."""
        def __init__(self, mode: str):
            self.mode = mode
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history: list[str] = []
        self.history_index: int = -1
        self.current_input: str = "" 
        self.mode: str = "CLI" # "CLI" or "AI"

    @property
    def is_ai_mode(self) -> bool:
        return self.mode == "AI"

    def toggle_mode(self):
        if self.mode == "CLI":
            self.mode = "AI"
            self.add_class("ai-mode")
            self.placeholder = "Ask AI..."
        else:
            self.mode = "CLI"
            self.remove_class("ai-mode")
            self.placeholder = "Type a command..."
        self.post_message(self.Toggled(self.mode))

    def on_mount(self):
        self.focus()

    def action_history_up(self):
        if not self.history:
            return
            
        if self.history_index == -1:
            self.current_input = self.value
            self.history_index = len(self.history) - 1
        elif self.history_index > 0:
            self.history_index -= 1
        
        self.value = self.history[self.history_index]
        self.cursor_position = len(self.value)

    def action_history_down(self):
        if self.history_index == -1:
            return

        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
        else:
            self.history_index = -1
            self.value = self.current_input
        
        self.cursor_position = len(self.value)

    def add_to_history(self, command: str):
        if command.strip():
            # Avoid duplicates if it matches the very last command? 
            # Standard terminals do.
            if not self.history or self.history[-1] != command:
                self.history.append(command)
        self.history_index = -1
        self.current_input = ""

class BlockHeader(Static):
    """Header for a block showing prompt, timestamp, etc."""
    DEFAULT_CSS = """
    BlockHeader {
        layout: horizontal;
        height: 1;
        dock: top;
        background: $surface;
        color: $text;
        padding-left: 1;
        padding-right: 1;
    }
    .prompt-symbol {
        color: $accent;
        margin-right: 1;
    }
    .prompt-symbol-ai {
        color: $warning;
        margin-right: 1;
    }
    .command-text {
        color: $success-lighten-2;
        text-style: bold;
    }
    .timestamp {
        color: $text-muted;
        min-width: 20;
        text-align: right;
        dock: right;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        icon = "➜"
        header_class = "prompt-symbol"
        
        if self.block.type == BlockType.AI_QUERY:
            icon = "🤖" # or ?
            header_class = "prompt-symbol-ai"
        elif self.block.type == BlockType.AI_RESPONSE:
            icon = "✨"
            header_class = "prompt-symbol-ai"
            
        yield Label(icon, classes=header_class)
        yield Label(self.block.content_input or "AI Generating...", classes="command-text")
        
        # Format timestamp
        ts_str = self.block.timestamp.strftime("%H:%M:%S")
        yield Label(ts_str, classes="timestamp")

class BlockBody(Static):
    """Body containing the command output."""
    DEFAULT_CSS = """
    BlockBody {
        padding: 0 1; 
        color: $text;
    }
    """
    
    content_text = reactive("")

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block
        self.content_text = block.content_output

    def watch_content_text(self, new_text: str):
        if self.block.type == BlockType.AI_RESPONSE:
            from rich.markdown import Markdown
            self.update(Markdown(new_text))
        else:
            self.update(new_text)

class BlockFooter(Static):
    """Footer showing exit code/status."""
    DEFAULT_CSS = """
    BlockFooter {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
        color: $error;
    }
    """
    
    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        if self.block.exit_code is not None and self.block.exit_code != 0:
            yield Label(f"Exit Code: {self.block.exit_code}")
        elif self.block.is_running:
            yield Label("Running...", classes="running-spinner")

class BlockWidget(Static):
    """
    A widget representing a single interaction block.
    """
    DEFAULT_CSS = """
    BlockWidget {
        layout: vertical;
        background: $surface-darken-1;
        margin-bottom: 1;
        border-bottom: solid $surface-lighten-1;
    }
    """

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block
        self.body_widget = BlockBody(block)
        self.footer_widget = BlockFooter(block)

    def compose(self) -> ComposeResult:
        yield BlockHeader(self.block)
        yield self.body_widget
        yield self.footer_widget

    def update_output(self, new_chunk: str):
        self.block.content_output += new_chunk
        self.body_widget.content_text = self.block.content_output

    def set_loading(self, loading: bool):
        self.block.is_running = loading
        self.footer_widget.remove()
        self.footer_widget = BlockFooter(self.block)
        self.mount(self.footer_widget)

    def set_exit_code(self, code: int):
        self.block.exit_code = code
        self.set_loading(False)

class HistoryViewport(VerticalScroll):
    """Scrollable container for blocks."""
    DEFAULT_CSS = """
    HistoryViewport {
        height: 1fr;
        border: solid $accent;
    }
    """
    
    def on_mount(self):
        self.scroll_end(animate=False)
