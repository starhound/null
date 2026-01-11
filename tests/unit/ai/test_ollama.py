"""Tests for ai/ollama.py - OllamaProvider implementation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ai.base import Message, StreamChunk, TokenUsage, ToolCallData
from ai.ollama import OllamaProvider


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    def test_init_sets_endpoint_and_model(self):
        """Provider should store endpoint and model."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        assert provider.endpoint == "http://localhost:11434"
        assert provider.model == "llama3.2"

    def test_init_creates_httpx_client(self):
        """Provider should create an httpx AsyncClient."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        assert isinstance(provider.client, httpx.AsyncClient)

    def test_init_sets_timeout_config(self):
        """Client should have short connect timeout and longer read timeout."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        # Timeout is set to 60s read, 3s connect
        assert provider.client.timeout.connect == 3.0
        assert provider.client.timeout.read == 60.0


class TestOllamaProviderSupportsTools:
    """Tests for supports_tools method."""

    def test_supports_tools_returns_true(self):
        """Ollama supports tool calling."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        assert provider.supports_tools() is True


class TestOllamaProviderBuildMessages:
    """Tests for _build_messages method."""

    def test_build_messages_with_system_prompt(self):
        """Should prepend system message when system_prompt provided."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        messages: list[Message] = []
        result = provider._build_messages(
            prompt="Hello", messages=messages, system_prompt="You are helpful."
        )

        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}

    def test_build_messages_without_system_prompt(self):
        """Should not add system message when system_prompt is None."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        messages: list[Message] = []
        result = provider._build_messages(
            prompt="Hello", messages=messages, system_prompt=None
        )

        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Hello"}

    def test_build_messages_preserves_history(self):
        """Should include all history messages."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        messages: list[Message] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = provider._build_messages(
            prompt="How are you?", messages=messages, system_prompt=None
        )

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hi"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hello!"
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "How are you?"

    def test_build_messages_includes_tool_calls(self):
        """Should preserve tool_calls in assistant messages."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        tool_calls = [{"id": "call_1", "function": {"name": "search"}}]
        messages: list[Message] = [
            {"role": "assistant", "content": "", "tool_calls": tool_calls},
        ]
        result = provider._build_messages(
            prompt="Continue", messages=messages, system_prompt=None
        )

        assert len(result) == 2
        assert result[0]["tool_calls"] == tool_calls

    def test_build_messages_handles_empty_content(self):
        """Should handle messages with empty content."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")
        messages: list[Message] = [
            {"role": "assistant", "content": ""},
        ]
        result = provider._build_messages(
            prompt="Hello", messages=messages, system_prompt=None
        )

        assert len(result) == 2
        # Empty content should not add "content" key
        assert "content" not in result[0] or result[0].get("content") == ""


class TestOllamaProviderGenerate:
    """Tests for generate method (streaming text generation)."""

    @pytest.mark.asyncio
    async def test_generate_yields_content(self):
        """Should yield text content from streaming response."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        # Mock streaming response
        async def mock_aiter_lines():
            yield json.dumps({"message": {"content": "Hello"}, "done": False})
            yield json.dumps({"message": {"content": " world"}, "done": False})
            yield json.dumps({"message": {"content": "!"}, "done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate(
                prompt="Hi", messages=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_generate_skips_empty_lines(self):
        """Should skip empty lines in response."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield ""
            yield json.dumps({"message": {"content": "Hi"}, "done": False})
            yield ""
            yield json.dumps({"done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate(
                prompt="Hi", messages=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert chunks == ["Hi"]

    @pytest.mark.asyncio
    async def test_generate_handles_json_decode_error(self):
        """Should skip lines that aren't valid JSON."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield "not valid json"
            yield json.dumps({"message": {"content": "Valid"}, "done": False})
            yield "also invalid"
            yield json.dumps({"done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate(
                prompt="Hi", messages=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert chunks == ["Valid"]

    @pytest.mark.asyncio
    async def test_generate_handles_http_error(self):
        """Should yield error message on HTTP error."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        with patch.object(
            provider.client,
            "stream",
            side_effect=httpx.HTTPError("Connection refused"),
        ):
            chunks = []
            async for chunk in provider.generate(
                prompt="Hi", messages=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: Could not connect to Ollama" in chunks[0]

    @pytest.mark.asyncio
    async def test_generate_stops_on_done(self):
        """Should stop yielding when done is True."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield json.dumps({"message": {"content": "First"}, "done": False})
            yield json.dumps({"message": {"content": "Last"}, "done": True})
            yield json.dumps({"message": {"content": "Should not see"}, "done": False})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate(
                prompt="Hi", messages=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert chunks == ["First", "Last"]


class TestOllamaProviderGenerateWithTools:
    """Tests for generate_with_tools method."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_stream_chunks(self):
        """Should yield StreamChunk objects."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield json.dumps({"message": {"content": "Hello"}, "done": False})
            yield json.dumps({"message": {"content": " world"}, "done": False})
            yield json.dumps({"done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert len(chunks) == 3
        assert all(isinstance(c, StreamChunk) for c in chunks)
        assert chunks[0].text == "Hello"
        assert chunks[1].text == " world"
        assert chunks[2].is_complete is True

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_calls(self):
        """Should parse and collect tool calls from response."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield json.dumps(
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "search",
                                    "arguments": {"query": "test"},
                                },
                            }
                        ],
                    },
                    "done": False,
                }
            )
            yield json.dumps({"done": True, "prompt_eval_count": 100, "eval_count": 50})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Search for test",
                messages=[],
                tools=[{"type": "function", "function": {"name": "search"}}],
                system_prompt=None,
            ):
                chunks.append(chunk)

        # Last chunk should have tool calls
        final_chunk = chunks[-1]
        assert final_chunk.is_complete is True
        assert len(final_chunk.tool_calls) == 1
        assert final_chunk.tool_calls[0].name == "search"
        assert final_chunk.tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_includes_token_usage(self):
        """Should include token usage when done."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield json.dumps({"message": {"content": "Response"}, "done": False})
            yield json.dumps({"done": True, "prompt_eval_count": 150, "eval_count": 75})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[], system_prompt=None
            ):
                chunks.append(chunk)

        final_chunk = chunks[-1]
        assert final_chunk.usage is not None
        assert final_chunk.usage.input_tokens == 150
        assert final_chunk.usage.output_tokens == 75
        assert final_chunk.usage.total_tokens == 225

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_tool_call_without_id(self):
        """Should generate ID for tool calls without explicit ID."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield json.dumps(
                {
                    "message": {
                        "tool_calls": [
                            {"function": {"name": "test_tool", "arguments": {}}}
                        ]
                    },
                    "done": False,
                }
            )
            yield json.dumps({"done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[], system_prompt=None
            ):
                chunks.append(chunk)

        final_chunk = chunks[-1]
        assert len(final_chunk.tool_calls) == 1
        assert final_chunk.tool_calls[0].id == "call_0"

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_http_error(self):
        """Should yield error StreamChunk on HTTP error."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        with patch.object(
            provider.client,
            "stream",
            side_effect=httpx.HTTPError("Connection refused"),
        ):
            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=[], system_prompt=None
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: Could not connect to Ollama" in chunks[0].text
        assert chunks[0].is_complete is True

    @pytest.mark.asyncio
    async def test_generate_with_tools_adds_tools_to_payload(self):
        """Should include tools in the API payload."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        async def mock_aiter_lines():
            yield json.dumps({"done": True})

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        tools = [
            {
                "type": "function",
                "function": {"name": "search", "description": "Search the web"},
            }
        ]

        with patch.object(
            provider.client, "stream", return_value=mock_response
        ) as mock_stream:
            async for _ in provider.generate_with_tools(
                prompt="Hi", messages=[], tools=tools, system_prompt=None
            ):
                pass

            # Verify tools were passed in the payload
            call_args = mock_stream.call_args
            assert call_args[1]["json"]["tools"] == tools


class TestOllamaProviderEmbedText:
    """Tests for embed_text method."""

    @pytest.mark.asyncio
    async def test_embed_text_returns_embedding(self):
        """Should return embedding vector on success."""
        provider = OllamaProvider(
            endpoint="http://localhost:11434", model="nomic-embed-text"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3, 0.4]}

        with patch.object(
            provider.client, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.embed_text("Hello world")

        assert result == [0.1, 0.2, 0.3, 0.4]

    @pytest.mark.asyncio
    async def test_embed_text_returns_none_on_error_status(self):
        """Should return None on non-200 status."""
        provider = OllamaProvider(
            endpoint="http://localhost:11434", model="nomic-embed-text"
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(
            provider.client, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.embed_text("Hello world")

        assert result is None

    @pytest.mark.asyncio
    async def test_embed_text_returns_none_on_exception(self):
        """Should return None on any exception."""
        provider = OllamaProvider(
            endpoint="http://localhost:11434", model="nomic-embed-text"
        )

        with patch.object(
            provider.client,
            "post",
            new_callable=AsyncMock,
            side_effect=Exception("Network error"),
        ):
            result = await provider.embed_text("Hello world")

        assert result is None

    @pytest.mark.asyncio
    async def test_embed_text_returns_none_on_missing_embedding(self):
        """Should return None if embedding not in response."""
        provider = OllamaProvider(
            endpoint="http://localhost:11434", model="nomic-embed-text"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.object(
            provider.client, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.embed_text("Hello world")

        assert result is None


class TestOllamaProviderListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_returns_model_names(self):
        """Should return list of model names."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "mistral:7b"},
                {"name": "codellama:13b"},
            ]
        }

        with patch.object(
            provider.client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.list_models()

        assert result == ["llama3.2:latest", "mistral:7b", "codellama:13b"]

    @pytest.mark.asyncio
    async def test_list_models_returns_empty_on_error(self):
        """Should return empty list on HTTP error."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        with patch.object(
            provider.client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPError("Connection refused"),
        ):
            result = await provider.list_models()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_models_returns_empty_on_non_200(self):
        """Should return empty list on non-200 status."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(
            provider.client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.list_models()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_models_handles_empty_models_list(self):
        """Should handle response with empty models array."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch.object(
            provider.client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.list_models()

        assert result == []


class TestOllamaProviderValidateConnection:
    """Tests for validate_connection method."""

    @pytest.mark.asyncio
    async def test_validate_connection_returns_true_on_success(self):
        """Should return True when Ollama is reachable."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(
            provider.client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_http_error(self):
        """Should return False when connection fails."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        with patch.object(
            provider.client,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPError("Connection refused"),
        ):
            result = await provider.validate_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_non_200(self):
        """Should return False on non-200 status code."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(
            provider.client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await provider.validate_connection()

        assert result is False


class TestOllamaProviderClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        """Should close the httpx client."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        with patch.object(
            provider.client, "aclose", new_callable=AsyncMock
        ) as mock_aclose:
            await provider.close()

        mock_aclose.assert_called_once()


class TestOllamaProviderIntegration:
    """Integration tests for complete flows."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation with history."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        messages: list[Message] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        async def mock_aiter_lines():
            yield json.dumps(
                {"message": {"content": "I'm doing well, thanks!"}, "done": True}
            )

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            provider.client, "stream", return_value=mock_response
        ) as mock_stream:
            chunks = []
            async for chunk in provider.generate(
                prompt="How are you?",
                messages=messages,
                system_prompt="Be friendly",
            ):
                chunks.append(chunk)

            # Verify the payload structure
            call_args = mock_stream.call_args
            payload = call_args[1]["json"]

            assert payload["model"] == "llama3.2"
            assert payload["stream"] is True
            assert len(payload["messages"]) == 4  # system + 2 history + current
            assert payload["messages"][0]["role"] == "system"
            assert payload["messages"][0]["content"] == "Be friendly"

    @pytest.mark.asyncio
    async def test_tool_calling_flow(self):
        """Test complete tool calling flow."""
        provider = OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }
        ]

        async def mock_aiter_lines():
            yield json.dumps(
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_weather_1",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": {"location": "Seattle"},
                                },
                            }
                        ],
                    },
                    "done": True,
                    "prompt_eval_count": 200,
                    "eval_count": 100,
                }
            )

        mock_response = AsyncMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        with patch.object(provider.client, "stream", return_value=mock_response):
            chunks = []
            async for chunk in provider.generate_with_tools(
                prompt="What's the weather in Seattle?",
                messages=[],
                tools=tools,
                system_prompt=None,
            ):
                chunks.append(chunk)

        # Should have gotten the tool call
        final_chunk = chunks[-1]
        assert final_chunk.is_complete
        assert len(final_chunk.tool_calls) == 1
        assert final_chunk.tool_calls[0].name == "get_weather"
        assert final_chunk.tool_calls[0].arguments["location"] == "Seattle"
        assert final_chunk.usage.total_tokens == 300
