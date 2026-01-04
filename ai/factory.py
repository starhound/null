"""AI provider factory."""

from typing import Any, ClassVar

from .anthropic import AnthropicProvider
from .azure import AzureProvider
from .base import LLMProvider
from .bedrock import BedrockProvider
from .cohere import CohereProvider
from .google_vertex import GoogleVertexProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatibleProvider


class AIFactory:
    """Factory for creating AI provider instances."""

    # Provider metadata for UI display
    PROVIDERS: ClassVar[dict[str, dict[str, Any]]] = {
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
        "perplexity": {
            "name": "Perplexity",
            "description": "Online LLMs (Sonar)",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "custom": {
            "name": "Custom HTTP",
            "description": "Any OpenAI-compatible API",
            "requires_api_key": True,
            "requires_endpoint": True,
        },
        "huggingface": {
            "name": "HuggingFace",
            "description": "Inference API (TGI/v1)",
            "requires_api_key": True,
            "requires_endpoint": False,
        },
        "llama_cpp": {
            "name": "Llama.cpp Server",
            "description": "Local Llama.cpp (OpenAI format)",
            "requires_api_key": False,
            "requires_endpoint": True,
        },
        "cloudflare": {
            "name": "Cloudflare Workers AI",
            "description": "Workers AI (Llama, etc.)",
            "requires_api_key": True,
            "requires_endpoint": True,
        },
    }

    @staticmethod
    def _get_or_default(config: dict[str, Any], key: str, default: str) -> str:
        """Get config value, using default if missing or empty."""
        value = config.get(key)
        return value if value else default

    @staticmethod
    def get_provider(config: dict[str, Any]) -> LLMProvider:
        """Create a provider instance from config."""
        provider_name = config.get("provider", "ollama")

        def get(k: str, d: Any) -> Any:
            return AIFactory._get_or_default(config, k, d)

        # =====================================================================
        # Local / Self-hosted
        # =====================================================================
        if provider_name == "ollama":
            return OllamaProvider(
                endpoint=get("endpoint", "http://localhost:11434"),
                model=get("model", "llama3.2"),
            )

        elif provider_name == "lm_studio":
            endpoint = get("endpoint", "http://localhost:1234/v1")
            # Ensure /v1 suffix for OpenAI-compatible API
            if endpoint and not endpoint.rstrip("/").endswith("/v1"):
                endpoint = endpoint.rstrip("/") + "/v1"
            return OpenAICompatibleProvider(
                api_key="lm-studio",
                base_url=endpoint,
                model=get("model", "local-model"),
            )

        # =====================================================================
        # Major Cloud Providers
        # =====================================================================
        elif provider_name == "openai":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""), model=get("model", "gpt-4o-mini")
            )

        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=config.get("api_key", ""),
                model=get("model", "claude-3-5-sonnet-20241022"),
            )

        elif provider_name == "google":
            return GoogleVertexProvider(
                project_id=config.get("project_id", ""),
                location=get("location", "us-central1"),
                api_key=config.get("api_key", ""),
                model=get("model", "gemini-2.0-flash"),
            )

        elif provider_name == "azure":
            return AzureProvider(
                endpoint=config.get("endpoint", ""),
                api_key=config.get("api_key", ""),
                api_version=get("api_version", "2024-02-01"),
                model=get("model", "gpt-4o"),
            )

        elif provider_name == "bedrock":
            return BedrockProvider(
                region_name=get("region", "us-east-1"),
                model=get("model", "anthropic.claude-3-sonnet-20240229-v1:0"),
            )

        # =====================================================================
        # OpenAI-Compatible API Providers
        # =====================================================================
        elif provider_name == "groq":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.groq.com/openai/v1",
                model=get("model", "llama-3.3-70b-versatile"),
            )

        elif provider_name == "mistral":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.mistral.ai/v1",
                model=get("model", "mistral-large-latest"),
            )

        elif provider_name == "together":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.together.xyz/v1",
                model=get("model", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            )

        elif provider_name == "nvidia":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://integrate.api.nvidia.com/v1",
                model=get("model", "meta/llama-3.1-405b-instruct"),
            )

        elif provider_name == "xai":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.x.ai/v1",
                model=get("model", "grok-beta"),
            )

        elif provider_name == "openrouter":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://openrouter.ai/api/v1",
                model=get("model", "openai/gpt-4o-mini"),
            )

        elif provider_name == "fireworks":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.fireworks.ai/inference/v1",
                model=get("model", "accounts/fireworks/models/llama-v3p3-70b-instruct"),
            )

        elif provider_name == "deepseek":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.deepseek.com/v1",
                model=get("model", "deepseek-chat"),
            )

        elif provider_name == "perplexity":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.perplexity.ai",
                model=get("model", "llama-3.1-sonar-large-128k-online"),
            )

        elif provider_name == "custom":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url=get("endpoint", "http://localhost:8000/v1"),
                model=get("model", "custom-model"),
            )

        elif provider_name == "cloudflare":
            account_id = config.get("account_id", "")
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
                model=get("model", "@cf/meta/llama-3-8b-instruct"),
            )

        elif provider_name == "huggingface":
            model_id = get("model", "meta-llama/Meta-Llama-3-8B-Instruct")
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url=f"https://api-inference.huggingface.co/models/{model_id}/v1",
                model=model_id,
            )

        elif provider_name == "llama_cpp":
            endpoint = get("endpoint", "http://localhost:8000/v1")
            # Ensure /v1 suffix for OpenAI-compatible API
            if endpoint and not endpoint.rstrip("/").endswith("/v1"):
                endpoint = endpoint.rstrip("/") + "/v1"
            return OpenAICompatibleProvider(
                api_key="token-not-needed",
                base_url=endpoint,
                model=get("model", "default"),
            )

        # =====================================================================
        # Native SDK Providers
        # =====================================================================
        elif provider_name == "cohere":
            return CohereProvider(
                api_key=config.get("api_key", ""), model=get("model", "command-r-plus")
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
