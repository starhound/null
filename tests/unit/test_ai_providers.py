"""Unit tests for AI providers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import StreamChunk, TokenUsage, ToolCallData


class TestOllamaProvider:
    """Tests for OllamaProvider class."""

    @pytest.fixture
    def provider(self):
        """Create OllamaProvider instance."""
        from ai.ollama import OllamaProvider

        return OllamaProvider(endpoint="http://localhost:11434", model="llama3.2")

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.endpoint == "http://localhost:11434"
        assert provider.model == "llama3.2"
        assert provider.client is not None

    def test_supports_tools(self, provider):
        """Test that Ollama supports tools."""
        assert provider.supports_tools() is True

    def test_build_messages_with_system_prompt(self, provider):
        """Test message building with system prompt."""
        messages = [{"role": "user", "content": "Hello"}]
        result = provider._build_messages("Test", messages, "Be helpful")

        assert result[0] == {"role": "system", "content": "Be helpful"}
        assert result[1] == {"role": "user", "content": "Hello"}
        assert result[2] == {"role": "user", "content": "Test"}

    def test_build_messages_without_system_prompt(self, provider):
        """Test message building without system prompt."""
        messages = []
        result = provider._build_messages("Test", messages, None)

        assert len(result) == 1
        assert result[0] == {"role": "user", "content": "Test"}

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test successful model listing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.2"}, {"name": "codellama"}]
        }

        with patch.object(provider.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            models = await provider.list_models()

        assert models == ["llama3.2", "codellama"]

    @pytest.mark.asyncio
    async def test_list_models_failure(self, provider):
        """Test model listing on HTTP error."""
        import httpx

        with patch.object(provider.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            models = await provider.list_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, provider):
        """Test successful connection validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(provider.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, provider):
        """Test connection validation failure."""
        import httpx

        with patch.object(provider.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            result = await provider.validate_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, provider):
        """Test client closure."""
        with patch.object(
            provider.client, "aclose", new_callable=AsyncMock
        ) as mock_close:
            await provider.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_text_success(self, provider):
        """Test successful text embedding."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}

        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await provider.embed_text("Hello world")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_text_failure(self, provider):
        """Test embedding failure returns None."""
        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API error")
            result = await provider.embed_text("Hello world")

        assert result is None


class TestAnthropicProvider:
    """Tests for AnthropicProvider class."""

    @pytest.fixture
    def provider(self):
        """Create AnthropicProvider instance."""
        from ai.anthropic import AnthropicProvider

        return AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.api_key == "test-key"
        assert provider.model == "claude-3-5-sonnet-20241022"
        assert provider._client is None

    def test_supports_tools(self, provider):
        """Test that Anthropic supports tools."""
        assert provider.supports_tools() is True

    def test_build_messages(self, provider):
        """Test message building for Anthropic API."""
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = provider._build_messages("Test prompt", messages)

        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there"}
        assert result[2] == {"role": "user", "content": "Test prompt"}

    def test_convert_tools(self, provider):
        """Test OpenAI to Anthropic tool format conversion."""
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather data",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                    },
                },
            }
        ]
        result = provider._convert_tools(openai_tools)

        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
        assert result[0]["description"] == "Get weather data"
        assert result[0]["input_schema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        """Test that list_models returns known models."""
        models = await provider.list_models()

        assert "claude-3-5-sonnet-20241022" in models
        assert "claude-3-opus-20240229" in models
        assert len(models) >= 5

    @pytest.mark.asyncio
    async def test_get_client_import_error(self):
        """Test ImportError when anthropic package not installed."""
        from ai.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test", model="claude-3-5-sonnet-20241022")

        with patch.dict("sys.modules", {"anthropic": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ImportError, match="anthropic package required"):
                    provider._get_client()

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, provider):
        """Test successful connection validation."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MagicMock())

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, provider):
        """Test connection validation failure."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.validate_connection()

        assert result is False


class TestOpenAICompatibleProvider:
    """Tests for OpenAICompatibleProvider class."""

    @pytest.fixture
    def provider(self):
        """Create OpenAICompatibleProvider instance."""
        from ai.openai_compat import OpenAICompatibleProvider

        with patch("openai.AsyncOpenAI"):
            return OpenAICompatibleProvider(
                api_key="test-key", base_url="https://api.openai.com/v1", model="gpt-4o"
            )

    def test_init(self, provider):
        """Test provider initialization."""
        assert provider.model == "gpt-4o"
        assert provider.client is not None

    def test_supports_tools(self, provider):
        """Test that OpenAI supports tools."""
        assert provider.supports_tools() is True

    def test_build_messages_with_system_prompt(self, provider):
        """Test message building with system prompt."""
        messages = [{"role": "user", "content": "Hello"}]
        result = provider._build_messages("Test", messages, "Be helpful")

        assert result[0] == {"role": "system", "content": "Be helpful"}
        assert result[1] == {"role": "user", "content": "Hello"}
        assert result[2] == {"role": "user", "content": "Test"}

    def test_build_messages_default_system_prompt(self, provider):
        """Test message building with default system prompt."""
        result = provider._build_messages("Test", [], None)

        assert result[0]["role"] == "system"
        assert "helpful AI assistant" in result[0]["content"]

    def test_build_messages_with_tool_calls(self, provider):
        """Test message building with tool calls."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call_1", "function": {"name": "test"}}],
            },
            {"role": "tool", "content": "result", "tool_call_id": "call_1"},
        ]
        result = provider._build_messages("Next", messages, "System")

        assert result[1]["tool_calls"] == [
            {"id": "call_1", "function": {"name": "test"}}
        ]
        assert result[2]["tool_call_id"] == "call_1"

    @pytest.mark.asyncio
    async def test_list_models_success(self, provider):
        """Test successful model listing."""
        mock_model = MagicMock()
        mock_model.id = "gpt-4o"

        mock_response = MagicMock()
        mock_response.data = [mock_model]

        provider.client.models.list = AsyncMock(return_value=mock_response)
        models = await provider.list_models()

        assert "gpt-4o" in models

    @pytest.mark.asyncio
    async def test_list_models_failure(self, provider):
        """Test model listing on failure."""
        provider.client.models.list = AsyncMock(side_effect=Exception("API error"))
        models = await provider.list_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, provider):
        """Test successful connection validation."""
        provider.client.models.list = AsyncMock(return_value=MagicMock())
        result = await provider.validate_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, provider):
        """Test connection validation failure."""
        provider.client.models.list = AsyncMock(side_effect=Exception("Error"))
        result = await provider.validate_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_embed_text_success(self, provider):
        """Test successful text embedding."""
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        provider.client.embeddings.create = AsyncMock(return_value=mock_response)
        result = await provider.embed_text("Hello")

        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_text_failure(self, provider):
        """Test embedding failure returns None."""
        provider.client.embeddings.create = AsyncMock(side_effect=Exception("Error"))
        result = await provider.embed_text("Hello")

        assert result is None


class TestAIFactory:
    """Tests for AIFactory class."""

    def test_list_providers(self):
        """Test listing available providers."""
        from ai.factory import AIFactory

        providers = AIFactory.list_providers()

        assert "ollama" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert len(providers) > 10

    def test_get_provider_info(self):
        """Test getting provider metadata."""
        from ai.factory import AIFactory

        info = AIFactory.get_provider_info("openai")

        assert info["name"] == "OpenAI"
        assert info["requires_api_key"] is True
        assert info["requires_endpoint"] is False

    def test_get_provider_info_unknown(self):
        """Test getting info for unknown provider."""
        from ai.factory import AIFactory

        info = AIFactory.get_provider_info("unknown_provider")

        assert info == {}

    def test_get_provider_ollama(self):
        """Test creating Ollama provider."""
        from ai.factory import AIFactory
        from ai.ollama import OllamaProvider

        config = {
            "provider": "ollama",
            "endpoint": "http://localhost:11434",
            "model": "llama3.2",
        }
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, OllamaProvider)
        assert provider.model == "llama3.2"

    def test_get_provider_ollama_defaults(self):
        """Test Ollama provider with default values."""
        from ai.factory import AIFactory
        from ai.ollama import OllamaProvider

        config = {"provider": "ollama"}
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, OllamaProvider)
        assert provider.endpoint == "http://localhost:11434"
        assert provider.model == "llama3.2"

    def test_get_provider_anthropic(self):
        """Test creating Anthropic provider."""
        from ai.anthropic import AnthropicProvider
        from ai.factory import AIFactory

        config = {
            "provider": "anthropic",
            "api_key": "test-key",
            "model": "claude-3-opus-20240229",
        }
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-3-opus-20240229"

    def test_get_provider_openai(self):
        """Test creating OpenAI provider."""
        from ai.factory import AIFactory
        from ai.openai_compat import OpenAICompatibleProvider

        config = {"provider": "openai", "api_key": "test-key", "model": "gpt-4o"}
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.model == "gpt-4o"

    def test_get_provider_groq(self):
        """Test creating Groq provider (OpenAI-compatible)."""
        from ai.factory import AIFactory
        from ai.openai_compat import OpenAICompatibleProvider

        config = {"provider": "groq", "api_key": "test-key"}
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, OpenAICompatibleProvider)
        assert "groq.com" in provider.client.base_url.host

    def test_get_provider_lm_studio(self):
        """Test creating LM Studio provider."""
        from ai.factory import AIFactory
        from ai.openai_compat import OpenAICompatibleProvider

        config = {"provider": "lm_studio", "endpoint": "http://localhost:1234"}
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, OpenAICompatibleProvider)

    def test_get_provider_lm_studio_adds_v1(self):
        """Test that LM Studio adds /v1 suffix."""
        from ai.factory import AIFactory

        config = {"provider": "lm_studio", "endpoint": "http://localhost:1234"}
        provider = AIFactory.get_provider(config)

        assert "/v1" in str(provider.client.base_url)

    def test_get_provider_custom(self):
        """Test creating custom provider."""
        from ai.factory import AIFactory
        from ai.openai_compat import OpenAICompatibleProvider

        config = {
            "provider": "custom",
            "api_key": "key",
            "endpoint": "http://custom:8000/v1",
            "model": "my-model",
        }
        provider = AIFactory.get_provider(config)

        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.model == "my-model"

    def test_get_provider_unknown_raises(self):
        """Test that unknown provider raises ValueError."""
        from ai.factory import AIFactory

        config = {"provider": "nonexistent_provider"}

        with pytest.raises(ValueError, match="Unknown provider"):
            AIFactory.get_provider(config)

    def test_get_or_default(self):
        """Test _get_or_default helper."""
        from ai.factory import AIFactory

        assert AIFactory._get_or_default({"key": "value"}, "key", "default") == "value"
        assert AIFactory._get_or_default({}, "key", "default") == "default"
        assert AIFactory._get_or_default({"key": ""}, "key", "default") == "default"
        assert AIFactory._get_or_default({"key": None}, "key", "default") == "default"

    def test_providers_metadata_structure(self):
        """Test that all providers have required metadata fields."""
        from ai.factory import AIFactory

        for provider_key, info in AIFactory.PROVIDERS.items():
            assert "name" in info, f"{provider_key} missing 'name'"
            assert "description" in info, f"{provider_key} missing 'description'"
            assert "requires_api_key" in info, (
                f"{provider_key} missing 'requires_api_key'"
            )
            assert "requires_endpoint" in info, (
                f"{provider_key} missing 'requires_endpoint'"
            )
