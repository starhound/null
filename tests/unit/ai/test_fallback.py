"""Unit tests for AI provider fallback system."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import StreamChunk
from ai.fallback import (
    FallbackConfig,
    FallbackEvent,
    ProviderFallback,
    get_fallback_config_from_settings,
)


@pytest.fixture
def mock_ai_manager():
    manager = MagicMock()
    manager.get_usable_providers.return_value = ["openai", "anthropic", "ollama"]
    return manager


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.model = "test-model"
    provider.validate_connection = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def fallback_config():
    return FallbackConfig(
        fallback_providers=["anthropic", "ollama"],
        max_retries=2,
        initial_backoff=0.1,
        max_backoff=1.0,
        backoff_multiplier=2.0,
        enabled=True,
    )


class TestFallbackConfig:
    def test_default_values(self):
        config = FallbackConfig()
        assert config.fallback_providers == []
        assert config.max_retries == 3
        assert config.initial_backoff == 1.0
        assert config.max_backoff == 30.0
        assert config.backoff_multiplier == 2.0
        assert config.enabled is True

    def test_custom_values(self, fallback_config):
        assert fallback_config.fallback_providers == ["anthropic", "ollama"]
        assert fallback_config.max_retries == 2
        assert fallback_config.initial_backoff == 0.1


class TestFallbackEvent:
    def test_event_creation(self):
        event = FallbackEvent(
            from_provider="openai",
            to_provider="anthropic",
            error="Connection timeout",
            attempt=1,
        )
        assert event.from_provider == "openai"
        assert event.to_provider == "anthropic"
        assert event.error == "Connection timeout"
        assert event.attempt == 1


class TestProviderFallback:
    def test_initialization(self, mock_ai_manager, fallback_config):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        assert fallback.config == fallback_config
        assert fallback.fallback_events == []

    def test_get_provider_chain(self, mock_ai_manager, fallback_config):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        chain = fallback._get_provider_chain("openai")
        assert chain == ["openai", "anthropic", "ollama"]

    def test_get_provider_chain_primary_in_fallbacks(
        self, mock_ai_manager, fallback_config
    ):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        chain = fallback._get_provider_chain("anthropic")
        assert chain == ["anthropic", "ollama"]
        assert "anthropic" not in chain[1:]

    def test_calculate_backoff(self, mock_ai_manager, fallback_config):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        assert fallback._calculate_backoff(0) == 0.1
        assert fallback._calculate_backoff(1) == 0.2
        assert fallback._calculate_backoff(2) == 0.4
        assert fallback._calculate_backoff(10) == 1.0

    def test_log_fallback(self, mock_ai_manager, fallback_config):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        fallback._log_fallback("openai", "anthropic", "timeout", 1)

        assert len(fallback.fallback_events) == 1
        event = fallback.fallback_events[0]
        assert event.from_provider == "openai"
        assert event.to_provider == "anthropic"

    def test_clear_events(self, mock_ai_manager, fallback_config):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        fallback._log_fallback("openai", "anthropic", "error", 1)
        assert len(fallback.fallback_events) == 1

        fallback.clear_events()
        assert len(fallback.fallback_events) == 0

    def test_fallback_events_returns_copy(self, mock_ai_manager, fallback_config):
        fallback = ProviderFallback(mock_ai_manager, fallback_config)
        fallback._log_fallback("openai", "anthropic", "error", 1)

        events = fallback.fallback_events
        events.clear()
        assert len(fallback.fallback_events) == 1


class TestProviderFallbackAsync:
    @pytest.mark.asyncio
    async def test_generate_success_first_try(
        self, mock_ai_manager, mock_provider, fallback_config
    ):
        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Hello", is_complete=False)
            yield StreamChunk(text=" World", is_complete=True)

        mock_provider.generate = mock_generate
        mock_ai_manager.get_provider.return_value = mock_provider

        fallback = ProviderFallback(mock_ai_manager, fallback_config)

        with patch.object(fallback, "_get_active_provider_name", return_value="openai"):
            chunks = []
            async for chunk in fallback.generate_with_fallback(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0].text == "Hello"
        assert chunks[1].text == " World"
        assert len(fallback.fallback_events) == 0

    @pytest.mark.asyncio
    async def test_generate_fallback_on_failure(self, mock_ai_manager, fallback_config):
        call_count = 0

        async def failing_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Provider unavailable")

        async def success_generate(*args, **kwargs):
            yield StreamChunk(text="Success", is_complete=True)

        failing_provider = MagicMock()
        failing_provider.generate = failing_generate

        success_provider = MagicMock()
        success_provider.generate = success_generate

        def get_provider(name):
            if name == "openai":
                return failing_provider
            return success_provider

        mock_ai_manager.get_provider.side_effect = get_provider

        fallback = ProviderFallback(mock_ai_manager, fallback_config)

        with patch.object(fallback, "_get_active_provider_name", return_value="openai"):
            chunks = []
            async for chunk in fallback.generate_with_fallback(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].text == "Success"
        assert len(fallback.fallback_events) == 1
        assert fallback.fallback_events[0].from_provider == "openai"
        assert fallback.fallback_events[0].to_provider == "anthropic"

    @pytest.mark.asyncio
    async def test_generate_retry_within_provider(
        self, mock_ai_manager, fallback_config
    ):
        attempt_count = 0

        async def flaky_generate(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ConnectionError("Temporary failure")
            yield StreamChunk(text="Success after retry", is_complete=True)

        mock_provider = MagicMock()
        mock_provider.generate = flaky_generate
        mock_ai_manager.get_provider.return_value = mock_provider

        fallback = ProviderFallback(mock_ai_manager, fallback_config)

        with patch.object(fallback, "_get_active_provider_name", return_value="openai"):
            chunks = []
            async for chunk in fallback.generate_with_fallback(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                chunks.append(chunk)

        assert attempt_count == 2
        assert len(chunks) == 1
        assert chunks[0].text == "Success after retry"
        assert len(fallback.fallback_events) == 0

    @pytest.mark.asyncio
    async def test_generate_all_providers_fail(self, mock_ai_manager, fallback_config):
        async def always_fail(*args, **kwargs):
            raise ConnectionError("Always fails")

        mock_provider = MagicMock()
        mock_provider.generate = always_fail
        mock_ai_manager.get_provider.return_value = mock_provider

        fallback = ProviderFallback(mock_ai_manager, fallback_config)

        with patch.object(fallback, "_get_active_provider_name", return_value="openai"):
            with pytest.raises(RuntimeError, match="All providers failed"):
                async for _ in fallback.generate_with_fallback(
                    messages=[{"role": "user", "content": "Hi"}]
                ):
                    pass

    @pytest.mark.asyncio
    async def test_generate_disabled_fallback(self, mock_ai_manager):
        config = FallbackConfig(enabled=False)

        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Direct", is_complete=True)

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate
        mock_ai_manager.get_active_provider.return_value = mock_provider

        fallback = ProviderFallback(mock_ai_manager, config)

        chunks = []
        async for chunk in fallback.generate_with_fallback(
            messages=[{"role": "user", "content": "Hi"}]
        ):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].text == "Direct"

    @pytest.mark.asyncio
    async def test_check_provider_health(self, mock_ai_manager, mock_provider):
        mock_ai_manager.get_provider.return_value = mock_provider
        fallback = ProviderFallback(mock_ai_manager)

        result = await fallback.check_provider_health("openai")
        assert result is True
        mock_provider.validate_connection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_provider_health_not_found(self, mock_ai_manager):
        mock_ai_manager.get_provider.return_value = None
        fallback = ProviderFallback(mock_ai_manager)

        result = await fallback.check_provider_health("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_healthy_providers(self, mock_ai_manager, mock_provider):
        mock_ai_manager.get_provider.return_value = mock_provider
        fallback = ProviderFallback(mock_ai_manager)

        healthy = await fallback.get_healthy_providers()
        assert healthy == ["openai", "anthropic", "ollama"]


class TestGetFallbackConfigFromSettings:
    def test_with_defaults(self, mock_config):
        config = get_fallback_config_from_settings()
        assert config.enabled is True
        assert config.max_retries == 3
        assert config.fallback_providers == []

    def test_with_custom_settings(self):
        with patch("config.Config") as patched_config:
            patched_config.get.side_effect = lambda key: {
                "ai.fallback_providers": ["anthropic", "groq"],
                "ai.fallback_max_retries": 5,
                "ai.fallback_enabled": False,
            }.get(key)

            config = get_fallback_config_from_settings()
            assert config.fallback_providers == ["anthropic", "groq"]
            assert config.max_retries == 5
            assert config.enabled is False
