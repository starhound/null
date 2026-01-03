"""Execution handlers for AI and CLI commands."""

from __future__ import annotations
import asyncio
import json
from typing import TYPE_CHECKING, List, Dict, Any, Optional

if TYPE_CHECKING:
    from app import NullApp

from models import BlockState
from widgets import BaseBlockWidget
from ai.base import TokenUsage, calculate_cost


class ExecutionHandler:
    """Handles AI and CLI command execution."""

    def __init__(self, app: "NullApp"):
        self.app = app
        self._tool_registry = None

    def _get_tool_registry(self):
        """Get or create the tool registry."""
        if self._tool_registry is None:
            from tools import ToolRegistry
            self._tool_registry = ToolRegistry(
                mcp_manager=getattr(self.app, 'mcp_manager', None)
            )
        return self._tool_registry

    async def execute_ai(self, prompt: str, block_state: BlockState, widget: BaseBlockWidget):
        """Execute AI generation with streaming response and tool support."""
        try:
            from context import ContextManager
            from prompts import get_prompt_manager
            from config import Config

            # Get FRESH config values (not stale self.app.config)
            provider_name = Config.get("ai.provider") or ""
            active_key = Config.get("ai.active_prompt") or "default"

            # Get model directly from provider (always current)
            model_name = self.app.ai_provider.model if self.app.ai_provider else ""

            prompt_manager = get_prompt_manager()
            system_prompt = prompt_manager.get_prompt_content(active_key, provider_name)

            # Get model info for context limits
            model_info = self.app.ai_provider.get_model_info()
            max_tokens = model_info.context_window

            # Build proper message array (exclude current block)
            context_info = ContextManager.build_messages(
                self.app.blocks[:-1],
                max_tokens=max_tokens,
                reserve_tokens=1024
            )

            # Check if we're using unknown model with default context
            from ai.base import KNOWN_MODEL_CONTEXTS
            if model_name.lower() not in KNOWN_MODEL_CONTEXTS:
                is_known = any(model_name.lower().startswith(k) for k in KNOWN_MODEL_CONTEXTS)
                if not is_known:
                    self.app.notify(
                        f"Unknown model '{model_name}', using 4k context limit",
                        severity="warning"
                    )

            if context_info.truncated:
                self.app.notify(
                    f"Context truncated to fit {max_tokens} token limit",
                    severity="warning"
                )

            # Store metadata
            block_state.metadata = {
                "provider": provider_name,
                "model": model_name,
                "context": f"~{context_info.estimated_tokens} tokens ({context_info.message_count} msgs)",
                "persona": active_key
            }
            if widget:
                widget.update_metadata()

            # Check if provider supports tools and if agent mode is enabled
            use_tools = self.app.ai_provider.supports_tools()
            agent_mode = self.app.config.get("ai", {}).get("agent_mode", False)

            if use_tools and agent_mode:
                # If using default prompt in agent mode, switch to specialized agent prompt
                # because default prompt forbids elaboration which contradicts agent reasoning
                if active_key == "default":
                    system_prompt = prompt_manager.get_prompt_content("agent", provider_name)

                await self._execute_agent_mode(
                    prompt, block_state, widget,
                    context_info.messages, system_prompt, max_tokens
                )
            elif use_tools:
                await self._execute_with_tools(
                    prompt, block_state, widget,
                    context_info.messages, system_prompt, max_tokens
                )
            else:
                await self._execute_without_tools(
                    prompt, block_state, widget,
                    context_info.messages, system_prompt, max_tokens
                )

        except asyncio.CancelledError:
            block_state.content_output += "\n\n[Cancelled]"
            block_state.is_running = False
            widget.update_output(block_state.content_output)
            widget.set_loading(False)
            self.app._active_worker = None
        except Exception as e:
            block_state.content_output = f"AI Error: {str(e)}"
            block_state.is_running = False
            widget.update_output(f"Error: {str(e)}")
            self.app._active_worker = None

    async def _execute_without_tools(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        max_tokens: int
    ):
        """Execute AI generation without tool support (legacy mode)."""
        full_response = ""

        async for chunk in self.app.ai_provider.generate(
            prompt, messages, system_prompt=system_prompt
        ):
            if self.app._ai_cancelled:
                full_response += "\n\n[Cancelled]"
                block_state.content_output = full_response
                widget.update_output(full_response)
                break

            full_response += chunk
            block_state.content_output = full_response
            widget.update_output(full_response)

        self._finalize_response(block_state, widget, full_response, messages, max_tokens)

    async def _execute_with_tools(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        max_tokens: int
    ):
        """Execute AI generation with tool calling support."""
        from tools import ToolCall

        registry = self._get_tool_registry()
        tools = registry.get_all_tools_schema()

        full_response = ""
        current_messages = list(messages)
        iteration = 0
        max_iterations = 3  # Limit tool loops - most tasks need 1-2
        total_usage: Optional[TokenUsage] = None

        while iteration < max_iterations:
            iteration += 1
            pending_tool_calls = []

            async for chunk in self.app.ai_provider.generate_with_tools(
                prompt if iteration == 1 else "",  # Only send prompt on first iteration
                current_messages,
                tools,
                system_prompt=system_prompt
            ):
                if self.app._ai_cancelled:
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    break

                # Handle text content
                if chunk.text:
                    full_response += chunk.text
                    block_state.content_output = full_response
                    widget.update_output(full_response)

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
            assistant_msg = {
                "role": "assistant",
                "content": full_response,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in tool_to_run
                ]
            }
            current_messages.append(assistant_msg)

            # Add tool result
            for result in tool_results:
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.content
                })

            # After first tool success, stop unless it was an error
            if iteration == 1 and tool_results and not tool_results[0].is_error:
                # Give LLM one chance to provide a brief summary, but don't pass tools
                # to prevent further tool calls
                break

            # Clear prompt for next iteration (context is in messages)
            prompt = ""

        self._finalize_response(block_state, widget, full_response, messages, max_tokens, total_usage)

    async def _execute_agent_mode(
        self,
        prompt: str,
        block_state: BlockState,
        widget: BaseBlockWidget,
        messages: List[Dict[str, Any]],
        system_prompt: str,
        max_tokens: int
    ):
        """Execute AI with structured think → tool → think flow.

        This uses model-specific thinking strategies and creates discrete
        iterations for each think → action cycle.
        """
        from tools import ToolCall, ToolResult
        from models import AgentIteration, ToolCallState
        from widgets.blocks import AIResponseBlock
        from ai.thinking import get_thinking_strategy
        from config import Config
        import time

        registry = self._get_tool_registry()
        tools = registry.get_all_tools_schema()

        # Get thinking strategy for this provider/model
        provider_name = Config.get("ai.provider") or ""
        model_name = self.app.ai_provider.model if self.app.ai_provider else ""
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
        approval_mode = ai_config.get("agent_approval_mode", "auto")  # auto, per_tool, per_iteration
        auto_approve_all = False  # Set to True when user chooses "Approve All"

        full_response = ""
        current_messages = list(messages)
        iteration_num = 0
        total_usage: Optional[TokenUsage] = None
        has_iteration_ui = isinstance(widget, AIResponseBlock)

        while iteration_num < max_iterations:
            iteration_num += 1
            pending_tool_calls = []
            raw_response = ""
            iteration_start = time.time()

            # Create iteration state
            iteration = AgentIteration(
                iteration_number=iteration_num,
                status="thinking"
            )

            # Add iteration to UI if widget supports it
            if has_iteration_ui:
                widget.add_iteration(iteration)

            # Stream AI response
            async for chunk in self.app.ai_provider.generate_with_tools(
                prompt if iteration_num == 1 else "",
                current_messages,
                tools,
                system_prompt=enhanced_prompt
            ):
                if self.app._ai_cancelled:
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    iteration.status = "complete"
                    if has_iteration_ui:
                        widget.update_iteration(iteration.id, status="complete")
                    break

                # Handle text content
                if chunk.text:
                    raw_response += chunk.text

                    # Extract thinking using strategy
                    thinking, remaining = strategy.extract_thinking(raw_response)

                    # Update iteration thinking
                    if thinking:
                        iteration.thinking = thinking
                        if has_iteration_ui:
                            widget.update_iteration(iteration.id, thinking=thinking)

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
                if has_iteration_ui:
                    # If this iteration has no thinking and no tools, remove it to avoid empty box
                    if not iteration.thinking and not iteration.tool_calls:
                        widget.remove_iteration(iteration.id)
                    else:
                        widget.update_iteration(
                            iteration.id,
                            status="complete",
                            duration=iteration.duration
                        )
                break

            # Check if approval is needed
            if approval_mode != "auto" and not auto_approve_all:
                iteration.status = "waiting_approval"
                if has_iteration_ui:
                    widget.update_iteration(iteration.id, status="waiting_approval")

                # Request approval for tool calls
                approval_result = await self._request_tool_approval(
                    pending_tool_calls,
                    iteration_num
                )

                if approval_result == "cancel":
                    # User cancelled the entire agent loop
                    full_response += "\n\n[Agent cancelled by user]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    iteration.status = "complete"
                    if has_iteration_ui:
                        widget.update_iteration(iteration.id, status="complete")
                    break

                elif approval_result == "reject":
                    # Skip these tools but continue
                    iteration.status = "complete"
                    iteration.duration = time.time() - iteration_start
                    if has_iteration_ui:
                        widget.update_iteration(
                            iteration.id,
                            status="complete",
                            duration=iteration.duration
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
            if has_iteration_ui:
                widget.update_iteration(iteration.id, status="executing")

            # Add assistant message with tool calls to conversation
            assistant_content = raw_response
            thinking, remaining = strategy.extract_thinking(raw_response)
            if remaining:
                assistant_content = remaining

            assistant_msg = {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in pending_tool_calls
                ]
            }
            current_messages.append(assistant_msg)

            # Execute tool calls within this iteration
            tool_results = await self._execute_iteration_tools(
                pending_tool_calls,
                registry,
                iteration,
                block_state,
                widget,
                has_iteration_ui
            )

            if not tool_results:
                # Tool execution failed or cancelled
                iteration.status = "complete"
                iteration.duration = time.time() - iteration_start
                if has_iteration_ui:
                    widget.update_iteration(
                        iteration.id,
                        status="complete",
                        duration=iteration.duration
                    )
                break

            # Add tool results to conversation
            for result in tool_results:
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.content
                })

            # Mark iteration complete
            iteration.status = "complete"
            iteration.duration = time.time() - iteration_start
            if has_iteration_ui:
                widget.update_iteration(
                    iteration.id,
                    status="complete",
                    duration=iteration.duration
                )

            # Clear prompt for next iteration
            prompt = ""

        # Check if we hit max iterations
        if iteration_num >= max_iterations:
            full_response += f"\n\n*Warning: Reached maximum iterations ({max_iterations})*"
            block_state.content_output = full_response
            widget.update_output(full_response)

        self._finalize_response(block_state, widget, full_response, messages, max_tokens, total_usage)

    async def _execute_iteration_tools(
        self,
        tool_calls: List,
        registry,
        iteration: "AgentIteration",
        block_state: BlockState,
        widget: BaseBlockWidget,
        has_iteration_ui: bool
    ) -> List:
        """Execute tools within a specific iteration.

        This creates tool call states within the iteration and updates
        both the iteration UI and the execution log.
        """
        from tools import ToolCall, ToolResult
        from models import ToolCallState
        import time

        results = []

        for tc in tool_calls:
            tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
            start_time = time.time()

            # Create tool call state
            tool_state = ToolCallState(
                id=tc.id,
                tool_name=tc.name,
                arguments=json.dumps(tc.arguments, indent=2) if isinstance(tc.arguments, dict) else str(tc.arguments),
                status="running"
            )

            # Add to iteration
            iteration.tool_calls.append(tool_state)

            # Update UI
            if has_iteration_ui:
                widget.add_iteration_tool_call(iteration.id, tool_state)

            # Also add to block's tool_calls for backwards compatibility
            block_state.tool_calls.append(tool_state)

            # Show in exec output for non-iteration-aware displays
            tool_display = f"\n\n**Tool: {tc.name}**\n```json\n{json.dumps(tc.arguments, indent=2)}\n```"
            block_state.content_exec_output += tool_display
            widget.update_output()

            try:
                # Execute the tool
                result = await registry.execute_tool(tool_call)
                results.append(result)

                duration = time.time() - start_time

                # Format result preview
                content_preview = result.content
                if len(result.content) > 2000:
                    content_preview = result.content[:2000] + f"\n... ({len(result.content)} chars total)"

                # Update tool state
                tool_state.status = "error" if result.is_error else "success"
                tool_state.output = result.content
                tool_state.duration = duration

                # Update iteration UI
                if has_iteration_ui:
                    widget.update_iteration_tool_call(
                        iteration.id,
                        tc.id,
                        status=tool_state.status,
                        duration=duration
                    )

                # Show result in exec output
                if result.is_error:
                    result_display = f"\n**Error ({duration:.1f}s):**\n```\n{content_preview}\n```"
                else:
                    result_display = f"\n**Result ({duration:.1f}s):**\n```\n{content_preview}\n```"

                block_state.content_exec_output += result_display
                widget.update_output()

            except Exception as e:
                duration = time.time() - start_time
                error_result = ToolResult(
                    tool_call_id=tc.id,
                    content=f"Error: {str(e)}",
                    is_error=True
                )
                results.append(error_result)

                # Update tool state
                tool_state.status = "error"
                tool_state.output = str(e)
                tool_state.duration = duration

                # Update UI
                if has_iteration_ui:
                    widget.update_iteration_tool_call(
                        iteration.id,
                        tc.id,
                        status="error",
                        duration=duration
                    )

                block_state.content_exec_output += f"\n**System Error ({duration:.1f}s):**\n```\n{str(e)}\n```"
                widget.update_output()

        return results

    async def _request_tool_approval(
        self,
        tool_calls: List,
        iteration_number: int
    ) -> str:
        """Request user approval for tool execution.

        Args:
            tool_calls: List of pending tool calls
            iteration_number: Current iteration number

        Returns:
            One of: "approve", "approve-all", "reject", "cancel"
        """
        from screens import ToolApprovalScreen
        import asyncio

        # Build tool call data for the approval screen
        tool_data = [
            {
                "name": tc.name,
                "arguments": tc.arguments
            }
            for tc in tool_calls
        ]

        # Create and push the approval screen
        screen = ToolApprovalScreen(
            tool_calls=tool_data,
            iteration_number=iteration_number
        )

        # Wait for user decision
        result = await self.app.push_screen_wait(screen)

        return result or "cancel"

    async def _execute_agent_tools(
        self,
        tool_calls: List,
        registry,
        block_state: BlockState,
        widget: BaseBlockWidget
    ) -> List:
        """Execute tools in agent mode - inline visualization in the main block.

        Note: In agent mode with multiple iterations, we use the ExecutionWidget
        (content_exec_output) for display since it shows the correct chronological
        flow. We skip the ToolAccordion here as it groups all tool calls together
        which breaks the interleaved thinking/tool call flow.
        """
        from tools import ToolCall, ToolResult
        from models import ToolCallState
        import time

        results = []

        for tc in tool_calls:
            tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
            start_time = time.time()

            # Create tool call state for tracking
            tool_state = ToolCallState(
                id=tc.id,
                tool_name=tc.name,
                arguments=json.dumps(tc.arguments, indent=2) if isinstance(tc.arguments, dict) else str(tc.arguments),
                status="running"
            )
            block_state.tool_calls.append(tool_state)

            # Show tool call in exec output (this maintains correct chronological order)
            tool_display = f"\n\n**Tool: {tc.name}**\n```json\n{json.dumps(tc.arguments, indent=2)}\n```"
            block_state.content_exec_output += tool_display
            widget.update_output()

            try:
                # Execute the tool
                result = await registry.execute_tool(tool_call)
                results.append(result)

                duration = time.time() - start_time

                # Format result
                content_preview = result.content
                if len(result.content) > 2000:
                    content_preview = result.content[:2000] + f"\n... ({len(result.content)} chars total)"

                # Update tool state
                tool_state.status = "error" if result.is_error else "success"
                tool_state.output = result.content
                tool_state.duration = duration

                # Show result in exec output
                if result.is_error:
                    result_display = f"\n**Error ({duration:.1f}s):**\n```\n{result.content}\n```"
                else:
                    result_display = f"\n**Result ({duration:.1f}s):**\n```\n{content_preview}\n```"

                block_state.content_exec_output += result_display
                widget.update_output()

            except Exception as e:
                duration = time.time() - start_time
                error_result = ToolResult(
                    tool_call_id=tc.id,
                    content=f"Error: {str(e)}",
                    is_error=True
                )
                results.append(error_result)

                # Update tool state
                tool_state.status = "error"
                tool_state.output = str(e)
                tool_state.duration = duration

                block_state.content_exec_output += f"\n**System Error ({duration:.1f}s):**\n```\n{str(e)}\n```"
                widget.update_output()

        return results

    async def _process_tool_calls(
        self,
        tool_calls: List,
        block_state: BlockState,
        widget: BaseBlockWidget,
        registry
    ) -> List:
        """Process tool calls with approval and execution."""
        from tools import ToolCall, ToolResult
        from models import ToolCallState
        from widgets.blocks import AIResponseBlock
        import time

        results = []
        has_accordion = isinstance(widget, AIResponseBlock)

        for tc in tool_calls:
            tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
            start_time = time.time()

            # Create tool call state
            tool_state = ToolCallState(
                id=tc.id,
                tool_name=tc.name,
                arguments=json.dumps(tc.arguments, indent=2) if isinstance(tc.arguments, dict) else str(tc.arguments),
                status="running"
            )
            block_state.tool_calls.append(tool_state)

            # Add to accordion if available
            if has_accordion:
                widget.add_tool_call(
                    tool_id=tc.id,
                    tool_name=tc.name,
                    arguments=tool_state.arguments,
                    status="running"
                )

            # Check if approval is needed
            needs_approval = registry.requires_approval(tc.name)

            if needs_approval:
                # Show the tool call and ask for approval
                tool_display = f"\n\n**Tool: {tc.name}**\n```json\n{json.dumps(tc.arguments, indent=2)}\n```\n"
                block_state.content_output += tool_display
                widget.update_output(block_state.content_output)

                # For now, auto-approve (TODO: add proper approval UI)
                self.app.notify(f"Executing tool: {tc.name}")

            # Execute the tool
            result = await registry.execute_tool(tool_call)
            results.append(result)

            duration = time.time() - start_time

            # Update tool state
            tool_state.status = "error" if result.is_error else "success"
            tool_state.output = result.content
            tool_state.duration = duration

            # Update accordion if available
            if has_accordion:
                content_preview = result.content[:1000] if len(result.content) > 1000 else result.content
                widget.update_tool_call(
                    tool_id=tc.id,
                    status=tool_state.status,
                    output=content_preview,
                    duration=duration
                )

            # Show the result
            result_display = f"\n**Result:**\n```\n{result.content[:1000]}\n```\n"
            if len(result.content) > 1000:
                result_display += f"... ({len(result.content)} chars total)\n"

            block_state.content_exec_output += result_display
            widget.update_output(block_state.content_output)

        return results

    def _finalize_response(
        self,
        block_state: BlockState,
        widget: BaseBlockWidget,
        full_response: str,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        usage: Optional[TokenUsage] = None
    ):
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
            block_state.metadata["tokens"] = f"{input_tokens:,} in / {output_tokens:,} out"
            if cost > 0:
                block_state.metadata["cost"] = f"${cost:.4f}"
        else:
            # Fall back to estimates
            response_tokens = len(full_response) // 4
            context_chars = sum(len(m.get("content", "")) for m in messages)
            context_tokens = context_chars // 4
            block_state.metadata["tokens"] = f"~{response_tokens} out / ~{context_tokens} ctx"
            # Create estimated usage for status bar
            input_tokens = context_tokens
            output_tokens = response_tokens
            usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
            cost = calculate_cost(usage, model_name)

        widget.update_metadata()

        # Update status bar with context and token usage
        try:
            from widgets import StatusBar
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
                cost=cost
            )
        except Exception:
            pass

        widget.set_loading(False)
        self.app._auto_save()

    def run_agent_command(self, command: str, ai_block: BlockState, ai_widget: BaseBlockWidget):
        """Execute a command requested by the AI agent."""

        async def run_inline():
            try:
                output_buffer = []

                def callback(line):
                    output_buffer.append(line)
                    current_text = "".join(output_buffer)
                    ai_block.content_exec_output = f"\n```text\n{current_text}\n```\n"
                    ai_widget.update_output("")

                # Execute command
                rc = await self.app.executor.run_command_and_get_rc(command, callback)

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
                err_msg = f"\n**Error Running Command:** {str(e)}\n"
                ai_block.content_exec_output = err_msg
                ai_widget.update_output("")
                self.app.notify(f"Agent Execution Error: {e}", severity="error")
            finally:
                ai_widget.set_loading(False)
                ai_block.is_running = False

        self.app.run_worker(run_inline())

    async def execute_cli(self, block: BlockState, widget: BaseBlockWidget):
        """Execute a CLI command and stream output."""
        import asyncio
        from widgets.blocks import CommandBlock

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        def mode_callback(mode: str, data: bytes):
            """Handle TUI mode changes."""
            self.app.notify(f"TUI mode: {mode}", severity="information")

            if not isinstance(widget, CommandBlock):
                return

            if mode == 'enter':
                # Switch to TUI mode
                widget.switch_to_tui()
                widget.feed_terminal(data)
                # Mark as TUI in process manager
                self.app.process_manager.set_tui_mode(block.id, True)
            elif mode == 'exit':
                # Switch back to line mode
                widget.switch_to_line()
                self.app.process_manager.set_tui_mode(block.id, False)

        def raw_callback(data: bytes):
            """Feed raw data to terminal widget in TUI mode."""
            if isinstance(widget, CommandBlock):
                widget.feed_terminal(data)

        from executor import ExecutionEngine
        executor = ExecutionEngine()

        # Start command execution
        exec_task = asyncio.create_task(
            executor.run_command_and_get_rc(
                block.content_input,
                update_callback,
                mode_callback=mode_callback,
                raw_callback=raw_callback
            )
        )

        # Wait briefly for process to start, then register it
        await asyncio.sleep(0.01)
        if executor.pid:
            self.app.process_manager.register(
                block_id=block.id,
                pid=executor.pid,
                command=block.content_input,
                master_fd=executor.master_fd,
                executor=executor
            )

        try:
            exit_code = await exec_task
        finally:
            # Unregister process when done
            self.app.process_manager.unregister(block.id)

        widget.set_exit_code(exit_code)
        self.app._auto_save()

    async def execute_cli_append(self, cmd: str, block: BlockState, widget: BaseBlockWidget):
        """Execute a command and append output to existing CLI block."""
        import asyncio
        from widgets.blocks import CommandBlock

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        def mode_callback(mode: str, data: bytes):
            """Handle TUI mode changes for appended commands."""
            if not isinstance(widget, CommandBlock):
                return

            if mode == 'enter':
                # Switch to TUI mode
                widget.switch_to_tui()
                widget.feed_terminal(data)
                self.app.process_manager.set_tui_mode(block.id, True)
            elif mode == 'exit':
                # Switch back to line mode
                widget.switch_to_line()
                self.app.process_manager.set_tui_mode(block.id, False)

        def raw_callback(data: bytes):
            """Feed raw data to terminal widget in TUI mode."""
            if isinstance(widget, CommandBlock):
                widget.feed_terminal(data)

        from executor import ExecutionEngine
        executor = ExecutionEngine()

        # Start execution with full TUI support
        exec_task = asyncio.create_task(
            executor.run_command_and_get_rc(
                cmd,
                update_callback,
                mode_callback=mode_callback,
                raw_callback=raw_callback
            )
        )

        # Wait briefly for process to start to register it
        await asyncio.sleep(0.01)
        if executor.pid:
            self.app.process_manager.register(
                block_id=block.id,
                pid=executor.pid,
                command=cmd,
                master_fd=executor.master_fd,
                executor=executor
            )

        try:
            exit_code = await exec_task
        finally:
            self.app.process_manager.unregister(block.id)

        if exit_code != 0:
            block.content_output += f"[exit: {exit_code}]\n"
            widget.update_output()

        self.app._auto_save()

    async def regenerate_ai(self, block: BlockState, widget: BaseBlockWidget):
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
        if hasattr(widget, 'thinking_widget') and widget.thinking_widget:
            widget.thinking_widget.thinking_text = ""
            widget.thinking_widget.start_loading()
        if hasattr(widget, 'exec_widget') and widget.exec_widget:
            widget.exec_widget.exec_output = ""

        widget.update_metadata()

        # Run AI worker
        self.app._ai_cancelled = False
        self.app._active_worker = self.app.run_worker(
            self.execute_ai(block.content_input, block, widget)
        )
