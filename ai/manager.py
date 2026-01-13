"""AI Manager - handles multiple AI providers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from config import Config

from .base import HealthStatus, LLMProvider, ProviderHealth
from .factory import AIFactory
from .model_cache import ModelCache

if TYPE_CHECKING:
    from .fallback import FallbackConfig, ProviderFallback


class AIManager:
    """Manages multiple AI provider instances."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._health_cache: dict[str, ProviderHealth] = {}
        self._model_cache = ModelCache()
        self._fallback: ProviderFallback | None = None
        self.get_active_provider()

    async def close_all(self) -> None:
        for provider in self._providers.values():
            try:
                await provider.close()
            except Exception:
                pass
        self._providers.clear()

    def get_provider(
        self, name: str, force_refresh: bool = False
    ) -> LLMProvider | None:
        """Get or create a provider instance.

        Args:
            name: Provider name
            force_refresh: If True, recreate the provider even if cached
        """
        if not name:
            return None

        # Check if we should update the cached provider's model
        if name in self._providers and not force_refresh:
            cached = self._providers[name]
            # Check if model in config differs from cached model
            config_model = Config.get(f"ai.{name}.model")
            if config_model and config_model != cached.model:
                # Update the model on the cached provider
                cached.model = config_model
            return cached

        # Try to initialize it
        try:
            provider_config = {
                "provider": name,
                "api_key": Config.get(f"ai.{name}.api_key"),
                "endpoint": Config.get(f"ai.{name}.endpoint"),
                "region": Config.get(f"ai.{name}.region"),
                "model": Config.get(f"ai.{name}.model"),
                "api_version": Config.get(f"ai.{name}.api_version"),
                "project_id": Config.get(f"ai.{name}.project_id"),
                "location": Config.get(f"ai.{name}.location"),
            }

            provider = AIFactory.get_provider(provider_config)
            self._providers[name] = provider

            # Auto-detect model for local providers if using default model
            local_providers = {"lm_studio", "ollama"}
            if name in local_providers and provider.model in (
                "local-model",
                "llama3.2",
            ):
                # Try to detect loaded model synchronously on first use
                # This will be updated async when list_all_models is called
                pass

            return provider
        except Exception:
            return None

    def get_active_provider(self) -> LLMProvider | None:
        """Get the currently selected main provider."""
        provider_name = Config.get("ai.provider")
        return self.get_provider(provider_name)

    def get_autocomplete_provider(self) -> LLMProvider | None:
        """Get the provider configured for autocomplete."""
        ac_provider_name = Config.get("ai.autocomplete.provider")
        if ac_provider_name:
            return self.get_provider(ac_provider_name)
        return self.get_active_provider()

    def list_available_providers(self) -> list[str]:
        """List connected/valid providers."""
        return list(self._providers.keys())

    def get_usable_providers(self) -> list[str]:
        """Get list of providers that have required config.

        For cloud providers: requires API key
        For local/endpoint providers: requires explicit endpoint config or being active
        For OAuth providers: only if active (token validation happens at use time)
        For AWS (bedrock): only if active (uses AWS credential chain)
        """
        usable = []
        all_types = AIFactory.list_providers()
        active = Config.get("ai.provider")

        for p_name in all_types:
            info = AIFactory.get_provider_info(p_name)

            # Cloud providers: require API key
            if info.get("requires_api_key"):
                key = Config.get(f"ai.{p_name}.api_key")
                if key:
                    usable.append(p_name)

            # Endpoint-based local providers: require endpoint config or being active
            elif info.get("requires_endpoint") and not info.get("requires_api_key"):
                endpoint = Config.get(f"ai.{p_name}.endpoint")
                if endpoint or p_name == active:
                    usable.append(p_name)

            # OAuth providers: only include if active (avoids unnecessary token checks)
            elif info.get("requires_oauth"):
                if p_name == active:
                    usable.append(p_name)

            # AWS/GCP providers without API key: only if active
            elif p_name in {"bedrock", "google_vertex"}:
                if p_name == active:
                    usable.append(p_name)

        # Ensure active provider is always included (if set)
        if active and active not in usable:
            usable.append(active)

        return usable

    async def _fetch_models_for_provider(
        self, provider_name: str, skip_cache: bool = False
    ) -> tuple[str, list[str], str | None]:
        """Fetch models for a single provider.

        Returns: (provider_name, models_list, error_message)
        """
        if not skip_cache:
            cached = await self._model_cache.get_models(provider_name)
            if cached is not None:
                return (provider_name, cached, None)

        try:
            provider = self.get_provider(provider_name)

            if not provider:
                return (provider_name, [], "Failed to initialize")

            models = await asyncio.wait_for(
                provider.list_models(),
                timeout=10.0,
            )

            local_providers = {"lm_studio", "ollama"}
            if provider_name in local_providers and models:
                current_model = provider.model
                if current_model in ("local-model", "llama3.2", ""):
                    provider.model = models[0]
                    Config.set(f"ai.{provider_name}.model", models[0])

            if models:
                await self._model_cache.set_models(provider_name, models)

            return (provider_name, models or [], None)

        except TimeoutError:
            return (provider_name, [], "Timeout")
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 50:
                error_msg = error_msg[:50] + "..."
            return (provider_name, [], error_msg)

    async def list_all_models(self, skip_cache: bool = False) -> dict[str, list[str]]:
        """Fetch models from ALL configured providers in parallel."""
        usable_providers = self.get_usable_providers()

        if not usable_providers:
            return {}

        tasks = [
            self._fetch_models_for_provider(p_name, skip_cache=skip_cache)
            for p_name in usable_providers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        models_by_provider: dict[str, list[str]] = {}
        for result in results:
            if isinstance(result, BaseException):
                continue
            # result is now tuple[str, list[str], str | None]
            provider_name, models, _error = result
            if models:  # Only include providers with models
                models_by_provider[provider_name] = models

        return models_by_provider

    def get_provider_health(self, name: str) -> ProviderHealth:
        """Get cached health status for a provider."""
        return self._health_cache.get(name, ProviderHealth())

    def get_active_provider_health(self) -> ProviderHealth:
        """Get health status for the currently active provider."""
        provider_name = Config.get("ai.provider")
        if provider_name:
            return self.get_provider_health(provider_name)
        return ProviderHealth()

    async def check_provider_health(self, name: str) -> ProviderHealth:
        """Check and cache health for a specific provider."""
        self._health_cache[name] = ProviderHealth(status=HealthStatus.CHECKING)

        provider = self.get_provider(name)
        if not provider:
            health = ProviderHealth(
                status=HealthStatus.ERROR,
                error_message="Provider not initialized",
            )
            self._health_cache[name] = health
            return health

        health = await provider.check_health()
        self._health_cache[name] = health
        return health

    async def check_all_health(self) -> dict[str, ProviderHealth]:
        """Check health for all usable providers in parallel."""
        usable = self.get_usable_providers()
        if not usable:
            return {}

        async def check_one(name: str) -> tuple[str, ProviderHealth]:
            health = await self.check_provider_health(name)
            return (name, health)

        tasks = [check_one(p) for p in usable]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_map: dict[str, ProviderHealth] = {}
        for result in results:
            if isinstance(result, tuple):
                name, health = result
                health_map[name] = health

        return health_map

    async def invalidate_model_cache(self, provider_id: str) -> bool:
        """Invalidate cached models for a provider."""
        return await self._model_cache.invalidate(provider_id)

    async def clear_model_cache(self) -> int:
        """Clear all cached model lists."""
        return await self._model_cache.clear_all()

    def get_fallback_handler(
        self, config: FallbackConfig | None = None
    ) -> ProviderFallback:
        """Get or create the provider fallback handler."""
        if self._fallback is None:
            from .fallback import ProviderFallback, get_fallback_config_from_settings

            if config is None:
                config = get_fallback_config_from_settings()
            self._fallback = ProviderFallback(self, config)
        elif config is not None:
            self._fallback.config = config
        return self._fallback

    async def list_all_models_streaming(
        self, skip_cache: bool = False
    ) -> AsyncGenerator[tuple[str, list[str], str | None, int, int], None]:
        """Fetch models from providers, yielding results as they complete.

        Yields: (provider_name, models, error, completed_count, total_count)
        """
        usable_providers = self.get_usable_providers()
        total = len(usable_providers)

        if total == 0:
            return

        tasks = {
            asyncio.create_task(
                self._fetch_models_for_provider(p_name, skip_cache=skip_cache)
            ): p_name
            for p_name in usable_providers
        }

        completed = 0
        pending = set(tasks.keys())

        while pending:
            # Wait for at least one task to complete
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                completed += 1
                try:
                    provider_name, models, error = task.result()
                    yield (provider_name, models, error, completed, total)
                except Exception as e:
                    # Task raised exception
                    provider_name = tasks.get(task, "unknown")
                    yield (provider_name, [], str(e), completed, total)
