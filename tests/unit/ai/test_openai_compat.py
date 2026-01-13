"""Tests for ai/openai_compat.py - OpenAI-compatible provider base."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import Message
from ai.openai_compat import OpenAICompatibleProvider


class TestOpenAICompatibleProviderInit:
    def test_init_sets_model(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test", model="gpt-4o")
        assert provider.model == "gpt-4o"

    def test_init_uses_default_model(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")
        assert provider.model == "gpt-3.5-turbo"

    def test_init_creates_client_with_base_url(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI") as mock_openai:
            OpenAICompatibleProvider(
                api_key="sk-test",
                base_url="http://localhost:1234",
                model="local-model",
            )
        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs["base_url"] == "http://localhost:1234"


class TestOpenAICompatibleProviderSupportsTools:
    def test_supports_tools_returns_true(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")
        assert provider.supports_tools() is True


class TestOpenAICompatibleProviderBuildMessages:
    def test_build_messages_adds_system_prompt(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        result = provider._build_messages(
            prompt="Hello", messages=[], system_prompt="Be concise"
        )

        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Be concise"

    def test_build_messages_uses_default_system_prompt(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        result = provider._build_messages(
            prompt="Hello", messages=[], system_prompt=None
        )

        assert result[0]["role"] == "system"
        assert "terminal" in result[0]["content"].lower()

    def test_build_messages_includes_history(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        messages: list[Message] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = provider._build_messages(
            prompt="Test", messages=messages, system_prompt="Be helpful"
        )

        assert len(result) == 4
        assert result[1]["content"] == "Hi"
        assert result[2]["content"] == "Hello!"
        assert result[3]["content"] == "Test"

    def test_build_messages_preserves_tool_calls(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        tool_calls = [{"id": "call_1", "function": {"name": "test"}}]
        messages: list[Message] = [
            {"role": "assistant", "content": "", "tool_calls": tool_calls}
        ]
        result = provider._build_messages(
            prompt="Continue", messages=messages, system_prompt=None
        )

        assert result[1]["tool_calls"] == tool_calls

    def test_build_messages_preserves_tool_call_id(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        messages: list[Message] = [
            {"role": "tool", "content": "Result", "tool_call_id": "call_1"}
        ]
        result = provider._build_messages(
            prompt="Continue", messages=messages, system_prompt=None
        )

        assert result[1]["tool_call_id"] == "call_1"


class TestOpenAICompatibleProviderGenerate:
    @pytest.mark.asyncio
    async def test_generate_yields_content(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content=" world"))]

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_generate_handles_empty_content(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content=None))]

        async def mock_stream():
            yield mock_chunk

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_generate_falls_back_without_stream_options(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="Fallback"))]

        async def mock_stream():
            yield mock_chunk

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if "stream_options" in kwargs:
                raise Exception("stream_options not supported")
            return mock_stream()

        provider.client.chat.completions.create = mock_create

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert chunks == ["Fallback"]
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_generate_handles_exception(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API error" in chunks[0]


class TestOpenAICompatibleProviderGenerateWithTools:
    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_text(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content="Hello", tool_calls=None),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk2.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert chunks[0].text == "Hello"
        assert chunks[-1].is_complete
        assert chunks[-1].usage.input_tokens == 10
        assert chunks[-1].usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_calls(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "search"
        mock_tc.function.arguments = '{"query": "test"}'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Search", messages=[], tools=[{"type": "function"}]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.is_complete
        assert len(final.tool_calls) == 1
        assert final.tool_calls[0].id == "call_1"
        assert final.tool_calls[0].name == "search"
        assert final.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_cleans_markdown_in_args(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "test"
        mock_tc.function.arguments = '```json\n{"key": "value"}\n```'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_invalid_json(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "test"
        mock_tc.function.arguments = "invalid json"

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_exception(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API error" in chunks[0].text
        assert chunks[0].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_skips_empty_choices(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = []
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content="Hi", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert any(c.text == "Hi" for c in chunks)


class TestOpenAICompatibleProviderEmbedText:
    @pytest.mark.asyncio
    async def test_embed_text_returns_embedding(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        provider.client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed_text("Hello world")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_text_uses_embed_model_if_specified(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(
                api_key="sk-test", model="text-embedding-ada-002"
            )

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1])]
        provider.client.embeddings.create = AsyncMock(return_value=mock_response)

        await provider.embed_text("Test")

        call_kwargs = provider.client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-ada-002"

    @pytest.mark.asyncio
    async def test_embed_text_returns_none_on_error(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.embeddings.create = AsyncMock(
            side_effect=Exception("Embedding failed")
        )

        result = await provider.embed_text("Test")
        assert result is None


class TestOpenAICompatibleProviderListModels:
    @pytest.mark.asyncio
    async def test_list_models_returns_model_ids(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="gpt-4o"),
            MagicMock(id="gpt-4o-mini"),
        ]
        provider.client.models.list = AsyncMock(return_value=mock_models)

        result = await provider.list_models()

        assert result == ["gpt-4o", "gpt-4o-mini"]

    @pytest.mark.asyncio
    async def test_list_models_handles_dict_response(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_models = MagicMock()
        mock_models.data = [{"id": "model-1"}, {"id": "model-2"}]
        provider.client.models.list = AsyncMock(return_value=mock_models)

        result = await provider.list_models()

        assert result == ["model-1", "model-2"]

    @pytest.mark.asyncio
    async def test_list_models_handles_list_response(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_list = [MagicMock(id="local-model"), {"id": "dict-model"}, "str-model"]
        provider.client.models.list = AsyncMock(return_value=mock_list)

        result = await provider.list_models()

        assert "local-model" in result
        assert "dict-model" in result
        assert "str-model" in result

    @pytest.mark.asyncio
    async def test_list_models_returns_empty_on_error(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.models.list = AsyncMock(side_effect=Exception("List failed"))

        result = await provider.list_models()
        assert result == []


class TestOpenAICompatibleProviderValidateConnection:
    @pytest.mark.asyncio
    async def test_validate_connection_returns_true_on_success(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.models.list = AsyncMock(return_value=MagicMock())

        result = await provider.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_error(self):
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.models.list = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await provider.validate_connection()
        assert result is False


class TestOpenAICompatibleProviderToolSupport:
    """Tests for tool calling support in OpenAICompatibleProvider."""

    def test_supports_tools_returns_true(self):
        """OpenAI-compatible providers support tool calling."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")
        assert provider.supports_tools() is True

    @pytest.mark.asyncio
    async def test_generate_with_tools_passes_tools_to_api(self):
        """Tools should be passed to the API when provided."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="Done", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        captured_params = {}

        async def mock_create(**kwargs):
            captured_params.update(kwargs)
            return mock_stream()

        provider.client.chat.completions.create = mock_create

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="What's the weather?", messages=[], tools=tools
        ):
            chunks.append(chunk)

        assert "tools" in captured_params
        assert captured_params["tools"] == tools
        assert captured_params["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_generate_with_tools_omits_tools_when_empty(self):
        """Tools and tool_choice should not be passed when tools list is empty."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="Hi", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        captured_params = {}

        async def mock_create(**kwargs):
            captured_params.update(kwargs)
            return mock_stream()

        provider.client.chat.completions.create = mock_create

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hello", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert "tools" not in captured_params
        assert "tool_choice" not in captured_params

    @pytest.mark.asyncio
    async def test_generate_with_tools_accumulates_streamed_args(self):
        """Tool call arguments should accumulate across multiple chunks."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        # First chunk: tool call starts with partial args
        mock_tc1 = MagicMock()
        mock_tc1.index = 0
        mock_tc1.id = "call_abc"
        mock_tc1.function = MagicMock()
        mock_tc1.function.name = "search"
        mock_tc1.function.arguments = '{"que'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc1]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        # Second chunk: continues args
        mock_tc2 = MagicMock()
        mock_tc2.index = 0
        mock_tc2.id = None
        mock_tc2.function = MagicMock()
        mock_tc2.function.name = None
        mock_tc2.function.arguments = 'ry": "te'

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc2]),
                finish_reason=None,
            )
        ]
        mock_chunk2.usage = None

        # Third chunk: finishes args
        mock_tc3 = MagicMock()
        mock_tc3.index = 0
        mock_tc3.id = None
        mock_tc3.function = MagicMock()
        mock_tc3.function.name = None
        mock_tc3.function.arguments = 'st"}'

        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc3]),
                finish_reason=None,
            )
        ]
        mock_chunk3.usage = None

        # Final chunk
        mock_chunk4 = MagicMock()
        mock_chunk4.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk4.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_chunk3
            yield mock_chunk4

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Search", messages=[], tools=[{"type": "function"}]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.is_complete
        assert len(final.tool_calls) == 1
        assert final.tool_calls[0].id == "call_abc"
        assert final.tool_calls[0].name == "search"
        assert final.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_multiple_tool_calls(self):
        """Multiple tool calls in same response should be handled."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc1 = MagicMock()
        mock_tc1.index = 0
        mock_tc1.id = "call_1"
        mock_tc1.function = MagicMock()
        mock_tc1.function.name = "tool_a"
        mock_tc1.function.arguments = '{"a": 1}'

        mock_tc2 = MagicMock()
        mock_tc2.index = 1
        mock_tc2.id = "call_2"
        mock_tc2.function = MagicMock()
        mock_tc2.function.name = "tool_b"
        mock_tc2.function.arguments = '{"b": 2}'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc1, mock_tc2]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Run both", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert len(final.tool_calls) == 2
        assert final.tool_calls[0].name == "tool_a"
        assert final.tool_calls[0].arguments == {"a": 1}
        assert final.tool_calls[1].name == "tool_b"
        assert final.tool_calls[1].arguments == {"b": 2}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_empty_args(self):
        """Tool calls with empty arguments should default to empty dict."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "no_args_tool"
        mock_tc.function.arguments = ""

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Run", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {}

    @pytest.mark.asyncio
    async def test_generate_with_tools_usage_tracking(self):
        """Usage data should be captured from the final chunk."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content="Response", tool_calls=None),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk2.usage = MagicMock(prompt_tokens=100, completion_tokens=50)

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.is_complete
        assert final.usage is not None
        assert final.usage.input_tokens == 100
        assert final.usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_generate_with_tools_falls_back_without_stream_options(self):
        """Should fall back to no stream_options if server doesn't support it."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="Fallback", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if "stream_options" in kwargs:
                raise Exception("stream_options not supported")
            return mock_stream()

        provider.client.chat.completions.create = mock_create

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert any(c.text == "Fallback" for c in chunks)
        assert call_count == 2


class TestOpenAICompatibleProviderToolSchemaConversion:
    """Tests for tool schema handling."""

    @pytest.mark.asyncio
    async def test_tools_passed_unchanged_to_api(self):
        """OpenAI-compatible API expects tools in OpenAI format - no conversion."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_chunk = MagicMock()
        mock_chunk.choices = [
            MagicMock(
                delta=MagicMock(content="OK", tool_calls=None),
                finish_reason="stop",
            )
        ]
        mock_chunk.usage = None

        async def mock_stream():
            yield mock_chunk

        captured_tools = None

        async def mock_create(**kwargs):
            nonlocal captured_tools
            captured_tools = kwargs.get("tools")
            return mock_stream()

        provider.client.chat.completions.create = mock_create

        complex_tool = {
            "type": "function",
            "function": {
                "name": "complex_tool",
                "description": "A complex tool with nested schema",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nested": {
                            "type": "object",
                            "properties": {
                                "inner": {"type": "string"},
                            },
                        },
                        "array_field": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": ["nested"],
                },
            },
        }

        async for _ in provider.generate_with_tools(
            prompt="Use tool", messages=[], tools=[complex_tool]
        ):
            pass

        assert captured_tools == [complex_tool]


class TestOpenAICompatibleProviderToolErrorHandling:
    """Tests for error handling during tool execution."""

    @pytest.mark.asyncio
    async def test_api_error_returns_error_chunk(self):
        """API errors should return an error StreamChunk."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        provider.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: Rate limit exceeded" in chunks[0].text
        assert chunks[0].is_complete

    @pytest.mark.asyncio
    async def test_malformed_tool_call_json_returns_empty_args(self):
        """Malformed JSON in tool call arguments should result in empty dict."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_bad"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "broken"
        mock_tc.function.arguments = "{broken: json, missing quotes}"

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].name == "broken"
        assert final.tool_calls[0].arguments == {}

    @pytest.mark.asyncio
    async def test_markdown_code_block_cleanup_json_only(self):
        """Should clean ```json prefix from arguments."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "test"
        mock_tc.function.arguments = '```json{"value": 42}```'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {"value": 42}

    @pytest.mark.asyncio
    async def test_markdown_code_block_cleanup_generic(self):
        """Should clean generic ``` prefix from arguments."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_1"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "test"
        mock_tc.function.arguments = '```{"key": "val"}```'

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk2.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {"key": "val"}

    @pytest.mark.asyncio
    async def test_tool_call_with_text_interleaved(self):
        """Text and tool calls can be interleaved in the response."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = OpenAICompatibleProvider(api_key="sk-test")

        # First chunk: text
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [
            MagicMock(
                delta=MagicMock(content="Let me search", tool_calls=None),
                finish_reason=None,
            )
        ]
        mock_chunk1.usage = None

        # Second chunk: tool call
        mock_tc = MagicMock()
        mock_tc.index = 0
        mock_tc.id = "call_search"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "search"
        mock_tc.function.arguments = '{"q": "test"}'

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=[mock_tc]),
                finish_reason=None,
            )
        ]
        mock_chunk2.usage = None

        # Final chunk
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [
            MagicMock(
                delta=MagicMock(content=None, tool_calls=None),
                finish_reason="tool_calls",
            )
        ]
        mock_chunk3.usage = None

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_chunk3

        provider.client.chat.completions.create = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Search", messages=[], tools=[{"type": "function"}]
        ):
            chunks.append(chunk)

        # Should have text chunk, then final with tool calls
        assert chunks[0].text == "Let me search"
        final = chunks[-1]
        assert final.is_complete
        assert len(final.tool_calls) == 1
        assert final.tool_calls[0].name == "search"
