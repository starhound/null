"""Rate limiting and cost tracking for AI API calls."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Token pricing per 1M tokens (USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    # Anthropic
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # Google
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    # Groq (free tier, but track anyway)
    "llama-3.3-70b": {"input": 0.59, "output": 0.79},
    "mixtral-8x7b": {"input": 0.24, "output": 0.24},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-coder": {"input": 0.14, "output": 0.28},
    # Mistral
    "mistral-large": {"input": 2.00, "output": 6.00},
    "codestral": {"input": 0.20, "output": 0.60},
    # Default for unknown models
    "_default": {"input": 1.00, "output": 3.00},
}


@dataclass
class UsageRecord:
    """Record of token usage for a single request."""

    timestamp: float
    input_tokens: int
    output_tokens: int
    model: str
    cost_usd: float


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API requests.

    Implements a simple token bucket algorithm with configurable
    refill rate and maximum capacity.
    """

    max_requests_per_minute: int = 60
    max_tokens_per_hour: int = 100_000
    enabled: bool = True

    # Internal state
    _request_timestamps: list[float] = field(default_factory=list)
    _hourly_tokens: int = 0
    _hour_start: float = field(default_factory=time.time)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self):
        # Ensure lock is created if not provided
        if not hasattr(self, "_lock") or self._lock is None:
            object.__setattr__(self, "_lock", asyncio.Lock())

    async def acquire(self, tokens: int = 1) -> tuple[bool, str]:
        """Try to acquire capacity for a request.

        Args:
            tokens: Estimated tokens for this request

        Returns:
            Tuple of (allowed, message)
        """
        if not self.enabled:
            return True, ""

        async with self._lock:
            now = time.time()

            # Reset hourly counter if needed
            if now - self._hour_start >= 3600:
                self._hourly_tokens = 0
                self._hour_start = now

            # Check requests per minute
            minute_ago = now - 60
            self._request_timestamps = [
                ts for ts in self._request_timestamps if ts > minute_ago
            ]

            if len(self._request_timestamps) >= self.max_requests_per_minute:
                wait_time = self._request_timestamps[0] - minute_ago
                return (
                    False,
                    f"Rate limit: {self.max_requests_per_minute} requests/min exceeded. Wait {wait_time:.1f}s",
                )

            # Check tokens per hour
            if self._hourly_tokens + tokens > self.max_tokens_per_hour:
                remaining = self.max_tokens_per_hour - self._hourly_tokens
                return (
                    False,
                    f"Token limit: {self.max_tokens_per_hour:,}/hour exceeded. {remaining:,} tokens remaining",
                )

            # Acquire
            self._request_timestamps.append(now)
            self._hourly_tokens += tokens
            return True, ""

    async def wait_for_capacity(self, tokens: int = 1) -> float:
        """Wait until capacity is available.

        Args:
            tokens: Estimated tokens for this request

        Returns:
            Time waited in seconds
        """
        start = time.time()
        while True:
            allowed, _ = await self.acquire(tokens)
            if allowed:
                return time.time() - start
            await asyncio.sleep(1.0)

    def record_usage(self, tokens: int) -> None:
        """Record actual token usage after request completes."""
        # Already counted in acquire, this is for tracking adjustments
        pass

    def get_usage(self) -> dict[str, Any]:
        """Get current usage statistics."""
        now = time.time()
        minute_ago = now - 60
        recent_requests = len(
            [ts for ts in self._request_timestamps if ts > minute_ago]
        )

        return {
            "requests_this_minute": recent_requests,
            "max_requests_per_minute": self.max_requests_per_minute,
            "tokens_this_hour": self._hourly_tokens,
            "max_tokens_per_hour": self.max_tokens_per_hour,
            "hour_resets_in": max(0, 3600 - (now - self._hour_start)),
            "enabled": self.enabled,
        }


@dataclass
class CostTracker:
    """Tracks API costs across sessions.

    Monitors spending and enforces cost limits to prevent
    runaway API usage.
    """

    max_cost_per_session: float = 5.0  # USD
    max_cost_per_hour: float = 10.0  # USD
    enabled: bool = True

    # Internal state
    _session_records: list[UsageRecord] = field(default_factory=list)
    _session_start: float = field(default_factory=time.time)

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> UsageRecord:
        """Record token usage and calculate cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name for pricing lookup

        Returns:
            UsageRecord with cost information
        """
        cost = self._calculate_cost(input_tokens, output_tokens, model)

        record = UsageRecord(
            timestamp=time.time(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost_usd=cost,
        )

        self._session_records.append(record)

        logger.debug(
            "API usage: %s tokens in, %s tokens out, $%.4f (%s)",
            input_tokens,
            output_tokens,
            cost,
            model,
        )

        return record

    def _calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> float:
        """Calculate cost for token usage."""
        # Normalize model name for lookup
        model_lower = model.lower()
        pricing = None

        # Try exact match first
        for model_key, prices in MODEL_PRICING.items():
            if model_key in model_lower or model_lower in model_key:
                pricing = prices
                break

        if pricing is None:
            pricing = MODEL_PRICING["_default"]

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def check_limit(self) -> tuple[bool, str]:
        """Check if we're within spending limits.

        Returns:
            Tuple of (within_limit, message)
        """
        if not self.enabled:
            return True, ""

        session_cost = self.get_session_cost()
        hour_cost = self.get_hourly_cost()

        if session_cost >= self.max_cost_per_session:
            return (
                False,
                f"Session cost limit (${self.max_cost_per_session:.2f}) reached. Current: ${session_cost:.2f}",
            )

        if hour_cost >= self.max_cost_per_hour:
            return (
                False,
                f"Hourly cost limit (${self.max_cost_per_hour:.2f}) reached. Current: ${hour_cost:.2f}",
            )

        # Warn at 80%
        warnings = []
        if session_cost >= self.max_cost_per_session * 0.8:
            warnings.append(
                f"Approaching session limit: ${session_cost:.2f}/${self.max_cost_per_session:.2f}"
            )
        if hour_cost >= self.max_cost_per_hour * 0.8:
            warnings.append(
                f"Approaching hourly limit: ${hour_cost:.2f}/${self.max_cost_per_hour:.2f}"
            )

        return True, "; ".join(warnings) if warnings else ""

    def get_session_cost(self) -> float:
        """Get total cost for current session."""
        return sum(r.cost_usd for r in self._session_records)

    def get_hourly_cost(self) -> float:
        """Get cost for the last hour."""
        hour_ago = time.time() - 3600
        return sum(r.cost_usd for r in self._session_records if r.timestamp > hour_ago)

    def get_session_tokens(self) -> tuple[int, int]:
        """Get total tokens for current session.

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        input_total = sum(r.input_tokens for r in self._session_records)
        output_total = sum(r.output_tokens for r in self._session_records)
        return input_total, output_total

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        input_tokens, output_tokens = self.get_session_tokens()
        session_cost = self.get_session_cost()
        hour_cost = self.get_hourly_cost()

        # Model breakdown
        model_costs: dict[str, float] = {}
        for record in self._session_records:
            model_costs[record.model] = (
                model_costs.get(record.model, 0) + record.cost_usd
            )

        return {
            "session_cost_usd": session_cost,
            "hourly_cost_usd": hour_cost,
            "max_session_cost": self.max_cost_per_session,
            "max_hourly_cost": self.max_cost_per_hour,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "total_requests": len(self._session_records),
            "session_duration_seconds": time.time() - self._session_start,
            "cost_by_model": model_costs,
            "enabled": self.enabled,
        }

    def reset_session(self) -> None:
        """Reset session tracking (call when starting new session)."""
        self._session_records = []
        self._session_start = time.time()


# Global instances
_rate_limiter: RateLimiter | None = None
_cost_tracker: CostTracker | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
