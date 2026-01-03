from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Label
from textual.reactive import reactive
from textual.events import Click
from textual import on

try:
    import pyperclip
except ImportError:
    pyperclip = None

from models import BlockState


class ExecutionWidget(Static):
    """Widget for command execution output with copy button."""

    exec_output = reactive("")
    is_expanded = reactive(False)

    def __init__(self, block: BlockState):
        super().__init__()
        self.block = block
        # Initialize from block state for restored sessions
        if hasattr(block, 'content_exec_output') and block.content_exec_output:
            self.exec_output = block.content_exec_output

    def compose(self) -> ComposeResult:
        with Container(id="exec-container", classes="hidden collapsed"):
            # Header is clickable to toggle
            with Static(classes="exec-header", id="exec-header"):
                yield Label("▶", classes="toggle-icon", id="toggle-icon")
                yield Label("⚡ Execution Log", classes="exec-title")
                yield Label("", classes="exec-count", id="exec-count")
                yield Static("copy", classes="copy-btn", id="copy-btn")
            
            # Content container
            with Container(classes="exec-scroll", id="exec-scroll"):
                yield Static(id="exec-content")

    def watch_is_expanded(self, expanded: bool):
        """Toggle expanded state."""
        try:
            container = self.query_one("#exec-container")
            icon = self.query_one("#toggle-icon", Label)
            
            if expanded:
                container.remove_class("collapsed")
                icon.update("▼")
            else:
                container.add_class("collapsed")
                icon.update("▶")
        except Exception:
            pass

    def on_click(self, event: Click):
        """Handle clicks."""
        # Toggle on header click (first row)
        # The copy button has its own handler via @on(Click, "#copy-btn")
        if event.y == 0:
            self.is_expanded = not self.is_expanded
            event.stop()

    def watch_exec_output(self, new_text: str):
        try:
            container = self.query_one("#exec-container")
            content = self.query_one("#exec-content", Static)
            count_label = self.query_one("#exec-count", Label)

            if new_text:
                self.add_class("has-content")
                container.remove_class("hidden")
                
                # Update content
                from rich.markdown import Markdown
                content.update(Markdown(new_text, code_theme="monokai"))
                
                # Update summary count (e.g. number of tool calls)
                import re
                tool_matches = re.findall(r'\*\*Tool Call: (.*?)\*\*', new_text)
                if tool_matches:
                    # Join unique names or sequentially? Sequential is better for history.
                    # Flatten/simplify showing only unique names if many? 
                    # Let's show first 3-4 distinct tools.
                    unique_tools = []
                    seen = set()
                    for t in tool_matches:
                        if t not in seen:
                            unique_tools.append(t)
                            seen.add(t)
                    
                    summary_text = ", ".join(unique_tools)
                    if len(summary_text) > 40:
                        summary_text = summary_text[:37] + "..."
                    
                    count_label.update(f"({summary_text})")
                else:
                    count_label.update("")
                    
            else:
                self.remove_class("has-content")
                container.add_class("hidden")
                content.update("")
        except Exception:
            pass

    @on(Click, "#copy-btn")
    def copy_output(self, event: Click):
        text = getattr(self.block, 'content_exec_output', '') or ''
        if not text:
            self.notify("Nothing to copy", severity="warning")
            return

        try:
            # Strip markdown code fences if present
            if text.startswith("```") and text.endswith("```"):
                lines = text.split('\n')
                if len(lines) > 2:
                    text = '\n'.join(lines[1:-1])

            if pyperclip:
                pyperclip.copy(text)
                self.notify("Copied to clipboard!")
            else:
                # Fallback: try using subprocess for Linux/macOS
                import subprocess
                import sys
                if sys.platform == 'linux':
                    try:
                        subprocess.run(['xclip', '-selection', 'clipboard'],
                                      input=text.encode(), check=True)
                        self.notify("Copied to clipboard!")
                        return
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pass
                self.notify("Install pyperclip: pip install pyperclip", severity="warning")
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")
