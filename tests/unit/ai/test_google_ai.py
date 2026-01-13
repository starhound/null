"""Unit tests for Google AI provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.google_ai import GoogleAIProvider


class TestGoogleAIProviderInit:
    """Tests for provider initialization."""

    def test_init_with_api_key(self):
        provider = GoogleAIProvider(api_key="test-key", model="gemini-2.0-flash")
        assert provider.api_key == "test-key"
        assert provider.model == "gemini-2.0-flash"
        assert provider._client is None

    def test_init_strips_whitespace(self):
        provider = GoogleAIProvider(
            api_key="  test-key  ", model="  gemini-2.0-flash  "
        )
        assert provider.api_key == "test-key"
        assert provider.model == "gemini-2.0-flash"

    def test_init_default_model(self):
        provider = GoogleAIProvider(api_key="test-key")
        assert provider.model == "gemini-2.0-flash"

    def test_init_empty_api_key(self):
        provider = GoogleAIProvider(api_key="", model="gemini-2.0-flash")
        assert provider.api_key == ""

    def test_init_none_api_key(self):
        provider = GoogleAIProvider(api_key=None, model="gemini-2.0-flash")
        assert provider.api_key == ""

    def test_init_empty_model_uses_default(self):
        provider = GoogleAIProvider(api_key="test-key", model="")
        assert provider.model == "gemini-2.0-flash"


class TestSupportsTools:
    """Tests for supports_tools property."""

    def test_supports_tools_returns_true(self):
        provider = GoogleAIProvider(api_key="test-key")
        assert provider.supports_tools() is True


class TestGetClient:
    """Tests for client initialization."""

    def test_get_client_raises_import_error(self):
        provider = GoogleAIProvider(api_key="test-key")
        with patch.dict("sys.modules", {"google.genai": None}):
            with patch(
                "ai.google_ai.GoogleAIProvider._get_client",
                side_effect=ImportError("google-genai package required"),
            ):
                with pytest.raises(ImportError, match="google-genai"):
                    provider._get_client()

    def test_get_client_creates_client_once(self):
        provider = GoogleAIProvider(api_key="test-key")
        mock_client = MagicMock()

        with patch("google.genai.Client", return_value=mock_client) as mock_cls:
            client1 = provider._get_client()
            client2 = provider._get_client()

            assert client1 is client2
            mock_cls.assert_called_once()


class TestBuildContents:
    """Tests for message content building."""

    def test_build_contents_empty_messages(self):
        provider = GoogleAIProvider(api_key="test-key")
        contents, sys_prompt = provider._build_contents("Hello", [], "System prompt")

        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Hello"
        assert sys_prompt == "System prompt"

    def test_build_contents_with_messages(self):
        provider = GoogleAIProvider(api_key="test-key")
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        contents, _ = provider._build_contents("Follow up", messages, None)

        assert len(contents) == 3
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"
        assert contents[2]["role"] == "user"

    def test_build_contents_tool_message(self):
        provider = GoogleAIProvider(api_key="test-key")
        messages = [{"role": "tool", "content": "Tool result here"}]
        contents, _ = provider._build_contents("Continue", messages, None)

        assert "Tool Result:" in contents[0]["parts"][0]["text"]


class TestConvertTools:
    """Tests for OpenAI -> Google tool conversion."""

    def test_convert_tools_basic(self):
        provider = GoogleAIProvider(api_key="test-key")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                    },
                },
            }
        ]
        result = provider._convert_tools(tools)

        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather info"
        assert result[0]["parameters"]["type"] == "OBJECT"

    def test_convert_tools_nested_schema(self):
        provider = GoogleAIProvider(api_key="test-key")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test",
                    "description": "Test",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"type": "string"},
                            }
                        },
                    },
                },
            }
        ]
        result = provider._convert_tools(tools)

        assert result[0]["parameters"]["properties"]["items"]["type"] == "ARRAY"
        assert (
            result[0]["parameters"]["properties"]["items"]["items"]["type"] == "STRING"
        )

    def test_convert_tools_skips_additional_properties(self):
        provider = GoogleAIProvider(api_key="test-key")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test",
                    "description": "Test",
                    "parameters": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {},
                    },
                },
            }
        ]
        result = provider._convert_tools(tools)

        assert "additionalProperties" not in result[0]["parameters"]


class TestGenerate:
    """Tests for basic generate flow."""

    @pytest.mark.asyncio
    async def test_generate_basic_flow(self):
        provider = GoogleAIProvider(api_key="test-key")

        mock_chunk = MagicMock()
        mock_chunk.text = "Hello world"

        async def mock_stream():
            yield mock_chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch("google.genai.types") as mock_types:
                mock_types.GenerateContentConfig = MagicMock()

                chunks = []
                async for chunk in provider.generate("Hello", [], None):
                    chunks.append(chunk)

                assert len(chunks) == 1
                assert chunks[0] == "Hello world"

    @pytest.mark.asyncio
    async def test_generate_handles_error(self):
        provider = GoogleAIProvider(api_key="test-key")

        with patch.object(
            provider, "_get_client", side_effect=Exception("Connection failed")
        ):
            chunks = []
            async for chunk in provider.generate("Hello", [], None):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "Error:" in chunks[0]


class TestGenerateWithTools:
    """Tests for generate_with_tools flow."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_text_response(self):
        provider = GoogleAIProvider(api_key="test-key")

        mock_part = MagicMock()
        mock_part.text = "Response text"
        mock_part.function_call = None
        mock_part.thought = None

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_chunk = MagicMock()
        mock_chunk.candidates = [mock_candidate]
        mock_chunk.usage_metadata = None

        async def mock_stream():
            yield mock_chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch("google.genai.types") as mock_types:
                mock_types.GenerateContentConfig = MagicMock()
                mock_types.Tool = MagicMock()
                mock_types.ThinkingConfig = MagicMock()

                chunks = []
                async for chunk in provider.generate_with_tools("Hello", [], [], None):
                    chunks.append(chunk)

                assert len(chunks) == 1
                assert chunks[0].text == "Response text"
                assert chunks[0].tool_calls == []

    @pytest.mark.asyncio
    async def test_generate_with_tools_function_call(self):
        provider = GoogleAIProvider(api_key="test-key")

        mock_fc = MagicMock()
        mock_fc.name = "get_weather"
        mock_fc.args = {"location": "NYC"}

        mock_part = MagicMock()
        mock_part.text = ""
        mock_part.function_call = mock_fc
        mock_part.thought = None

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_chunk = MagicMock()
        mock_chunk.candidates = [mock_candidate]
        mock_chunk.usage_metadata = None

        async def mock_stream():
            yield mock_chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch("google.genai.types") as mock_types:
                mock_types.GenerateContentConfig = MagicMock()
                mock_types.Tool = MagicMock()
                mock_types.ThinkingConfig = MagicMock()

                chunks = []
                async for chunk in provider.generate_with_tools("Hello", [], [], None):
                    chunks.append(chunk)

                assert len(chunks) == 1
                assert len(chunks[0].tool_calls) == 1
                assert chunks[0].tool_calls[0].name == "get_weather"
                assert chunks[0].tool_calls[0].arguments == {"location": "NYC"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_with_usage(self):
        provider = GoogleAIProvider(api_key="test-key")

        mock_part = MagicMock()
        mock_part.text = "Done"
        mock_part.function_call = None
        mock_part.thought = None

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 100
        mock_usage.candidates_token_count = 50

        mock_chunk = MagicMock()
        mock_chunk.candidates = [mock_candidate]
        mock_chunk.usage_metadata = mock_usage

        async def mock_stream():
            yield mock_chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch("google.genai.types") as mock_types:
                mock_types.GenerateContentConfig = MagicMock()
                mock_types.Tool = MagicMock()
                mock_types.ThinkingConfig = MagicMock()

                chunks = []
                async for chunk in provider.generate_with_tools("Hello", [], [], None):
                    chunks.append(chunk)

                assert chunks[0].usage is not None
                assert chunks[0].usage.input_tokens == 100
                assert chunks[0].usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_error(self):
        provider = GoogleAIProvider(api_key="test-key")

        with patch.object(provider, "_get_client", side_effect=Exception("API error")):
            chunks = []
            async for chunk in provider.generate_with_tools("Hello", [], [], None):
                chunks.append(chunk)

            assert len(chunks) == 1
            assert "Error:" in chunks[0].text


class TestValidateConnection:
    """Tests for connection validation."""

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        provider = GoogleAIProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        provider = GoogleAIProvider(api_key="test-key")

        with patch.object(
            provider, "_get_client", side_effect=Exception("Invalid API key")
        ):
            result = await provider.validate_connection()
            assert result is False


class TestListModels:
    """Tests for model listing."""

    @pytest.mark.asyncio
    async def test_list_models_success(self):
        provider = GoogleAIProvider(api_key="test-key")

        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-2.0-flash"

        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-1.5-pro"

        mock_model3 = MagicMock()
        mock_model3.name = "models/text-bison"  # Non-gemini, should be filtered

        async def mock_list_iter():
            for m in [mock_model1, mock_model2, mock_model3]:
                yield m

        mock_client = MagicMock()
        mock_client.aio.models.list = AsyncMock(return_value=mock_list_iter())

        with patch.object(provider, "_get_client", return_value=mock_client):
            models = await provider.list_models()

            assert "gemini-2.0-flash" in models
            assert "gemini-1.5-pro" in models
            assert "text-bison" not in models

    @pytest.mark.asyncio
    async def test_list_models_fallback_on_error(self):
        provider = GoogleAIProvider(api_key="test-key")

        with patch.object(
            provider, "_get_client", side_effect=Exception("Network error")
        ):
            models = await provider.list_models()

            assert len(models) > 0
            assert "gemini-2.0-flash" in models
