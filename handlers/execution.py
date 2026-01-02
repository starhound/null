"""Execution handlers for AI and CLI commands."""

from __future__ import annotations
import asyncio
import json
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from app import NullApp

from models import BlockState
from widgets import BaseBlockWidget


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

            # Get system prompt from prompt manager
            active_key = self.app.config.get("ai", {}).get("active_prompt", "default")
            provider_name = self.app.config.get("ai", {}).get("provider", "")
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
            model_name = self.app.config['ai']['model']
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
                "model": f"{provider_name}/{model_name}",
                "context": f"~{context_info.estimated_tokens} tokens ({context_info.message_count} msgs)",
                "persona": active_key
            }
            if widget:
                widget.update_metadata()

            # Check if provider supports tools
            use_tools = self.app.ai_provider.supports_tools()

            if use_tools:
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
        max_iterations = 10  # Prevent infinite tool loops

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

                if chunk.is_complete:
                    break

            # Check for cancellation
            if self.app._ai_cancelled:
                break

            # If no tool calls, we're done
            if not pending_tool_calls:
                break

            # Process tool calls
            tool_results = await self._process_tool_calls(
                pending_tool_calls, block_state, widget, registry
            )

            if not tool_results:
                # User cancelled or no results
                break

            # Add assistant message with tool calls
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
                    for tc in pending_tool_calls
                ]
            }
            current_messages.append(assistant_msg)

            # Add tool results
            for result in tool_results:
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.content
                })

            # Clear prompt for next iteration (context is in messages)
            prompt = ""

        self._finalize_response(block_state, widget, full_response, messages, max_tokens)

    async def _process_tool_calls(
        self,
        tool_calls: List,
        block_state: BlockState,
        widget: BaseBlockWidget,
        registry
    ) -> List:
        """Process tool calls with approval and execution."""
        from tools import ToolCall, ToolResult

        results = []

        for tc in tool_calls:
            tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)

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
        max_tokens: int
    ):
        """Finalize the AI response."""
        block_state.is_running = False
        self.app._active_worker = None

        # Update metadata with token estimate
        response_tokens = len(full_response) // 4
        context_chars = sum(len(m.get("content", "")) for m in messages)
        context_tokens = context_chars // 4
        block_state.metadata["tokens"] = f"~{response_tokens} out / ~{context_tokens} ctx"
        widget.update_metadata()

        # Update status bar
        try:
            from widgets import StatusBar
            status_bar = self.app.query_one("#status-bar", StatusBar)
            total_context = context_chars + len(full_response)
            limit_chars = max_tokens * 4
            status_bar.set_context(total_context, limit_chars)
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

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        exit_code = await self.app.executor.run_command_and_get_rc(
            block.content_input,
            update_callback
        )

        widget.set_exit_code(exit_code)
        self.app._auto_save()

    async def execute_cli_append(self, cmd: str, block: BlockState, widget: BaseBlockWidget):
        """Execute a command and append output to existing CLI block."""

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        exit_code = await self.app.executor.run_command_and_get_rc(cmd, update_callback)

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
