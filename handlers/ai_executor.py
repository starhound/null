"""AI Execution Handler."""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any, cast

from ai.base import Message, TokenUsage, calculate_cost, ToolCallData
from config import Config, get_settings
from models import AgentIteration, BlockType, ToolCallState
from textual.css.query import NoMatches
from tools import ToolCall, ToolResult, ToolRegistry
from widgets import BaseBlockWidget, AIResponseBlock, AgentResponseBlock, StatusBar
from .common import UIBuffer

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState


class AIExecutor:
    """Handles AI generation and execution."""

    def __init__(self, app: NullApp):
        self.app = app
        self._tool_registry: ToolRegistry | None = None

    def _get_tool_registry(self) -> ToolRegistry:
        """Get or create the tool registry."""
        if self._tool_registry is None:
            self._tool_registry = ToolRegistry(
                mcp_manager=getattr(self.app, "mcp_manager", None)
            )
        return self._tool_registry

    async def execute_ai(
        self, prompt: str, block_state: BlockState, widget: BaseBlockWidget
    ) -> None:
        """Execute AI generation with streaming response and tool support."""
        try:
            from context import ContextManager
            from prompts import get_prompt_manager

            # Get FRESH config values (not stale self.app.config)
            provider_name = Config.get("ai.provider") or ""
            active_key = Config.get("ai.active_prompt") or "default"

            # Get the AI provider (bail early if not configured)
            ai_provider = self.app.ai_provider
            if not ai_provider:
                widget.update_output("AI Provider not configured")
                widget.set_loading(False)
                return

            # Get model directly from provider (always current)
            model_name = ai_provider.model

            prompt_manager = get_prompt_manager()
            system_prompt = prompt_manager.get_prompt_content(active_key, provider_name)

            # Get model info for context limits
            model_info = ai_provider.get_model_info()
            max_tokens = model_info.context_window

            # Build proper message array (exclude current block)
            context_info = ContextManager.build_messages(
                self.app.blocks[:-1], max_tokens=max_tokens, reserve_tokens=1024
            )

            # Check if we're using unknown model with default context
            from ai.base import KNOWN_MODEL_CONTEXTS

            if model_name.lower() not in KNOWN_MODEL_CONTEXTS:
                is_known = any(
                    model_name.lower().startswith(k) for k in KNOWN_MODEL_CONTEXTS
                )
                if not is_known:
                    self.app.notify(
                        f"Unknown model '{model_name}', using 4k context limit",
                        severity="warning",
                    )

            if context_info.truncated:
                self.app.notify(
                    f"Context truncated to fit {max_tokens} token limit",
                    severity="warning",
                )

            # Store metadata
            block_state.metadata = {
                "provider": provider_name,
                "model": model_name,
                "context": f"~{context_info.estimated_tokens} tokens ({context_info.message_count} msgs)",
                "persona": active_key,
            }
            if widget:
                widget.update_metadata()

            is_agent_block = block_state.type == BlockType.AGENT_RESPONSE
            use_tools = ai_provider.supports_tools()

            # Cast messages to proper type (ContextManager returns compatible dict structure)
            messages = cast(list[Message], context_info.messages)

            if is_agent_block:
                # Agent mode: structured iterations with tool use
                # If using default prompt in agent mode, switch to specialized agent prompt
                # because default prompt forbids elaboration which contradicts agent reasoning
                if active_key == "default":
                    system_prompt = prompt_manager.get_prompt_content(
                        "agent", provider_name
                    )

                await self._execute_agent_mode(
                    prompt,
                    block_state,
                    widget,
                    messages,
                    system_prompt,
                    max_tokens,
                )
            elif use_tools:
                # Chat mode with tools
                await self._execute_with_tools(
                    prompt,
                    block_state,
                    widget,
                    messages,
                    system_prompt,
                    max_tokens,
                )
            else:
                # Chat mode without tools
                await self._execute_without_tools(
                    prompt,
                    block_state,
                    widget,
                    messages,
                    system_prompt,
                    max_tokens,
                )

        except asyncio.CancelledError:
            block_state.content_output += "\n\n[Cancelled]"
            block_state.is_running = False
            widget.update_output(block_state.content_output)
            widget.set_loading(False)
            self.app._active_worker = None
        except Exception as e:
            block_state.content_output = f"AI Error: {e!s}"
            block_state.is_running = False
            widget.update_output(f"Error: {e!s}")
            self.app._active_worker = None

    async def _execute_without_tools(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int,
    ):
        """Execute AI generation without tool support (legacy mode)."""
        ai_provider = self.app.ai_provider
        assert ai_provider is not None, "AI provider must be set"

        full_response = ""

        def update_callback(chunk: str):
            nonlocal full_response
            full_response += chunk
            block_state.content_output = full_response
            widget.update_output(full_response)

        buffer = UIBuffer(self.app, update_callback)

        try:
            async for chunk in ai_provider.generate(
                prompt, messages, system_prompt=system_prompt
            ):
                if self.app._ai_cancelled:
                    buffer.flush()
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    break

                buffer.write(chunk)

            buffer.flush()

        finally:
            buffer.stop()

        self._finalize_response(
            block_state, widget, full_response, messages, max_tokens
        )

    async def _execute_with_tools(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int,
    ):
        """Execute AI generation with tool calling support."""
        ai_provider = self.app.ai_provider
        assert ai_provider is not None, "AI provider must be set"

        registry = self._get_tool_registry()
        tools = registry.get_all_tools_schema()

        full_response = ""
        current_messages: list[Message] = list(messages)
        iteration = 0
        max_iterations = 3  # Limit tool loops - most tasks need 1-2
        total_usage: TokenUsage | None = None

        def update_callback(chunk: str):
            nonlocal full_response
            full_response += chunk
            block_state.content_output = full_response
            widget.update_output(full_response)

        buffer = UIBuffer(self.app, update_callback)

        try:
            while iteration < max_iterations:
                iteration += 1
                pending_tool_calls: list[Any] = []

                async for chunk in ai_provider.generate_with_tools(
                    prompt
                    if iteration == 1
                    else "",  # Only send prompt on first iteration
                    current_messages,
                    tools,
                    system_prompt=system_prompt,
                ):
                    if self.app._ai_cancelled:
                        buffer.flush()
                        full_response += "\n\n[Cancelled]"
                        block_state.content_output = full_response
                        widget.update_output(full_response)
                        break

                    # Handle text content
                    if chunk.text:
                        buffer.write(chunk.text)

                    # Collect tool calls
                    if chunk.tool_calls:
                        pending_tool_calls.extend(chunk.tool_calls)

                    # Track token usage from completed chunks
                    if chunk.is_complete and chunk.usage:
                        if total_usage is None:
                            total_usage = chunk.usage
                        else:
                            total_usage = total_usage + chunk.usage

                    if chunk.is_complete:
                        break

                # Flush remaining text from this iteration
                buffer.flush()

                # Check for cancellation
                if self.app._ai_cancelled:
                    break

                # If no tool calls, we're done
                if not pending_tool_calls:
                    break

                # Process tool calls (only take the first one to prevent over-eager behavior)
                tool_to_run = pending_tool_calls[:1]
                tool_results = await self._process_tool_calls(
                    tool_to_run, block_state, widget, registry
                )

                if not tool_results:
                    # User cancelled or no results
                    break

                # Add assistant message with tool call
                assistant_msg: Message = {
                    "role": "assistant",
                    "content": full_response,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in tool_to_run
                    ],
                }
                current_messages.append(assistant_msg)

                # Add tool result
                for result in tool_results:
                    tool_result_msg: Message = {
                        "role": "tool",
                        "tool_call_id": result.tool_call_id,
                        "content": result.content,
                    }
                    current_messages.append(tool_result_msg)

                # After first tool success, stop unless it was an error
                if iteration == 1 and tool_results and not tool_results[0].is_error:
                    # Give LLM one chance to provide a brief summary, but don't pass tools
                    # to prevent further tool calls
                    break

                # Clear prompt for next iteration (context is in messages)
                prompt = ""

        finally:
            buffer.stop()

        self._finalize_response(
            block_state, widget, full_response, messages, max_tokens, total_usage
        )

    async def _execute_agent_mode(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int,
    ):
        """Execute AI with structured think → tool → think flow."""
        from ai.thinking import get_thinking_strategy

        ai_provider = self.app.ai_provider
        assert ai_provider is not None, "AI provider must be set"

        registry = self._get_tool_registry()
        tools = registry.get_all_tools_schema()

        # Get thinking strategy for this provider/model
        provider_name = Config.get("ai.provider") or ""
        model_name = ai_provider.model
        strategy = get_thinking_strategy(provider_name, model_name)

        # Enhance system prompt with thinking instructions if needed
        enhanced_prompt = system_prompt
        if strategy.requires_prompting:
            prompt_addition = strategy.get_prompt_addition()
            if prompt_addition:
                enhanced_prompt = system_prompt + "\n\n" + prompt_addition

        # Agent settings
        ai_config = self.app.config.get("ai", {})
        max_iterations = ai_config.get("agent_max_iterations", 10)
        approval_mode = ai_config.get(
            "agent_approval_mode", "auto"
        )  # auto, per_tool, per_iteration
        auto_approve_all = False  # Set to True when user chooses "Approve All"

        full_response = ""
        current_messages: list[Message] = list(messages)
        iteration_num = 0
        total_usage: TokenUsage | None = None
        has_iteration_ui = isinstance(widget, AgentResponseBlock)
        # Cast widget to AgentResponseBlock for type checker when has_iteration_ui is True
        agent_widget: AgentResponseBlock | None = None
        if has_iteration_ui:
            assert isinstance(widget, AgentResponseBlock)
            agent_widget = widget

        while iteration_num < max_iterations:
            iteration_num += 1
            pending_tool_calls: list[Any] = []
            raw_response = ""
            iteration_start = time.time()

            # Create iteration state
            iteration = AgentIteration(
                iteration_number=iteration_num, status="thinking"
            )

            # Add iteration to UI if widget supports it
            if agent_widget is not None:
                agent_widget.add_iteration(iteration)

            # Stream AI response
            async for chunk in ai_provider.generate_with_tools(
                prompt if iteration_num == 1 else "",
                current_messages,
                tools,
                system_prompt=enhanced_prompt,
            ):
                if self.app._ai_cancelled:
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    iteration.status = "complete"
                    if agent_widget is not None:
                        agent_widget.update_iteration(iteration.id, status="complete")
                    break

                # Handle text content
                if chunk.text:
                    raw_response += chunk.text

                    # Extract thinking using strategy
                    thinking, remaining = strategy.extract_thinking(raw_response)

                    # Update iteration thinking
                    if thinking:
                        iteration.thinking = thinking
                        if agent_widget is not None:
                            agent_widget.update_iteration(
                                iteration.id, thinking=thinking
                            )

                    # Update main response (non-thinking content)
                    full_response = remaining if thinking else raw_response
                    block_state.content_output = full_response
                    widget.update_output(full_response)

                # Collect tool calls
                if chunk.tool_calls:
                    pending_tool_calls.extend(chunk.tool_calls)

                # Track token usage
                if chunk.is_complete and chunk.usage:
                    if total_usage is None:
                        total_usage = chunk.usage
                    else:
                        total_usage = total_usage + chunk.usage

                if chunk.is_complete:
                    break

            # Check for cancellation
            if self.app._ai_cancelled:
                break

            # If no tool calls, we're done - AI provided final response
            if not pending_tool_calls:
                iteration.status = "complete"
                iteration.duration = time.time() - iteration_start
                if agent_widget is not None:
                    # If this iteration has no thinking and no tools, remove it to avoid empty box
                    if not iteration.thinking and not iteration.tool_calls:
                        agent_widget.remove_iteration(iteration.id)
                    else:
                        agent_widget.update_iteration(
                            iteration.id, status="complete", duration=iteration.duration
                        )
                break

            # Check if approval is needed
            if approval_mode != "auto" and not auto_approve_all:
                iteration.status = "waiting_approval"
                if agent_widget is not None:
                    agent_widget.update_iteration(
                        iteration.id, status="waiting_approval"
                    )

                # Request approval for tool calls
                approval_result = await self._request_tool_approval(
                    pending_tool_calls, iteration_num
                )

                if approval_result == "cancel":
                    # User cancelled the entire agent loop
                    full_response += "\n\n[Agent cancelled by user]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    iteration.status = "complete"
                    if agent_widget is not None:
                        agent_widget.update_iteration(iteration.id, status="complete")
                    break

                elif approval_result == "reject":
                    # Skip these tools but continue
                    iteration.status = "complete"
                    iteration.duration = time.time() - iteration_start
                    if agent_widget is not None:
                        agent_widget.update_iteration(
                            iteration.id, status="complete", duration=iteration.duration
                        )
                    # Don't break - continue to next iteration without executing tools
                    prompt = ""
                    continue

                elif approval_result == "approve-all":
                    # Don't ask again
                    auto_approve_all = True

                # If "approve" or "approve-all", continue to execute

            # Update iteration status to executing
            iteration.status = "executing"
            if agent_widget is not None:
                agent_widget.update_iteration(iteration.id, status="executing")

            # Add assistant message with tool calls to conversation
            assistant_content = raw_response
            thinking, remaining = strategy.extract_thinking(raw_response)
            if remaining:
                assistant_content = remaining

            assistant_msg: Message = {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in pending_tool_calls
                ],
            }
            current_messages.append(assistant_msg)

            # Execute tool calls within this iteration
            tool_results = await self._execute_iteration_tools(
                pending_tool_calls,
                registry,
                iteration,
                block_state,
                widget,
                has_iteration_ui,
            )

            if not tool_results:
                # Tool execution failed or cancelled
                iteration.status = "complete"
                iteration.duration = time.time() - iteration_start
                if agent_widget is not None:
                    agent_widget.update_iteration(
                        iteration.id, status="complete", duration=iteration.duration
                    )
                break

            # Add tool results to conversation
            for result in tool_results:
                tool_result_msg: Message = {
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.content,
                }
                current_messages.append(tool_result_msg)

            # Mark iteration complete
            iteration.status = "complete"
            iteration.duration = time.time() - iteration_start
            if agent_widget is not None:
                agent_widget.update_iteration(
                    iteration.id, status="complete", duration=iteration.duration
                )

            # Clear prompt for next iteration
            prompt = ""

        # Check if we hit max iterations
        if iteration_num >= max_iterations:
            full_response += (
                f"\n\n*Warning: Reached maximum iterations ({max_iterations})*"
            )
            block_state.content_output = full_response
            widget.update_output(full_response)

        self._finalize_response(
            block_state, widget, full_response, messages, max_tokens, total_usage
        )

    async def _process_tool_calls(
        self,
        tool_calls: list[ToolCallData],
        block_state: BlockState,
        widget: BaseBlockWidget,
        registry: ToolRegistry,
    ) -> list[ToolResult]:
        """Process tool calls in chat mode (non-agent)."""
        import time

        from models import ToolCallState
        from tools import ToolCall, ToolResult
        from widgets.blocks import AIResponseBlock

        results: list[ToolResult] = []
        has_accordion = isinstance(widget, AIResponseBlock)
        ai_widget: AIResponseBlock | None = None
        if has_accordion:
            ai_widget = cast(AIResponseBlock, widget)

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

            if ai_widget is not None:
                ai_widget.add_tool_call(
                    tool_id=tc.id,
                    tool_name=tc.name,
                    arguments=tool_state.arguments,
                    status="running",
                )

            needs_approval = registry.requires_approval(tc.name)
            if needs_approval:
                approval_result = await self._request_tool_approval([tc])

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

            if ai_widget is not None:
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

    async def _execute_iteration_tools(
        self,
        tool_calls: list[ToolCallData],
        registry: ToolRegistry,
        iteration: AgentIteration,
        block_state: BlockState,
        widget: BaseBlockWidget,
        has_iteration_ui: bool,
    ) -> list[ToolResult]:
        """Execute tools within a specific iteration."""
        import time

        from models import ToolCallState
        from tools import ToolCall, ToolResult
        from widgets.blocks import AIResponseBlock

        results: list[Any] = []
        has_accordion = isinstance(widget, AIResponseBlock)
        # Cast widget to AIResponseBlock for type checker when has_accordion is True
        ai_widget: AIResponseBlock | None = None
        if has_accordion:
            assert isinstance(widget, AIResponseBlock)
            ai_widget = widget

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
            if ai_widget is not None:
                ai_widget.add_tool_call(
                    tool_id=tc.id,
                    tool_name=tc.name,
                    arguments=tool_state.arguments,
                    status="running",
                )

            # Check if approval is needed
            needs_approval = registry.requires_approval(tc.name)

            if needs_approval:
                # Request approval for this specific tool call
                approval_result = await self._request_tool_approval([tc])

                if approval_result == "cancel":
                    # Cancel entire process
                    self.app._ai_cancelled = True
                    break
                elif approval_result == "reject":
                    # Skip this tool but continue (add error message so LLM knows)
                    tool_result_msg: Message = {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Tool execution rejected by user.",
                    }
                    results.append(
                        ToolResult(
                            tc.id, "Tool execution rejected by user.", is_error=True
                        )
                    )
                    continue
                # If "approve" or "approve-all", proceed to execute

            # Execute the tool
            result = await registry.execute_tool(tool_call)
            results.append(result)

            duration = time.time() - start_time

            # Update tool state
            tool_state.status = "error" if result.is_error else "success"
            tool_state.output = result.content
            tool_state.duration = duration

            # Update accordion if available
            if ai_widget is not None:
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

    async def _request_tool_approval(
        self, tool_calls: list, iteration_number: int = 1
    ) -> str:
        """Request user approval for tool execution."""

        from screens import ToolApprovalScreen

        # Build tool call data for the approval screen
        tool_data = [{"name": tc.name, "arguments": tc.arguments} for tc in tool_calls]

        # Create and push the approval screen
        screen = ToolApprovalScreen(
            tool_calls=tool_data, iteration_number=iteration_number
        )

        # Wait for user decision
        result = await self.app.push_screen_wait(screen)

        return result or "cancel"

    def _finalize_response(
        self,
        block_state: BlockState,
        widget: BaseBlockWidget,
        full_response: str,
        messages: list[Message],
        max_tokens: int,
        usage: TokenUsage | None = None,
    ) -> None:
        """Finalize the AI response."""
        block_state.is_running = False
        self.app._active_worker = None

        # Get model name directly from provider (always current)
        model_name = self.app.ai_provider.model if self.app.ai_provider else ""

        # Update metadata with token info
        if usage:
            # Use actual token counts from API
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cost = calculate_cost(usage, model_name)
            block_state.metadata["tokens"] = (
                f"{input_tokens:,} in / {output_tokens:,} out"
            )
            if cost > 0:
                block_state.metadata["cost"] = f"${cost:.4f}"
        else:
            # Fall back to estimates
            response_tokens = len(full_response) // 4
            context_chars = sum(len(m.get("content", "")) for m in messages)
            context_tokens = context_chars // 4
            block_state.metadata["tokens"] = (
                f"~{response_tokens} out / ~{context_tokens} ctx"
            )
            # Create estimated usage for status bar
            input_tokens = context_tokens
            output_tokens = response_tokens
            usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
            cost = calculate_cost(usage, model_name)

        widget.update_metadata()

        # Update status bar with context and token usage
        try:
            status_bar = self.app.query_one("#status-bar", StatusBar)

            # Update context display
            context_chars = sum(len(m.get("content", "")) for m in messages)
            total_context = context_chars + len(full_response)
            limit_chars = max_tokens * 4
            status_bar.set_context(total_context, limit_chars)

            # Update token usage display
            status_bar.add_token_usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost=cost,
            )
        except (ImportError, NoMatches):
            pass
        except Exception as e:
            self.app.log(f"Error updating status bar: {e}")

        widget.set_loading(False)
        if get_settings().terminal.auto_save_session:
            self.app._auto_save()

    def run_agent_command(
        self, command: str, ai_block: BlockState, ai_widget: BaseBlockWidget
    ) -> None:
        """Execute a command requested by the AI agent."""
        from executor import ExecutionEngine

        async def run_inline():
            try:
                output_buffer: list[str] = []

                def callback(line: str) -> None:
                    output_buffer.append(line)
                    current_text = "".join(output_buffer)
                    ai_block.content_exec_output = f"\n```text\n{current_text}\n```\n"
                    ai_widget.update_output("")

                # Execute command
                executor = ExecutionEngine()
                rc = await executor.run_command_and_get_rc(command, callback)

                output_text = "".join(output_buffer)
                if not output_text.strip():
                    output_text = "(Command execution completed with no output)"

                # Format output
                result_md = f"\n```text\n{output_text}\n```\n"
                if rc != 0:
                    result_md += f"\n*Exit Code: {rc}*\n"

                ai_block.content_exec_output = result_md
                ai_widget.update_output("")

            except Exception as e:
                err_msg = f"\n**Error Running Command:** {e!s}\n"
                ai_block.content_exec_output = err_msg
                ai_widget.update_output("")
                self.app.notify(f"Agent Execution Error: {e}", severity="error")
            finally:
                ai_widget.set_loading(False)
                ai_block.is_running = False

        self.app.run_worker(run_inline())

    async def regenerate_ai(self, block: BlockState, widget: BaseBlockWidget) -> None:
        """Regenerate an AI response block."""
        if not self.app.ai_provider:
            self.app.notify("AI Provider not configured", severity="error")
            return

        # Clear output and reset state
        block.content_output = ""
        block.content_exec_output = ""
        block.is_running = True
        block.exit_code = None

        # Reset widget display
        widget.set_loading(True)

        thinking_widget = getattr(widget, "thinking_widget", None)
        if thinking_widget:
            thinking_widget.thinking_text = ""
            thinking_widget.start_loading()

        exec_widget = getattr(widget, "exec_widget", None)
        if exec_widget:
            exec_widget.exec_output = ""

        iteration_container = getattr(widget, "iteration_container", None)
        if iteration_container:
            iteration_container.clear()

        widget.update_metadata()

        # Run AI worker
        self.app._ai_cancelled = False
        self.app._active_worker = self.app.run_worker(
            self.execute_ai(block.content_input, block, widget)
        )
