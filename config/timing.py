"""Timing configuration for async operations.

Centralizes all configurable delays, intervals, and timeouts
used throughout the application for asyncio.sleep calls.
"""

from dataclasses import dataclass, field


@dataclass
class TimingConfig:
    """Configurable timing values for async operations.

    All values are in seconds unless otherwise noted.
    """

    # Executor timing (executor.py)
    executor_poll_interval: float = 0.01  # Polling interval when waiting for data
    executor_yield_interval: float = 0.0  # Yield to event loop after reading data
    executor_cancel_grace_period: float = (
        0.1  # Wait before force killing cancelled process
    )

    # Sidebar timing (widgets/sidebar.py)
    sidebar_update_interval: float = 2.0  # Interval for periodic process list updates

    # Provider timing (screens/provider.py)
    provider_model_load_delay: float = (
        0.5  # Delay after loading models in provider screen
    )

    # Agent timing (handlers/ai/agent_loop.py)
    agent_loop_interval: float = 0.1  # Interval between agent loop iterations

    # AI/RAG timing (ai/rag.py)
    rag_batch_yield: float = 0.001  # Yield interval during RAG batch processing
    rag_progress_interval: float = 0.01  # Progress update interval for RAG indexing

    # Rate limiter timing (security/rate_limiter.py)
    rate_limiter_backoff: float = 1.0  # Backoff delay when rate limited

    # SSH timing (managers/ssh.py)
    ssh_reconnect_delay: float = 1.0  # Delay before SSH reconnection attempts

    # MCP timing (mcp/)
    mcp_health_check_interval: float = 60.0  # Interval between MCP health checks


# Global timing configuration instance
_timing_config: TimingConfig | None = None


def get_timing_config() -> TimingConfig:
    """Get the global timing configuration.

    Returns:
        TimingConfig: The current timing configuration instance.
    """
    global _timing_config
    if _timing_config is None:
        _timing_config = TimingConfig()
    return _timing_config


def set_timing_config(config: TimingConfig) -> None:
    """Set the global timing configuration.

    Args:
        config: The new timing configuration to use.
    """
    global _timing_config
    _timing_config = config


def reset_timing_config() -> None:
    """Reset timing configuration to defaults."""
    global _timing_config
    _timing_config = None
