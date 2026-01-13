"""Integration tests for AI providers."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import LLMProvider, StreamChunk, TokenUsage
from ai.factory import AIFactory
from ai.manager import AIManager


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_home(tmp_path, monkeypatch):
    """Mock home directory to use temp directory."""
    null_dir = tmp_path / ".null"
    null_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Patch storage and settings modules
    import config.storage as storage_module
    import config.settings as settings_module

    monkeypatch.setattr(storage_module, "DB_PATH", null_dir / "null.db")
    monkeypatch.setattr(settings_module, "CONFIG_PATH", null_dir / "config.json")

    # Reset singleton
    settings_module.SettingsManager._instance = None
    settings_module.SettingsManager._settings = None

    return tmp_path


@pytest.fixture
def mock_storage(mock_home):
    """Create storage manager with temp database."""
    from config.storage import StorageManager

    storage = StorageManager()
    yield storage
    storage.close()


@pytest.fixture
def mock_config(mock_storage):
    """Provide Config with mocked storage."""
    from config import Config

    return Config


# =============================================================================
# AIManager Initialization Tests
# =============================================================================


class TestAIManagerInitialization:
    """Test AIManager initialization."""

    def test_manager_creates_empty_providers_dict(self, mock_config):
        """AIManager starts with empty providers cache."""
        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()
            assert manager._providers == {}

    def test_manager_preloads_active_provider(self, mock_config):
        """AIManager preloads active provider on init."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test-key")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.model = "gpt-4"
            mock_factory.return_value = mock_provider

            manager = AIManager()
            assert "openai" in manager._providers

    def test_manager_handles_missing_provider(self, mock_config):
        """AIManager handles missing provider gracefully."""
        mock_config.set("ai.provider", "")

        manager = AIManager()
        assert manager.get_active_provider() is None


# =============================================================================
# Provider Registration & Discovery Tests
# =============================================================================


class TestProviderRegistration:
    """Test provider registration and discovery."""

    def test_factory_lists_all_providers(self):
        """AIFactory lists all registered provider types."""
        providers = AIFactory.list_providers()

        assert "ollama" in providers
        assert "openai" in providers
        assert "anthropic" in providers
        assert "openrouter" in providers
        assert len(providers) >= 20  # Many providers registered

    def test_factory_provides_provider_info(self):
        """AIFactory returns metadata for providers."""
        openai_info = AIFactory.get_provider_info("openai")

        assert openai_info["name"] == "OpenAI"
        assert openai_info["requires_api_key"] is True
        assert openai_info["requires_endpoint"] is False

    def test_factory_provider_info_for_local(self):
        """AIFactory shows local providers don't need API key."""
        ollama_info = AIFactory.get_provider_info("ollama")

        assert ollama_info["requires_api_key"] is False
        assert ollama_info["requires_endpoint"] is True

    def test_manager_get_usable_providers_with_api_key(self, mock_config):
        """Manager returns providers with configured API keys."""
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.anthropic.api_key", "sk-ant-test")
        mock_config.set("ai.provider", "openai")

        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()
            usable = manager.get_usable_providers()

            assert "openai" in usable
            assert "anthropic" in usable

    def test_manager_get_usable_providers_includes_active(self, mock_config):
        """Manager always includes active provider."""
        mock_config.set("ai.provider", "ollama")

        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()
            usable = manager.get_usable_providers()

            assert "ollama" in usable


# =============================================================================
# Model Listing Tests
# =============================================================================


class TestModelListing:
    """Test model listing for each provider type."""

    @pytest.mark.asyncio
    async def test_list_models_ollama(self, mock_config):
        """Test Ollama model listing."""
        mock_config.set("ai.provider", "ollama")
        mock_config.set("ai.ollama.endpoint", "http://localhost:11434")

        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.model = "llama3.2"
        mock_provider.list_models = AsyncMock(
            return_value=["llama3.2", "codellama", "mistral"]
        )

        with patch.object(AIFactory, "get_provider", return_value=mock_provider):
            with patch.object(AIManager, "get_active_provider", return_value=None):
                manager = AIManager()
                manager._providers["ollama"] = mock_provider

                result = await manager._fetch_models_for_provider("ollama")

                assert result[0] == "ollama"
                assert "llama3.2" in result[1]

    @pytest.mark.asyncio
    async def test_list_models_openai(self, mock_config):
        """Test OpenAI model listing."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test")

        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.model = "gpt-4"
        mock_provider.list_models = AsyncMock(
            return_value=["gpt-4", "gpt-4o", "gpt-3.5-turbo"]
        )

        with patch.object(AIFactory, "get_provider", return_value=mock_provider):
            with patch.object(AIManager, "get_active_provider", return_value=None):
                manager = AIManager()
                manager._providers["openai"] = mock_provider

                result = await manager._fetch_models_for_provider("openai")

                assert result[0] == "openai"
                assert "gpt-4" in result[1]

    @pytest.mark.asyncio
    async def test_list_models_anthropic(self, mock_config):
        """Test Anthropic model listing."""
        mock_config.set("ai.provider", "anthropic")
        mock_config.set("ai.anthropic.api_key", "sk-ant-test")

        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.model = "claude-3-sonnet"
        mock_provider.list_models = AsyncMock(
            return_value=["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
        )

        with patch.object(AIFactory, "get_provider", return_value=mock_provider):
            with patch.object(AIManager, "get_active_provider", return_value=None):
                manager = AIManager()
                manager._providers["anthropic"] = mock_provider

                result = await manager._fetch_models_for_provider("anthropic")

                assert result[0] == "anthropic"
                assert "claude-3-sonnet" in result[1]

    @pytest.mark.asyncio
    async def test_list_models_openrouter(self, mock_config):
        """Test OpenRouter model listing."""
        mock_config.set("ai.provider", "openrouter")
        mock_config.set("ai.openrouter.api_key", "sk-or-test")

        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.model = "openai/gpt-4o"
        mock_provider.list_models = AsyncMock(
            return_value=["openai/gpt-4o", "anthropic/claude-3", "meta/llama-3"]
        )

        with patch.object(AIFactory, "get_provider", return_value=mock_provider):
            with patch.object(AIManager, "get_active_provider", return_value=None):
                manager = AIManager()
                manager._providers["openrouter"] = mock_provider

                result = await manager._fetch_models_for_provider("openrouter")

                assert result[0] == "openrouter"
                assert "openai/gpt-4o" in result[1]

    @pytest.mark.asyncio
    async def test_list_all_models_parallel(self, mock_config):
        """Test parallel model fetching from multiple providers."""
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.anthropic.api_key", "sk-ant-test")
        mock_config.set("ai.provider", "openai")

        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()

            # Mock fetch for each provider
            async def mock_fetch(name):
                if name == "openai":
                    return ("openai", ["gpt-4"], None)
                elif name == "anthropic":
                    return ("anthropic", ["claude-3"], None)
                return (name, [], "Error")

            manager._fetch_models_for_provider = mock_fetch
            manager.get_usable_providers = MagicMock(
                return_value=["openai", "anthropic"]
            )

            result = await manager.list_all_models()

            assert "openai" in result
            assert "anthropic" in result

    @pytest.mark.asyncio
    async def test_list_models_timeout_handling(self, mock_config):
        """Test timeout handling during model listing."""
        mock_config.set("ai.provider", "slow_provider")

        mock_provider = MagicMock(spec=LLMProvider)

        async def slow_list():
            await asyncio.sleep(20)  # Will timeout
            return []

        mock_provider.list_models = slow_list

        with patch.object(AIFactory, "get_provider", return_value=mock_provider):
            with patch.object(AIManager, "get_active_provider", return_value=None):
                manager = AIManager()
                manager._providers["slow_provider"] = mock_provider

                result = await manager._fetch_models_for_provider("slow_provider")

                assert result[0] == "slow_provider"
                assert result[1] == []
                assert result[2] == "Timeout"


# =============================================================================
# Provider Connection Tests
# =============================================================================


class TestProviderConnection:
    """Test provider connection testing."""

    @pytest.mark.asyncio
    async def test_close_all_providers(self, mock_config):
        """Test closing all provider connections."""
        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()

            mock_provider1 = MagicMock(spec=LLMProvider)
            mock_provider1.close = AsyncMock()
            mock_provider2 = MagicMock(spec=LLMProvider)
            mock_provider2.close = AsyncMock()

            manager._providers = {"openai": mock_provider1, "anthropic": mock_provider2}

            await manager.close_all()

            mock_provider1.close.assert_called_once()
            mock_provider2.close.assert_called_once()
            assert manager._providers == {}


# =============================================================================
# Provider Configuration Tests
# =============================================================================


class TestProviderConfiguration:
    """Test provider configuration (API keys, endpoints)."""

    def test_openai_requires_api_key(self, mock_config):
        """OpenAI provider requires API key."""
        config = {"provider": "openai", "api_key": "sk-test-key"}
        provider = AIFactory.get_provider(config)

        assert provider is not None
        assert provider.model == "gpt-4o-mini"

    def test_ollama_requires_endpoint(self, mock_config):
        """Ollama provider requires endpoint."""
        config = {
            "provider": "ollama",
            "endpoint": "http://localhost:11434",
        }
        provider = AIFactory.get_provider(config)

        assert provider is not None
        assert provider.model == "llama3.2"

    def test_anthropic_api_key_config(self, mock_config):
        """Anthropic provider with API key."""
        config = {
            "provider": "anthropic",
            "api_key": "sk-ant-test",
        }
        provider = AIFactory.get_provider(config)

        assert provider is not None
        assert "claude" in provider.model.lower()

    def test_openrouter_api_key_config(self, mock_config):
        """OpenRouter provider with API key."""
        config = {
            "provider": "openrouter",
            "api_key": "sk-or-test",
        }
        provider = AIFactory.get_provider(config)

        assert provider is not None
        assert "openai/gpt" in provider.model

    def test_unknown_provider_raises_error(self, mock_config):
        """Unknown provider raises ValueError."""
        config = {"provider": "unknown_provider"}

        with pytest.raises(ValueError, match="Unknown provider"):
            AIFactory.get_provider(config)

    def test_custom_model_override(self, mock_config):
        """Custom model can be specified in config."""
        config = {
            "provider": "openai",
            "api_key": "sk-test",
            "model": "gpt-4-turbo",
        }
        provider = AIFactory.get_provider(config)

        assert provider.model == "gpt-4-turbo"


# =============================================================================
# Provider Switching Tests
# =============================================================================


class TestProviderSwitching:
    """Test switching between providers."""

    def test_switch_active_provider(self, mock_config):
        """Test switching active provider."""
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.anthropic.api_key", "sk-ant-test")

        # Start with OpenAI
        mock_config.set("ai.provider", "openai")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_openai = MagicMock(spec=LLMProvider)
            mock_openai.model = "gpt-4"
            mock_anthropic = MagicMock(spec=LLMProvider)
            mock_anthropic.model = "claude-3-sonnet"

            def get_provider_side_effect(config):
                if config.get("provider") == "openai":
                    return mock_openai
                return mock_anthropic

            mock_factory.side_effect = get_provider_side_effect

            manager = AIManager()
            active = manager.get_active_provider()
            assert active.model == "gpt-4"

            # Switch to Anthropic
            mock_config.set("ai.provider", "anthropic")
            new_active = manager.get_active_provider()
            assert new_active.model == "claude-3-sonnet"

    def test_provider_caching(self, mock_config):
        """Test that providers are cached."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.model = "gpt-4"
            mock_factory.return_value = mock_provider

            manager = AIManager()

            # Get provider twice
            p1 = manager.get_provider("openai")
            p2 = manager.get_provider("openai")

            # Factory should only be called once (cached)
            assert mock_factory.call_count == 1
            assert p1 is p2

    def test_force_refresh_provider(self, mock_config):
        """Test force refresh recreates provider."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.model = "gpt-4"
            mock_factory.return_value = mock_provider

            manager = AIManager()

            # Get provider, then force refresh
            manager.get_provider("openai")
            manager.get_provider("openai", force_refresh=True)

            # Factory called twice due to force refresh
            assert mock_factory.call_count == 2

    def test_model_update_on_cached_provider(self, mock_config):
        """Test model update on cached provider."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.openai.model", "gpt-4")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.model = "gpt-4"
            mock_factory.return_value = mock_provider

            manager = AIManager()

            # Initial provider
            manager.get_provider("openai")
            assert mock_provider.model == "gpt-4"

            # Change model in config
            mock_config.set("ai.openai.model", "gpt-4o")

            # Get provider again - should update model
            manager.get_provider("openai")
            assert mock_provider.model == "gpt-4o"


# =============================================================================
# Streaming Model List Tests
# =============================================================================


class TestStreamingModelList:
    """Test streaming model list functionality."""

    @pytest.mark.asyncio
    async def test_list_all_models_streaming(self, mock_config):
        """Test streaming model list yields results as they complete."""
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.provider", "openai")

        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()
            manager.get_usable_providers = MagicMock(return_value=["openai"])

            async def mock_fetch(name):
                return (name, ["model-1", "model-2"], None)

            manager._fetch_models_for_provider = mock_fetch

            results = []
            async for item in manager.list_all_models_streaming():
                results.append(item)

            assert len(results) == 1
            assert results[0][0] == "openai"
            assert results[0][3] == 1  # completed count
            assert results[0][4] == 1  # total count

    @pytest.mark.asyncio
    async def test_streaming_returns_empty_for_no_providers(self, mock_config):
        """Test streaming returns nothing when no providers configured."""
        mock_config.set("ai.provider", "")

        with patch.object(AIManager, "get_active_provider", return_value=None):
            manager = AIManager()
            manager.get_usable_providers = MagicMock(return_value=[])

            results = []
            async for item in manager.list_all_models_streaming():
                results.append(item)

            assert results == []


# =============================================================================
# Autocomplete Provider Tests
# =============================================================================


class TestAutocompleteProvider:
    """Test autocomplete provider functionality."""

    def test_get_autocomplete_provider_dedicated(self, mock_config):
        """Test getting dedicated autocomplete provider."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.autocomplete.provider", "groq")
        mock_config.set("ai.groq.api_key", "sk-groq-test")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_openai = MagicMock(spec=LLMProvider)
            mock_openai.model = "gpt-4"
            mock_groq = MagicMock(spec=LLMProvider)
            mock_groq.model = "llama-3.3-70b-versatile"

            def get_provider_side_effect(config):
                if config.get("provider") == "groq":
                    return mock_groq
                return mock_openai

            mock_factory.side_effect = get_provider_side_effect

            manager = AIManager()

            ac_provider = manager.get_autocomplete_provider()
            assert ac_provider.model == "llama-3.3-70b-versatile"

    def test_get_autocomplete_provider_fallback(self, mock_config):
        """Test autocomplete falls back to active provider."""
        mock_config.set("ai.provider", "openai")
        mock_config.set("ai.openai.api_key", "sk-test")
        mock_config.set("ai.autocomplete.provider", "")

        with patch.object(AIFactory, "get_provider") as mock_factory:
            mock_openai = MagicMock(spec=LLMProvider)
            mock_openai.model = "gpt-4"
            mock_factory.return_value = mock_openai

            manager = AIManager()

            ac_provider = manager.get_autocomplete_provider()
            active_provider = manager.get_active_provider()

            assert ac_provider is active_provider
