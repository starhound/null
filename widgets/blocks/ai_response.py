"""AI Response block widget with chat/agent mode distinction."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual import on

from models import BlockState, AgentIteration, ToolCallState
from .base import BaseBlockWidget
from .parts import BlockHeader, BlockMeta, BlockFooter
from .thinking import ThinkingWidget
from .execution import ExecutionWidget
from .response import ResponseWidget
from .actions import ActionBar, ActionButton
from .tool_accordion import ToolAccordion
from .iteration_container import IterationContainer


class AIResponseBlock(BaseBlockWidget):
    """Block widget for AI responses with chat/agent mode distinction.

    Chat mode: Simple Q&A without tool execution - subtle styling
    Agent mode: Tool-using responses - bold styling with tool accordion
    """

    is_agent_mode = reactive(False, init=False)

    def __init__(self, block: BlockState):
        super().__init__(block)

        # Detect agent mode from presence of tool calls, thinking, or exec output
        self._detect_mode()

        # Create sub-widgets
        self.header = BlockHeader(block)
        self.meta_widget = BlockMeta(block)
        self.thinking_widget = ThinkingWidget(block)
        self.exec_widget = ExecutionWidget(block)
        self.tool_accordion = ToolAccordion(classes="empty")
        self.iteration_container = IterationContainer(
            show_thinking=True,
            classes="empty" if not block.iterations else ""
        )
        self.response_widget = ResponseWidget(block)

        # Create action bar with meta info
        meta_text = self._build_meta_text()
        self.action_bar = ActionBar(
            block_id=block.id,
            show_fork=True,
            show_edit=True,
            meta_text=meta_text
        )

        self.footer_widget = BlockFooter(block)

        # Apply mode class
        self._apply_mode_class()

    def _detect_mode(self) -> None:
        """Detect whether this is chat or agent mode."""
        has_thinking = bool(self.block.content_thinking)
        has_exec = bool(getattr(self.block, 'content_exec_output', ''))
        has_tool_calls = bool(self.block.metadata.get('tool_calls'))
        has_iterations = bool(self.block.iterations)

        self.is_agent_mode = has_thinking or has_exec or has_tool_calls or has_iterations

    def _apply_mode_class(self) -> None:
        """Apply the appropriate CSS class for the current mode."""
        self.remove_class("mode-chat", "mode-agent")
        if self.is_agent_mode:
            self.add_class("mode-agent")
        else:
            self.add_class("mode-chat")

    def _build_meta_text(self) -> str:
        """Build the metadata text for the action bar."""
        parts = []
        meta = self.block.metadata

        if meta.get('model'):
            model = meta['model']
            # Shorten long model names
            if len(model) > 20:
                model = model[:17] + "..."
            parts.append(model)

        if meta.get('tokens'):
            parts.append(f"{meta['tokens']} tok")

        if meta.get('cost'):
            parts.append(f"${meta['cost']:.4f}")

        return " · ".join(parts) if parts else ""

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.meta_widget
        yield self.thinking_widget
        yield self.exec_widget
        yield self.iteration_container
        yield self.tool_accordion
        yield self.response_widget
        yield self.action_bar
        if self.footer_widget._has_content():
            yield self.footer_widget

    def watch_is_agent_mode(self, is_agent: bool) -> None:
        """Update styling when mode changes."""
        self._apply_mode_class()

        # Hide global thinking widget in agent mode (thinking is in iterations)
        if hasattr(self, 'thinking_widget') and self.thinking_widget:
            if is_agent:
                self.thinking_widget.display = False
            else:
                # Only show if it has content or we are not in agent mode
                self.thinking_widget.display = bool(self.thinking_widget.thinking_text)

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
                    reasoning = reasoning_raw
            else:
                # Still streaming reasoning
                final_answer = ""
                parts = full_text.split("<think>", 1)
                if len(parts) > 1:
                    reasoning = parts[1].strip()
                else:
                    reasoning = full_text

        # Update widgets
        if self.thinking_widget:
            self.thinking_widget.thinking_text = reasoning

        exec_out = getattr(self.block, 'content_exec_output', '')
        if self.exec_widget:
            self.exec_widget.exec_output = exec_out

        if self.response_widget:
            self.response_widget.content_text = final_answer

            # Simple mode if no reasoning and no execution
            is_simple = (not reasoning) and (not exec_out)
            self.response_widget.set_simple(is_simple)

        # Re-detect mode based on updated content
        old_mode = self.is_agent_mode
        self._detect_mode()
        if old_mode != self.is_agent_mode:
            self._apply_mode_class()

    def update_metadata(self):
        """Refresh the metadata widget and action bar."""
        try:
            # Remove old meta widget if it exists
            if self.meta_widget and self.meta_widget in self.children:
                self.meta_widget.remove()

            # Create new meta widget with current metadata
            self.meta_widget = BlockMeta(self.block)

            # Find the position after header
            children_list = list(self.children)
            if children_list:
                self.mount(self.meta_widget, after=children_list[0])
            else:
                self.mount(self.meta_widget)

            # Update action bar meta text
            if self.action_bar:
                meta_text = self._build_meta_text()
                self.action_bar.update_meta(meta_text)

        except Exception as e:
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

        # Update mode detection when loading completes
        if not loading:
            self._detect_mode()
            self._apply_mode_class()

    def add_tool_call(
        self,
        tool_id: str,
        tool_name: str,
        arguments: str = "",
        status: str = "running"
    ):
        """Add a tool call to the accordion (for agent mode)."""
        # Switch to agent mode if not already
        if not self.is_agent_mode:
            self.is_agent_mode = True
            self._apply_mode_class()

        return self.tool_accordion.add_tool(
            tool_id=tool_id,
            tool_name=tool_name,
            arguments=arguments,
            status=status
        )

    def update_tool_call(
        self,
        tool_id: str,
        status: str | None = None,
        output: str | None = None,
        duration: float | None = None
    ):
        """Update an existing tool call in the accordion."""
        self.tool_accordion.update_tool(
            tool_id=tool_id,
            status=status,
            output=output,
            duration=duration
        )

    # Iteration management methods for structured agent mode
    def add_iteration(self, iteration: AgentIteration):
        """Add a new iteration to the container (for structured agent mode)."""
        # Switch to agent mode if not already
        if not self.is_agent_mode:
            self.is_agent_mode = True
            self._apply_mode_class()

        # Add to block state
        self.block.iterations.append(iteration)

        # Add to container
        return self.iteration_container.add_iteration(iteration)

    def update_iteration(
        self,
        iteration_id: str,
        status: str | None = None,
        thinking: str | None = None,
        response: str | None = None,
        duration: float | None = None
    ):
        """Update an existing iteration."""
        self.iteration_container.update_iteration(
            iteration_id=iteration_id,
            status=status,
            thinking=thinking,
            response=response,
            duration=duration
        )

    def remove_iteration(self, iteration_id: str) -> None:
        """Remove a specific iteration."""
        self.iteration_container.remove_iteration(iteration_id)
        # Also remove from block state
        self.block.iterations = [i for i in self.block.iterations if i.id != iteration_id]

    def add_iteration_tool_call(
        self,
        iteration_id: str,
        tool_call: ToolCallState
    ):
        """Add a tool call to a specific iteration."""
        self.iteration_container.add_tool_call(iteration_id, tool_call)

    def update_iteration_tool_call(
        self,
        iteration_id: str,
        tool_id: str,
        status: str | None = None,
        duration: float | None = None
    ):
        """Update a tool call within an iteration."""
        self.iteration_container.update_tool_call(
            iteration_id=iteration_id,
            tool_id=tool_id,
            status=status,
            duration=duration
        )

    def get_current_iteration(self):
        """Get the most recently added iteration widget."""
        return self.iteration_container.get_current_iteration()

    # Action button handlers
    @on(ActionButton.Pressed)
    def on_action_pressed(self, event: ActionButton.Pressed) -> None:
        """Handle action button clicks."""
        event.stop()

        if event.action == "copy":
            self.post_message(self.CopyRequested(
                self.block.id,
                self.block.content_output or ""
            ))
        elif event.action == "retry":
            self.post_message(self.RetryRequested(self.block.id))
        elif event.action == "edit":
            self.post_message(self.EditRequested(
                self.block.id,
                self.block.content_input
            ))
        elif event.action == "fork":
            self.post_message(self.ForkRequested(self.block.id))
