import asyncio
import json
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import boto3

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class BedrockProvider(LLMProvider):
    """AWS Bedrock provider with tool calling support for Claude models."""

    def __init__(self, region_name: str, model: str = "anthropic.claude-v2"):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.bedrock = boto3.client("bedrock", region_name=region_name)
        self.model = model
        self._executor = ThreadPoolExecutor(max_workers=2)

    def supports_tools(self) -> bool:
        """Only Claude models on Bedrock support tool calling."""
        return "claude" in self.model.lower()

    def _is_claude_model(self) -> bool:
        """Check if this is a Claude model."""
        return "claude" in self.model.lower()

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Bedrock Claude format.

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }

        Bedrock Claude format:
        {
            "name": "...",
            "description": "...",
            "input_schema": {...}
        }
        """
        bedrock_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                bedrock_tools.append(
                    {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "input_schema": func.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    }
                )
        return bedrock_tools

    def _build_claude_messages(
        self, prompt: str, messages: list[Message]
    ) -> list[dict[str, Any]]:
        """Build messages array for Claude on Bedrock."""
        claude_messages = []

        for msg in messages:
            role = msg["role"]
            if role == "system":
                continue  # System handled separately

            msg_content: Any = msg.get("content", "")

            # Handle tool calls from assistant
            if role == "assistant" and "tool_calls" in msg:
                content_blocks = []
                if msg_content:
                    content_blocks.append({"type": "text", "text": msg_content})

                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}

                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": args,
                        }
                    )

                claude_messages.append({"role": "assistant", "content": content_blocks})

            # Handle tool results
            elif role == "tool":
                claude_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.get("tool_call_id", ""),
                                "content": msg_content,
                            }
                        ],
                    }
                )

            # Regular messages
            else:
                claude_messages.append({"role": role, "content": msg_content})

        # Add current prompt
        claude_messages.append({"role": "user", "content": prompt})
        return claude_messages

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Generate response using Bedrock with proper message format."""
        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."

        body = {}
        if self._is_claude_model():
            claude_messages = self._build_claude_messages(prompt, messages)
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": claude_messages,
                }
            )
        elif "llama" in self.model.lower():
            # Build context string for Llama
            context_parts = []
            for msg in messages:
                if msg["role"] == "user":
                    context_parts.append(f"User: {msg.get('content', '')}")
                else:
                    context_parts.append(f"Assistant: {msg.get('content', '')}")
            context = "\n".join(context_parts)

            body = json.dumps(
                {
                    "prompt": f"[INST] <<SYS>>{system_prompt}<</SYS>>\n\n{context}\n\nUser: {prompt} [/INST]",
                    "max_gen_len": 2048,
                    "temperature": 0.1,
                    "top_p": 0.9,
                }
            )
        else:
            yield "Error: Unsupported model family for auto-formatting."
            return

        try:
            # Run blocking boto3 call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: self.client.invoke_model_with_response_stream(
                    modelId=self.model, body=body
                ),
            )

            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_json = json.loads(chunk.get("bytes").decode())
                        text = ""
                        if self._is_claude_model():
                            if chunk_json.get("type") == "content_block_delta":
                                delta = chunk_json.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                        elif "llama" in self.model.lower():
                            text = chunk_json.get("generation", "")

                        if text:
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
        """Generate response with tool calling support (Claude only)."""
        if not self._is_claude_model():
            # Fall back to regular generation for non-Claude models
            async for text in self.generate(prompt, messages, system_prompt):
                yield StreamChunk(text=text)
            yield StreamChunk(is_complete=True)
            return

        if not system_prompt:
            system_prompt = "You are a helpful AI assistant."

        try:
            claude_messages = self._build_claude_messages(prompt, messages)

            # Build request body with tools
            request_body: dict[str, Any] = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": claude_messages,
            }

            # Add tools if provided
            if tools:
                request_body["tools"] = self._convert_tools(tools)

            body = json.dumps(request_body)

            # Run blocking boto3 call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                lambda: self.client.invoke_model_with_response_stream(
                    modelId=self.model, body=body
                ),
            )

            # Track tool calls and response
            tool_calls: list[ToolCallData] = []
            current_tool_use: dict[str, Any] | None = None
            usage_data: TokenUsage | None = None
            text_buffer = ""

            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if not chunk:
                        continue

                    chunk_json = json.loads(chunk.get("bytes").decode())
                    event_type = chunk_json.get("type", "")

                    # Message start - may contain usage info
                    if event_type == "message_start":
                        msg = chunk_json.get("message", {})
                        usage = msg.get("usage", {})
                        if usage:
                            usage_data = TokenUsage(
                                input_tokens=usage.get("input_tokens", 0),
                                output_tokens=0,
                            )

                    # Content block start - might be text or tool_use
                    elif event_type == "content_block_start":
                        content_block = chunk_json.get("content_block", {})
                        block_type = content_block.get("type", "")

                        if block_type == "tool_use":
                            current_tool_use = {
                                "id": content_block.get("id", ""),
                                "name": content_block.get("name", ""),
                                "input_json": "",
                            }

                    # Content block delta - text or tool input
                    elif event_type == "content_block_delta":
                        delta = chunk_json.get("delta", {})
                        delta_type = delta.get("type", "")

                        if delta_type == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                text_buffer += text
                                yield StreamChunk(text=text)

                        elif delta_type == "input_json_delta":
                            if current_tool_use:
                                json_chunk = delta.get("partial_json", "")
                                current_tool_use["input_json"] += json_chunk

                    # Content block stop - finalize tool use
                    elif event_type == "content_block_stop":
                        if current_tool_use:
                            try:
                                args = (
                                    json.loads(current_tool_use["input_json"])
                                    if current_tool_use["input_json"]
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

                    # Message delta - may contain stop reason and usage
                    elif event_type == "message_delta":
                        delta = chunk_json.get("delta", {})
                        usage = chunk_json.get("usage", {})
                        if usage and usage_data:
                            usage_data = TokenUsage(
                                input_tokens=usage_data.input_tokens,
                                output_tokens=usage.get("output_tokens", 0),
                            )

                    # Message stop - final event
                    elif event_type == "message_stop":
                        pass  # Will yield final chunk after loop

            # Final chunk with all tool calls
            yield StreamChunk(
                text="", tool_calls=tool_calls, is_complete=True, usage=usage_data
            )

        except Exception as e:
            yield StreamChunk(text=f"Error: {e!s}", is_complete=True)

    async def list_models(self) -> list[str]:
        """List available Bedrock foundation models."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor, self.bedrock.list_foundation_models
            )
            return [m["modelId"] for m in response.get("modelSummaries", [])]
        except Exception:
            return []

    async def validate_connection(self) -> bool:
        """Validate connection to Bedrock."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor, self.bedrock.list_foundation_models
            )
            return True
        except Exception:
            return False
