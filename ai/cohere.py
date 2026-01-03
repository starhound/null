"""Cohere API provider."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class CohereProvider(LLMProvider):
    """Cohere Command API provider."""

    def __init__(self, api_key: str, model: str = "command-r-plus"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-load the Cohere client."""
        if self._client is None:
            try:
                import cohere

                self._client = cohere.AsyncClientV2(api_key=self.api_key)
            except ImportError as e:
                raise ImportError(
                    "cohere package required. Install with: pip install cohere"
                ) from e
        return self._client

    def supports_tools(self) -> bool:
        """Cohere Command models support tool calling."""
        return True

    def _build_messages(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Build messages for Cohere API."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant integrated into a terminal."

        chat_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue

            msg_dict: dict[str, Any] = {"role": role}

            # Handle content
            if "content" in msg:
                msg_dict["content"] = msg["content"]

            # Handle tool calls from assistant
            if "tool_calls" in msg and role == "assistant":
                msg_dict["tool_calls"] = msg["tool_calls"]

            # Handle tool results
            if role == "tool" and "tool_call_id" in msg:
                msg_dict["role"] = "tool"
                msg_dict["tool_call_id"] = msg["tool_call_id"]

            chat_messages.append(msg_dict)

        chat_messages.append({"role": "user", "content": prompt})
        return chat_messages

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Cohere format.

        Cohere V2 uses a similar format to OpenAI:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        # Cohere V2 API accepts OpenAI-style tool format directly
        return tools

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Cohere."""
        try:
            client = self._get_client()
            chat_messages = self._build_messages(prompt, messages, system_prompt)

            stream = client.chat_stream(model=self.model, messages=chat_messages)

            async for event in stream:
                if event.type == "content-delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "message"):
                        if hasattr(event.delta.message, "content"):
                            content = event.delta.message.content
                            if content and hasattr(content, "text"):
                                yield content.text

        except Exception as e:
            yield f"Error: {e!s}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate with tool calling support."""
        try:
            client = self._get_client()
            chat_messages = self._build_messages(prompt, messages, system_prompt)

            # Build request parameters
            params: dict[str, Any] = {
                "model": self.model,
                "messages": chat_messages,
            }

            # Add tools if provided
            if tools:
                params["tools"] = self._convert_tools(tools)

            # Use streaming
            stream = client.chat_stream(**params)

            # Track tool calls and text
            text_buffer = ""
            tool_calls: list[ToolCallData] = []
            current_tool_call: dict[str, Any] | None = None
            usage_data: TokenUsage | None = None

            async for event in stream:
                event_type = getattr(event, "type", "")

                # Handle text content
                if event_type == "content-delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "message"):
                        if hasattr(event.delta.message, "content"):
                            content = event.delta.message.content
                            if content and hasattr(content, "text"):
                                text = content.text
                                text_buffer += text
                                yield StreamChunk(text=text)

                # Handle tool call start
                elif event_type == "tool-call-start":
                    if hasattr(event, "delta") and hasattr(event.delta, "message"):
                        tc = event.delta.message.tool_calls
                        if tc:
                            current_tool_call = {
                                "id": getattr(tc, "id", "")
                                or f"call_{len(tool_calls)}",
                                "name": getattr(tc, "function", {}).get("name", ""),
                                "arguments": "",
                            }

                # Handle tool call delta (arguments streaming)
                elif event_type == "tool-call-delta":
                    if current_tool_call and hasattr(event, "delta"):
                        if hasattr(event.delta, "message"):
                            tc = event.delta.message.tool_calls
                            if tc and hasattr(tc, "function"):
                                args = getattr(tc.function, "arguments", "")
                                if args:
                                    current_tool_call["arguments"] += args

                # Handle tool call end
                elif event_type == "tool-call-end":
                    if current_tool_call:
                        try:
                            args = (
                                json.loads(current_tool_call["arguments"])
                                if current_tool_call["arguments"]
                                else {}
                            )
                        except json.JSONDecodeError:
                            args = {}

                        tool_calls.append(
                            ToolCallData(
                                id=current_tool_call["id"],
                                name=current_tool_call["name"],
                                arguments=args,
                            )
                        )
                        current_tool_call = None

                # Handle message end for usage data
                elif event_type == "message-end":
                    if hasattr(event, "delta") and hasattr(event.delta, "usage"):
                        usage = event.delta.usage
                        if usage:
                            usage_data = TokenUsage(
                                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                            )

            # Final chunk with tool calls and completion
            yield StreamChunk(
                text="", tool_calls=tool_calls, is_complete=True, usage=usage_data
            )

        except Exception as e:
            yield StreamChunk(text=f"Error: {e!s}", is_complete=True)

    async def list_models(self) -> list[str]:
        """Return available Cohere models."""
        try:
            client = self._get_client()
            response = await client.models.list()
            return [m.name for m in response.models if hasattr(m, "name")]
        except Exception:
            # Return known models as fallback
            return [
                "command-r-plus",
                "command-r",
                "command",
                "command-light",
                "command-nightly",
            ]

    async def validate_connection(self) -> bool:
        """Check if Cohere API is reachable."""
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False
