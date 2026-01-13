import pytest
from security.rate_limiter import (
    CostTracker,
    RateLimiter,
    get_cost_tracker,
    get_rate_limiter,
)


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        return RateLimiter(max_requests_per_minute=5, max_tokens_per_hour=1000)

    @pytest.mark.asyncio
    async def test_acquire_within_limits(self, limiter):
        allowed, msg = await limiter.acquire(100)
        assert allowed
        assert msg == ""

    @pytest.mark.asyncio
    async def test_acquire_exceeds_request_limit(self, limiter):
        for _ in range(5):
            await limiter.acquire(1)
        allowed, msg = await limiter.acquire(1)
        assert not allowed
        assert "requests/min" in msg

    @pytest.mark.asyncio
    async def test_acquire_exceeds_token_limit(self, limiter):
        allowed, msg = await limiter.acquire(1001)
        assert not allowed
        assert "Token limit" in msg

    def test_get_usage(self, limiter):
        usage = limiter.get_usage()
        assert "requests_this_minute" in usage
        assert "tokens_this_hour" in usage
        assert usage["max_requests_per_minute"] == 5
        assert usage["max_tokens_per_hour"] == 1000

    @pytest.mark.asyncio
    async def test_disabled_limiter(self):
        limiter = RateLimiter(enabled=False)
        for _ in range(100):
            allowed, _ = await limiter.acquire(1000000)
            assert allowed


class TestCostTracker:
    @pytest.fixture
    def tracker(self):
        return CostTracker(max_cost_per_session=1.0, max_cost_per_hour=2.0)

    def test_record_usage(self, tracker):
        record = tracker.record_usage(1000, 500, "gpt-4o")
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.cost_usd > 0

    def test_check_limit_within_bounds(self, tracker):
        tracker.record_usage(100, 50, "gpt-4o")
        within, msg = tracker.check_limit()
        assert within

    def test_check_limit_exceeds_session(self, tracker):
        for _ in range(100):
            tracker.record_usage(10000, 10000, "gpt-4")
        within, msg = tracker.check_limit()
        assert not within
        assert "Session cost limit" in msg

    def test_get_session_cost(self, tracker):
        tracker.record_usage(1000000, 0, "gpt-4o")
        cost = tracker.get_session_cost()
        assert cost == pytest.approx(2.50, rel=0.01)

    def test_get_session_tokens(self, tracker):
        tracker.record_usage(100, 50, "gpt-4o")
        tracker.record_usage(200, 100, "gpt-4o")
        input_t, output_t = tracker.get_session_tokens()
        assert input_t == 300
        assert output_t == 150

    def test_reset_session(self, tracker):
        tracker.record_usage(1000, 500, "gpt-4o")
        tracker.reset_session()
        assert tracker.get_session_cost() == 0

    def test_get_stats(self, tracker):
        tracker.record_usage(1000, 500, "gpt-4o")
        stats = tracker.get_stats()
        assert "session_cost_usd" in stats
        assert "total_requests" in stats
        assert stats["total_requests"] == 1

    def test_disabled_tracker(self):
        tracker = CostTracker(enabled=False)
        for _ in range(1000):
            tracker.record_usage(1000000, 1000000, "gpt-4")
        within, _ = tracker.check_limit()
        assert within


class TestGlobalInstances:
    def test_get_rate_limiter_singleton(self):
        l1 = get_rate_limiter()
        l2 = get_rate_limiter()
        assert l1 is l2

    def test_get_cost_tracker_singleton(self):
        t1 = get_cost_tracker()
        t2 = get_cost_tracker()
        assert t1 is t2
