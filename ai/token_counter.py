"""Token counting with accurate tiktoken for OpenAI models and fallback estimation."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.base import Message

# Try to import tiktoken, fallback gracefully
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None  # type: ignore[assignment]
    TIKTOKEN_AVAILABLE = False


# Encoding name mappings for different model families
MODEL_ENCODINGS: dict[str, str] = {
    # OpenAI GPT-4 and GPT-3.5 use cl100k_base
    "gpt-4": "cl100k_base",
    "gpt-4o": "cl100k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-3.5": "cl100k_base",
    "text-embedding": "cl100k_base",
    # OpenAI o-series reasoning models
    "o1": "cl100k_base",
    "o3": "cl100k_base",
    "o4": "cl100k_base",
}

# Default encoding for OpenAI models
DEFAULT_OPENAI_ENCODING = "cl100k_base"

# Characters per token estimates for different providers
CHARS_PER_TOKEN: dict[str, float] = {
    "openai": 4.0,
    "anthropic": 3.5,  # Claude tends to have slightly smaller tokens
    "google": 4.0,
    "ollama": 4.0,
    "mistral": 4.0,
    "cohere": 4.0,
    "default": 4.0,
}


class TokenCounter:
    """Token counter with tiktoken for OpenAI and estimation for other providers."""

    _encoding_cache: dict[str, object] = {}

    def __init__(self, provider: str = "default", model: str = ""):
        """Initialize token counter.

        Args:
            provider: Provider name (openai, anthropic, etc.)
            model: Model name for encoding selection.
        """
        self.provider = provider.lower()
        self.model = model.lower()
        self._encoding = self._get_encoding()

    @classmethod
    @lru_cache(maxsize=8)
    def _get_cached_encoding(cls, encoding_name: str) -> object | None:
        """Get cached tiktoken encoding instance.

        Args:
            encoding_name: Name of the encoding (e.g., 'cl100k_base').

        Returns:
            Encoding instance or None if tiktoken unavailable.
        """
        if not TIKTOKEN_AVAILABLE or tiktoken is None:
            return None
        try:
            return tiktoken.get_encoding(encoding_name)
        except Exception:
            return None

    def _get_encoding(self) -> object | None:
        """Get the appropriate encoding for the current model.

        Returns:
            Tiktoken encoding or None for non-OpenAI/unavailable.
        """
        if not TIKTOKEN_AVAILABLE:
            return None

        # Only use tiktoken for OpenAI-compatible models
        if self.provider not in ("openai", "azure", "openai_compat"):
            return None

        # Find matching encoding
        for prefix, encoding_name in MODEL_ENCODINGS.items():
            if prefix in self.model:
                return self._get_cached_encoding(encoding_name)

        # Default to cl100k_base for OpenAI
        return self._get_cached_encoding(DEFAULT_OPENAI_ENCODING)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Uses tiktoken for OpenAI models, falls back to estimation.

        Args:
            text: Text to count tokens for.

        Returns:
            Token count (exact for OpenAI, estimated for others).
        """
        if not text:
            return 0

        # Use tiktoken if available
        if self._encoding is not None:
            try:
                return len(self._encoding.encode(text))  # type: ignore[union-attr]
            except Exception:
                pass

        # Fallback to character-based estimation
        return self._estimate_tokens(text)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens based on character count.

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        chars_per_token = CHARS_PER_TOKEN.get(self.provider, CHARS_PER_TOKEN["default"])
        return int(len(text) / chars_per_token)

    def count_message_tokens(self, message: Message) -> int:
        """Count tokens in a chat message.

        Accounts for message structure overhead.

        Args:
            message: Chat message dict with role and content.

        Returns:
            Token count for the message.
        """
        # Base tokens for message structure (role, separators)
        overhead = 4  # <|im_start|>role\n...content...<|im_end|>

        content = message.get("content", "")
        tokens = self.count_tokens(content) if content else 0

        # Add overhead for tool calls if present
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                # Count function name and arguments
                if isinstance(tc, dict):
                    func = tc.get("function", {})
                    tokens += self.count_tokens(func.get("name", ""))
                    tokens += self.count_tokens(str(func.get("arguments", "")))
                    overhead += 3  # Additional structure tokens per tool call

        return tokens + overhead

    def count_messages_tokens(self, messages: list[Message]) -> int:
        """Count total tokens in a list of messages.

        Args:
            messages: List of chat messages.

        Returns:
            Total token count.
        """
        total = 0
        for msg in messages:
            total += self.count_message_tokens(msg)

        # Add priming tokens (assistant response start)
        total += 3

        return total

    @property
    def is_accurate(self) -> bool:
        """Check if token counting is accurate (tiktoken) or estimated.

        Returns:
            True if using tiktoken, False if estimating.
        """
        return self._encoding is not None


def count_tokens(text: str, provider: str = "default", model: str = "") -> int:
    """Convenience function to count tokens.

    Args:
        text: Text to count tokens for.
        provider: Provider name.
        model: Model name.

    Returns:
        Token count.
    """
    counter = TokenCounter(provider=provider, model=model)
    return counter.count_tokens(text)


def estimate_tokens(text: str) -> int:
    """Simple token estimation (4 chars per token).

    This maintains backward compatibility with the existing estimate_tokens
    function in base.py.

    Args:
        text: Text to estimate.

    Returns:
        Estimated token count.
    """
    return len(text) // 4
