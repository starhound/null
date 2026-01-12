"""Agent reasoning loop."""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any

from ai.base import Message, TokenUsage
from config import Config
from managers.agent import AgentState
from models import AgentIteration, BlockState
from widgets import AgentResponseBlock, BaseBlockWidget

if TYPE_CHECKING:
    from app import NullApp
    from handlers.ai.tool_runner import ToolRunner


class AgentLoop:
    """Manages the iterative agent reasoning loop."""

    def __init__(self, app: NullApp, tool_runner: ToolRunner):
        self.app = app
        self.tool_runner = tool_runner

    async def run_loop(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int,
        finalize_callback: Any,  # Callback to _finalize_response
    ):
        """Execute the agent loop."""
        from ai.thinking import get_thinking_strategy

        ai_provider = self.app.ai_provider
        assert ai_provider is not None, "AI provider must be set"

        registry = self.tool_runner.get_registry()
        tools = registry.get_all_tools_schema()

        provider_name = Config.get("ai.provider") or ""
        model_name = ai_provider.model
        strategy = get_thinking_strategy(provider_name, model_name)

        enhanced_prompt = system_prompt
        if strategy.requires_prompting:
            prompt_addition = strategy.get_prompt_addition()
            if prompt_addition:
                enhanced_prompt = system_prompt + "\n\n" + prompt_addition

        ai_config = self.app.config.get("ai", {})
        max_iterations = ai_config.get("agent_max_iterations", 10)
        approval_mode = ai_config.get("agent_approval_mode", "auto")
        auto_approve_all = False

        full_response = ""
        current_messages: list[Message] = list(messages)
        iteration_num = 0
        total_usage: TokenUsage | None = None

        agent_widget: AgentResponseBlock | None = (
            widget if isinstance(widget, AgentResponseBlock) else None
        )

        agent_manager = self.app.agent_manager
        task_preview = prompt[:100] + ("..." if len(prompt) > 100 else "")
        agent_manager.start_session(task_preview)

        while iteration_num < max_iterations:
            if agent_manager.should_cancel():
                full_response += "\n\n[Cancelled by user]"
                block_state.content_output = full_response
                widget.update_output(full_response)
                agent_manager.end_session(cancelled=True)
                break

            if agent_manager.should_pause():
                agent_manager.update_state(AgentState.PAUSED)
                # Deliberate busy-wait for pause/resume functionality
                while (  # noqa: ASYNC110
                    agent_manager.should_pause() and not agent_manager.should_cancel()
                ):
                    await asyncio.sleep(0.1)
                if agent_manager.should_cancel():
                    continue

            iteration_num += 1
            pending_tool_calls: list[Any] = []
            raw_response = ""
            iteration_start = time.time()

            agent_manager.record_iteration()
            agent_manager.update_state(AgentState.THINKING)

            iteration = AgentIteration(
                iteration_number=iteration_num, status="thinking"
            )

            if agent_widget:
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
                    if agent_widget:
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
                        if agent_widget:
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
                if agent_widget:
                    # If this iteration has no thinking and no tools, remove it
                    if not iteration.thinking and not iteration.tool_calls:
                        agent_widget.remove_iteration(iteration.id)
                    else:
                        agent_widget.update_iteration(
                            iteration.id, status="complete", duration=iteration.duration
                        )
                break

            if approval_mode != "auto" and not auto_approve_all:
                iteration.status = "waiting_approval"
                agent_manager.update_state(AgentState.WAITING_APPROVAL)
                if agent_widget:
                    agent_widget.update_iteration(
                        iteration.id, status="waiting_approval"
                    )

                # Request approval for tool calls
                approval_result = await self.tool_runner.request_approval(
                    pending_tool_calls, iteration_num
                )

                if approval_result == "cancel":
                    full_response += "\n\n[Agent cancelled by user]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    iteration.status = "complete"
                    if agent_widget:
                        agent_widget.update_iteration(iteration.id, status="complete")
                    break

                elif approval_result == "reject":
                    iteration.status = "complete"
                    iteration.duration = time.time() - iteration_start
                    if agent_widget:
                        agent_widget.update_iteration(
                            iteration.id, status="complete", duration=iteration.duration
                        )
                    prompt = ""
                    continue

                elif approval_result == "approve-all":
                    auto_approve_all = True

            iteration.status = "executing"
            agent_manager.update_state(AgentState.EXECUTING)
            if agent_widget:
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
            tool_results = await self.tool_runner.process_agent_tools(
                pending_tool_calls,
                registry,
                iteration,
                block_state,
                widget,
                agent_widget is not None,
            )

            if not tool_results:
                # Tool execution failed or cancelled
                iteration.status = "complete"
                iteration.duration = time.time() - iteration_start
                if agent_widget:
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
            if agent_widget:
                agent_widget.update_iteration(
                    iteration.id, status="complete", duration=iteration.duration
                )

            # Clear prompt for next iteration
            prompt = ""

        if iteration_num >= max_iterations:
            full_response += (
                f"\n\n*Warning: Reached maximum iterations ({max_iterations})*"
            )
            block_state.content_output = full_response
            widget.update_output(full_response)

        if total_usage:
            agent_manager.record_tokens(
                total_usage.input_tokens + total_usage.output_tokens
            )

        agent_manager.end_session(cancelled=self.app._ai_cancelled)

        finalize_callback(
            block_state, widget, full_response, messages, max_tokens, total_usage
        )
