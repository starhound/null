"""Tests for ai/anthropic.py - AnthropicProvider implementation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.anthropic import AnthropicProvider
from ai.base import Message, StreamChunk, TokenUsage


class TestAnthropicProviderInit:
    """Tests for AnthropicProvider initialization."""

    def test_init_sets_api_key_and_model(self):
        """Provider stores api_key and model."""
        provider = AnthropicProvider(api_key="sk-ant-test", model="claude-3-opus")
        assert provider.api_key == "sk-ant-test"
        assert provider.model == "claude-3-opus"

    def test_init_uses_default_model(self):
        """Provider uses default model when not specified."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        assert provider.model == "claude-3-5-sonnet-20241022"

    def test_init_client_is_none(self):
        """Client should be None initially (lazy loading)."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        assert provider._client is None


class TestAnthropicProviderGetClient:
    """Tests for _get_client method."""

    def test_get_client_creates_anthropic_client(self):
        """Should create AsyncAnthropic client on first call."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with patch("ai.anthropic.anthropic", mock_anthropic, create=True):
                # Patch the import
                import sys

                sys.modules["anthropic"] = mock_anthropic

                result = provider._get_client()

        assert result is mock_client

    def test_get_client_raises_import_error(self):
        """Should raise ImportError if anthropic not installed."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic package required"):
                # Force import by clearing cached client
                provider._client = None
                # Mock the import to fail
                with patch("builtins.__import__", side_effect=ImportError("No module")):
                    provider._get_client()

    def test_get_client_caches_client(self):
        """Should return cached client on subsequent calls."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        mock_client = MagicMock()
        provider._client = mock_client

        result = provider._get_client()
        assert result is mock_client


class TestAnthropicProviderSupportsTools:
    """Tests for supports_tools method."""

    def test_supports_tools_returns_true(self):
        """Anthropic supports tool calling."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        assert provider.supports_tools() is True


class TestAnthropicProviderBuildMessages:
    """Tests for _build_messages method."""

    def test_build_messages_adds_current_prompt(self):
        """Should add current prompt as final user message."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        result = provider._build_messages(prompt="Hello", messages=[])

        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Hello"}

    def test_build_messages_preserves_history(self):
        """Should include history messages."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        messages: list[Message] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = provider._build_messages(prompt="How are you?", messages=messages)

        assert len(result) == 3
        assert result[0]["content"] == "Hi"
        assert result[1]["content"] == "Hello!"
        assert result[2]["content"] == "How are you?"

    def test_build_messages_skips_system_messages(self):
        """Should skip system role messages (handled separately)."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        messages: list[Message] = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ]
        result = provider._build_messages(prompt="Test", messages=messages)

        assert len(result) == 2
        assert all(m["role"] != "system" for m in result)

    def test_build_messages_converts_tool_calls(self):
        """Should convert tool_calls to Anthropic tool_use format."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        messages: list[Message] = [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "test"}',
                        },
                    }
                ],
            },
        ]
        result = provider._build_messages(prompt="Continue", messages=messages)

        assert len(result) == 2
        tool_msg = result[0]
        assert tool_msg["role"] == "assistant"
        assert len(tool_msg["content"]) == 1
        assert tool_msg["content"][0]["type"] == "tool_use"
        assert tool_msg["content"][0]["name"] == "search"
        assert tool_msg["content"][0]["input"] == {"query": "test"}

    def test_build_messages_skips_empty_content(self):
        """Should skip messages without content."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        messages: list[Message] = [
            {"role": "assistant", "content": ""},
        ]
        result = provider._build_messages(prompt="Test", messages=messages)

        # Only the prompt message
        assert len(result) == 1


class TestAnthropicProviderConvertTools:
    """Tests for _convert_tools method."""

    def test_convert_tools_to_anthropic_format(self):
        """Should convert OpenAI tool format to Anthropic."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search the web",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                },
            }
        ]

        result = provider._convert_tools(tools)

        assert len(result) == 1
        assert result[0]["name"] == "search"
        assert result[0]["description"] == "Search the web"
        assert result[0]["input_schema"]["type"] == "object"

    def test_convert_tools_handles_missing_description(self):
        """Should use empty description if not provided."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        tools = [
            {
                "type": "function",
                "function": {"name": "test_tool"},
            }
        ]

        result = provider._convert_tools(tools)

        assert result[0]["description"] == ""

    def test_convert_tools_handles_missing_parameters(self):
        """Should use default schema if parameters not provided."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        tools = [
            {
                "type": "function",
                "function": {"name": "test_tool", "description": "A tool"},
            }
        ]

        result = provider._convert_tools(tools)

        assert result[0]["input_schema"] == {"type": "object", "properties": {}}

    def test_convert_tools_skips_non_function_types(self):
        """Should only convert function-type tools."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        tools = [
            {"type": "other", "data": {}},
            {"type": "function", "function": {"name": "valid"}},
        ]

        result = provider._convert_tools(tools)

        assert len(result) == 1
        assert result[0]["name"] == "valid"


class TestAnthropicProviderGenerate:
    """Tests for generate method."""

    @pytest.mark.asyncio
    async def test_generate_yields_text(self):
        """Should yield text from stream."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        async def mock_text_stream():
            yield "Hello"
            yield " world"
            yield "!"

        mock_stream = AsyncMock()
        mock_stream.text_stream = mock_text_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate(
            prompt="Hi", messages=[], system_prompt="Be helpful"
        ):
            chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_generate_uses_default_system_prompt(self):
        """Should use default system prompt when not provided."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        async def mock_text_stream():
            yield "Response"

        mock_stream = AsyncMock()
        mock_stream.text_stream = mock_text_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        async for _ in provider.generate(prompt="Hi", messages=[], system_prompt=None):
            pass

        call_kwargs = mock_client.messages.stream.call_args[1]
        assert "terminal" in call_kwargs["system"].lower()

    @pytest.mark.asyncio
    async def test_generate_handles_exception(self):
        """Should yield error message on exception."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception("API error")
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate(prompt="Hi", messages=[]):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API error" in chunks[0]


class TestAnthropicProviderGenerateWithTools:
    """Tests for generate_with_tools method."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_text_delta(self):
        """Should yield text from content_block_delta events."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        # Create mock events
        text_delta = MagicMock()
        text_delta.type = "content_block_delta"
        text_delta.delta = MagicMock()
        text_delta.delta.text = "Hello"

        stop_event = MagicMock()
        stop_event.type = "message_stop"

        async def mock_event_stream():
            yield text_delta
            yield stop_event

        mock_stream = AsyncMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert any(c.text == "Hello" for c in chunks)

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_use(self):
        """Should collect tool calls from tool_use events."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        # Tool use block start
        tool_start = MagicMock()
        tool_start.type = "content_block_start"
        tool_start.content_block = MagicMock()
        tool_start.content_block.type = "tool_use"
        tool_start.content_block.id = "call_1"
        tool_start.content_block.name = "search"

        # Tool input delta
        tool_delta = MagicMock()
        tool_delta.type = "content_block_delta"
        tool_delta.delta = MagicMock()
        tool_delta.delta.partial_json = '{"query": "test"}'
        delattr(tool_delta.delta, "text")

        # Tool block stop
        tool_stop = MagicMock()
        tool_stop.type = "content_block_stop"

        # Message stop
        msg_stop = MagicMock()
        msg_stop.type = "message_stop"

        async def mock_event_stream():
            yield tool_start
            yield tool_delta
            yield tool_stop
            yield msg_stop

        mock_stream = AsyncMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Search for test", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.is_complete
        assert len(final.tool_calls) == 1
        assert final.tool_calls[0].name == "search"
        assert final.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_usage(self):
        """Should capture token usage from events."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        # Message start with input tokens
        msg_start = MagicMock()
        msg_start.type = "message_start"
        msg_start.message = MagicMock()
        msg_start.message.usage = MagicMock()
        msg_start.message.usage.input_tokens = 100

        # Message delta with output tokens
        msg_delta = MagicMock()
        msg_delta.type = "message_delta"
        msg_delta.usage = MagicMock()
        msg_delta.usage.output_tokens = 50

        msg_stop = MagicMock()
        msg_stop.type = "message_stop"

        async def mock_event_stream():
            yield msg_start
            yield msg_delta
            yield msg_stop

        mock_stream = AsyncMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.usage is not None
        assert final.usage.input_tokens == 100
        assert final.usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_exception(self):
        """Should yield error StreamChunk on exception."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception("API error")
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API error" in chunks[0].text
        assert chunks[0].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_passes_tools_to_api(self):
        """Should pass converted tools to API."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        msg_stop = MagicMock()
        msg_stop.type = "message_stop"

        async def mock_event_stream():
            yield msg_stop

        mock_stream = AsyncMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        tools = [
            {
                "type": "function",
                "function": {"name": "test", "description": "Test tool"},
            }
        ]

        async for _ in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=tools
        ):
            pass

        call_kwargs = mock_client.messages.stream.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["name"] == "test"

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_invalid_json(self):
        """Should handle invalid JSON in tool arguments."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        tool_start = MagicMock()
        tool_start.type = "content_block_start"
        tool_start.content_block = MagicMock()
        tool_start.content_block.type = "tool_use"
        tool_start.content_block.id = "call_1"
        tool_start.content_block.name = "test"

        tool_delta = MagicMock()
        tool_delta.type = "content_block_delta"
        tool_delta.delta = MagicMock()
        tool_delta.delta.partial_json = "invalid json"
        delattr(tool_delta.delta, "text")

        tool_stop = MagicMock()
        tool_stop.type = "content_block_stop"

        msg_stop = MagicMock()
        msg_stop.type = "message_stop"

        async def mock_event_stream():
            yield tool_start
            yield tool_delta
            yield tool_stop
            yield msg_stop

        mock_stream = AsyncMock()
        mock_stream.__aiter__ = lambda self: mock_event_stream()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools(
            prompt="Hi", messages=[], tools=[]
        ):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {}


class TestAnthropicProviderListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_returns_known_models(self):
        """Should return list of known Claude models."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        models = await provider.list_models()

        assert len(models) > 0
        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-opus-20240229" in models

    @pytest.mark.asyncio
    async def test_list_models_includes_haiku(self):
        """Should include Haiku models."""
        provider = AnthropicProvider(api_key="sk-ant-test")
        models = await provider.list_models()

        haiku_models = [m for m in models if "haiku" in m]
        assert len(haiku_models) >= 1


class TestAnthropicProviderValidateConnection:
    """Tests for validate_connection method."""

    @pytest.mark.asyncio
    async def test_validate_connection_returns_true_on_success(self):
        """Should return True when API is reachable."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_error(self):
        """Should return False on exception."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("Auth failed"))
        provider._client = mock_client

        result = await provider.validate_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_uses_minimal_request(self):
        """Should make minimal API request for validation."""
        provider = AnthropicProvider(api_key="sk-ant-test")

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MagicMock())
        provider._client = mock_client

        await provider.validate_connection()

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 10
        assert call_kwargs["messages"][0]["content"] == "Hi"
