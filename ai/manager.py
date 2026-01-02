"""AI Manager - handles multiple AI providers."""

from typing import Dict, List, Optional, Any
from config import Config
from .base import LLMProvider
from .factory import AIFactory


class AIManager:
    """Manages multiple AI provider instances."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        # Pre-load the active provider
        self.get_active_provider()

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        """Get or create a provider instance."""
        if not name:
            return None

        if name in self._providers:
            return self._providers[name]

        # Try to initialize it
        try:
            # Construct config for this provider
            # The config structure is "ai.<provider>.key"
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
            return provider
        except Exception as e:
            # If initialization fails (e.g. missing API key), return None
            # print(f"Failed to init {name}: {e}")
            return None

    def get_active_provider(self) -> Optional[LLMProvider]:
        """Get the currently selected main provider."""
        provider_name = Config.get("ai.provider")
        return self.get_provider(provider_name)

    def get_autocomplete_provider(self) -> Optional[LLMProvider]:
        """Get the provider configured for autocomplete (or default to active)."""
        # check specific override first
        # override_provider = Config.get("ai.autocomplete.provider") # Todo in config
        # For now, we will add this logic later when we do autocomplete config.
        # Fallback to active for now or separate config
        
        # Check if there is an explicit provider set for autocomplete
        ac_provider_name = Config.get("ai.autocomplete.provider")
        if ac_provider_name:
            return self.get_provider(ac_provider_name)
            
        return self.get_active_provider()

    def list_available_providers(self) -> List[str]:
        """List connected/valid providers."""
        return list(self._providers.keys())

    async def list_all_models(self) -> Dict[str, List[str]]:
        """Fetch models from ALL configured providers."""
        results = {}

        # Get all known providers from factory
        all_types = AIFactory.list_providers()

        # Check which ones have enough config to be usable
        usable_providers = []
        for p_name in all_types:
            info = AIFactory.get_provider_info(p_name)

            # Check for API key if required
            if info.get("requires_api_key"):
                key = Config.get(f"ai.{p_name}.api_key")
                if not key:
                    continue

            # For local providers (ollama, lm_studio), always try them
            # since they have sensible defaults
            usable_providers.append(p_name)

        # Initialize providers
        for p_name in usable_providers:
            try:
                self.get_provider(p_name)
            except Exception:
                pass

        # Also ensure the currently active provider is included
        active_provider = Config.get("ai.provider")
        if active_provider and active_provider not in self._providers:
            try:
                self.get_provider(active_provider)
            except Exception:
                pass

        # Fetch models from all instantiated providers
        for name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                if models:
                    results[name] = models
            except Exception:
                # Provider failed to list models - skip it
                pass

        return results

