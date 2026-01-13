"""Unit tests for ModelCache."""

import asyncio
import time
from unittest.mock import patch

import pytest

from ai.model_cache import CacheEntry, ModelCache


class TestCacheEntry:
    def test_is_expired_false_when_fresh(self):
        entry = CacheEntry(models=["model-a"])
        assert not entry.is_expired(ttl=300.0)

    def test_is_expired_true_when_old(self):
        entry = CacheEntry(models=["model-a"], timestamp=time.time() - 400)
        assert entry.is_expired(ttl=300.0)

    def test_timestamp_defaults_to_now(self):
        before = time.time()
        entry = CacheEntry(models=[])
        after = time.time()
        assert before <= entry.timestamp <= after


class TestModelCacheInit:
    def test_default_ttl(self):
        cache = ModelCache()
        assert cache.ttl == 300.0

    def test_custom_ttl(self):
        cache = ModelCache(ttl=60.0)
        assert cache.ttl == 60.0


class TestGetModels:
    @pytest.mark.asyncio
    async def test_returns_none_for_uncached(self):
        cache = ModelCache()
        result = await cache.get_models("openai")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_models(self):
        cache = ModelCache()
        await cache.set_models("openai", ["gpt-4", "gpt-3.5"])
        result = await cache.get_models("openai")
        assert result == ["gpt-4", "gpt-3.5"]

    @pytest.mark.asyncio
    async def test_returns_none_for_expired(self):
        cache = ModelCache(ttl=0.01)
        await cache.set_models("openai", ["gpt-4"])
        await asyncio.sleep(0.02)
        result = await cache.get_models("openai")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_copy_not_reference(self):
        cache = ModelCache()
        original = ["model-a", "model-b"]
        await cache.set_models("test", original)
        result = await cache.get_models("test")
        result.append("model-c")
        cached = await cache.get_models("test")
        assert "model-c" not in cached


class TestSetModels:
    @pytest.mark.asyncio
    async def test_stores_models(self):
        cache = ModelCache()
        await cache.set_models("anthropic", ["claude-3"])
        result = await cache.get_models("anthropic")
        assert result == ["claude-3"]

    @pytest.mark.asyncio
    async def test_overwrites_existing(self):
        cache = ModelCache()
        await cache.set_models("openai", ["old-model"])
        await cache.set_models("openai", ["new-model"])
        result = await cache.get_models("openai")
        assert result == ["new-model"]

    @pytest.mark.asyncio
    async def test_stores_copy_not_reference(self):
        cache = ModelCache()
        original = ["model-a"]
        await cache.set_models("test", original)
        original.append("model-b")
        result = await cache.get_models("test")
        assert result == ["model-a"]


class TestInvalidate:
    @pytest.mark.asyncio
    async def test_removes_cached_entry(self):
        cache = ModelCache()
        await cache.set_models("openai", ["gpt-4"])
        removed = await cache.invalidate("openai")
        assert removed is True
        assert await cache.get_models("openai") is None

    @pytest.mark.asyncio
    async def test_returns_false_if_not_found(self):
        cache = ModelCache()
        removed = await cache.invalidate("nonexistent")
        assert removed is False


class TestClearAll:
    @pytest.mark.asyncio
    async def test_clears_all_entries(self):
        cache = ModelCache()
        await cache.set_models("openai", ["gpt-4"])
        await cache.set_models("anthropic", ["claude"])
        count = await cache.clear_all()
        assert count == 2
        assert await cache.get_models("openai") is None
        assert await cache.get_models("anthropic") is None

    @pytest.mark.asyncio
    async def test_returns_zero_when_empty(self):
        cache = ModelCache()
        count = await cache.clear_all()
        assert count == 0


class TestGetCachedProviders:
    @pytest.mark.asyncio
    async def test_returns_valid_providers(self):
        cache = ModelCache()
        await cache.set_models("openai", ["gpt-4"])
        await cache.set_models("anthropic", ["claude"])
        providers = await cache.get_cached_providers()
        assert set(providers) == {"openai", "anthropic"}

    @pytest.mark.asyncio
    async def test_excludes_expired(self):
        cache = ModelCache(ttl=0.01)
        await cache.set_models("openai", ["gpt-4"])
        await asyncio.sleep(0.02)
        await cache.set_models("anthropic", ["claude"])
        providers = await cache.get_cached_providers()
        assert providers == ["anthropic"]


class TestThreadSafety:
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        cache = ModelCache()

        async def writer(provider: str):
            for i in range(10):
                await cache.set_models(provider, [f"model-{i}"])
                await asyncio.sleep(0.001)

        async def reader(provider: str):
            for _ in range(10):
                await cache.get_models(provider)
                await asyncio.sleep(0.001)

        tasks = [
            writer("openai"),
            writer("anthropic"),
            reader("openai"),
            reader("anthropic"),
        ]
        await asyncio.gather(*tasks)
        openai_models = await cache.get_models("openai")
        anthropic_models = await cache.get_models("anthropic")
        assert openai_models is not None
        assert anthropic_models is not None
