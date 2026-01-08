"""Google AI Studio provider (API key based)."""

from collections.abc import AsyncGenerator
from typing import Any

from .base import LLMProvider, Message, StreamChunk, TokenUsage, ToolCallData


class GoogleAIProvider(LLMProvider):
    """Google AI Studio provider using API key authentication."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key.strip() if api_key else ""
        self.model = model.strip() if model else "gemini-2.0-flash"
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google.genai import Client

                self._client = Client(
                    api_key=self.api_key,
                    http_options={"timeout": 60},
                )
            except ImportError as e:
                raise ImportError(
                    "google-genai package required. Install with: pip install google-genai"
                ) from e
        return self._client

    def _build_contents(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> tuple[list[dict], str | None]:
        contents = []

        for msg in messages:
            msg_role = msg.get("role", "user")
            role = "model" if msg_role == "assistant" else "user"
            content_part = msg.get("content", "")

            if msg_role == "tool":
                content_part = f"Tool Result: {content_part}"

            parts = []
            if content_part:
                parts.append({"text": content_part})

            if parts:
                contents.append({"role": role, "parts": parts})

        contents.append({"role": "user", "parts": [{"text": prompt}]})
        return contents, system_prompt

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        try:
            from google.genai import types

            client = self._get_client()
            contents, sys_prompt = self._build_contents(prompt, messages, system_prompt)

            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=sys_prompt if sys_prompt else None,
            )

            response = await client.aio.models.generate_content_stream(
                model=self.model, contents=contents, config=config
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"Error: {e!s}"

    async def generate_with_tools(
        self,
        prompt: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        try:
            from google.genai import types

            client = self._get_client()
            google_tools = self._convert_tools(tools)
            contents, sys_prompt = self._build_contents(prompt, messages, system_prompt)

            thinking_config = None
            if "2.5" in self.model or "3" in self.model:
                try:
                    thinking_config = types.ThinkingConfig(include_thoughts=True)
                except Exception:
                    pass

            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=sys_prompt if sys_prompt else None,
                tools=[types.Tool(function_declarations=google_tools)],
                thinking_config=thinking_config,
            )

            response = await client.aio.models.generate_content_stream(
                model=self.model, contents=contents, config=config
            )

            async for chunk in response:
                text_content = ""
                thinking_content = ""
                tool_calls = []

                if chunk.candidates:
                    for cand in chunk.candidates:
                        if cand.content and cand.content.parts:
                            for part in cand.content.parts:
                                is_thought = False
                                if hasattr(part, "thought") and part.thought:
                                    if isinstance(part.thought, bool):
                                        if part.text:
                                            thinking_content += part.text
                                        is_thought = True
                                    else:
                                        thinking_content += str(part.thought)
                                        is_thought = True

                                if part.text and not is_thought:
                                    text_content += part.text

                                if part.function_call:
                                    import uuid

                                    fc = part.function_call
                                    call_id = f"call_{str(uuid.uuid4())[:8]}"
                                    args = fc.args
                                    if not isinstance(args, dict):
                                        args = dict(args)

                                    tool_calls.append(
                                        ToolCallData(
                                            id=call_id, name=fc.name, arguments=args
                                        )
                                    )

                usage = None
                if chunk.usage_metadata:
                    usage = TokenUsage(
                        input_tokens=chunk.usage_metadata.prompt_token_count,
                        output_tokens=chunk.usage_metadata.candidates_token_count,
                    )

                combined_text = ""
                if thinking_content:
                    combined_text = f"<think>{thinking_content}</think>\n"
                combined_text += text_content

                yield StreamChunk(
                    text=combined_text, tool_calls=tool_calls, usage=usage
                )

        except Exception as e:
            yield StreamChunk(text=f"Error: {e!s}")

    def supports_tools(self) -> bool:
        return True

    def _convert_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(schema, dict):
            return schema

        new_schema: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "type":
                if isinstance(value, str):
                    new_schema[key] = value.upper()
            elif key == "properties":
                new_props = {}
                for prop_name, prop_schema in value.items():
                    new_props[prop_name] = self._convert_schema(prop_schema)
                new_schema[key] = new_props
            elif key == "items":
                new_schema[key] = self._convert_schema(value)
            elif key == "additionalProperties":
                continue
            else:
                new_schema[key] = value

        return new_schema

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        google_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                parameters = func.get("parameters", {})
                converted_params = self._convert_schema(parameters)

                google_tools.append(
                    {
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": converted_params,
                    }
                )
        return google_tools

    async def list_models(self) -> list[str]:
        try:
            client = self._get_client()
            models = []
            async for model in await client.aio.models.list(config={"page_size": 100}):
                name = model.name.replace("models/", "")
                if name.startswith("gemini"):
                    models.append(name)
            return sorted(models, reverse=True)
        except Exception:
            return [
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ]

    async def validate_connection(self) -> bool:
        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self.model, contents="Hi"
            )
            return response is not None
        except Exception:
            return False
