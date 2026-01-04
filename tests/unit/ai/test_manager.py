"""Tests for ai/manager.py - AIManager provider management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.manager import AIManager


class TestAIManagerInit:
    """Tests for AIManager initialization."""

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_init_creates_instance(self, mock_factory, mock_config):
        """Should create AIManager instance."""
        mock_config.get.return_value = None
        manager = AIManager()
        assert manager is not None
        assert isinstance(manager._providers, dict)

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_init_loads_active_provider(self, mock_factory, mock_config):
        """Should attempt to load active provider on init."""
        mock_config.get.return_value = "openai"
        mock_provider = MagicMock()
        mock_factory.get_provider.return_value = mock_provider

        manager = AIManager()

        # get_active_provider is called during init
        mock_config.get.assert_called()


class TestAIManagerGetProvider:
    """Tests for AIManager.get_provider method."""

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_get_provider_returns_none_for_empty_name(self, mock_factory, mock_config):
        """Should return None for empty provider name."""
        mock_config.get.return_value = None
        manager = AIManager()
        result = manager.get_provider("")
        assert result is None

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_get_provider_caches_provider(self, mock_factory, mock_config):
        """Should cache provider after first creation."""
        mock_config.get.return_value = "test-key"
        mock_provider = MagicMock()
        mock_provider.model = "gpt-4"
        mock_factory.get_provider.return_value = mock_provider

        manager = AIManager()
        manager._providers = {}  # Clear cache

        # First call creates provider
        provider1 = manager.get_provider("openai")
        # Second call should use cache
        provider2 = manager.get_provider("openai")

        assert provider1 is provider2

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_get_provider_updates_model_from_config(self, mock_factory, mock_config):
        """Should update cached provider's model if config changed."""
        mock_provider = MagicMock()
        mock_provider.model = "old-model"
        mock_factory.get_provider.return_value = mock_provider

        # First call returns old model, second call returns new model
        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
            "ai.openai.api_key": "key",
            "ai.openai.model": "new-model",
            "ai.openai.endpoint": None,
            "ai.openai.region": None,
            "ai.openai.api_version": None,
            "ai.openai.project_id": None,
            "ai.openai.location": None,
        }.get(key)

        manager = AIManager()
        manager._providers = {"openai": mock_provider}

        provider = manager.get_provider("openai")

        # Model should be updated
        assert provider.model == "new-model"

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_get_provider_force_refresh(self, mock_factory, mock_config):
        """Should recreate provider when force_refresh is True."""
        mock_config.get.return_value = "test-key"
        old_provider = MagicMock()
        old_provider.model = "old"
        new_provider = MagicMock()
        new_provider.model = "new"
        mock_factory.get_provider.side_effect = [old_provider, new_provider]

        manager = AIManager()
        manager._providers = {"openai": old_provider}

        provider = manager.get_provider("openai", force_refresh=True)

        assert provider.model == "new"

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_get_provider_returns_none_on_error(self, mock_factory, mock_config):
        """Should return None if provider creation fails."""
        mock_config.get.return_value = "test"
        mock_factory.get_provider.side_effect = Exception("Creation failed")

        manager = AIManager()
        manager._providers = {}

        result = manager.get_provider("broken")
        assert result is None


class TestAIManagerGetActiveProvider:
    """Tests for AIManager.get_active_provider method."""

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_get_active_provider(self, mock_factory, mock_config):
        """Should get provider for active provider name from config."""
        mock_config.get.return_value = "anthropic"
        mock_provider = MagicMock()
        mock_provider.model = "claude"
        mock_factory.get_provider.return_value = mock_provider

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=mock_provider) as mock_get:
            provider = manager.get_active_provider()
            mock_get.assert_called_with("anthropic")


class TestAIManagerGetAutocompleteProvider:
    """Tests for AIManager.get_autocomplete_provider method."""

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_returns_autocomplete_provider_when_configured(self, mock_factory, mock_config):
        """Should return autocomplete-specific provider when configured."""
        mock_provider = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
            "ai.autocomplete.provider": "groq",
        }.get(key)

        manager = AIManager()

        with patch.object(manager, 'get_provider', return_value=mock_provider) as mock_get:
            manager.get_autocomplete_provider()
            # Should try to get groq provider
            mock_get.assert_called_with("groq")

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_falls_back_to_active_provider(self, mock_factory, mock_config):
        """Should fall back to active provider when no autocomplete provider configured."""
        mock_provider = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
            "ai.autocomplete.provider": None,
        }.get(key)

        manager = AIManager()

        with patch.object(manager, 'get_active_provider', return_value=mock_provider) as mock_get:
            manager.get_autocomplete_provider()
            mock_get.assert_called_once()


class TestAIManagerListAvailableProviders:
    """Tests for AIManager.list_available_providers method."""

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_returns_cached_provider_keys(self, mock_factory, mock_config):
        """Should return list of cached provider keys."""
        mock_config.get.return_value = None
        manager = AIManager()
        manager._providers = {
            "openai": MagicMock(),
            "anthropic": MagicMock(),
        }

        result = manager.list_available_providers()

        assert "openai" in result
        assert "anthropic" in result
        assert len(result) == 2


class TestAIManagerGetUsableProviders:
    """Tests for AIManager.get_usable_providers method."""

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_includes_providers_with_api_key(self, mock_factory, mock_config):
        """Should include cloud providers that have API keys configured."""
        mock_factory.list_providers.return_value = ["openai", "anthropic"]
        mock_factory.get_provider_info.side_effect = lambda p: {
            "openai": {"requires_api_key": True, "requires_endpoint": False},
            "anthropic": {"requires_api_key": True, "requires_endpoint": False},
        }.get(p, {})

        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
            "ai.openai.api_key": "sk-test",
            "ai.anthropic.api_key": "sk-ant-test",
        }.get(key)

        manager = AIManager()
        result = manager.get_usable_providers()

        assert "openai" in result
        assert "anthropic" in result

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_excludes_providers_without_api_key(self, mock_factory, mock_config):
        """Should exclude cloud providers without API keys."""
        mock_factory.list_providers.return_value = ["openai", "anthropic"]
        mock_factory.get_provider_info.side_effect = lambda p: {
            "openai": {"requires_api_key": True, "requires_endpoint": False},
            "anthropic": {"requires_api_key": True, "requires_endpoint": False},
        }.get(p, {})

        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
            "ai.openai.api_key": "sk-test",
            "ai.anthropic.api_key": None,  # No key
        }.get(key)

        manager = AIManager()
        result = manager.get_usable_providers()

        assert "openai" in result
        assert "anthropic" not in result

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_includes_local_providers_with_endpoint(self, mock_factory, mock_config):
        """Should include local providers that have endpoint configured."""
        mock_factory.list_providers.return_value = ["ollama", "lm_studio"]
        mock_factory.get_provider_info.side_effect = lambda p: {
            "ollama": {"requires_api_key": False, "requires_endpoint": True},
            "lm_studio": {"requires_api_key": False, "requires_endpoint": True},
        }.get(p, {})

        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
            "ai.ollama.endpoint": "http://localhost:11434",
            "ai.lm_studio.endpoint": None,
        }.get(key)

        manager = AIManager()
        result = manager.get_usable_providers()

        assert "ollama" in result
        assert "lm_studio" not in result

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_includes_active_local_provider(self, mock_factory, mock_config):
        """Should include local provider if it's the active one."""
        mock_factory.list_providers.return_value = ["ollama"]
        mock_factory.get_provider_info.side_effect = lambda p: {
            "ollama": {"requires_api_key": False, "requires_endpoint": True},
        }.get(p, {})

        mock_config.get.side_effect = lambda key: {
            "ai.provider": "ollama",  # Active
            "ai.ollama.endpoint": None,  # No explicit endpoint
        }.get(key)

        manager = AIManager()
        result = manager.get_usable_providers()

        assert "ollama" in result

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_includes_bedrock_only_when_active(self, mock_factory, mock_config):
        """Should include AWS Bedrock only when it's the active provider."""
        mock_factory.list_providers.return_value = ["bedrock"]
        mock_factory.get_provider_info.side_effect = lambda p: {
            "bedrock": {"requires_api_key": False, "requires_endpoint": False},
        }.get(p, {})

        # Not active
        mock_config.get.side_effect = lambda key: {
            "ai.provider": "openai",
        }.get(key)

        manager = AIManager()
        result = manager.get_usable_providers()

        assert "bedrock" not in result

        # Now make it active
        mock_config.get.side_effect = lambda key: {
            "ai.provider": "bedrock",
        }.get(key)

        result = manager.get_usable_providers()
        assert "bedrock" in result

    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    def test_always_includes_active_provider(self, mock_factory, mock_config):
        """Active provider should always be included."""
        mock_factory.list_providers.return_value = ["custom"]
        mock_factory.get_provider_info.side_effect = lambda p: {
            "custom": {"requires_api_key": True, "requires_endpoint": True},
        }.get(p, {})

        mock_config.get.side_effect = lambda key: {
            "ai.provider": "custom",
            "ai.custom.api_key": None,  # No key
            "ai.custom.endpoint": None,  # No endpoint
        }.get(key)

        manager = AIManager()
        result = manager.get_usable_providers()

        # Even without config, active provider is included
        assert "custom" in result


class TestAIManagerFetchModelsForProvider:
    """Tests for AIManager._fetch_models_for_provider method."""

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_returns_models_on_success(self, mock_factory, mock_config):
        """Should return provider name and models on success."""
        mock_config.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.model = "test"
        mock_provider.list_models = AsyncMock(return_value=["model1", "model2"])

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=mock_provider):
            name, models, error = await manager._fetch_models_for_provider("test")

        assert name == "test"
        assert models == ["model1", "model2"]
        assert error is None

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_returns_error_when_provider_fails(self, mock_factory, mock_config):
        """Should return error message when provider initialization fails."""
        mock_config.get.return_value = None

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=None):
            name, models, error = await manager._fetch_models_for_provider("broken")

        assert name == "broken"
        assert models == []
        assert error == "Failed to initialize"

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_returns_error_on_timeout(self, mock_factory, mock_config):
        """Should return timeout error when list_models takes too long."""
        import asyncio

        mock_config.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.model = "test"

        async def slow_list():
            await asyncio.sleep(15)  # Longer than timeout
            return []

        mock_provider.list_models = slow_list

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=mock_provider):
            # Use a short timeout for testing
            with patch("ai.manager.asyncio.wait_for", side_effect=TimeoutError):
                name, models, error = await manager._fetch_models_for_provider("slow")

        assert name == "slow"
        assert models == []
        assert error == "Timeout"

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_returns_error_on_exception(self, mock_factory, mock_config):
        """Should return error message on exception."""
        mock_config.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.model = "test"
        mock_provider.list_models = AsyncMock(side_effect=Exception("Network error"))

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=mock_provider):
            name, models, error = await manager._fetch_models_for_provider("failing")

        assert name == "failing"
        assert models == []
        assert "Network error" in error

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_truncates_long_error_message(self, mock_factory, mock_config):
        """Should truncate error messages longer than 50 chars."""
        mock_config.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.model = "test"
        long_error = "A" * 100
        mock_provider.list_models = AsyncMock(side_effect=Exception(long_error))

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=mock_provider):
            name, models, error = await manager._fetch_models_for_provider("verbose")

        assert len(error) <= 53  # 50 chars + "..."
        assert error.endswith("...")

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_updates_local_provider_model(self, mock_factory, mock_config):
        """Should update local provider model when using default."""
        mock_provider = MagicMock()
        mock_provider.model = "local-model"  # Default placeholder
        mock_provider.list_models = AsyncMock(return_value=["actual-model", "other-model"])

        mock_config.get.return_value = None

        manager = AIManager()
        manager._providers = {}

        with patch.object(manager, 'get_provider', return_value=mock_provider):
            name, models, error = await manager._fetch_models_for_provider("lm_studio")

        # Should update to first available model
        assert mock_provider.model == "actual-model"
        mock_config.set.assert_called_with("ai.lm_studio.model", "actual-model")


class TestAIManagerListAllModels:
    """Tests for AIManager.list_all_models method."""

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_returns_empty_dict_when_no_providers(self, mock_factory, mock_config):
        """Should return empty dict when no usable providers."""
        mock_config.get.return_value = None

        manager = AIManager()

        with patch.object(manager, 'get_usable_providers', return_value=[]):
            result = await manager.list_all_models()

        assert result == {}

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_fetches_models_from_all_providers(self, mock_factory, mock_config):
        """Should fetch models from all usable providers in parallel."""
        mock_config.get.return_value = None

        manager = AIManager()

        async def mock_fetch(name):
            return (name, [f"{name}-model1", f"{name}-model2"], None)

        with patch.object(manager, 'get_usable_providers', return_value=["openai", "anthropic"]):
            with patch.object(manager, '_fetch_models_for_provider', side_effect=mock_fetch):
                result = await manager.list_all_models()

        assert "openai" in result
        assert "anthropic" in result
        assert result["openai"] == ["openai-model1", "openai-model2"]
        assert result["anthropic"] == ["anthropic-model1", "anthropic-model2"]

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_excludes_providers_with_no_models(self, mock_factory, mock_config):
        """Should exclude providers that return no models."""
        mock_config.get.return_value = None

        manager = AIManager()

        async def mock_fetch(name):
            if name == "empty":
                return (name, [], None)
            return (name, ["model"], None)

        with patch.object(manager, 'get_usable_providers', return_value=["working", "empty"]):
            with patch.object(manager, '_fetch_models_for_provider', side_effect=mock_fetch):
                result = await manager.list_all_models()

        assert "working" in result
        assert "empty" not in result

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_handles_exceptions_gracefully(self, mock_factory, mock_config):
        """Should handle exceptions from individual providers."""
        mock_config.get.return_value = None

        manager = AIManager()

        async def mock_fetch(name):
            if name == "broken":
                raise Exception("Provider error")
            return (name, ["model"], None)

        with patch.object(manager, 'get_usable_providers', return_value=["working", "broken"]):
            with patch.object(manager, '_fetch_models_for_provider', side_effect=mock_fetch):
                result = await manager.list_all_models()

        # Should still have working provider
        assert "working" in result
        # Broken provider not included
        assert "broken" not in result


class TestAIManagerListAllModelsStreaming:
    """Tests for AIManager.list_all_models_streaming method."""

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_yields_nothing_when_no_providers(self, mock_factory, mock_config):
        """Should yield nothing when no usable providers."""
        mock_config.get.return_value = None

        manager = AIManager()

        with patch.object(manager, 'get_usable_providers', return_value=[]):
            results = [r async for r in manager.list_all_models_streaming()]

        assert results == []

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_yields_results_as_they_complete(self, mock_factory, mock_config):
        """Should yield results as each provider completes."""
        mock_config.get.return_value = None

        manager = AIManager()

        async def mock_fetch(name):
            return (name, [f"{name}-model"], None)

        with patch.object(manager, 'get_usable_providers', return_value=["p1", "p2"]):
            with patch.object(manager, '_fetch_models_for_provider', side_effect=mock_fetch):
                results = [r async for r in manager.list_all_models_streaming()]

        assert len(results) == 2

        # Each result should have (name, models, error, completed, total)
        for name, models, error, completed, total in results:
            assert total == 2
            assert completed <= total
            assert name in ["p1", "p2"]

    @pytest.mark.asyncio
    @patch("ai.manager.Config")
    @patch("ai.manager.AIFactory")
    async def test_includes_progress_counts(self, mock_factory, mock_config):
        """Should include completed and total counts."""
        mock_config.get.return_value = None

        manager = AIManager()

        async def mock_fetch(name):
            return (name, ["model"], None)

        with patch.object(manager, 'get_usable_providers', return_value=["a", "b", "c"]):
            with patch.object(manager, '_fetch_models_for_provider', side_effect=mock_fetch):
                results = [r async for r in manager.list_all_models_streaming()]

        # Check that all have total=3
        for _, _, _, completed, total in results:
            assert total == 3

        # Final result should have completed=3
        completed_counts = [r[3] for r in results]
        assert max(completed_counts) == 3
