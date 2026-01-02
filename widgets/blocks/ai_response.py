from textual.app import ComposeResult
from textual.events import Click
from textual import on

from models import BlockState
from .base import BaseBlockWidget
from .parts import BlockHeader, BlockMeta, BlockFooter
from .thinking import ThinkingWidget
from .execution import ExecutionWidget
from .response import ResponseWidget

class AIResponseBlock(BaseBlockWidget):
    """Block widget for AI responses with thinking and execution sections."""

    def __init__(self, block: BlockState):
        super().__init__(block)
        self.header = BlockHeader(block)
        self.meta_widget = BlockMeta(block)
        self.thinking_widget = ThinkingWidget(block)
        self.exec_widget = ExecutionWidget(block)
        self.response_widget = ResponseWidget(block)
        self.footer_widget = BlockFooter(block)

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.meta_widget
        yield self.thinking_widget
        yield self.exec_widget
        yield self.response_widget
        if self.footer_widget._has_content():
            yield self.footer_widget

    def update_output(self, new_content: str = ""):
        """Update the AI response display."""
        full_text = self.block.content_output or ""
        
        # Split Reasoning vs Final Answer
        # We look for <think> ... </think> style reasoning
        reasoning = ""
        final_answer = full_text
        
        lower_text = full_text.lower()
        if "<think>" in lower_text:
            if "</think>" in lower_text:
                # Completed reasoning
                parts = full_text.split("</think>", 1)
                reasoning_raw = parts[0]
                final_answer = parts[1].strip()
                
                # Clean up opening tag
                if "<think>" in reasoning_raw:
                     reasoning = reasoning_raw.split("<think>", 1)[1].strip()
                else:
                     reasoning = reasoning_raw # Should be rare
            else:
                # Still streaming reasoning
                final_answer = "" # No answer yet
                parts = full_text.split("<think>", 1)
                if len(parts) > 1:
                    reasoning = parts[1].strip()
                else:
                    reasoning = full_text # Edge case
        
        # Update widgets
        if self.thinking_widget:
            self.thinking_widget.thinking_text = reasoning
            
        exec_out = getattr(self.block, 'content_exec_output', '')
        if self.exec_widget:
            self.exec_widget.exec_output = exec_out

        if self.response_widget:
            self.response_widget.content_text = final_answer
            
            # Simple mode if no reasoning and no execution
            # This distinguishes "Chat" from "Agent" visually
            is_simple = (not reasoning) and (not exec_out)
            self.response_widget.set_simple(is_simple)

    def update_metadata(self):
        """Refresh the metadata widget to show updated values."""
        try:
            # Remove old meta widget if it exists
            if self.meta_widget and self.meta_widget in self.children:
                self.meta_widget.remove()

            # Create new meta widget with current metadata
            self.meta_widget = BlockMeta(self.block)

            # Find the position after header
            children_list = list(self.children)
            if children_list:
                # Mount after first child (header)
                self.mount(self.meta_widget, after=children_list[0])
            else:
                self.mount(self.meta_widget)
        except Exception as e:
            # Log error for debugging
            self.log.error(f"Failed to update metadata: {e}")

    def set_loading(self, loading: bool):
        """Set the loading state and update widgets."""
        self.block.is_running = loading

        try:
            self.footer_widget.remove()
        except Exception:
            pass

        self.footer_widget = BlockFooter(self.block)
        if self.footer_widget._has_content():
            self.mount(self.footer_widget)

        if self.thinking_widget:
            if not loading:
                self.thinking_widget.stop_loading()
                self.thinking_widget.force_render()

    @on(Click, "#retry-btn")
    def on_retry_clicked(self, event: Click):
        """Handle retry label click."""
        event.stop()
        self.post_message(self.RetryRequested(self.block.id))

    @on(Click, "#edit-btn")
    def on_edit_clicked(self, event: Click):
        """Handle edit label click."""
        event.stop()
        self.post_message(self.EditRequested(self.block.id, self.block.content_input))
