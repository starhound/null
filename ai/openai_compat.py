import json
from collections.abc import AsyncGenerator
from typing import Any, cast

import httpx
import openai

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self, api_key: str, base_url: str | None = None, model: str = "gpt-3.5-turbo"
    ):
        # Short connect timeout (3s) to fail fast if server isn't available
        # Longer read timeout (120s) for model generation
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(120.0, connect=3.0),
        )
        self.model = model

    def supports_tools(self) -> bool:
        """OpenAI models support tool calling."""
        return True

    def _build_messages(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Build the messages array for the API call."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant integrated into a terminal."

        chat_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            msg_dict: dict[str, Any] = {"role": msg.get("role", "user")}
            if msg.get("content"):
                msg_dict["content"] = msg.get("content")
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
        """Generate response using OpenAI chat API with proper message format."""
        chat_messages = self._build_messages(prompt, messages, system_prompt)

        try:
            # Try with stream_options first, fall back without if not supported
            params = {
                "model": self.model,
                "messages": chat_messages,
                "stream": True,
            }

            # Some servers (like LM Studio) may not support stream_options
            try:
                stream = await self.client.chat.completions.create(
                    **params, stream_options={"include_usage": True}
                )  # type: ignore[call-overload]
            except Exception:
                # Fallback without stream_options
                stream = await self.client.chat.completions.create(**params)  # type: ignore[call-overload]

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
            params = {
                "model": self.model,
                "messages": chat_messages,
                "stream": True,
            }

            # Only add tools if provided
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            # Try with stream_options first (for usage tracking), fall back if not supported
            try:
                stream = await self.client.chat.completions.create(
                    **params, stream_options={"include_usage": True}
                )  # type: ignore[call-overload]
            except Exception:
                # Some servers (LM Studio, etc.) don't support stream_options
                stream = await self.client.chat.completions.create(**params)  # type: ignore[call-overload]

            # Track tool calls being built up across chunks
            current_tool_calls: dict[int, dict[str, Any]] = {}
            text_buffer = ""
            usage_data: TokenUsage | None = None

            async for chunk in stream:
                # Check for usage data (comes in final chunk for OpenAI)
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
                            arg_str = tc_data["arguments"] or "{}"
                            # Cleanup potential markdown code blocks
                            if arg_str.startswith("```json"):
                                arg_str = arg_str[7:]
                            if arg_str.startswith("```"):
                                arg_str = arg_str[3:]
                            if arg_str.endswith("```"):
                                arg_str = arg_str[:-3]

                            args = json.loads(arg_str.strip())
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

    async def embed_text(self, text: str) -> list[float] | None:
        """Get vector embedding for text using OpenAI compatible API."""
        try:
            # We assume "text-embedding-3-small" or fallback to model default if specific embedding model not set
            # But usually we need a dedicated embedding model.
            # For now, let's try using the current model or a standard one.
            # Ideally config should specify embedding model.
            # Let's default to text-embedding-3-small if available, or just fail if user hasn't configured one.
            # Actually, `client.embeddings.create` requires a model.
            model = "text-embedding-3-small"

            # If using local provider (like LM Studio), they might need a specific model loaded.
            # We'll use self.model if it looks like an embedding model, otherwise default.
            if "embed" in self.model:
                model = self.model

            response = await self.client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception:
            return None

    async def embed_text(self, text: str) -> list[float] | None:
        """Get vector embedding for text using OpenAI compatible API."""
        try:
            # Default to standard OpenAI embedding model unless current model name implies embedding capability
            model = "text-embedding-3-small"
            if "embed" in self.model:
                model = self.model

            response = await self.client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception:
            return None

    async def list_models(self) -> list[str]:
        try:
            models_response = await self.client.models.list()

            # Handle different response formats
            models = []

            # Standard OpenAI format: response.data is a list of Model objects
            if hasattr(models_response, "data"):
                for m in models_response.data:
                    if hasattr(m, "id"):
                        models.append(m.id)
                    elif isinstance(m, dict) and "id" in m:
                        models.append(m["id"])
            # Some servers return list directly
            elif isinstance(models_response, list):
                for m_item in models_response:
                    m = cast(Any, m_item)
                    if hasattr(m, "id"):
                        models.append(m.id)
                    elif isinstance(m, dict) and "id" in m:
                        models.append(m["id"])
                    elif isinstance(m, str):
                        models.append(m)

            return models
        except Exception:
            return []

    async def validate_connection(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
