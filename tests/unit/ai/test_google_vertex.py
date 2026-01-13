"""Tests for ai/google_vertex.py - GoogleVertexProvider implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import Message, StreamChunk, TokenUsage, ToolCallData
from ai.google_vertex import GoogleVertexProvider


class TestGoogleVertexProviderInit:
    """Tests for GoogleVertexProvider initialization."""

    def test_init_sets_project_id_and_location(self):
        """Provider should store project_id and location."""
        provider = GoogleVertexProvider(
            project_id="my-project", location="us-east1", model="gemini-2.0-flash"
        )
        assert provider.project_id == "my-project"
        assert provider.location == "us-east1"
        assert provider.model == "gemini-2.0-flash"

    def test_init_strips_whitespace(self):
        """Provider should strip whitespace from parameters."""
        provider = GoogleVertexProvider(
            project_id="  my-project  ",
            location="  us-central1  ",
            model="  gemini-2.0-flash  ",
        )
        assert provider.project_id == "my-project"
        assert provider.location == "us-central1"
        assert provider.model == "gemini-2.0-flash"

    def test_init_default_values(self):
        """Provider should use defaults for location and model."""
        provider = GoogleVertexProvider(project_id="my-project")
        assert provider.project_id == "my-project"
        assert provider.location == "us-central1"
        assert provider.model == "gemini-2.0-flash"

    def test_init_handles_empty_strings(self):
        """Provider should handle empty strings gracefully."""
        provider = GoogleVertexProvider(project_id="", location="", model="")
        assert provider.project_id == ""
        assert provider.location == "us-central1"
        assert provider.model == "gemini-2.0-flash"

    def test_init_client_is_none(self):
        """Client should not be initialized until first use."""
        provider = GoogleVertexProvider(project_id="my-project")
        assert provider._client is None


class TestGoogleVertexProviderSupportsTools:
    """Tests for supports_tools method."""

    def test_supports_tools_returns_true(self):
        """GoogleVertexProvider supports tool calling."""
        provider = GoogleVertexProvider(project_id="my-project")
        assert provider.supports_tools() is True


class TestGoogleVertexProviderGetClient:
    """Tests for _get_client method."""

    def test_get_client_creates_client_on_first_call(self):
        """Should create Client on first call."""
        provider = GoogleVertexProvider(project_id="my-project", location="us-central1")

        mock_client_cls = MagicMock()
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_genai = MagicMock()
        mock_genai.Client = mock_client_cls

        with patch.dict("sys.modules", {"google.genai": mock_genai}):
            client = provider._get_client()

            mock_client_cls.assert_called_once_with(
                vertexai=True,
                project="my-project",
                location="us-central1",
                http_options={"timeout": 60},
            )
            assert client is mock_client

    def test_get_client_returns_cached_client(self):
        """Should return cached client on subsequent calls."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_client_cls = MagicMock()
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_genai = MagicMock()
        mock_genai.Client = mock_client_cls

        with patch.dict("sys.modules", {"google.genai": mock_genai}):
            client1 = provider._get_client()
            client2 = provider._get_client()

            assert mock_client_cls.call_count == 1
            assert client1 is client2

    def test_get_client_raises_import_error(self):
        """Should raise ImportError with helpful message when google-genai not installed."""
        provider = GoogleVertexProvider(project_id="my-project")

        with patch.dict("sys.modules", {"google.genai": None, "google": MagicMock()}):
            with pytest.raises(ImportError, match="google-genai package required"):
                provider._get_client()


class TestGoogleVertexProviderBuildContents:
    """Tests for _build_contents method."""

    def test_build_contents_with_empty_history(self):
        """Should return prompt as user content."""
        provider = GoogleVertexProvider(project_id="my-project")
        contents, sys_prompt = provider._build_contents(
            prompt="Hello", messages=[], system_prompt="You are helpful."
        )

        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"] == [{"text": "Hello"}]
        assert sys_prompt == "You are helpful."

    def test_build_contents_with_message_history(self):
        """Should convert message history to Gemini format."""
        provider = GoogleVertexProvider(project_id="my-project")
        messages: list[Message] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        contents, sys_prompt = provider._build_contents(
            prompt="How are you?", messages=messages, system_prompt=None
        )

        assert len(contents) == 3
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"] == [{"text": "Hi"}]
        assert contents[1]["role"] == "model"  # assistant -> model
        assert contents[1]["parts"] == [{"text": "Hello!"}]
        assert contents[2]["role"] == "user"
        assert contents[2]["parts"] == [{"text": "How are you?"}]

    def test_build_contents_handles_tool_role(self):
        """Should prefix tool role content with 'Tool Result:'."""
        provider = GoogleVertexProvider(project_id="my-project")
        messages: list[Message] = [
            {"role": "tool", "content": "42"},
        ]
        contents, _ = provider._build_contents(
            prompt="Continue", messages=messages, system_prompt=None
        )

        assert len(contents) == 2
        assert contents[0]["parts"] == [{"text": "Tool Result: 42"}]


class TestGoogleVertexProviderGenerate:
    """Tests for generate method (streaming text generation)."""

    @pytest.mark.asyncio
    async def test_generate_yields_content(self):
        """Should yield text content from streaming response."""
        provider = GoogleVertexProvider(project_id="my-project")

        # Create mock chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello"
        mock_chunk2 = MagicMock()
        mock_chunk2.text = " world"
        mock_chunk3 = MagicMock()
        mock_chunk3.text = "!"

        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.dict("sys.modules", {"google.genai": mock_genai}):
                chunks = []
                async for chunk in provider.generate(
                    prompt="Hi", messages=[], system_prompt=None
                ):
                    chunks.append(chunk)

        assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_generate_skips_empty_text(self):
        """Should skip chunks with empty text."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello"
        mock_chunk2 = MagicMock()
        mock_chunk2.text = ""
        mock_chunk3 = MagicMock()
        mock_chunk3.text = None

        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.dict("sys.modules", {"google.genai": mock_genai}):
                chunks = []
                async for chunk in provider.generate(
                    prompt="Hi", messages=[], system_prompt=None
                ):
                    chunks.append(chunk)

        assert chunks == ["Hello"]

    @pytest.mark.asyncio
    async def test_generate_handles_exception(self):
        """Should yield error message on exception."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            side_effect=Exception("API Error")
        )

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.dict("sys.modules", {"google.genai": mock_genai}):
                chunks = []
                async for chunk in provider.generate(
                    prompt="Hi", messages=[], system_prompt=None
                ):
                    chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: API Error" in chunks[0]


class TestGoogleVertexProviderGenerateWithTools:
    """Tests for generate_with_tools method."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_text_chunks(self):
        """Should yield StreamChunks with text content."""
        provider = GoogleVertexProvider(project_id="my-project")

        # Create mock part with text
        mock_part = MagicMock()
        mock_part.text = "Response text"
        mock_part.thought = None
        mock_part.function_call = None

        # Create mock candidate
        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        # Create mock chunk
        mock_chunk = MagicMock()
        mock_chunk.candidates = [mock_candidate]
        mock_chunk.usage_metadata = None

        async def mock_stream():
            yield mock_chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.object(provider, "_convert_tools", return_value=[]):
                with patch.dict("sys.modules", {"google.genai": mock_genai}):
                    chunks = []
                    async for chunk in provider.generate_with_tools(
                        prompt="Hi",
                        messages=[],
                        tools=[],
                        system_prompt=None,
                    ):
                        chunks.append(chunk)

        assert len(chunks) == 1
        assert isinstance(chunks[0], StreamChunk)
        assert chunks[0].text == "Response text"

    @pytest.mark.asyncio
    async def test_generate_with_tools_yields_tool_calls(self):
        """Should yield StreamChunks with tool calls."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_fc = MagicMock()
        mock_fc.name = "search"
        mock_fc.args = {"query": "test"}

        mock_part = MagicMock()
        mock_part.text = ""
        mock_part.thought = None
        mock_part.function_call = mock_fc

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

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.object(provider, "_convert_tools", return_value=[]):
                with patch.dict("sys.modules", {"google.genai": mock_genai}):
                    chunks = []
                    async for chunk in provider.generate_with_tools(
                        prompt="Hi",
                        messages=[],
                        tools=[{"type": "function", "function": {"name": "search"}}],
                        system_prompt=None,
                    ):
                        chunks.append(chunk)

        assert len(chunks) == 1
        assert len(chunks[0].tool_calls) == 1
        assert chunks[0].tool_calls[0].name == "search"
        assert chunks[0].tool_calls[0].arguments == {"query": "test"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_includes_usage(self):
        """Should include token usage when available."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_part = MagicMock()
        mock_part.text = "Hi"
        mock_part.thought = None
        mock_part.function_call = None

        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 20

        mock_chunk = MagicMock()
        mock_chunk.candidates = [mock_candidate]
        mock_chunk.usage_metadata = mock_usage

        async def mock_stream():
            yield mock_chunk

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            return_value=mock_stream()
        )

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.object(provider, "_convert_tools", return_value=[]):
                with patch.dict("sys.modules", {"google.genai": mock_genai}):
                    chunks = []
                    async for chunk in provider.generate_with_tools(
                        prompt="Hi",
                        messages=[],
                        tools=[],
                        system_prompt=None,
                    ):
                        chunks.append(chunk)

        assert chunks[0].usage is not None
        assert chunks[0].usage.input_tokens == 10
        assert chunks[0].usage.output_tokens == 20

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_thinking(self):
        """Should wrap thinking content in <think> tags."""
        provider = GoogleVertexProvider(
            project_id="my-project", model="gemini-2.5-flash"
        )

        mock_part = MagicMock()
        mock_part.text = "Let me think..."
        mock_part.thought = True
        mock_part.function_call = None

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

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.object(provider, "_convert_tools", return_value=[]):
                with patch.dict("sys.modules", {"google.genai": mock_genai}):
                    chunks = []
                    async for chunk in provider.generate_with_tools(
                        prompt="Hi",
                        messages=[],
                        tools=[],
                        system_prompt=None,
                    ):
                        chunks.append(chunk)

        assert "<think>Let me think...</think>" in chunks[0].text

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_exception(self):
        """Should yield error StreamChunk on exception."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(
            side_effect=Exception("Tool Error")
        )

        mock_types = MagicMock()
        mock_genai = MagicMock()
        mock_genai.types = mock_types

        with patch.object(provider, "_get_client", return_value=mock_client):
            with patch.object(provider, "_convert_tools", return_value=[]):
                with patch.dict("sys.modules", {"google.genai": mock_genai}):
                    chunks = []
                    async for chunk in provider.generate_with_tools(
                        prompt="Hi",
                        messages=[],
                        tools=[],
                        system_prompt=None,
                    ):
                        chunks.append(chunk)

        assert len(chunks) == 1
        assert "Error: Tool Error" in chunks[0].text


class TestGoogleVertexProviderConvertTools:
    """Tests for _convert_tools method."""

    def test_convert_tools_basic(self):
        """Should convert OpenAI tool format to Google format."""
        provider = GoogleVertexProvider(project_id="my-project")
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
        assert result[0]["parameters"]["type"] == "OBJECT"
        assert result[0]["parameters"]["properties"]["query"]["type"] == "STRING"

    def test_convert_tools_skips_non_function(self):
        """Should skip tools that are not of type 'function'."""
        provider = GoogleVertexProvider(project_id="my-project")
        tools = [{"type": "other", "function": {"name": "test"}}]

        result = provider._convert_tools(tools)

        assert len(result) == 0

    def test_convert_tools_empty_list(self):
        """Should return empty list for empty input."""
        provider = GoogleVertexProvider(project_id="my-project")

        result = provider._convert_tools([])

        assert result == []


class TestGoogleVertexProviderConvertSchema:
    """Tests for _convert_schema method."""

    def test_convert_schema_uppercase_types(self):
        """Should convert type values to uppercase."""
        provider = GoogleVertexProvider(project_id="my-project")
        schema = {"type": "string"}

        result = provider._convert_schema(schema)

        assert result["type"] == "STRING"

    def test_convert_schema_nested_properties(self):
        """Should recursively convert nested properties."""
        provider = GoogleVertexProvider(project_id="my-project")
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }

        result = provider._convert_schema(schema)

        assert result["type"] == "OBJECT"
        assert result["properties"]["name"]["type"] == "STRING"
        assert result["properties"]["age"]["type"] == "INTEGER"

    def test_convert_schema_array_items(self):
        """Should recursively convert array items."""
        provider = GoogleVertexProvider(project_id="my-project")
        schema = {"type": "array", "items": {"type": "string"}}

        result = provider._convert_schema(schema)

        assert result["type"] == "ARRAY"
        assert result["items"]["type"] == "STRING"

    def test_convert_schema_skips_additional_properties(self):
        """Should skip additionalProperties to avoid issues."""
        provider = GoogleVertexProvider(project_id="my-project")
        schema = {"type": "object", "additionalProperties": True}

        result = provider._convert_schema(schema)

        assert result["type"] == "OBJECT"
        assert "additionalProperties" not in result


class TestGoogleVertexProviderListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_returns_gemini_models(self):
        """Should return sorted Gemini models."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-2.0-flash"
        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-1.5-pro"
        mock_model3 = MagicMock()
        mock_model3.name = "models/embedding-001"  # Should be filtered

        async def mock_list(*args, **kwargs):
            for model in [mock_model1, mock_model2, mock_model3]:
                yield model

        mock_client = MagicMock()
        mock_client.aio.models.list = AsyncMock(return_value=mock_list())

        with patch.object(provider, "_get_client", return_value=mock_client):
            models = await provider.list_models()

        assert "gemini-2.0-flash" in models
        assert "gemini-1.5-pro" in models
        assert "embedding-001" not in models

    @pytest.mark.asyncio
    async def test_list_models_returns_fallback_on_error(self):
        """Should return fallback models on exception."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_client = MagicMock()
        mock_client.aio.models.list = AsyncMock(side_effect=Exception("API Error"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            models = await provider.list_models()

        assert "gemini-2.0-flash" in models
        assert "gemini-2.5-pro" in models


class TestGoogleVertexProviderValidateConnection:
    """Tests for validate_connection method."""

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Should return True when API is reachable."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Should return False on exception."""
        provider = GoogleVertexProvider(project_id="my-project")

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("Connection Error")
        )

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.validate_connection()

        assert result is False
