from datetime import datetime
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical, Container
from textual.widgets import Input, Static, Label, Button
from textual.reactive import reactive
from textual.message import Message
from textual import on
try:
    import pyperclip
except ImportError:
    pyperclip = None

from rich.syntax import Syntax
from rich.text import Text

from models import BlockState, BlockType

class InputController(Input):
    """
    Detached input widget.
    State management (history cycling) will be handled by the main App or a controller class
    wrapping this, for simplicity we just emit events on submit.
    """
    # Removed BINDINGS for up/down to handle manually in on_key
    
    async def on_key(self, event):
        # Handle navigation keys manually to support both Suggester and History
        if event.key == "up":
            if self.value.startswith("/"):
                # Delegate to Suggester logic
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    suggester.select_prev()
                    event.stop()
                    return
            # Fallback to History
            self.action_history_up()
            event.stop()
            
        elif event.key == "down":
            if self.value.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    suggester.select_next()
                    event.stop()
                    return
            self.action_history_down()
            event.stop()

        elif event.key == "tab" or event.key == "enter":
            if self.value.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    complete = suggester.get_selected()
                    if complete:
                        # Logic to determine if we are completing a command or an arg
                        parts = self.value.split(" ")
                        if len(parts) == 1:
                            # Completing command
                            self.value = complete + " "
                            # Is there a submenu? The updated filters will run on change.
                            # We stop event to prevent submit
                            event.stop()
                        else:
                            # Completing arg
                            # Replace last part
                            new_val = " ".join(parts[:-1]) + " " + complete
                            self.value = new_val
                            suggester.display = False
                            # We might want to submit here if user hit enter?
                            # User said "drill into sub menu", so maybe enter on arg submits?
                            # If it was Tab, we don't submit. If Enter, we might.
                            if event.key == "enter":
                                # Let it bubble to submit?
                                # But we just autocompleted. Usually you hit enter again.
                                suggester.display = False
                                event.stop()
                            else:
                                event.stop()
                        
                        self.cursor_position = len(self.value)
                        return
                    
        elif event.key == "escape":
             # Close suggester
             suggester = self.app.query_one("CommandSuggester")
             if suggester.display:
                 suggester.display = False
                 event.stop()


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

    def add_to_history(self, command: str):
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
        self.history_index = -1

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
            self.cursor_position = len(self.value)
        else:
            self.history_index = -1
            self.value = self.current_input
            self.cursor_position = len(self.value)

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

from textual.widgets import ListView, ListItem
class CommandItem(ListItem):
    def __init__(self, label_text: str, value: str):
        super().__init__(Label(label_text))
        self.value = value

class CommandSuggester(Static):
    """Popup for command suggestions."""
    DEFAULT_CSS = """
    CommandSuggester {
        layer: overlay;
        dock: bottom;
        margin-bottom: 4; /* Input(3) + Footer(1) space */
        width: 100%;
        height: auto;
        max-height: 10;
        background: $surface;
        border: solid $accent;
        display: none;
    }
    ListView {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0;
    }
    """
    
    can_focus = False 

    commands_data = {
        "/help": {"desc": "Show help screen", "args": []},
        "/provider": {"desc": "Select AI provider", "args": ["ollama", "openai", "lm_studio", "azure", "bedrock", "xai"]},
        "/model": {"desc": "Select AI model", "args": []}, # Dynamic?
        "/theme": {"desc": "Change UI theme", "args": ["monokai", "dracula", "nord", "solarized-light", "solarized-dark"]},
        "/ai": {"desc": "Toggle AI Mode", "args": []},
        "/chat": {"desc": "Toggle AI Mode", "args": []},
        "/prompts": {"desc": "Select System Persona", "args": ["default", "pirate", "concise", "agent"]},
        "/clear": {"desc": "Clear history", "args": []},
        "/quit": {"desc": "Exit application", "args": []}
    }

    def compose(self) -> ComposeResult:
        # yield ListView(id="suggestions")
        # We need to set can_focus on the ListView too
        lv = ListView(id="suggestions")
        lv.can_focus = False
        yield lv

    def update_filter(self, text: str):
        if not text.startswith("/"):
            self.display = False
            return
        
        lv = self.query_one(ListView)
        lv.clear()
        
        # Check for subcommand context
        # e.g. "/theme " -> show args
        parts = text.split(" ")
        base_cmd = parts[0]
        
        is_submenu = False
        candidates = []
        
        if len(parts) > 1 and base_cmd in self.commands_data:
             # We are in args mode
             is_submenu = True
             prefix = " ".join(parts[1:])
             args = self.commands_data[base_cmd]["args"]
             # Filter args
             for arg in args:
                 if arg.startswith(prefix):
                     candidates.append((arg, ""))
        else:
            # We are in command mode
            # Filter commands
            for cmd, data in self.commands_data.items():
                if cmd.startswith(base_cmd):
                    candidates.append((cmd, data["desc"]))

        if not candidates:
            self.display = False
            return
            
        self.display = True
        
        for text_val, desc in candidates:
            # Render: Command (bold) -- Description (dim)
            label_str = f"{text_val:<15} {desc}" if desc else text_val
            # Store just the text_val as the value to autocomplete
            lv.append(CommandItem(label_str, text_val))
        
        # Select first by default
        if len(lv.children) > 0:
            lv.index = 0

    def select_next(self):
        self.query_one(ListView).action_cursor_down()
        
    def select_prev(self):
        self.query_one(ListView).action_cursor_up()
        
    def get_selected(self) -> str:
        lv = self.query_one(ListView)
        if lv.index is not None and 0 <= lv.index < len(lv.children):
             # Access value from CommandItem
             item = lv.children[lv.index]
             if isinstance(item, CommandItem):
                 return item.value
        return ""

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
    .metadata-label {
        color: $text-muted;
        text-style: italic;
        margin-right: 1;
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
        
        if self.block.type == BlockType.AI_RESPONSE:
            # Metadata
            meta = self.block.metadata
            if meta:
                model = meta.get("model", "")
                ctx = meta.get("context", "")
                if model:
                    # Clean model name (e.g. ollama/llama3 -> llama3)
                    if "/" in model:
                        model = model.split("/")[-1]
                    yield Label(f" [{model}]", classes="metadata-label")
                if ctx and ctx != "0 chars":
                    yield Label(f" ({ctx})", classes="metadata-label")

        # Format timestamp
        ts_str = self.block.timestamp.strftime("%H:%M:%S")
        yield Label(ts_str, classes="timestamp")



class ThinkingWidget(Static):
    """Collapsible widget for AI thinking process."""
    DEFAULT_CSS = """
    ThinkingWidget {
        height: auto;
        padding: 0 1;
    }
    .thinking-header {
        color: $text-muted;
        text-style: italic;
    }
    .thinking-content {
        display: none;
        color: $text-muted;
        padding-left: 2;
        border-left: solid $text-muted;
    }
    .thinking-content.visible {
        display: block;
    }
    """
    
    thinking_text = reactive("")

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        yield Button("▶ Thinking...", variant="default", classes="thinking-header")
        yield Static("", classes="thinking-content", id="thinking-content")

    def watch_thinking_text(self, new_text: str):
        content = self.query_one("#thinking-content", Static)
        from rich.markdown import Markdown
        content.update(Markdown(new_text))
        
    @on(Button.Pressed)
    def toggle_thinking(self):
        content = self.query_one("#thinking-content")
        content.toggle_class("visible")
        btn = self.query_one(Button)
        if content.has_class("visible"):
            btn.label = "▼ Thinking..."
        else:
            btn.label = "▶ Thinking..."


class ExecutionWidget(Static):
    """Widget for Command execution output with Copy button."""
    DEFAULT_CSS = """
    ExecutionWidget {
        height: auto;
        padding: 0 1;
        margin-top: 1;
    }
    .exec-header {
        layout: horizontal;
        height: 1;
        background: $surface-lighten-1;
    }
    .exec-title {
        color: $accent;
        width: 1fr;
    }
    .copy-btn {
        min-width: 1;
        width: 8;
        height: 1;
        border: none;
        background: $primary;
        color: $text;
    }
    """
    
    exec_output = reactive("")

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block

    def compose(self) -> ComposeResult:
        # If there is output, show header + content
        yield Static(id="exec-area")

    def watch_exec_output(self, new_text: str):
        # We only rebuild if there is content
        area = self.query_one("#exec-area")
        area.remove_children()
        
        if new_text:
            # Header with Copy
            with Container(classes="exec-header"):
                 yield Label("Command Output", classes="exec-title")
                 yield Button("Copy", classes="copy-btn", id="copy-btn")
            
            # Content
            # We assume it's text, or markdown code block? 
            # App handles formatting in previous implementation. 
            # Let's just render the raw text in a rich Syntax or Markdown block? 
            # The app was appending ```text ... ```. 
            # Let's stick to Markdown update for now.
            from rich.markdown import Markdown
            area.mount(Static(Markdown(new_text)))

    @on(Button.Pressed, "#copy-btn")
    def copy_output(self):
        # Strip markdown fences if simple
        text = self.block.content_exec_output
        try:
            # Simple heuristic to strip markdown code blocks if present
            if text.startswith("\n```text\n") and text.endswith("\n```\n"):
                text = text[7:-5]
            
            if pyperclip:
                pyperclip.copy(text)
                self.notify("Copied to clipboard!")
            else:
                self.notify("pyperclip not installed", severity="error")
        except Exception as e:
            self.notify(f"Clipboard error: {e}", severity="error")

class BlockBody(Static):
    """Body containing the simple text content (e.g. User Input)."""
    DEFAULT_CSS = """
    BlockBody {
        padding: 0 1; 
        color: $text;
    }
    """
    def __init__(self, text: str):
        super().__init__()
        self.text = text
    
    def compose(self) -> ComposeResult:
        yield Label(self.text)

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
        self.header = BlockHeader(block)
        
        # Sub-widgets
        self.body_widget = None # For simple text (User Query)
        self.thinking_widget = None 
        self.exec_widget = None
        self.footer_widget = BlockFooter(block)

        if block.type == BlockType.AI_RESPONSE:
            self.thinking_widget = ThinkingWidget(block)
            self.exec_widget = ExecutionWidget(block)
        else:
            # Command or AI Query
            # For AI Query, content_input is the text.
            # For Command (CLI mode), content_input is command, content_output is result.
            # But we merged AI Response.
            # Let's keep it simple: If not AI_RESPONSE, just show generic body.
            text = block.content_input if block.type == BlockType.AI_QUERY else block.content_output
            if block.type == BlockType.COMMAND:
                 # CLI command output
                 text = block.content_output
            self.body_widget = BlockBody(text)

    def compose(self) -> ComposeResult:
        yield self.header
        
        if self.thinking_widget:
            yield self.thinking_widget
        
        if self.exec_widget:
            yield self.exec_widget
            
        if self.body_widget:
            yield self.body_widget
            
        yield self.footer_widget

    def update_output(self, new_chunk: str):
        # Dispatch update
        if self.block.type == BlockType.AI_RESPONSE:
            # We assume new_chunk is appended to content_output (Thinking)
            # UNLESS app.py updates content_exec_output using a different specific method?
            # app.py calls `widget.update_output(chunk)` for AI text.
            # app.py calls `widget.update_output(full_exec)` for execution?
            # We need to distinguish or update properties directly.
            
            # For now, let's assume `update_output` is for the MAIN text stream (Thinking).
            self.block.content_output = new_chunk # app.py passes full text usually? No, execute_ai passes chunk?
            # execute_ai passes chunk.
            # run_agent_command passes full text.
            # This is messy.
            
            # Let's rely on Reactive?
            # If app.py updates block.content_output, does widget know?
            # We need to manually update widget reactive props.
            if self.thinking_widget:
                 self.thinking_widget.thinking_text = self.block.content_output
            if self.exec_widget:
                 self.exec_widget.exec_output = self.block.content_exec_output
                 
        else:
             # Standard body update
             # self.body_widget.update(...) # Body is static label?
             # Re-mount or update generic text
             pass

    def update_metadata(self):
        self.header.remove()
        self.header = BlockHeader(self.block)
        # We need to mount it at top
        self.mount(self.header, before=self.children[0])

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
