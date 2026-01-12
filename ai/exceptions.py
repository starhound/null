"""Standardized exceptions for AI operations."""

from __future__ import annotations


class AIError(Exception):
    """Base class for all AI provider exceptions."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class AIProviderError(AIError):
    """Generic error from the AI provider."""


class AuthenticationError(AIError):
    """Authentication failed (invalid API key, expired token)."""


class RateLimitError(AIError):
    """Rate limit exceeded."""


class ContextLengthExceededError(AIError):
    """Prompt exceeds the model's context window."""


class APIConnectionError(AIError):
    """Network connection failed."""


class InvalidRequestError(AIError):
    """The request was malformed or invalid."""
