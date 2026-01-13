"""Tests for ai/token_counter.py - Token counting with tiktoken and estimation."""

import pytest

from ai.token_counter import (
    CHARS_PER_TOKEN,
    TIKTOKEN_AVAILABLE,
    TokenCounter,
    count_tokens,
    estimate_tokens,
)


class TestTokenCounter:
    """Tests for the TokenCounter class."""

    def test_init_default(self):
        """TokenCounter initializes with defaults."""
        counter = TokenCounter()
        assert counter.provider == "default"
        assert counter.model == ""

    def test_init_with_provider(self):
        """TokenCounter accepts provider and model."""
        counter = TokenCounter(provider="openai", model="gpt-4o")
        assert counter.provider == "openai"
        assert counter.model == "gpt-4o"

    def test_provider_case_insensitive(self):
        """Provider name is case-insensitive."""
        counter = TokenCounter(provider="OpenAI", model="GPT-4O")
        assert counter.provider == "openai"
        assert counter.model == "gpt-4o"

    def test_count_empty_string(self):
        """Empty string returns 0 tokens."""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0

    def test_count_simple_text(self):
        """Simple text returns reasonable token count."""
        counter = TokenCounter()
        result = counter.count_tokens("Hello, world!")
        assert result > 0
        assert result < 10  # Reasonable range for short text

    def test_count_longer_text(self):
        """Longer text scales appropriately."""
        counter = TokenCounter()
        short = counter.count_tokens("Hello")
        long = counter.count_tokens("Hello " * 100)
        assert long > short

    def test_estimation_fallback(self):
        """Non-OpenAI providers use estimation."""
        counter = TokenCounter(provider="anthropic", model="claude-3")
        # Anthropic uses 3.5 chars per token estimate
        text = "A" * 35
        result = counter.count_tokens(text)
        assert result == 10  # 35 / 3.5 = 10

    def test_default_estimation(self):
        """Unknown providers use default estimation."""
        counter = TokenCounter(provider="unknown")
        text = "A" * 40
        result = counter.count_tokens(text)
        assert result == 10  # 40 / 4.0 = 10

    def test_is_accurate_property_non_openai(self):
        """Non-OpenAI providers report inaccurate counting."""
        counter = TokenCounter(provider="anthropic", model="claude-3")
        assert counter.is_accurate is False

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_openai_uses_tiktoken(self):
        """OpenAI provider uses tiktoken when available."""
        counter = TokenCounter(provider="openai", model="gpt-4o")
        assert counter.is_accurate is True

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_tiktoken_accurate_count(self):
        """Tiktoken provides accurate counts for known text."""
        counter = TokenCounter(provider="openai", model="gpt-4o")
        # "Hello, world!" is typically 4 tokens with cl100k_base
        result = counter.count_tokens("Hello, world!")
        assert result == 4

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_azure_uses_tiktoken(self):
        """Azure OpenAI also uses tiktoken."""
        counter = TokenCounter(provider="azure", model="gpt-4")
        assert counter.is_accurate is True


class TestCountMessageTokens:
    """Tests for message token counting."""

    def test_simple_message(self):
        """Count tokens in simple user message."""
        counter = TokenCounter()
        msg = {"role": "user", "content": "Hello"}
        result = counter.count_message_tokens(msg)
        # Content tokens + overhead
        assert result >= 4  # At least overhead

    def test_empty_content(self):
        """Message with empty content returns overhead only."""
        counter = TokenCounter()
        msg = {"role": "assistant", "content": ""}
        result = counter.count_message_tokens(msg)
        assert result == 4  # Just overhead

    def test_message_with_tool_calls(self):
        """Messages with tool calls include extra tokens."""
        counter = TokenCounter()
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {"name": "test_tool", "arguments": '{"arg": "value"}'},
                }
            ],
        }
        result = counter.count_message_tokens(msg)
        assert result > 4  # More than just overhead

    def test_multiple_messages(self):
        """Count tokens across multiple messages."""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        result = counter.count_messages_tokens(messages)
        assert result > 0

        # Should be sum of individual + priming
        individual_sum = sum(counter.count_message_tokens(m) for m in messages)
        assert result == individual_sum + 3  # +3 for priming


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_count_tokens_function(self):
        """count_tokens convenience function works."""
        result = count_tokens("Hello, world!")
        assert result > 0

    def test_count_tokens_with_provider(self):
        """count_tokens accepts provider and model."""
        result = count_tokens("Test text", provider="anthropic", model="claude-3")
        assert result > 0

    def test_estimate_tokens_backward_compat(self):
        """estimate_tokens maintains backward compatibility."""
        # Uses 4 chars per token
        assert estimate_tokens("") == 0
        assert estimate_tokens("AAAA") == 1
        assert estimate_tokens("A" * 100) == 25


class TestCharsPerToken:
    """Tests for provider-specific token ratios."""

    def test_openai_ratio(self):
        """OpenAI uses 4 chars per token."""
        assert CHARS_PER_TOKEN["openai"] == 4.0

    def test_anthropic_ratio(self):
        """Anthropic uses 3.5 chars per token."""
        assert CHARS_PER_TOKEN["anthropic"] == 3.5

    def test_default_ratio(self):
        """Default ratio is 4 chars per token."""
        assert CHARS_PER_TOKEN["default"] == 4.0


class TestEncodingCache:
    """Tests for encoding caching behavior."""

    @pytest.mark.skipif(not TIKTOKEN_AVAILABLE, reason="tiktoken not installed")
    def test_encoding_cached(self):
        """Encodings are cached and reused."""
        counter1 = TokenCounter(provider="openai", model="gpt-4o")
        counter2 = TokenCounter(provider="openai", model="gpt-4-turbo")
        # Both should get the same cached encoding
        assert counter1._encoding is counter2._encoding

    def test_cache_miss_graceful(self):
        """Non-OpenAI models don't hit cache."""
        counter = TokenCounter(provider="ollama", model="llama3")
        assert counter._encoding is None
