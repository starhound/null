"""AI Execution Handler."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from textual.css.query import NoMatches

from ai.base import KNOWN_MODEL_CONTEXTS, Message, TokenUsage
from config import Config, get_settings
from context import ContextManager
from executor import ExecutionEngine
from handlers.ai.agent_loop import AgentLoop
from handlers.ai.response_formatter import ResponseFormatter
from handlers.ai.stream_handler import StreamHandler
from handlers.ai.tool_processor import append_tool_messages
from handlers.ai.tool_runner import ToolRunner
from handlers.common import UIBuffer
from models import BlockType
from prompts import get_prompt_manager
from tools import ToolRegistry

from .base_executor import BaseExecutor, ExecutorContext

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState
    from widgets import BaseBlockWidget, StatusBar


class AIExecutor(BaseExecutor):
    """Handles AI generation and execution."""

    def __init__(self, app: NullApp) -> None:
        self.app = app
        super().__init__(ExecutorContext.from_app(app))
        self._tool_runner = ToolRunner(app)
        self._agent_loop = AgentLoop(app, self._tool_runner)
        self._stream_handler = StreamHandler(app)
        self._response_formatter = ResponseFormatter(app)

    async def cancel_tool(self, tool_id: str) -> None:
        await self._tool_runner.cancel_tool(tool_id)

    def _get_tool_registry(self) -> ToolRegistry:
        return self._tool_runner.get_registry()

    def _get_status_bar(self) -> StatusBar | None:
        try:
            return self.app.query_one("#status-bar", StatusBar)
        except Exception:
            return None

    async def execute_ai(
        self, prompt: str, block_state: BlockState, widget: BaseBlockWidget
    ) -> None:
        try:
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

            if model_name.lower() not in KNOWN_MODEL_CONTEXTS:
                is_known = any(
                    model_name.lower().startswith(k) for k in KNOWN_MODEL_CONTEXTS
                )
                if not is_known:
                    self.app.notify(
                        f"Unknown model '{model_name}', using 4k context limit",
                        severity="warning",
                    )

            if context_info.summarized:
                summary_msg = (
                    f"Context summarized: {context_info.summary_details} "
                    f"(kept {context_info.message_count - 1} recent + summary)"
                )
                self.app.notify(summary_msg, severity="information")
            elif context_info.truncated:
                dropped = (
                    context_info.original_message_count - context_info.message_count
                )
                self.app.notify(
                    f"Context truncated: dropped {dropped} oldest messages to fit {max_tokens} token limit",
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
        ai_provider = self.app.ai_provider
        assert ai_provider is not None, "AI provider must be set"

        full_response = ""

        def update_callback(chunk: str):
            nonlocal full_response
            full_response += chunk
            block_state.content_output = full_response
            widget.update_output(full_response)

        full_response, _ = await self._stream_handler.stream_response(
            ai_provider,
            prompt,
            messages,
            system_prompt,
            update_callback,
        )

        block_state.content_output = full_response
        widget.update_output(full_response)

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

                (
                    response_text,
                    tool_calls,
                    usage,
                ) = await self._stream_handler.stream_tool_response(
                    ai_provider,
                    prompt if iteration == 1 else "",
                    current_messages,
                    tools,
                    system_prompt,
                    buffer,
                )

                if self.app._ai_cancelled:
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    break

                if usage:
                    if total_usage is None:
                        total_usage = usage
                    else:
                        total_usage = total_usage + usage

                if not tool_calls:
                    break

                tool_results = await self._tool_runner.process_chat_tools(
                    tool_calls, block_state, widget, registry
                )

                if not tool_results:
                    break

                append_tool_messages(
                    current_messages, response_text, tool_calls, tool_results
                )

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
        self._response_formatter.finalize_response(
            block_state, widget, full_response, messages, max_tokens, usage
        )

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
