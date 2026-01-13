import json
import os
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData

# Default timeouts (can be overridden via environment variables)
DEFAULT_CONNECT_TIMEOUT = 10.0  # Seconds to establish connection
DEFAULT_READ_TIMEOUT = 60.0  # Seconds for model generation


class OllamaProvider(LLMProvider):
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model
        # Timeouts configurable via env vars for slow machines
        connect_timeout = float(
            os.environ.get("OLLAMA_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT)
        )
        read_timeout = float(
            os.environ.get("OLLAMA_READ_TIMEOUT", DEFAULT_READ_TIMEOUT)
        )
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout)
        )

    def supports_tools(self) -> bool:
        """Ollama supports tool calling for compatible models."""
        return True

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        """Convert a single Message to API format."""
        result: dict[str, Any] = {"role": msg.get("role", "user")}
        if content := msg.get("content"):
            result["content"] = content
        if tool_calls := msg.get("tool_calls"):
            result["tool_calls"] = tool_calls
        return result

    def _build_messages(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Build the messages array for the API call."""
        chat_messages: list[dict[str, Any]] = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(self._convert_message(msg) for msg in messages)
        chat_messages.append({"role": "user", "content": prompt})
        return chat_messages

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Generate response using Ollama's chat API with proper message format."""
        url = f"{self.endpoint}/api/chat"
        chat_messages = self._build_messages(prompt, messages, system_prompt)

        payload = {"model": self.model, "messages": chat_messages, "stream": True}

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError as e:
            yield f"[Connection failed: {e!s}]"
        except httpx.TimeoutException as e:
            yield f"[Connection timeout: {e!s}]"
        except httpx.HTTPError as e:
            yield f"[HTTP error: {e!s}]"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate response with tool calling support."""
        url = f"{self.endpoint}/api/chat"
        chat_messages = self._build_messages(prompt, messages, system_prompt)

        payload = {"model": self.model, "messages": chat_messages, "stream": True}

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                collected_tool_calls: list[ToolCallData] = []

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)

                        # Handle text content
                        if "message" in data:
                            msg = data["message"]
                            if msg.get("content"):
                                yield StreamChunk(text=msg["content"])

                            # Handle tool calls
                            if "tool_calls" in msg:
                                for tc in msg["tool_calls"]:
                                    func = tc.get("function", {})
                                    collected_tool_calls.append(
                                        ToolCallData(
                                            id=tc.get(
                                                "id",
                                                f"call_{len(collected_tool_calls)}",
                                            ),
                                            name=func.get("name", ""),
                                            arguments=func.get("arguments", {}),
                                        )
                                    )

                        # Check if done
                        if data.get("done", False):
                            # Ollama includes token counts in the final response
                            usage_data = None
                            if "prompt_eval_count" in data or "eval_count" in data:
                                usage_data = TokenUsage(
                                    input_tokens=data.get("prompt_eval_count", 0),
                                    output_tokens=data.get("eval_count", 0),
                                )

                            yield StreamChunk(
                                text="",
                                tool_calls=collected_tool_calls,
                                is_complete=True,
                                usage=usage_data,
                            )
                            break

                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError as e:
            yield StreamChunk(
                text="", is_complete=True, error=f"Connection failed: {e!s}"
            )
        except httpx.TimeoutException as e:
            yield StreamChunk(
                text="", is_complete=True, error=f"Connection timeout: {e!s}"
            )
        except httpx.HTTPError as e:
            yield StreamChunk(text="", is_complete=True, error=f"HTTP error: {e!s}")

    async def embed_text(self, text: str) -> list[float] | None:
        """Get vector embedding for text using Ollama /api/embeddings."""
        url = f"{self.endpoint}/api/embeddings"
        payload = {"model": self.model, "prompt": text}

        try:
            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
        except Exception:
            pass
        return None

    async def list_models(self) -> list[str]:
        url = f"{self.endpoint}/api/tags"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except httpx.HTTPError:
            pass
        return []

    async def validate_connection(self) -> bool:
        url = f"{self.endpoint}/api/tags"
        try:
            response = await self.client.get(url)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self.client.aclose()
