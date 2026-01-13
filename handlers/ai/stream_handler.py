"""Streaming response handler for AI generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai.base import Message, TokenUsage
from handlers.common import UIBuffer

if TYPE_CHECKING:
    from app import NullApp
    from widgets import StatusBar


class StreamHandler:
    """Handles streaming AI responses with buffering and UI updates."""

    def __init__(self, app: NullApp):
        self.app = app

    def _get_status_bar(self) -> StatusBar | None:
        """Get the status bar widget if available."""
        try:
            from widgets import StatusBar

            return self.app.query_one("#status-bar", StatusBar)
        except Exception:
            return None

    async def stream_response(
        self,
        ai_provider: Any,
        prompt: str,
        messages: list[Message],
        system_prompt: str,
        on_chunk: Any,
    ) -> tuple[str, TokenUsage | None]:
        """Stream a simple AI response without tools.

        Args:
            ai_provider: The AI provider instance.
            prompt: User prompt text.
            messages: Conversation history.
            system_prompt: System prompt for the AI.
            on_chunk: Callback for each text chunk.

        Returns:
            Tuple of (full_response_text, token_usage).
        """
        full_response = ""
        usage: TokenUsage | None = None
        status_bar = self._get_status_bar()

        buffer = UIBuffer(self.app, on_chunk)

        if status_bar:
            status_bar.start_streaming()

        try:
            async for chunk in ai_provider.generate(
                prompt, messages, system_prompt=system_prompt
            ):
                if self.app._ai_cancelled:
                    buffer.flush()
                    full_response += "\n\n[Cancelled]"
                    break

                if chunk.text:
                    buffer.write(chunk.text)
                    full_response += chunk.text

                    if status_bar:
                        status_bar.update_streaming_tokens(len(full_response))

                if chunk.is_complete and hasattr(chunk, "usage") and chunk.usage:
                    usage = chunk.usage

            buffer.flush()

        finally:
            buffer.stop()
            if status_bar:
                status_bar.stop_streaming()

        return full_response, usage

    async def stream_tool_response(
        self,
        ai_provider: Any,
        prompt: str,
        messages: list[Message],
        tools: list[Any],
        system_prompt: str,
        buffer: UIBuffer,
    ) -> tuple[str, list[Any], TokenUsage | None]:
        """Stream AI response that may include tool calls.

        Args:
            ai_provider: The AI provider instance.
            prompt: User prompt text.
            messages: Conversation history.
            tools: Available tool schemas.
            system_prompt: System prompt for the AI.
            buffer: UIBuffer for buffered updates.

        Returns:
            Tuple of (response_text, tool_calls, token_usage).
        """
        pending_tool_calls: list[Any] = []
        usage_data: TokenUsage | None = None
        response_text = ""

        status_bar = self._get_status_bar()
        if status_bar:
            status_bar.start_streaming()

        async for chunk in ai_provider.generate_with_tools(
            prompt,
            messages,
            tools,
            system_prompt=system_prompt,
        ):
            if self.app._ai_cancelled:
                buffer.flush()
                break

            if chunk.text:
                buffer.write(chunk.text)
                response_text += chunk.text
                if status_bar:
                    status_bar.update_streaming_tokens(len(response_text))

            if chunk.tool_calls:
                pending_tool_calls.extend(chunk.tool_calls)

            if chunk.is_complete and chunk.usage:
                usage_data = chunk.usage

            if chunk.is_complete:
                break

        buffer.flush()
        if status_bar:
            status_bar.stop_streaming()

        return response_text, pending_tool_calls, usage_data
