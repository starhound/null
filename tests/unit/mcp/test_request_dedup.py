import asyncio
import time

import pytest

from mcp.request_dedup import CachedResult, RequestDeduplicator


class TestCachedResult:
    def test_creation(self):
        result = CachedResult(
            result={"data": "test"}, timestamp=100.0, tool_name="test_tool"
        )
        assert result.result == {"data": "test"}
        assert result.timestamp == 100.0
        assert result.tool_name == "test_tool"


class TestRequestDeduplicator:
    @pytest.fixture
    def dedup(self):
        return RequestDeduplicator(dedup_window=1.0, enabled=True)

    def test_default_values(self):
        dedup = RequestDeduplicator()
        assert dedup.dedup_window == 1.0
        assert dedup.enabled is True
        assert dedup.cache_size == 0

    def test_make_key_deterministic(self, dedup):
        key1 = dedup._make_key("tool_a", {"arg1": "value1", "arg2": 2})
        key2 = dedup._make_key("tool_a", {"arg2": 2, "arg1": "value1"})
        assert key1 == key2

    def test_make_key_different_tools(self, dedup):
        key1 = dedup._make_key("tool_a", {"arg": 1})
        key2 = dedup._make_key("tool_b", {"arg": 1})
        assert key1 != key2

    def test_make_key_different_args(self, dedup):
        key1 = dedup._make_key("tool", {"arg": 1})
        key2 = dedup._make_key("tool", {"arg": 2})
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_cache_miss_on_empty(self, dedup):
        hit, result = await dedup.get_cached("tool", {"arg": 1})
        assert hit is False
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_after_store(self, dedup):
        await dedup.cache_result("tool", {"arg": 1}, {"response": "data"})
        hit, result = await dedup.get_cached("tool", {"arg": 1})
        assert hit is True
        assert result == {"response": "data"}

    @pytest.mark.asyncio
    async def test_cache_expires(self, dedup):
        dedup.dedup_window = 0.05
        await dedup.cache_result("tool", {"arg": 1}, {"response": "data"})
        await asyncio.sleep(0.1)
        hit, result = await dedup.get_cached("tool", {"arg": 1})
        assert hit is False
        assert result is None

    @pytest.mark.asyncio
    async def test_disabled_dedup_no_cache(self):
        dedup = RequestDeduplicator(enabled=False)
        await dedup.cache_result("tool", {"arg": 1}, {"response": "data"})
        hit, result = await dedup.get_cached("tool", {"arg": 1})
        assert hit is False
        assert dedup.cache_size == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, dedup):
        dedup.dedup_window = 0.05
        await dedup.cache_result("tool1", {}, "result1")
        await dedup.cache_result("tool2", {}, "result2")
        assert dedup.cache_size == 2

        await asyncio.sleep(0.1)
        removed = await dedup.cleanup_expired()
        assert removed == 2
        assert dedup.cache_size == 0

    @pytest.mark.asyncio
    async def test_cleanup_partial(self, dedup):
        dedup.dedup_window = 0.1
        await dedup.cache_result("tool1", {}, "result1")
        await asyncio.sleep(0.05)
        await dedup.cache_result("tool2", {}, "result2")
        await asyncio.sleep(0.06)

        removed = await dedup.cleanup_expired()
        assert removed == 1
        assert dedup.cache_size == 1
        hit, _ = await dedup.get_cached("tool2", {})
        assert hit is True

    def test_clear(self, dedup):
        dedup._cache["key1"] = CachedResult(result="a", timestamp=0, tool_name="t")
        dedup._cache["key2"] = CachedResult(result="b", timestamp=0, tool_name="t")
        assert dedup.cache_size == 2
        dedup.clear()
        assert dedup.cache_size == 0

    @pytest.mark.asyncio
    async def test_concurrent_access(self, dedup):
        async def writer():
            for i in range(10):
                await dedup.cache_result(f"tool_{i}", {"i": i}, f"result_{i}")
                await asyncio.sleep(0.001)

        async def reader():
            for i in range(10):
                await dedup.get_cached(f"tool_{i}", {"i": i})
                await asyncio.sleep(0.001)

        await asyncio.gather(writer(), reader())
        assert dedup.cache_size == 10
