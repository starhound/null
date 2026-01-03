import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from openai import AsyncAzureOpenAI

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class AzureProvider(LLMProvider):
    """Azure OpenAI provider with full tool calling support."""

    def __init__(self, endpoint: str, api_key: str, api_version: str, model: str):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            timeout=httpx.Timeout(120.0, connect=3.0),
        )
        self.deployment_name = (
            model  # In Azure, model usually refers to deployment name
        )
        self.model = model

    def supports_tools(self) -> bool:
        """Azure OpenAI deployments support tool calling."""
        return True

    def _build_messages(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Build the messages array for the API call."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant integrated into a terminal."

        chat_messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        for msg in messages:
            msg_dict: dict[str, Any] = {"role": msg["role"]}
            if "content" in msg:
                msg_dict["content"] = msg["content"]
            if "tool_calls" in msg:
                msg_dict["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                msg_dict["tool_call_id"] = msg["tool_call_id"]
            chat_messages.append(msg_dict)

        chat_messages.append({"role": "user", "content": prompt})
        return chat_messages

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Generate response using Azure OpenAI with proper message format."""
        chat_messages = self._build_messages(prompt, messages, system_prompt)

        try:
            stream = await self.client.chat.completions.create(
                model=self.deployment_name, messages=chat_messages, stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {e!s}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate response with tool calling support."""
        chat_messages = self._build_messages(prompt, messages, system_prompt)

        try:
            # Prepare API call parameters
            params: dict[str, Any] = {
                "model": self.deployment_name,
                "messages": chat_messages,
                "stream": True,
            }

            # Only add tools if provided
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            # Try with stream_options first (for usage tracking)
            try:
                stream = await self.client.chat.completions.create(
                    **params, stream_options={"include_usage": True}
                )
            except Exception:
                # Some Azure deployments may not support stream_options
                stream = await self.client.chat.completions.create(**params)

            # Track tool calls being built up across chunks
            current_tool_calls: dict[int, dict[str, Any]] = {}
            text_buffer = ""
            usage_data: TokenUsage | None = None

            async for chunk in stream:
                # Check for usage data (comes in final chunk)
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_data = TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens or 0,
                        output_tokens=chunk.usage.completion_tokens or 0,
                    )

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Handle text content
                if delta.content:
                    text_buffer += delta.content
                    yield StreamChunk(text=delta.content)

                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments": "",
                            }

                        if tc.id:
                            current_tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                current_tool_calls[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                current_tool_calls[idx]["arguments"] += (
                                    tc.function.arguments
                                )

                # Check if this is the final chunk
                if chunk.choices[0].finish_reason:
                    tool_calls = []
                    for tc_data in current_tool_calls.values():
                        try:
                            args = (
                                json.loads(tc_data["arguments"])
                                if tc_data["arguments"]
                                else {}
                            )
                        except json.JSONDecodeError:
                            args = {}

                        tool_calls.append(
                            ToolCallData(
                                id=tc_data["id"], name=tc_data["name"], arguments=args
                            )
                        )

                    yield StreamChunk(
                        text="",
                        tool_calls=tool_calls,
                        is_complete=True,
                        usage=usage_data,
                    )

        except Exception as e:
            yield StreamChunk(text=f"Error: {e!s}", is_complete=True)

    async def list_models(self) -> list[str]:
        """Return available Azure deployments.

        Azure doesn't easily list deployments via standard API.
        Returns the configured deployment name.
        """
        return [self.deployment_name]

    async def validate_connection(self) -> bool:
        """Validate connection by attempting a simple API call."""
        try:
            # Try to make a minimal request to validate connection
            await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False
