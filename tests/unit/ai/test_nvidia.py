"""Tests for ai/nvidia.py - NVIDIA NIM provider."""

from unittest.mock import AsyncMock, patch

import pytest

from ai.nvidia import NVIDIA_FREE_MODELS, NVIDIAProvider


class TestNVIDIAFreeModels:
    """Tests for the NVIDIA_FREE_MODELS constant."""

    def test_free_models_is_list(self):
        """NVIDIA_FREE_MODELS should be a list."""
        assert isinstance(NVIDIA_FREE_MODELS, list)

    def test_free_models_not_empty(self):
        """NVIDIA_FREE_MODELS should contain models."""
        assert len(NVIDIA_FREE_MODELS) > 0

    def test_free_models_contains_llama(self):
        """Should include popular Llama models."""
        llama_models = [m for m in NVIDIA_FREE_MODELS if "llama" in m.lower()]
        assert len(llama_models) > 0

    def test_free_models_contains_mistral(self):
        """Should include Mistral models."""
        mistral_models = [m for m in NVIDIA_FREE_MODELS if "mistral" in m.lower()]
        assert len(mistral_models) > 0

    def test_free_models_all_have_org_prefix(self):
        """All models should have organization/model format."""
        for model in NVIDIA_FREE_MODELS:
            assert "/" in model, f"Model {model} missing org prefix"


class TestNVIDIAProviderInit:
    """Tests for NVIDIAProvider.__init__."""

    def test_init_with_api_key(self):
        """Provider should initialize with valid API key."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test-key")
        assert provider.model == "meta/llama-3.1-8b-instruct"

    def test_init_with_custom_model(self):
        """Provider should accept custom model."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(
                api_key="nvapi-test-key",
                model="meta/llama-3.3-70b-instruct",
            )
        assert provider.model == "meta/llama-3.3-70b-instruct"

    def test_init_raises_on_empty_api_key(self):
        """Provider should raise ValueError for empty API key."""
        with pytest.raises(ValueError, match="NVIDIA API key is required"):
            NVIDIAProvider(api_key="")

    def test_init_raises_on_none_api_key(self):
        """Provider should raise ValueError for None API key."""
        with pytest.raises(ValueError, match="NVIDIA API key is required"):
            NVIDIAProvider(api_key=None)

    def test_init_sets_correct_base_url(self):
        """Provider should use NVIDIA API base URL."""
        with patch("ai.openai_compat.openai.AsyncOpenAI") as mock_openai:
            NVIDIAProvider(api_key="nvapi-test-key")
        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"

    def test_init_passes_api_key_to_client(self):
        """Provider should pass API key to OpenAI client."""
        with patch("ai.openai_compat.openai.AsyncOpenAI") as mock_openai:
            NVIDIAProvider(api_key="nvapi-test-key-123")
        call_kwargs = mock_openai.call_args[1]
        assert call_kwargs["api_key"] == "nvapi-test-key-123"


class TestNVIDIAProviderListModels:
    """Tests for NVIDIAProvider.list_models."""

    @pytest.mark.asyncio
    async def test_list_models_filters_to_free_models(self):
        """Should return only free models from API response."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        all_models = [
            "meta/llama-3.1-8b-instruct",
            "meta/llama-3.1-70b-instruct",
            "some/paid-model",
            "microsoft/phi-3-mini-128k-instruct",
        ]
        provider.client.models.list = AsyncMock(
            return_value=type(
                "ModelsResponse",
                (),
                {"data": [type("Model", (), {"id": m})() for m in all_models]},
            )()
        )

        result = await provider.list_models()

        assert "meta/llama-3.1-8b-instruct" in result
        assert "meta/llama-3.1-70b-instruct" in result
        assert "microsoft/phi-3-mini-128k-instruct" in result
        assert "some/paid-model" not in result

    @pytest.mark.asyncio
    async def test_list_models_returns_sorted(self):
        """Should return models in sorted order."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        all_models = [
            "microsoft/phi-3-mini-128k-instruct",
            "meta/llama-3.1-8b-instruct",
            "google/gemma-2-9b-it",
        ]
        provider.client.models.list = AsyncMock(
            return_value=type(
                "ModelsResponse",
                (),
                {"data": [type("Model", (), {"id": m})() for m in all_models]},
            )()
        )

        result = await provider.list_models()

        assert result == sorted(result)

    @pytest.mark.asyncio
    async def test_list_models_returns_fallback_when_no_free_models(self):
        """Should return NVIDIA_FREE_MODELS when API has no free models."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        all_models = ["paid/model-1", "paid/model-2"]
        provider.client.models.list = AsyncMock(
            return_value=type(
                "ModelsResponse",
                (),
                {"data": [type("Model", (), {"id": m})() for m in all_models]},
            )()
        )

        result = await provider.list_models()

        assert result == NVIDIA_FREE_MODELS

    @pytest.mark.asyncio
    async def test_list_models_returns_fallback_on_exception(self):
        """Should return NVIDIA_FREE_MODELS when API call fails."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        provider.client.models.list = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        result = await provider.list_models()

        assert result == NVIDIA_FREE_MODELS

    @pytest.mark.asyncio
    async def test_list_models_returns_fallback_on_empty_response(self):
        """Should return NVIDIA_FREE_MODELS when API returns empty list."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        provider.client.models.list = AsyncMock(
            return_value=type("ModelsResponse", (), {"data": []})()
        )

        result = await provider.list_models()

        assert result == NVIDIA_FREE_MODELS

    @pytest.mark.asyncio
    async def test_list_models_handles_all_free_models_available(self):
        """Should return all free models when all are available."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        all_models = [*NVIDIA_FREE_MODELS, "extra/model"]
        provider.client.models.list = AsyncMock(
            return_value=type(
                "ModelsResponse",
                (),
                {"data": [type("Model", (), {"id": m})() for m in all_models]},
            )()
        )

        result = await provider.list_models()

        assert len(result) == len(NVIDIA_FREE_MODELS)
        for model in NVIDIA_FREE_MODELS:
            assert model in result


class TestNVIDIAProviderInheritedBehavior:
    """Tests for inherited OpenAICompatibleProvider behavior."""

    def test_supports_tools(self):
        """NVIDIA provider should support tool calling."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")
        assert provider.supports_tools() is True

    @pytest.mark.asyncio
    async def test_generate_yields_content(self):
        """Should yield streaming content from generate."""
        from unittest.mock import MagicMock

        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

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
    async def test_validate_connection_returns_true_on_success(self):
        """Should return True when connection is valid."""
        from unittest.mock import MagicMock

        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        provider.client.models.list = AsyncMock(return_value=MagicMock())

        result = await provider.validate_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_returns_false_on_error(self):
        """Should return False when connection fails."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        provider.client.models.list = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await provider.validate_connection()
        assert result is False

    @pytest.mark.asyncio
    async def test_embed_text_returns_embedding(self):
        """Should return embedding vector."""
        from unittest.mock import MagicMock

        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        provider.client.embeddings.create = AsyncMock(return_value=mock_response)

        result = await provider.embed_text("Hello world")

        assert result == [0.1, 0.2, 0.3]


class TestNVIDIAProviderEdgeCases:
    """Edge case tests for NVIDIAProvider."""

    def test_init_with_whitespace_api_key_does_not_raise(self):
        """Provider accepts whitespace API key (validation left to API)."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="   ")
        assert provider.model == "meta/llama-3.1-8b-instruct"

    @pytest.mark.asyncio
    async def test_list_models_with_partial_free_models(self):
        """Should return only the free models that are available."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        partial_models = [
            "meta/llama-3.1-8b-instruct",
            "google/gemma-2-9b-it",
        ]
        provider.client.models.list = AsyncMock(
            return_value=type(
                "ModelsResponse",
                (),
                {"data": [type("Model", (), {"id": m})() for m in partial_models]},
            )()
        )

        result = await provider.list_models()

        assert len(result) == 2
        assert "meta/llama-3.1-8b-instruct" in result
        assert "google/gemma-2-9b-it" in result

    @pytest.mark.asyncio
    async def test_list_models_preserves_case(self):
        """Model IDs should preserve their original case."""
        with patch("ai.openai_compat.openai.AsyncOpenAI"):
            provider = NVIDIAProvider(api_key="nvapi-test")

        all_models = ["meta/llama-3.1-8b-instruct"]
        provider.client.models.list = AsyncMock(
            return_value=type(
                "ModelsResponse",
                (),
                {"data": [type("Model", (), {"id": m})() for m in all_models]},
            )()
        )

        result = await provider.list_models()

        assert "meta/llama-3.1-8b-instruct" in result
