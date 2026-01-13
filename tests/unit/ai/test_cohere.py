"""Unit tests for CohereProvider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.cohere import CohereProvider
from ai.base import StreamChunk, ToolCallData, TokenUsage


class TestCohereProviderInit:
    """Test provider initialization."""

    def test_init_with_defaults(self):
        provider = CohereProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model == "command-r-plus"
        assert provider._client is None

    def test_init_with_custom_model(self):
        provider = CohereProvider(api_key="test-key", model="command-r")
        assert provider.model == "command-r"

    def test_client_lazy_loaded(self):
        provider = CohereProvider(api_key="test-key")
        assert provider._client is None


class TestSupportsTools:
    """Test supports_tools property."""

    def test_supports_tools_returns_true(self):
        provider = CohereProvider(api_key="test-key")
        assert provider.supports_tools() is True


class TestGetClient:
    """Test client initialization."""

    def test_get_client_raises_import_error_when_missing(self):
        provider = CohereProvider(api_key="test-key")

        with patch.dict("sys.modules", {"cohere": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ImportError, match="cohere package required"):
                    provider._get_client()

    def test_get_client_creates_async_client(self):
        provider = CohereProvider(api_key="test-key")

        mock_cohere = MagicMock()
        mock_client = MagicMock()
        mock_cohere.AsyncClientV2.return_value = mock_client

        with patch.dict("sys.modules", {"cohere": mock_cohere}):
            client = provider._get_client()
            mock_cohere.AsyncClientV2.assert_called_once_with(api_key="test-key")
            assert client == mock_client

    def test_get_client_reuses_existing_client(self):
        provider = CohereProvider(api_key="test-key")
        mock_client = MagicMock()
        provider._client = mock_client

        result = provider._get_client()
        assert result == mock_client


class TestBuildMessages:
    """Test message building."""

    def test_build_messages_with_defaults(self):
        provider = CohereProvider(api_key="test-key")
        messages = provider._build_messages("Hello", [], None)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "helpful AI assistant" in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "Hello"}

    def test_build_messages_with_custom_system_prompt(self):
        provider = CohereProvider(api_key="test-key")
        messages = provider._build_messages("Hello", [], "Custom prompt")

        assert messages[0]["content"] == "Custom prompt"

    def test_build_messages_with_history(self):
        provider = CohereProvider(api_key="test-key")
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response"},
        ]
        messages = provider._build_messages("Second", history, None)

        assert len(messages) == 4
        assert messages[1] == {"role": "user", "content": "First"}
        assert messages[2] == {"role": "assistant", "content": "Response"}
        assert messages[3] == {"role": "user", "content": "Second"}

    def test_build_messages_skips_system_role_in_history(self):
        provider = CohereProvider(api_key="test-key")
        history = [
            {"role": "system", "content": "Should be skipped"},
            {"role": "user", "content": "User msg"},
        ]
        messages = provider._build_messages("Hello", history, None)

        assert len(messages) == 3
        assert messages[1] == {"role": "user", "content": "User msg"}

    def test_build_messages_handles_tool_calls(self):
        provider = CohereProvider(api_key="test-key")
        history = [
            {
                "role": "assistant",
                "content": "Using tool",
                "tool_calls": [{"id": "1", "function": {"name": "test"}}],
            }
        ]
        messages = provider._build_messages("Next", history, None)

        assert messages[1]["tool_calls"] == [{"id": "1", "function": {"name": "test"}}]

    def test_build_messages_handles_tool_results(self):
        provider = CohereProvider(api_key="test-key")
        history = [{"role": "tool", "content": "Result", "tool_call_id": "call_123"}]
        messages = provider._build_messages("Next", history, None)

        assert messages[1]["role"] == "tool"
        assert messages[1]["tool_call_id"] == "call_123"


class TestConvertTools:
    """Test tool conversion."""

    def test_convert_tools_passes_through(self):
        provider = CohereProvider(api_key="test-key")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test",
                    "parameters": {"type": "object"},
                },
            }
        ]
        result = provider._convert_tools(tools)
        assert result == tools


class TestGenerate:
    """Test basic generate method."""

    @pytest.mark.asyncio
    async def test_generate_streams_text(self):
        provider = CohereProvider(api_key="test-key")

        mock_event = MagicMock()
        mock_event.type = "content-delta"
        mock_event.delta.message.content.text = "Hello"

        async def mock_stream():
            yield mock_event

        mock_client = MagicMock()
        mock_client.chat_stream.return_value = mock_stream()
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate("Test", []):
            chunks.append(chunk)

        assert chunks == ["Hello"]

    @pytest.mark.asyncio
    async def test_generate_handles_error(self):
        provider = CohereProvider(api_key="test-key")

        mock_client = MagicMock()
        mock_client.chat_stream.side_effect = Exception("API Error")
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate("Test", []):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error:" in chunks[0]


class TestGenerateWithTools:
    """Test generate_with_tools method."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_streams_text(self):
        provider = CohereProvider(api_key="test-key")

        mock_event = MagicMock()
        mock_event.type = "content-delta"
        mock_event.delta.message.content.text = "Response"

        mock_end = MagicMock()
        mock_end.type = "message-end"
        mock_end.delta.usage = None

        async def mock_stream():
            yield mock_event
            yield mock_end

        mock_client = MagicMock()
        mock_client.chat_stream.return_value = mock_stream()
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools("Test", [], []):
            chunks.append(chunk)

        assert any(c.text == "Response" for c in chunks)
        assert chunks[-1].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_calls(self):
        provider = CohereProvider(api_key="test-key")

        # Tool call start event
        start_event = MagicMock()
        start_event.type = "tool-call-start"
        start_event.delta.message.tool_calls = MagicMock()
        start_event.delta.message.tool_calls.id = "call_1"
        start_event.delta.message.tool_calls.function = {"name": "test_func"}

        # Tool call delta event
        delta_event = MagicMock()
        delta_event.type = "tool-call-delta"
        delta_event.delta.message.tool_calls = MagicMock()
        delta_event.delta.message.tool_calls.function = MagicMock()
        delta_event.delta.message.tool_calls.function.arguments = '{"arg": "value"}'

        # Tool call end event
        end_event = MagicMock()
        end_event.type = "tool-call-end"

        # Message end event
        msg_end = MagicMock()
        msg_end.type = "message-end"
        msg_end.delta.usage = None

        async def mock_stream():
            yield start_event
            yield delta_event
            yield end_event
            yield msg_end

        mock_client = MagicMock()
        mock_client.chat_stream.return_value = mock_stream()
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools("Test", [], []):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.is_complete
        assert len(final.tool_calls) == 1
        assert final.tool_calls[0].name == "test_func"
        assert final.tool_calls[0].arguments == {"arg": "value"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_usage(self):
        provider = CohereProvider(api_key="test-key")

        mock_end = MagicMock()
        mock_end.type = "message-end"
        mock_end.delta.usage = MagicMock()
        mock_end.delta.usage.input_tokens = 100
        mock_end.delta.usage.output_tokens = 50

        async def mock_stream():
            yield mock_end

        mock_client = MagicMock()
        mock_client.chat_stream.return_value = mock_stream()
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools("Test", [], []):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.usage is not None
        assert final.usage.input_tokens == 100
        assert final.usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_error(self):
        provider = CohereProvider(api_key="test-key")

        mock_client = MagicMock()
        mock_client.chat_stream.side_effect = Exception("API Error")
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools("Test", [], []):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error:" in chunks[0].text
        assert chunks[0].is_complete

    @pytest.mark.asyncio
    async def test_generate_with_tools_invalid_json_args(self):
        provider = CohereProvider(api_key="test-key")

        start_event = MagicMock()
        start_event.type = "tool-call-start"
        start_event.delta.message.tool_calls = MagicMock()
        start_event.delta.message.tool_calls.id = "call_1"
        start_event.delta.message.tool_calls.function = {"name": "func"}

        delta_event = MagicMock()
        delta_event.type = "tool-call-delta"
        delta_event.delta.message.tool_calls = MagicMock()
        delta_event.delta.message.tool_calls.function = MagicMock()
        delta_event.delta.message.tool_calls.function.arguments = "invalid json{"

        end_event = MagicMock()
        end_event.type = "tool-call-end"

        msg_end = MagicMock()
        msg_end.type = "message-end"
        msg_end.delta.usage = None

        async def mock_stream():
            yield start_event
            yield delta_event
            yield end_event
            yield msg_end

        mock_client = MagicMock()
        mock_client.chat_stream.return_value = mock_stream()
        provider._client = mock_client

        chunks = []
        async for chunk in provider.generate_with_tools("Test", [], []):
            chunks.append(chunk)

        final = chunks[-1]
        assert final.tool_calls[0].arguments == {}


class TestListModels:
    """Test list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_returns_from_api(self):
        provider = CohereProvider(api_key="test-key")

        mock_model = MagicMock()
        mock_model.name = "command-r-plus"

        mock_response = MagicMock()
        mock_response.models = [mock_model]

        mock_client = AsyncMock()
        mock_client.models.list.return_value = mock_response
        provider._client = mock_client

        models = await provider.list_models()
        assert "command-r-plus" in models

    @pytest.mark.asyncio
    async def test_list_models_returns_fallback_on_error(self):
        provider = CohereProvider(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.models.list.side_effect = Exception("API Error")
        provider._client = mock_client

        models = await provider.list_models()
        assert "command-r-plus" in models
        assert "command-r" in models


class TestValidateConnection:
    """Test validate_connection method."""

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        provider = CohereProvider(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.models.list.return_value = MagicMock()
        provider._client = mock_client

        result = await provider.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        provider = CohereProvider(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.models.list.side_effect = Exception("Connection failed")
        provider._client = mock_client

        result = await provider.validate_connection()
        assert result is False
