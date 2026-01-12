"""AI Execution Handler."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, ClassVar, cast

from textual.css.query import NoMatches

from ai.base import Message, TokenUsage, calculate_cost
from config import Config, get_settings
from handlers.ai.agent_loop import AgentLoop
from handlers.ai.tool_runner import ToolRunner
from models import BlockType
from tools import ToolRegistry
from widgets import BaseBlockWidget, StatusBar

from .common import UIBuffer

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState


class AIExecutor:
    """Handles AI generation and execution."""

    _background_tasks: ClassVar[set[asyncio.Task[None]]] = set()

    def __init__(self, app: NullApp):
        self.app = app
        self._tool_runner = ToolRunner(app)
        self._agent_loop = AgentLoop(app, self._tool_runner)

    async def cancel_tool(self, tool_id: str) -> None:
        await self._tool_runner.cancel_tool(tool_id)

    def _get_tool_registry(self) -> ToolRegistry:
        """Get or create the tool registry."""
        return self._tool_runner.get_registry()

    async def execute_ai(
        self, prompt: str, block_state: BlockState, widget: BaseBlockWidget
    ) -> None:
        """Execute AI generation with streaming response and tool support."""
        try:
            from context import ContextManager
            from prompts import get_prompt_manager

            provider_name = Config.get("ai.provider") or ""
            model_override = None

            if hasattr(self.app, "mcp_manager"):
                profile_ai = self.app.mcp_manager.config.get_active_ai_config()
                if profile_ai:
                    if "provider" in profile_ai:
                        provider_name = profile_ai["provider"]
                    if "model" in profile_ai:
                        model_override = profile_ai["model"]

            ai_provider = self.app.ai_manager.get_provider(provider_name)

            if not ai_provider:
                widget.update_output(f"AI Provider '{provider_name}' not configured")
                widget.set_loading(False)
                return

            if model_override:
                ai_provider.model = model_override

            model_name = ai_provider.model

            active_key = Config.get("ai.active_prompt") or "default"

            prompt_manager = get_prompt_manager()
            system_prompt = prompt_manager.get_prompt_content(active_key, provider_name)

            model_info = ai_provider.get_model_info()
            max_tokens = model_info.context_window

            context_info = ContextManager.build_messages(
                self.app.blocks[:-1], max_tokens=max_tokens, reserve_tokens=1024
            )

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

            messages = cast(list[Message], context_info.messages)

            settings = get_settings()
            if settings.ai.use_rag:
                messages = await self._inject_rag_context(
                    prompt, messages, ai_provider, settings.ai.rag_top_k
                )

            if is_agent_block:
                if active_key == "default":
                    system_prompt = prompt_manager.get_prompt_content(
                        "agent", provider_name
                    )

                await self._agent_loop.run_loop(
                    prompt,
                    block_state,
                    widget,
                    messages,
                    system_prompt,
                    max_tokens,
                    self._finalize_response,
                )
            elif use_tools:
                await self._execute_with_tools(
                    prompt,
                    block_state,
                    widget,
                    messages,
                    system_prompt,
                    max_tokens,
                )
            else:
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
            error_msg = f"**⚠️ Error:** {e!s}"
            block_state.content_output = error_msg
            block_state.is_running = False
            widget.update_output(error_msg)
            widget.set_loading(False)
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

                if chunk.text:
                    buffer.write(chunk.text)

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
        import json
        from typing import Any

        ai_provider = self.app.ai_provider
        assert ai_provider is not None, "AI provider must be set"

        registry = self._get_tool_registry()
        tools = registry.get_all_tools_schema()

        full_response = ""
        current_messages: list[Message] = list(messages)
        iteration = 0
        max_iterations = 3
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
                    prompt if iteration == 1 else "",
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

                    if chunk.text:
                        buffer.write(chunk.text)

                    if chunk.tool_calls:
                        pending_tool_calls.extend(chunk.tool_calls)

                    if chunk.is_complete and chunk.usage:
                        if total_usage is None:
                            total_usage = chunk.usage
                        else:
                            total_usage = total_usage + chunk.usage

                    if chunk.is_complete:
                        break

                buffer.flush()

                if self.app._ai_cancelled:
                    break

                if not pending_tool_calls:
                    break

                tool_to_run = pending_tool_calls[:1]
                tool_results = await self._tool_runner.process_chat_tools(
                    tool_to_run, block_state, widget, registry
                )

                if not tool_results:
                    break

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

                for result in tool_results:
                    tool_result_msg: Message = {
                        "role": "tool",
                        "tool_call_id": result.tool_call_id,
                        "content": result.content,
                    }
                    current_messages.append(tool_result_msg)

                if iteration == 1 and tool_results and not tool_results[0].is_error:
                    break

                prompt = ""

        finally:
            buffer.stop()

        self._finalize_response(
            block_state, widget, full_response, messages, max_tokens, total_usage
        )

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

        model_name = self.app.ai_provider.model if self.app.ai_provider else ""

        if usage:
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cost = calculate_cost(usage, model_name)
            block_state.metadata["tokens"] = (
                f"{input_tokens:,} in / {output_tokens:,} out"
            )
            if cost > 0:
                block_state.metadata["cost"] = f"${cost:.4f}"
        else:
            response_tokens = len(full_response) // 4
            context_chars = sum(len(m.get("content", "")) for m in messages)
            context_tokens = context_chars // 4
            block_state.metadata["tokens"] = (
                f"~{response_tokens} out / ~{context_tokens} ctx"
            )
            input_tokens = context_tokens
            output_tokens = response_tokens
            usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
            cost = calculate_cost(usage, model_name)

        widget.update_metadata()

        try:
            status_bar = self.app.query_one("#status-bar", StatusBar)

            context_chars = sum(len(m.get("content", "")) for m in messages)
            total_context = context_chars + len(full_response)
            limit_chars = max_tokens * 4
            status_bar.set_context(total_context, limit_chars)

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

        try:
            from managers.recall import RecallManager

            recall_manager = RecallManager()
            task = asyncio.create_task(recall_manager.index_interaction(block_state))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception:
            pass

    async def _inject_rag_context(
        self,
        prompt: str,
        messages: list[Message],
        ai_provider,
        top_k: int = 3,
    ) -> list[Message]:
        try:
            from ai.rag import RAGManager

            rag_manager = RAGManager()
            stats = rag_manager.get_stats()

            if stats.get("total_chunks", 0) == 0:
                return messages

            chunks = await rag_manager.search(prompt, ai_provider, limit=top_k)
            if not chunks:
                return messages

            rag_context = "## Relevant Context from Local Index:\n\n"
            for chunk in chunks:
                rag_context += f"From {chunk.source}:\n```\n{chunk.content}\n```\n\n"

            rag_message: Message = {"role": "user", "content": rag_context}
            return [rag_message, *messages]

        except Exception as e:
            self.app.log(f"RAG context injection failed: {e}")
            return messages

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

                executor = ExecutionEngine()
                rc = await executor.run_command_and_get_rc(command, callback)

                output_text = "".join(output_buffer)
                if not output_text.strip():
                    output_text = "(Command execution completed with no output)"

                result_md = f"\n```text\n{output_text}\n```\n"
                if rc != 0:
                    result_md += f"\n*Exit Code: {rc}*\n"

                ai_block.content_exec_output = result_md
                ai_widget.update_output("")

            except Exception as e:
                err_msg = f"\n**⚠️ Error Running Command:** {e!s}\n"
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

        block.content_output = ""
        block.content_exec_output = ""
        block.is_running = True
        block.exit_code = None

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

        self.app._ai_cancelled = False
        self.app._active_worker = self.app.run_worker(
            self.execute_ai(block.content_input, block, widget)
        )
