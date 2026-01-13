"""Unit tests for AIManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import HealthStatus, LLMProvider, ProviderHealth
from ai.manager import AIManager


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.model = "test-model"
    provider.close = AsyncMock()
    provider.list_models = AsyncMock(return_value=["model-a", "model-b"])
    provider.check_health = AsyncMock(
        return_value=ProviderHealth(status=HealthStatus.CONNECTED, latency_ms=100)
    )
    return provider


@pytest.fixture
def ai_manager(mock_home, mock_config):
    """Create AIManager with mocked config."""
    with patch("ai.manager.Config") as mock_cfg:
        mock_cfg.get.return_value = None
        manager = AIManager()
        yield manager


class TestAIManagerInit:
    """Tests for AIManager initialization."""

    def test_init_creates_empty_providers(self, mock_home, mock_config):
        """Manager starts with empty provider dict."""
        with patch("ai.manager.Config") as mock_cfg:
            mock_cfg.get.return_value = None
            manager = AIManager()
            assert manager._providers == {}
            assert manager._health_cache == {}


class TestGetProvider:
    """Tests for get_provider method."""

    def test_get_provider_empty_name_returns_none(self, ai_manager):
        """Empty provider name returns None."""
        assert ai_manager.get_provider("") is None
        assert ai_manager.get_provider(None) is None

    def test_get_provider_caches_instance(self, ai_manager, mock_provider):
        """Provider instances are cached."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.return_value = "test-key"
            mock_factory.get_provider.return_value = mock_provider

            provider1 = ai_manager.get_provider("openai")
            provider2 = ai_manager.get_provider("openai")

            assert provider1 is provider2
            assert mock_factory.get_provider.call_count == 1

    def test_get_provider_force_refresh_recreates(self, ai_manager, mock_provider):
        """force_refresh creates new provider instance."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.return_value = "test-key"
            mock_factory.get_provider.return_value = mock_provider

            ai_manager.get_provider("openai")
            ai_manager.get_provider("openai", force_refresh=True)

            assert mock_factory.get_provider.call_count == 2

    def test_get_provider_updates_model_from_config(self, ai_manager, mock_provider):
        """Cached provider model is updated from config."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.side_effect = lambda key: {
                "ai.openai.api_key": "key",
                "ai.openai.model": "gpt-4o",
            }.get(key)
            mock_factory.get_provider.return_value = mock_provider
            mock_provider.model = "gpt-3.5-turbo"

            ai_manager.get_provider("openai")
            mock_cfg.get.side_effect = lambda key: {
                "ai.openai.api_key": "key",
                "ai.openai.model": "gpt-4o",
            }.get(key)

            provider = ai_manager.get_provider("openai")
            assert provider.model == "gpt-4o"

    def test_get_provider_returns_none_on_exception(self, ai_manager):
        """Returns None if factory raises exception."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.return_value = "key"
            mock_factory.get_provider.side_effect = ValueError("bad config")

            result = ai_manager.get_provider("invalid")
            assert result is None


class TestGetActiveProvider:
    """Tests for get_active_provider method."""

    def test_get_active_provider_uses_config(self, ai_manager, mock_provider):
        """Uses ai.provider config key."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.side_effect = lambda key: {
                "ai.provider": "anthropic",
                "ai.anthropic.api_key": "sk-ant-xxx",
            }.get(key, None)
            mock_factory.get_provider.return_value = mock_provider

            provider = ai_manager.get_active_provider()
            assert provider is mock_provider


class TestGetAutocompleteProvider:
    """Tests for get_autocomplete_provider method."""

    def test_autocomplete_provider_fallback(self, ai_manager, mock_provider):
        """Falls back to active provider if not configured."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.side_effect = lambda key: {
                "ai.autocomplete.provider": None,
                "ai.provider": "openai",
                "ai.openai.api_key": "key",
            }.get(key)
            mock_factory.get_provider.return_value = mock_provider

            provider = ai_manager.get_autocomplete_provider()
            assert provider is mock_provider

    def test_autocomplete_provider_separate_config(self, ai_manager, mock_provider):
        """Uses separate autocomplete provider if configured."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_cfg.get.side_effect = lambda key: {
                "ai.autocomplete.provider": "groq",
                "ai.groq.api_key": "gsk_xxx",
            }.get(key)
            mock_factory.get_provider.return_value = mock_provider

            provider = ai_manager.get_autocomplete_provider()
            assert provider is mock_provider


class TestListAvailableProviders:
    """Tests for list_available_providers method."""

    def test_list_available_returns_cached_keys(self, ai_manager, mock_provider):
        """Returns keys of cached providers."""
        ai_manager._providers = {"openai": mock_provider, "anthropic": mock_provider}
        result = ai_manager.list_available_providers()
        assert set(result) == {"openai", "anthropic"}

    def test_list_available_empty_when_none_cached(self, ai_manager):
        """Returns empty list when no providers cached."""
        assert ai_manager.list_available_providers() == []


class TestGetUsableProviders:
    """Tests for get_usable_providers method."""

    def test_usable_providers_with_api_key(self, ai_manager):
        """Cloud providers with API keys are usable."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_factory.list_providers.return_value = ["openai", "anthropic"]
            mock_factory.get_provider_info.side_effect = lambda p: {
                "openai": {"requires_api_key": True},
                "anthropic": {"requires_api_key": True},
            }[p]
            mock_cfg.get.side_effect = lambda key: {
                "ai.openai.api_key": "sk-xxx",
                "ai.anthropic.api_key": None,
                "ai.provider": None,
            }.get(key)

            result = ai_manager.get_usable_providers()
            assert "openai" in result
            assert "anthropic" not in result

    def test_usable_includes_active_provider(self, ai_manager):
        """Active provider always included."""
        with (
            patch("ai.manager.AIFactory") as mock_factory,
            patch("ai.manager.Config") as mock_cfg,
        ):
            mock_factory.list_providers.return_value = ["ollama"]
            mock_factory.get_provider_info.return_value = {
                "requires_api_key": False,
                "requires_endpoint": True,
            }
            mock_cfg.get.side_effect = lambda key: {
                "ai.provider": "ollama",
                "ai.ollama.endpoint": None,
            }.get(key)

            result = ai_manager.get_usable_providers()
            assert "ollama" in result


class TestListAllModels:
    """Tests for list_all_models method."""

    @pytest.mark.asyncio
    async def test_list_all_models_empty_when_no_providers(self, ai_manager):
        """Returns empty dict when no usable providers."""
        with patch.object(ai_manager, "get_usable_providers", return_value=[]):
            result = await ai_manager.list_all_models()
            assert result == {}

    @pytest.mark.asyncio
    async def test_list_all_models_aggregates_results(self, ai_manager, mock_provider):
        """Aggregates models from all providers."""
        mock_provider2 = MagicMock(spec=LLMProvider)
        mock_provider2.model = "claude-3"
        mock_provider2.list_models = AsyncMock(return_value=["claude-3-opus"])

        with (
            patch.object(
                ai_manager, "get_usable_providers", return_value=["openai", "anthropic"]
            ),
            patch.object(
                ai_manager,
                "get_provider",
                side_effect=lambda p: mock_provider
                if p == "openai"
                else mock_provider2,
            ),
        ):
            result = await ai_manager.list_all_models()
            assert "openai" in result
            assert "anthropic" in result
            assert result["openai"] == ["model-a", "model-b"]
            assert result["anthropic"] == ["claude-3-opus"]

    @pytest.mark.asyncio
    async def test_list_all_models_handles_timeout(self, ai_manager, mock_provider):
        """Handles provider timeout gracefully."""

        async def slow_list():
            await asyncio.sleep(20)
            return []

        mock_provider.list_models = slow_list

        with (
            patch.object(ai_manager, "get_usable_providers", return_value=["slow"]),
            patch.object(ai_manager, "get_provider", return_value=mock_provider),
        ):
            result = await asyncio.wait_for(ai_manager.list_all_models(), timeout=15)
            assert "slow" not in result


class TestProviderHealth:
    """Tests for health check methods."""

    def test_get_provider_health_returns_cached(self, ai_manager):
        """Returns cached health status."""
        health = ProviderHealth(status=HealthStatus.CONNECTED)
        ai_manager._health_cache["openai"] = health
        assert ai_manager.get_provider_health("openai") == health

    def test_get_provider_health_default_unknown(self, ai_manager):
        """Returns UNKNOWN status for uncached provider."""
        health = ai_manager.get_provider_health("uncached")
        assert health.status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_check_provider_health_updates_cache(self, ai_manager, mock_provider):
        """Health check updates cache."""
        with patch.object(ai_manager, "get_provider", return_value=mock_provider):
            health = await ai_manager.check_provider_health("openai")
            assert health.status == HealthStatus.CONNECTED
            assert ai_manager._health_cache["openai"].status == HealthStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_check_provider_health_no_provider(self, ai_manager):
        """Returns ERROR if provider not initialized."""
        with patch.object(ai_manager, "get_provider", return_value=None):
            health = await ai_manager.check_provider_health("invalid")
            assert health.status == HealthStatus.ERROR
            assert "not initialized" in health.error_message

    @pytest.mark.asyncio
    async def test_check_all_health_parallel(self, ai_manager, mock_provider):
        """Checks all providers in parallel."""
        with (
            patch.object(
                ai_manager, "get_usable_providers", return_value=["openai", "anthropic"]
            ),
            patch.object(ai_manager, "get_provider", return_value=mock_provider),
        ):
            results = await ai_manager.check_all_health()
            assert "openai" in results
            assert "anthropic" in results


class TestCloseAll:
    """Tests for close_all method."""

    @pytest.mark.asyncio
    async def test_close_all_closes_providers(self, ai_manager, mock_provider):
        """Closes all cached providers."""
        ai_manager._providers = {"openai": mock_provider, "anthropic": mock_provider}
        await ai_manager.close_all()

        assert mock_provider.close.call_count == 2
        assert ai_manager._providers == {}

    @pytest.mark.asyncio
    async def test_close_all_handles_exceptions(self, ai_manager, mock_provider):
        """Continues closing even if one fails."""
        failing_provider = MagicMock(spec=LLMProvider)
        failing_provider.close = AsyncMock(side_effect=Exception("close failed"))

        ai_manager._providers = {"fail": failing_provider, "ok": mock_provider}
        await ai_manager.close_all()

        assert ai_manager._providers == {}
        mock_provider.close.assert_called_once()


class TestListAllModelsStreaming:
    """Tests for list_all_models_streaming method."""

    @pytest.mark.asyncio
    async def test_streaming_yields_progress(self, ai_manager, mock_provider):
        """Yields results with progress counts."""
        with (
            patch.object(ai_manager, "get_usable_providers", return_value=["openai"]),
            patch.object(ai_manager, "get_provider", return_value=mock_provider),
        ):
            results = []
            async for item in ai_manager.list_all_models_streaming():
                results.append(item)

            assert len(results) == 1
            provider_name, models, error, completed, total = results[0]
            assert provider_name == "openai"
            assert models == ["model-a", "model-b"]
            assert error is None
            assert completed == 1
            assert total == 1

    @pytest.mark.asyncio
    async def test_streaming_empty_when_no_providers(self, ai_manager):
        """Yields nothing when no providers."""
        with patch.object(ai_manager, "get_usable_providers", return_value=[]):
            results = [item async for item in ai_manager.list_all_models_streaming()]
            assert results == []
