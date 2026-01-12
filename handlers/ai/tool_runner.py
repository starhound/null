"""Tool execution engine."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, ClassVar

from models import AgentIteration, BlockState, ToolCallState
from tools import ToolCall, ToolRegistry, ToolResult
from tools.streaming import StreamingToolCall

if TYPE_CHECKING:
    from app import NullApp
    from widgets import AIResponseBlock, BaseBlockWidget


class ToolRunner:
    """Handles tool execution, streaming, and approval."""

    _active_streaming_calls: ClassVar[dict[str, StreamingToolCall]] = {}

    def __init__(self, app: NullApp):
        self.app = app
        self._tool_registry: ToolRegistry | None = None

    def get_registry(self) -> ToolRegistry:
        """Get or create the tool registry."""
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry(
                mcp_manager=getattr(self.app, "mcp_manager", None)
            )
        return self._tool_registry

    async def cancel_tool(self, tool_id: str) -> None:
        """Cancel a running streaming tool."""
        if tool_id in self._active_streaming_calls:
            self._active_streaming_calls[tool_id].cancel()

    async def request_approval(
        self, tool_calls: list, iteration_number: int = 1
    ) -> str:
        """Request user approval for tool execution."""
        from screens import ToolApprovalScreen

        tool_data = [{"name": tc.name, "arguments": tc.arguments} for tc in tool_calls]

        screen = ToolApprovalScreen(
            tool_calls=tool_data, iteration_number=iteration_number
        )

        # Wait for user decision
        result = await self.app.push_screen_wait(screen)
        return result or "cancel"

    async def execute_streaming_command(
        self,
        tool_call: ToolCall,
        registry: ToolRegistry,
        ai_widget: AIResponseBlock,
        tool_id: str,
        tool_state: Any,
    ) -> ToolResult:
        """Execute run_command with streaming output."""
        from tools import ToolProgress, ToolStatus
        from tools.builtin import run_command

        command = tool_call.arguments.get("command", "")
        working_dir = tool_call.arguments.get("working_dir")

        streaming_call = StreamingToolCall(
            id=tool_id,
            name=tool_call.name,
            arguments=tool_call.arguments,
        )
        self._active_streaming_calls[tool_id] = streaming_call

        ai_widget.update_tool_call(
            tool_id=tool_id,
            status="running",
            output="",
            streaming=True,
        )

        def on_progress(progress: ToolProgress) -> None:
            status_map = {
                ToolStatus.RUNNING: "running",
                ToolStatus.COMPLETED: "success",
                ToolStatus.FAILED: "error",
                ToolStatus.CANCELLED: "error",
            }
            status = status_map.get(progress.status, "running")

            self.app.call_from_thread(
                ai_widget.update_tool_call,
                tool_id=tool_id,
                status=status if progress.is_complete else "running",
                output=progress.output,
                duration=progress.elapsed,
                streaming=not progress.is_complete,
            )

            if progress.progress is not None:
                self.app.call_from_thread(
                    ai_widget.update_tool_progress,
                    tool_id,
                    progress,
                )

        try:
            result = await run_command(
                command=command,
                working_dir=working_dir,
                on_progress=on_progress,
                tool_call=streaming_call,
            )
            is_error = "[Exit code:" in result or "[Error" in result
            return ToolResult(tool_call.id, result, is_error=is_error)
        except Exception as e:
            return ToolResult(tool_call.id, f"[Error: {e!s}]", is_error=True)
        finally:
            self._active_streaming_calls.pop(tool_id, None)

    async def process_chat_tools(
        self,
        tool_calls: list,
        block_state: BlockState,
        widget: BaseBlockWidget,
        registry: ToolRegistry,
    ) -> list[ToolResult]:
        """Process tool calls in chat mode (non-agent)."""
        from widgets.blocks import AIResponseBlock

        results: list[ToolResult] = []
        ai_widget: AIResponseBlock | None = (
            widget if isinstance(widget, AIResponseBlock) else None
        )

        for tc in tool_calls:
            tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
            start_time = time.time()

            tool_state = ToolCallState(
                id=tc.id,
                tool_name=tc.name,
                arguments=json.dumps(tc.arguments, indent=2)
                if isinstance(tc.arguments, dict)
                else str(tc.arguments),
                status="running",
            )
            block_state.tool_calls.append(tool_state)

            if ai_widget:
                ai_widget.add_tool_call(
                    tool_id=tc.id,
                    tool_name=tc.name,
                    arguments=tool_state.arguments,
                    status="running",
                )

            needs_approval = registry.requires_approval(tc.name)
            if needs_approval:
                approval_result = await self.request_approval([tc])

                if approval_result == "cancel":
                    self.app._ai_cancelled = True
                    break
                elif approval_result == "reject":
                    results.append(
                        ToolResult(
                            tc.id, "Tool execution rejected by user.", is_error=True
                        )
                    )
                    continue

            try:
                result = await registry.execute_tool(tool_call)
            except Exception as e:
                result = ToolResult(
                    tc.id, f"Error executing tool: {e!s}", is_error=True
                )

            results.append(result)
            duration = time.time() - start_time

            tool_state.status = "error" if result.is_error else "success"
            tool_state.output = result.content
            tool_state.duration = duration

            if ai_widget:
                content_preview = (
                    result.content[:1000]
                    if len(result.content) > 1000
                    else result.content
                )
                ai_widget.update_tool_call(
                    tool_id=tc.id,
                    status=tool_state.status,
                    output=content_preview,
                    duration=duration,
                )

            result_display = (
                f"\n**Result ({tc.name}):**\n```\n{result.content[:1000]}\n```\n"
            )
            if len(result.content) > 1000:
                result_display += f"... ({len(result.content)} chars total)\n"

            block_state.content_exec_output += result_display
            widget.update_output(block_state.content_output)

        return results

    async def process_agent_tools(
        self,
        tool_calls: list,
        registry: ToolRegistry,
        iteration: AgentIteration,
        block_state: BlockState,
        widget: BaseBlockWidget,
        has_iteration_ui: bool,
    ) -> list[ToolResult]:
        """Execute tools within a specific agent iteration."""
        from widgets.blocks import AIResponseBlock

        results: list[ToolResult] = []
        ai_widget: AIResponseBlock | None = (
            widget if isinstance(widget, AIResponseBlock) else None
        )

        for tc in tool_calls:
            tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
            start_time = time.time()

            # Create tool call state
            tool_state = ToolCallState(
                id=tc.id,
                tool_name=tc.name,
                arguments=json.dumps(tc.arguments, indent=2)
                if isinstance(tc.arguments, dict)
                else str(tc.arguments),
                status="running",
            )
            block_state.tool_calls.append(tool_state)

            # Add to accordion if available
            if ai_widget:
                ai_widget.add_tool_call(
                    tool_id=tc.id,
                    tool_name=tc.name,
                    arguments=tool_state.arguments,
                    status="running",
                )

            # Check if approval is needed
            needs_approval = registry.requires_approval(tc.name)

            if needs_approval:
                approval_result = await self.request_approval([tc])

                if approval_result == "cancel":
                    self.app._ai_cancelled = True
                    break
                elif approval_result == "reject":
                    results.append(
                        ToolResult(
                            tc.id, "Tool execution rejected by user.", is_error=True
                        )
                    )
                    continue

            is_run_command = tc.name == "run_command"

            if is_run_command and ai_widget:
                result = await self.execute_streaming_command(
                    tool_call, registry, ai_widget, tc.id, tool_state
                )
            else:
                result = await registry.execute_tool(tool_call)

            results.append(result)
            duration = time.time() - start_time

            tool_state.status = "error" if result.is_error else "success"
            tool_state.output = result.content
            tool_state.duration = duration

            self.app.agent_manager.record_tool_call(
                tool_name=tc.name,
                args=tool_state.arguments,
                result=result.content[:500],
                success=not result.is_error,
                duration=duration,
            )

            if ai_widget:
                content_preview = (
                    result.content[:1000]
                    if len(result.content) > 1000
                    else result.content
                )
                ai_widget.update_tool_call(
                    tool_id=tc.id,
                    status=tool_state.status,
                    output=content_preview,
                    duration=duration,
                )

            # Show the result
            result_display = f"\n**Result:**\n```\n{result.content[:1000]}\n```\n"
            if len(result.content) > 1000:
                result_display += f"... ({len(result.content)} chars total)\n"

            block_state.content_exec_output += result_display
            widget.update_output(block_state.content_output)

        return results
