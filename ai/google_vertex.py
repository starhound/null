"""Google Vertex AI provider."""

from collections.abc import AsyncGenerator
from typing import Any

from .base import LLMProvider, Message, StreamChunk


class GoogleVertexProvider(LLMProvider):
    """Google Vertex AI / Gemini provider."""

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "gemini-2.0-flash",
        api_key: str | None = None,
    ):
        self.project_id = project_id.strip() if project_id else ""
        self.location = location
        self.model = model.strip() if model else "gemini-2.0-flash"
        self.api_key = api_key.strip() if api_key else None
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load the Vertex AI client."""
        if self._client is None:
            try:
                from google import genai

                from google.genai import Client

                if self.api_key:
                    self._client = Client(
                        api_key=self.api_key, http_options={"timeout": 60}
                    )
                else:
                    self._client = Client(
                        vertexai=True,
                        project=self.project_id,
                        location=self.location,
                        http_options={"timeout": 60},
                    )

            except ImportError as e:
                raise ImportError(
                    "google-genai package required. "
                    "Install with: pip install google-genai"
                ) from e
        return self._client

    def _build_contents(
        self, prompt: str, messages: list[Message], system_prompt: str | None
    ) -> tuple:
        """Build contents for Gemini API (V2 SDK)."""
        contents = []

        for msg in messages:
            msg_role = msg.get("role", "user")
            role = "model" if msg_role == "assistant" else "user"
            content_part = msg.get("content", "")

            # Helper to create part dict
            parts = []

            # Handle tool roles to avoid confusion
            if msg_role == "tool":
                content_part = f"Tool Result: {content_part}"

            if content_part:
                parts.append({"text": content_part})

            # Add existing tool calls
            # (New SDK handles tool history differently, sticking to basic text history for now)
            # If we need to support full chat history with tools, we'd add proper Parts

            if parts:
                contents.append({"role": role, "parts": parts})

        # Add current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        return contents, system_prompt

    async def generate(
        self, prompt: str, messages: list[Message], system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Gemini."""
        try:
            from google.genai import types

            client = self._get_client()
            contents, sys_prompt = self._build_contents(prompt, messages, system_prompt)

            config = types.GenerateContentConfig(
                temperature=0.7, system_instruction=sys_prompt if sys_prompt else None
            )

            # Use stream=True using async client
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
        """Generate with tool support."""
        try:
            from google.genai import types

            from .base import TokenUsage, ToolCallData

            client = self._get_client()

            # Convert tools (Reuse our helper, it produces valid JSON schema for Tools)
            google_tools = self._convert_tools(tools)

            # With new SDK, we pass tools in config as Tool objects
            # The types.Tool wraps function_declarations for proper SDK format

            # Construct config
            contents, sys_prompt = self._build_contents(prompt, messages, system_prompt)

            # Enable thinking for Gemini 2.5 models
            thinking_config = None
            if "2.5" in self.model or "2.5" in str(self.model):
                try:
                    thinking_config = types.ThinkingConfig(include_thoughts=True)
                except Exception:
                    # ThinkingConfig may not be available in older SDK versions
                    pass

            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=sys_prompt if sys_prompt else None,
                tools=[types.Tool(function_declarations=google_tools)],  # type: ignore[arg-type]
                thinking_config=thinking_config,
            )

            # Use client.aio for async operations
            response = await client.aio.models.generate_content_stream(
                model=self.model, contents=contents, config=config
            )

            async for chunk in response:
                text_content = ""
                thinking_content = ""
                tool_calls = []

                # Check for candidates / parts
                # New SDK chunk structure: chunk.candidates[0].content.parts
                if chunk.candidates:
                    for cand in chunk.candidates:
                        if cand.content and cand.content.parts:
                            for part in cand.content.parts:
                                # Check for thinking/thought content (Gemini 2.5 native thinking)
                                is_thought = False
                                if hasattr(part, "thought") and part.thought:
                                    if isinstance(part.thought, bool):
                                        # It's a flag, content is in text
                                        if part.text:
                                            thinking_content += part.text
                                        is_thought = True
                                    else:
                                        # It's likely the content itself
                                        thinking_content += str(part.thought)
                                        is_thought = True

                                # Only add to main text if it wasn't a thought
                                if part.text and not is_thought:
                                    text_content += part.text

                                # Check for function call
                                # In V1 it was .function_call, in V2 likely same or slightly different
                                if part.function_call:
                                    import uuid

                                    fc = part.function_call
                                    call_id = f"call_{str(uuid.uuid4())[:8]}"

                                    # Convert args to dict if not already
                                    args = fc.args
                                    if not isinstance(args, dict):
                                        # Try to convert if it's a map/struct
                                        # New SDK might return native dict
                                        args = dict(args)

                                    tool_calls.append(
                                        ToolCallData(
                                            id=call_id, name=fc.name, arguments=args
                                        )
                                    )

                usage = None
                # Check usage metadata
                if chunk.usage_metadata:
                    usage = TokenUsage(
                        input_tokens=chunk.usage_metadata.prompt_token_count,
                        output_tokens=chunk.usage_metadata.candidates_token_count,
                    )

                # Include thinking content with <think> tags if present
                combined_text = ""
                if thinking_content:
                    combined_text = f"<think>{thinking_content}</think>\n"
                combined_text += text_content

                yield StreamChunk(
                    text=combined_text, tool_calls=tool_calls, usage=usage
                )

        except Exception as e:
            import traceback

            traceback.print_exc()
            yield StreamChunk(text=f"Error: {e!s}")

    def supports_tools(self) -> bool:
        """Check if this provider supports tool calling."""
        return True

    def _convert_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Recursively convert OpenAI schema to Google Gemini schema."""
        if not isinstance(schema, dict):
            return schema

        new_schema: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "type":
                # Google expects uppercase types (STRING, OBJECT, INTEGER, etc.)
                if isinstance(value, str):
                    new_schema[key] = value.upper()
            elif key == "properties":
                # Recursively convert properties
                new_props = {}
                for prop_name, prop_schema in value.items():
                    new_props[prop_name] = self._convert_schema(prop_schema)
                new_schema[key] = new_props
            elif key == "items":
                # Recursively convert array items
                new_schema[key] = self._convert_schema(value)
            elif key == "additionalProperties":
                # Skip additionalProperties for now as it causes issues
                continue
            else:
                new_schema[key] = value

        return new_schema

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI tool format to Google Gemini format."""
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
        """List available Gemini models."""
        try:
            client = self._get_client()

            models = []
            # V2 SDK paging list - using aio
            async for model in await client.aio.models.list(config={"page_size": 100}):
                name = model.name.replace("models/", "")
                # Filter for Gemini generation models (skip embedding models)
                if name.startswith("gemini"):
                    models.append(name)
            return sorted(models, reverse=True)  # Newest first
        except Exception as e:
            # Log the error for debugging
            import sys

            print(f"[GoogleVertexProvider] list_models failed: {e}", file=sys.stderr)
            # Return common models as fallback
            return [
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ]

    async def validate_connection(self) -> bool:
        """Check if Gemini API is reachable."""
        try:
            client = self._get_client()
            # V2 SDK - using aio
            response = await client.aio.models.generate_content(
                model=self.model, contents="Hi"
            )
            return response is not None
        except Exception:
            return False
