"""Agent Response block widget for structured think → tool → response flow."""

from textual import on
from textual.app import ComposeResult

from models import AgentIteration, BlockState, ToolCallState

from .actions import ActionBar, ActionButton
from .base import BaseBlockWidget
from .execution import ExecutionWidget
from .iteration_container import IterationContainer
from .parts import BlockFooter, BlockHeader, BlockMeta
from .response import ResponseWidget


class AgentResponseBlock(BaseBlockWidget):
    """Block widget for agent mode responses with structured iterations.

    Agent mode displays:
    - Iterations (each with thinking, tool calls, response fragments)
    - Final response
    - Execution output (for backwards compatibility)

    This is distinct from AIResponseBlock which handles simple chat mode.
    """

    def __init__(self, block: BlockState):
        super().__init__(block)

        # Create sub-widgets
        self.header = BlockHeader(block)
        self.meta_widget = BlockMeta(block)
        self.exec_widget = ExecutionWidget(block)
        self.iteration_container = IterationContainer(
            show_thinking=True, classes="" if block.iterations else "empty"
        )
        self.response_widget = ResponseWidget(block)

        # Create action bar with meta info
        meta_text = self._build_meta_text()
        self.action_bar = ActionBar(
            block_id=block.id, show_fork=True, show_edit=True, meta_text=meta_text
        )

        self.footer_widget = BlockFooter(block)

        # Apply agent mode class
        self.add_class("mode-agent")

    def _build_meta_text(self) -> str:
        """Build the metadata text for the action bar."""
        parts = []
        meta = self.block.metadata

        if meta.get("model"):
            model = meta["model"]
            if len(model) > 20:
                model = model[:17] + "..."
            parts.append(model)

        if meta.get("tokens"):
            parts.append(f"{meta['tokens']} tok")

        if meta.get("cost"):
            parts.append(f"${meta['cost']:.4f}")

        return " · ".join(parts) if parts else ""

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.meta_widget
        # Note: exec_widget intentionally not yielded - iterations handle tool display
        yield self.iteration_container
        yield self.response_widget
        yield self.action_bar
        if self.footer_widget._has_content():
            yield self.footer_widget

    def update_output(self, new_content: str = ""):
        """Update the response display."""
        full_text = self.block.content_output or ""

        # In agent mode, thinking is extracted per-iteration
        # so we just display the final response directly
        if self.response_widget:
            self.response_widget.content_text = full_text
            # Simple mode if no execution output
            exec_out = getattr(self.block, "content_exec_output", "")
            is_simple = not exec_out and not self.block.iterations
            self.response_widget.set_simple(is_simple)

        # Update exec output widget
        exec_out = getattr(self.block, "content_exec_output", "")
        if self.exec_widget:
            self.exec_widget.exec_output = exec_out

    def update_metadata(self):
        """Refresh the metadata widget and action bar."""
        try:
            if self.meta_widget and self.meta_widget in self.children:
                self.meta_widget.remove()

            self.meta_widget = BlockMeta(self.block)

            children_list = list(self.children)
            if children_list:
                self.mount(self.meta_widget, after=children_list[0])
            else:
                self.mount(self.meta_widget)

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

    # Iteration management methods
    def add_iteration(self, iteration: AgentIteration):
        """Add a new iteration to the container."""
        self.block.iterations.append(iteration)
        return self.iteration_container.add_iteration(iteration)

    def update_iteration(
        self,
        iteration_id: str,
        status: str | None = None,
        thinking: str | None = None,
        response: str | None = None,
        duration: float | None = None,
    ):
        """Update an existing iteration."""
        self.iteration_container.update_iteration(
            iteration_id=iteration_id,
            status=status,
            thinking=thinking,
            response=response,
            duration=duration,
        )

    def remove_iteration(self, iteration_id: str) -> None:
        """Remove a specific iteration."""
        self.iteration_container.remove_iteration(iteration_id)
        self.block.iterations = [
            i for i in self.block.iterations if i.id != iteration_id
        ]

    def add_iteration_tool_call(self, iteration_id: str, tool_call: ToolCallState):
        """Add a tool call to a specific iteration."""
        self.iteration_container.add_tool_call(iteration_id, tool_call)

    def update_iteration_tool_call(
        self,
        iteration_id: str,
        tool_id: str,
        status: str | None = None,
        duration: float | None = None,
    ):
        """Update a tool call within an iteration."""
        self.iteration_container.update_tool_call(
            iteration_id=iteration_id, tool_id=tool_id, status=status, duration=duration
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
            self.post_message(
                self.CopyRequested(self.block.id, self.block.content_output or "")
            )
        elif event.action == "retry":
            self.post_message(self.RetryRequested(self.block.id))
        elif event.action == "edit":
            self.post_message(
                self.EditRequested(self.block.id, self.block.content_input)
            )
        elif event.action == "fork":
            self.post_message(self.ForkRequested(self.block.id))
