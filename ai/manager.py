"""AI Manager - handles multiple AI providers."""

import asyncio
from collections.abc import AsyncGenerator

from config import Config

from .base import LLMProvider
from .factory import AIFactory


class AIManager:
    """Manages multiple AI provider instances."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        # Pre-load the active provider
        self.get_active_provider()

    def get_provider(self, name: str) -> LLMProvider | None:
        """Get or create a provider instance."""
        if not name:
            return None

        if name in self._providers:
            return self._providers[name]

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
        For local providers (ollama, lm_studio): requires explicit endpoint config or being active
        For AWS (bedrock): only if active (uses AWS credential chain)
        """
        usable = []
        all_types = AIFactory.list_providers()
        active = Config.get("ai.provider")

        # Local providers that don't need API keys
        local_providers = {"ollama", "lm_studio"}
        # AWS provider that uses credential chain
        aws_providers = {"bedrock"}

        for p_name in all_types:
            info = AIFactory.get_provider_info(p_name)

            # Cloud providers: require API key
            if info.get("requires_api_key"):
                key = Config.get(f"ai.{p_name}.api_key")
                if not key:
                    continue
                usable.append(p_name)

            # Local providers: only include if explicitly configured or active
            elif p_name in local_providers:
                endpoint = Config.get(f"ai.{p_name}.endpoint")
                if endpoint or p_name == active:
                    usable.append(p_name)

            # AWS providers: only include if active (avoids slow credential checks)
            elif p_name in aws_providers:
                if p_name == active:
                    usable.append(p_name)

        # Ensure active provider is always included
        if active and active not in usable:
            usable.append(active)

        return usable

    async def _fetch_models_for_provider(
        self, provider_name: str
    ) -> tuple[str, list[str], str | None]:
        """Fetch models for a single provider.

        Returns: (provider_name, models_list, error_message)
        """
        try:
            # Get or create provider (cached after first call)
            provider = self.get_provider(provider_name)

            if not provider:
                return (provider_name, [], "Failed to initialize")

            # Fetch models with timeout
            models = await asyncio.wait_for(
                provider.list_models(),
                timeout=10.0,  # 10 second timeout per provider
            )

            # Auto-update model name for local providers using default
            local_providers = {"lm_studio", "ollama"}
            if provider_name in local_providers and models:
                current_model = provider.model
                # If using a default/placeholder model name, update to first available
                if current_model in ("local-model", "llama3.2", ""):
                    provider.model = models[0]
                    # Also save to config so it persists
                    Config.set(f"ai.{provider_name}.model", models[0])

            return (provider_name, models or [], None)

        except TimeoutError:
            return (provider_name, [], "Timeout")
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 50:
                error_msg = error_msg[:50] + "..."
            return (provider_name, [], error_msg)

    async def list_all_models(self) -> dict[str, list[str]]:
        """Fetch models from ALL configured providers in parallel."""
        usable_providers = self.get_usable_providers()

        if not usable_providers:
            return {}

        # Fetch all providers in parallel
        tasks = [self._fetch_models_for_provider(p_name) for p_name in usable_providers]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        models_by_provider = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            provider_name, models, error = result
            if models:  # Only include providers with models
                models_by_provider[provider_name] = models

        return models_by_provider

    async def list_all_models_streaming(
        self,
    ) -> AsyncGenerator[tuple[str, list[str], str | None, int, int], None]:
        """Fetch models from providers, yielding results as they complete.

        Yields: (provider_name, models, error, completed_count, total_count)
        """
        usable_providers = self.get_usable_providers()
        total = len(usable_providers)

        if total == 0:
            return

        # Create tasks
        tasks = {
            asyncio.create_task(self._fetch_models_for_provider(p_name)): p_name
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
