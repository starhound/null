"""Provider fallback system for automatic retry on failure."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import LLMProvider, Message, StreamChunk

if TYPE_CHECKING:
    from .manager import AIManager

logger = logging.getLogger(__name__)


@dataclass
class FallbackEvent:
    """Records a fallback event for logging/metrics."""

    from_provider: str
    to_provider: str
    error: str
    attempt: int


@dataclass
class FallbackConfig:
    """Configuration for provider fallback behavior."""

    fallback_providers: list[str] = field(default_factory=list)
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 30.0
    backoff_multiplier: float = 2.0
    enabled: bool = True


class ProviderFallback:
    """Manages automatic provider fallback on failures.

    Provides automatic retry with exponential backoff and fallback to
    alternative providers when the primary provider fails.
    """

    def __init__(
        self,
        ai_manager: AIManager,
        config: FallbackConfig | None = None,
    ):
        self._ai_manager = ai_manager
        self._config = config or FallbackConfig()
        self._fallback_events: list[FallbackEvent] = []

    @property
    def config(self) -> FallbackConfig:
        """Get fallback configuration."""
        return self._config

    @config.setter
    def config(self, value: FallbackConfig) -> None:
        """Set fallback configuration."""
        self._config = value

    @property
    def fallback_events(self) -> list[FallbackEvent]:
        """Get list of recorded fallback events."""
        return self._fallback_events.copy()

    def clear_events(self) -> None:
        """Clear recorded fallback events."""
        self._fallback_events.clear()

    def _get_provider_chain(self, primary: str) -> list[str]:
        """Build the ordered list of providers to try.

        Args:
            primary: The primary provider name

        Returns:
            List of provider names to try in order
        """
        chain = [primary]
        for fallback in self._config.fallback_providers:
            if fallback != primary and fallback not in chain:
                chain.append(fallback)
        return chain

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay for given attempt number.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self._config.initial_backoff * (
            self._config.backoff_multiplier**attempt
        )
        return min(delay, self._config.max_backoff)

    def _log_fallback(
        self,
        from_provider: str,
        to_provider: str,
        error: str,
        attempt: int,
    ) -> None:
        """Log and record a fallback event.

        Args:
            from_provider: Provider that failed
            to_provider: Provider being tried next
            error: Error message from failed provider
            attempt: Current attempt number
        """
        event = FallbackEvent(
            from_provider=from_provider,
            to_provider=to_provider,
            error=error,
            attempt=attempt,
        )
        self._fallback_events.append(event)
        logger.warning(
            "Provider fallback: %s -> %s (attempt %d): %s",
            from_provider,
            to_provider,
            attempt,
            error,
        )

    async def generate_with_fallback(
        self,
        messages: list[Message],
        system_prompt: str = "",
        primary_provider: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate response with automatic fallback on failure.

        Args:
            messages: Conversation messages
            system_prompt: System prompt to use
            primary_provider: Primary provider name (uses active if not specified)
            **kwargs: Additional arguments passed to provider

        Yields:
            StreamChunk objects from the successful provider

        Raises:
            RuntimeError: If all providers fail
        """
        if not self._config.enabled:
            provider = self._ai_manager.get_active_provider()
            if provider:
                async for chunk in self._generate_from_provider(
                    provider, messages, system_prompt, **kwargs
                ):
                    yield chunk
                return
            raise RuntimeError("No active provider configured")

        if primary_provider:
            primary = primary_provider
        else:
            primary = self._get_active_provider_name()
            if not primary:
                raise RuntimeError("No active provider configured")

        provider_chain = self._get_provider_chain(primary)
        last_error: Exception | None = None

        for provider_idx, provider_name in enumerate(provider_chain):
            provider = self._ai_manager.get_provider(provider_name)
            if not provider:
                logger.debug("Provider %s not available, skipping", provider_name)
                continue

            for attempt in range(self._config.max_retries):
                try:
                    if attempt > 0:
                        delay = self._calculate_backoff(attempt - 1)
                        logger.debug(
                            "Retrying %s after %.1fs (attempt %d)",
                            provider_name,
                            delay,
                            attempt + 1,
                        )
                        await asyncio.sleep(delay)

                    async for chunk in self._generate_from_provider(
                        provider, messages, system_prompt, **kwargs
                    ):
                        yield chunk
                    return

                except Exception as e:
                    last_error = e
                    error_msg = str(e)

                    if attempt < self._config.max_retries - 1:
                        logger.warning(
                            "Provider %s failed (attempt %d/%d): %s",
                            provider_name,
                            attempt + 1,
                            self._config.max_retries,
                            error_msg,
                        )

            if provider_idx < len(provider_chain) - 1:
                next_provider = provider_chain[provider_idx + 1]
                self._log_fallback(
                    provider_name,
                    next_provider,
                    str(last_error),
                    provider_idx + 1,
                )

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def _generate_from_provider(
        self,
        provider: LLMProvider,
        messages: list[Message],
        system_prompt: str,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate response from a specific provider.

        This is an internal method that handles the actual generation.
        Override in subclasses for custom behavior.
        """
        tools = kwargs.pop("tools", None)

        if tools and hasattr(provider, "generate_with_tools"):
            async for chunk in provider.generate_with_tools(
                messages=messages,
                tools=tools,
                system_prompt=system_prompt,
                **kwargs,
            ):
                yield chunk
        elif hasattr(provider, "generate"):
            async for chunk in provider.generate(
                messages=messages,
                system_prompt=system_prompt,
                **kwargs,
            ):
                yield chunk
        else:
            raise NotImplementedError(
                f"Provider {provider.__class__.__name__} does not support generation"
            )

    def _get_active_provider_name(self) -> str | None:
        """Get the name of the currently active provider."""
        from config import Config

        return Config.get("ai.provider")

    async def check_provider_health(self, provider_name: str) -> bool:
        """Check if a specific provider is healthy.

        Args:
            provider_name: Name of the provider to check

        Returns:
            True if provider is healthy, False otherwise
        """
        provider = self._ai_manager.get_provider(provider_name)
        if not provider:
            return False

        try:
            return await provider.validate_connection()
        except Exception:
            return False

    async def get_healthy_providers(self) -> list[str]:
        """Get list of currently healthy providers.

        Returns:
            List of healthy provider names
        """
        healthy = []
        usable = self._ai_manager.get_usable_providers()

        for provider_name in usable:
            if await self.check_provider_health(provider_name):
                healthy.append(provider_name)

        return healthy


def get_fallback_config_from_settings() -> FallbackConfig:
    """Create FallbackConfig from application settings.

    Returns:
        FallbackConfig populated from settings
    """
    from config import Config

    fallback_providers = Config.get("ai.fallback_providers") or []
    max_retries = Config.get("ai.fallback_max_retries") or 3
    enabled = Config.get("ai.fallback_enabled")

    if enabled is None:
        enabled = True

    return FallbackConfig(
        fallback_providers=fallback_providers,
        max_retries=max_retries,
        enabled=enabled,
    )
