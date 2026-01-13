"""AI Response block widget for chat mode (simple Q&A)."""

from typing import Any

from textual import on
from textual.app import ComposeResult

from models import BlockState

from .actions import ActionBar, ActionButton
from .base import BaseBlockWidget
from .execution import ExecutionWidget
from .parts import BlockFooter, BlockHeader, BlockMeta
from .response import ResponseWidget
from .thinking import ThinkingWidget
from .tool_accordion import ToolAccordion


class AIResponseBlock(BaseBlockWidget):
    """Block widget for simple chat mode AI responses.

    Chat mode: Simple Q&A without structured iterations
    - Optional thinking (for models that include <think> tags)
    - Optional tool accordion (for single-shot tool calls)
    - Response content

    For agent mode with structured iterations, use AgentResponseBlock.
    """

    def __init__(self, block: BlockState):
        super().__init__(block)

        # Create sub-widgets
        self.header = BlockHeader(block)
        self.meta_widget = BlockMeta(block)
        self.thinking_widget = ThinkingWidget(block)
        self.exec_widget = ExecutionWidget(block)
        self.tool_accordion = ToolAccordion(classes="empty")
        self.response_widget = ResponseWidget(block)

        # Create action bar with meta info
        meta_text = self._build_meta_text()
        self.action_bar = ActionBar(
            block_id=block.id, show_fork=True, show_edit=True, meta_text=meta_text
        )

        self.footer_widget = BlockFooter(block)

        # Apply chat mode class
        self.add_class("mode-chat")

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
        yield self.thinking_widget
        yield self.exec_widget
        yield self.tool_accordion
        yield self.response_widget
        yield self.action_bar
        if self.footer_widget._has_content():
            yield self.footer_widget

    def update_output(self, new_content: str = ""):
        """Update the AI response display."""
        full_text = self.block.content_output or ""

        # Split Reasoning vs Final Answer for models that use <think> tags
        reasoning = ""
        final_answer = full_text

        lower_text = full_text.lower()
        if "<think>" in lower_text:
            if "</think>" in lower_text:
                # Completed reasoning
                parts = full_text.split("</think>", 1)
                reasoning_raw = parts[0]
                final_answer = parts[1].strip()

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

        exec_out = getattr(self.block, "content_exec_output", "")
        if self.exec_widget:
            self.exec_widget.exec_output = exec_out

        # Check if we have tool calls
        has_tools = (
            bool(self.block.tool_calls) or "empty" not in self.tool_accordion.classes
        )

        if self.response_widget:
            self.response_widget.content_text = final_answer

            # Simple mode conditions:
            # - No reasoning AND no execution output
            # - OR we have tools and minimal response (tool result is the answer)
            is_minimal_response = len(final_answer.strip()) < 50
            is_simple = (
                (not reasoning)
                and (not exec_out)
                and not (has_tools and is_minimal_response)
            )

            # If we have tools and very little text response, use simple mode
            # to de-emphasize the text (tool result is the answer)
            if has_tools and is_minimal_response and final_answer.strip():
                is_simple = True

            self.response_widget.set_simple(is_simple)

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

        if self.thinking_widget:
            if not loading:
                self.thinking_widget.stop_loading()
                self.thinking_widget.force_render()

    def add_tool_call(
        self,
        tool_id: str,
        tool_name: str,
        arguments: str = "",
        status: str = "running",
        streaming: bool = False,
    ):
        """Add a tool call to the accordion (for chat mode tool calls)."""
        return self.tool_accordion.add_tool(
            tool_id=tool_id,
            tool_name=tool_name,
            arguments=arguments,
            status=status,
            streaming=streaming,
        )

    def update_tool_call(
        self,
        tool_id: str,
        status: str | None = None,
        output: str | None = None,
        duration: float | None = None,
        streaming: bool = False,
    ):
        """Update an existing tool call in the accordion."""
        self.tool_accordion.update_tool(
            tool_id=tool_id,
            status=status,
            output=output,
            duration=duration,
            streaming=streaming,
        )

    def update_tool_progress(self, tool_id: str, progress: Any) -> None:
        item = self.tool_accordion.get_tool(tool_id)
        if item:
            item.update_progress(progress)

    @on(ActionButton.ActionPressed)
    def on_action_pressed(self, event: ActionButton.ActionPressed) -> None:
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
