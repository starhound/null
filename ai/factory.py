"""AI provider factory."""

from typing import Dict, Any
from .base import LLMProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatibleProvider
from .azure import AzureProvider
from .bedrock import BedrockProvider
from .anthropic import AnthropicProvider
from .google_vertex import GoogleVertexProvider
from .cohere import CohereProvider


class AIFactory:
    """Factory for creating AI provider instances."""

    # Provider metadata for UI display
    PROVIDERS = {
        "ollama": {
            "name": "Ollama",
            "description": "Local models via Ollama",
            "requires_api_key": False,
            "requires_endpoint": True,
        },
        "openai": {
            "name": "OpenAI",
            "description": "GPT-4, GPT-3.5, etc.",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "anthropic": {
            "name": "Anthropic",
            "description": "Claude 3.5, Claude 3, etc.",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "google": {
            "name": "Google AI",
            "description": "Gemini 1.5, Gemini 2.0",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "azure": {
            "name": "Azure OpenAI",
            "description": "OpenAI models via Azure",
            "requires_api_key": True,
            "requires_endpoint": True,
        },
        "bedrock": {
            "name": "AWS Bedrock",
            "description": "Claude, Titan, etc. via AWS",
            "requires_api_key": False,
            "requires_endpoint": False,
        },
        "groq": {
            "name": "Groq",
            "description": "Fast inference (Llama, Mixtral)",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "mistral": {
            "name": "Mistral AI",
            "description": "Mistral, Mixtral, Codestral",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "together": {
            "name": "Together AI",
            "description": "Open models (Llama, Qwen, etc.)",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "nvidia": {
            "name": "NVIDIA NIM",
            "description": "NVIDIA AI Foundation models",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "cohere": {
            "name": "Cohere",
            "description": "Command R, Command R+",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "xai": {
            "name": "xAI",
            "description": "Grok models",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "lm_studio": {
            "name": "LM Studio",
            "description": "Local models via LM Studio",
            "requires_api_key": False,
            "requires_endpoint": True,
        },
        "openrouter": {
            "name": "OpenRouter",
            "description": "Unified API for many models",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "fireworks": {
            "name": "Fireworks AI",
            "description": "Fast open model inference",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "deepseek": {
            "name": "DeepSeek",
            "description": "DeepSeek Coder & Chat",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
    }

    @staticmethod
    def get_provider(config: Dict[str, Any]) -> LLMProvider:
        """Create a provider instance from config."""
        provider_name = config.get("provider", "ollama")

        # =====================================================================
        # Local / Self-hosted
        # =====================================================================
        if provider_name == "ollama":
            return OllamaProvider(
                endpoint=config.get("endpoint", "http://localhost:11434"),
                model=config.get("model", "llama3.2")
            )

        elif provider_name == "lm_studio":
            return OpenAICompatibleProvider(
                api_key="lm-studio",
                base_url=config.get("endpoint", "http://localhost:1234/v1"),
                model=config.get("model", "local-model")
            )

        # =====================================================================
        # Major Cloud Providers
        # =====================================================================
        elif provider_name == "openai":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "gpt-4o-mini")
            )

        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "claude-3-5-sonnet-20241022")
            )

        elif provider_name == "google":
            return GoogleVertexProvider(
                project_id=config.get("project_id", ""),
                location=config.get("location", "us-central1"),
                api_key=config.get("api_key", ""),
                model=config.get("model", "gemini-1.5-flash")
            )

        elif provider_name == "azure":
            return AzureProvider(
                endpoint=config.get("endpoint", ""),
                api_key=config.get("api_key", ""),
                api_version=config.get("api_version", "2024-02-01"),
                model=config.get("model", "gpt-4o")
            )

        elif provider_name == "bedrock":
            return BedrockProvider(
                region_name=config.get("region", "us-east-1"),
                model=config.get("model", "anthropic.claude-3-sonnet-20240229-v1:0")
            )

        # =====================================================================
        # OpenAI-Compatible API Providers
        # =====================================================================
        elif provider_name == "groq":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.groq.com/openai/v1",
                model=config.get("model", "llama-3.3-70b-versatile")
            )

        elif provider_name == "mistral":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.mistral.ai/v1",
                model=config.get("model", "mistral-large-latest")
            )

        elif provider_name == "together":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.together.xyz/v1",
                model=config.get("model", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
            )

        elif provider_name == "nvidia":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://integrate.api.nvidia.com/v1",
                model=config.get("model", "meta/llama-3.1-405b-instruct")
            )

        elif provider_name == "xai":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.x.ai/v1",
                model=config.get("model", "grok-beta")
            )

        elif provider_name == "openrouter":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://openrouter.ai/api/v1",
                model=config.get("model", "openai/gpt-4o-mini")
            )

        elif provider_name == "fireworks":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.fireworks.ai/inference/v1",
                model=config.get("model", "accounts/fireworks/models/llama-v3p3-70b-instruct")
            )

        elif provider_name == "deepseek":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.deepseek.com/v1",
                model=config.get("model", "deepseek-chat")
            )

        # =====================================================================
        # Native SDK Providers
        # =====================================================================
        elif provider_name == "cohere":
            return CohereProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "command-r-plus")
            )

        raise ValueError(f"Unknown provider: {provider_name}")

    @classmethod
    def list_providers(cls) -> list:
        """Return list of provider keys."""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def get_provider_info(cls, provider: str) -> dict:
        """Get metadata for a provider."""
        return cls.PROVIDERS.get(provider, {})
