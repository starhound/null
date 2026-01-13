"""Unit tests for timing configuration."""

import pytest

from config.timing import (
    TimingConfig,
    get_timing_config,
    reset_timing_config,
    set_timing_config,
)


class TestTimingConfig:
    def test_default_values(self):
        config = TimingConfig()
        assert config.executor_poll_interval == 0.01
        assert config.executor_yield_interval == 0.0
        assert config.executor_cancel_grace_period == 0.1
        assert config.sidebar_update_interval == 2.0
        assert config.provider_model_load_delay == 0.5
        assert config.agent_loop_interval == 0.1
        assert config.rag_batch_yield == 0.001
        assert config.rag_progress_interval == 0.01
        assert config.rate_limiter_backoff == 1.0
        assert config.ssh_reconnect_delay == 1.0
        assert config.mcp_health_check_interval == 60.0

    def test_custom_values(self):
        config = TimingConfig(
            executor_poll_interval=0.05,
            sidebar_update_interval=5.0,
        )
        assert config.executor_poll_interval == 0.05
        assert config.sidebar_update_interval == 5.0
        assert config.executor_yield_interval == 0.0

    def test_all_values_are_floats(self):
        config = TimingConfig()
        for field_name in config.__dataclass_fields__:
            value = getattr(config, field_name)
            assert isinstance(value, float), f"{field_name} should be float"


class TestTimingConfigGlobal:
    def setup_method(self):
        reset_timing_config()

    def teardown_method(self):
        reset_timing_config()

    def test_get_timing_config_returns_default(self):
        config = get_timing_config()
        assert isinstance(config, TimingConfig)
        assert config.executor_poll_interval == 0.01

    def test_get_timing_config_returns_same_instance(self):
        config1 = get_timing_config()
        config2 = get_timing_config()
        assert config1 is config2

    def test_set_timing_config(self):
        custom = TimingConfig(executor_poll_interval=0.1)
        set_timing_config(custom)
        config = get_timing_config()
        assert config.executor_poll_interval == 0.1
        assert config is custom

    def test_reset_timing_config(self):
        custom = TimingConfig(executor_poll_interval=0.1)
        set_timing_config(custom)
        reset_timing_config()
        config = get_timing_config()
        assert config.executor_poll_interval == 0.01
        assert config is not custom
