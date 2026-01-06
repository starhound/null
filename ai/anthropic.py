"""Anthropic Claude API provider."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(
                    api_key=self.api_key, timeout=60.0
                )
            except ImportError as e:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
                ) from e
        return self._client

    def supports_tools(self) -> bool:
        """Anthropic models support tool calling."""
        return True

    def _build_messages(
        self, prompt: str, messages: list[Message]
    ) -> list[dict[str, Any]]:
        """Build messages for Anthropic API (system prompt handled separately)."""
        api_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            # Anthropic uses 'user' and 'assistant' only in messages
            if role == "system":
                continue  # System handled separately

            msg_dict: dict[str, Any] = {"role": role}

            # Handle content
            if msg.get("content"):
                msg_dict["content"] = msg.get("content")
            elif "tool_calls" in msg:
                # Convert tool calls to Anthropic format
                content = []
                for tc in msg["tool_calls"]:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"]),
                        }
                    )
                msg_dict["content"] = content

            if msg_dict.get("content"):
                api_messages.append(msg_dict)

        # Add current prompt
        api_messages.append({"role": "user", "content": prompt})

        return api_messages

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append(
                    {
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "input_schema": func.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    }
                )
        return anthropic_tools

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Claude."""
        try:
            client = self._get_client()

            if not system_prompt:
                system_prompt = (
                    "You are a helpful AI assistant integrated into a terminal."
                )

            api_messages = self._build_messages(prompt, messages)

            async with client.messages.stream(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=api_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            yield f"Error: {e!s}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream response with tool calling support."""
        try:
            client = self._get_client()

            if not system_prompt:
                system_prompt = (
                    "You are a helpful AI assistant integrated into a terminal."
                )

            api_messages = self._build_messages(prompt, messages)
            anthropic_tools = self._convert_tools(tools) if tools else None

            params = {
                "model": self.model,
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": api_messages,
            }
            if anthropic_tools:
                params["tools"] = anthropic_tools

            async with client.messages.stream(**params) as stream:
                tool_calls = []
                current_tool_use = None
                usage_data: TokenUsage | None = None

                async for event in stream:
                    # Handle text delta
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                yield StreamChunk(text=event.delta.text)
                            elif hasattr(event.delta, "partial_json"):
                                # Tool input being streamed
                                if current_tool_use:
                                    current_tool_use["arguments"] += (
                                        event.delta.partial_json
                                    )

                        elif event.type == "content_block_start":
                            if hasattr(event.content_block, "type"):
                                if event.content_block.type == "tool_use":
                                    current_tool_use = {
                                        "id": event.content_block.id,
                                        "name": event.content_block.name,
                                        "arguments": "",
                                    }

                        elif event.type == "content_block_stop":
                            if current_tool_use:
                                try:
                                    args = (
                                        json.loads(current_tool_use["arguments"])
                                        if current_tool_use["arguments"]
                                        else {}
                                    )
                                except json.JSONDecodeError:
                                    args = {}

                                tool_calls.append(
                                    ToolCallData(
                                        id=current_tool_use["id"],
                                        name=current_tool_use["name"],
                                        arguments=args,
                                    )
                                )
                                current_tool_use = None

                        elif event.type == "message_delta":
                            # Anthropic sends usage in message_delta event
                            if hasattr(event, "usage") and event.usage:
                                output_tokens = getattr(event.usage, "output_tokens", 0)
                                if usage_data:
                                    usage_data.output_tokens = output_tokens
                                else:
                                    usage_data = TokenUsage(output_tokens=output_tokens)

                        elif event.type == "message_start":
                            # Anthropic sends input tokens in message_start
                            if hasattr(event, "message") and hasattr(
                                event.message, "usage"
                            ):
                                input_tokens = getattr(
                                    event.message.usage, "input_tokens", 0
                                )
                                usage_data = TokenUsage(input_tokens=input_tokens)

                        elif event.type == "message_stop":
                            yield StreamChunk(
                                text="",
                                tool_calls=tool_calls,
                                is_complete=True,
                                usage=usage_data,
                            )

        except Exception as e:
            yield StreamChunk(text=f"Error: {e!s}", is_complete=True)

    async def list_models(self) -> list[str]:
        """Return available Claude models."""
        # Anthropic doesn't have a list models endpoint, return known models
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    async def validate_connection(self) -> bool:
        """Check if Anthropic API is reachable."""
        try:
            client = self._get_client()
            # Quick validation by trying to create a minimal message
            response = await client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return response is not None
        except Exception:
            return False
