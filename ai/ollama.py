import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class OllamaProvider(LLMProvider):
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint
        self.model = model
        # Short connect timeout (3s) to fail fast if Ollama isn't running
        # Longer read timeout (60s) for model generation
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=3.0))

    def supports_tools(self) -> bool:
        """Ollama supports tool calling for compatible models."""
        return True

    def _build_messages(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """Build the messages array for the API call."""
        chat_messages = []

        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            msg_dict: dict[str, Any] = {"role": msg["role"]}
            if "content" in msg:
                msg_dict["content"] = msg["content"]
            if "tool_calls" in msg:
                msg_dict["tool_calls"] = msg["tool_calls"]
            chat_messages.append(msg_dict)

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
        except httpx.HTTPError as e:
            yield f"Error: Could not connect to Ollama. {e!s}"

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
                collected_tool_calls = []

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

        except httpx.HTTPError as e:
            yield StreamChunk(
                text=f"Error: Could not connect to Ollama. {e!s}", is_complete=True
            )

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

    async def close(self):
        await self.client.aclose()
