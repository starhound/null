from typing import AsyncGenerator, List, Optional, Dict, Any
import json
import openai
from .base import LLMProvider, Message, StreamChunk, ToolCallData, TokenUsage


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model

    def supports_tools(self) -> bool:
        """OpenAI models support tool calling."""
        return True

    def _build_messages(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build the messages array for the API call."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant integrated into a terminal."

        chat_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            msg_dict: Dict[str, Any] = {"role": msg["role"]}
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
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str] = None
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
                    **params,
                    stream_options={"include_usage": True}
                )
            except Exception:
                # Fallback without stream_options
                stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {str(e)}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
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
                    **params,
                    stream_options={"include_usage": True}
                )
            except Exception:
                # Some servers (LM Studio, etc.) don't support stream_options
                stream = await self.client.chat.completions.create(**params)

            # Track tool calls being built up across chunks
            current_tool_calls: Dict[int, Dict[str, Any]] = {}
            text_buffer = ""
            usage_data: Optional[TokenUsage] = None

            async for chunk in stream:
                # Check for usage data (comes in final chunk for OpenAI)
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage_data = TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens or 0,
                        output_tokens=chunk.usage.completion_tokens or 0
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
                                "arguments": ""
                            }

                        if tc.id:
                            current_tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                current_tool_calls[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                current_tool_calls[idx]["arguments"] += tc.function.arguments

                # Check if this is the final chunk
                if chunk.choices[0].finish_reason:
                    tool_calls = []
                    for tc_data in current_tool_calls.values():
                        try:
                            args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                        except json.JSONDecodeError:
                            args = {}

                        tool_calls.append(ToolCallData(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=args
                        ))

                    yield StreamChunk(
                        text="",
                        tool_calls=tool_calls,
                        is_complete=True,
                        usage=usage_data
                    )

        except Exception as e:
            yield StreamChunk(text=f"Error: {str(e)}", is_complete=True)

    async def list_models(self) -> List[str]:
        try:
            models_page = await self.client.models.list()
            return [m.id for m in models_page.data]
        except Exception:
            return []

    async def validate_connection(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
