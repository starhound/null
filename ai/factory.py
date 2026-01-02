from typing import Dict, Any
from .base import LLMProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatibleProvider
from .azure import AzureProvider
from .bedrock import BedrockProvider

class AIFactory:
    @staticmethod
    def get_provider(config: Dict[str, Any]) -> LLMProvider:
        provider_name = config.get("provider", "ollama")
        
        if provider_name == "ollama":
            return OllamaProvider(
                endpoint=config.get("endpoint", "http://localhost:11434"),
                model=config.get("model", "llama3")
            )
        
        elif provider_name == "openai":
            return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "gpt-3.5-turbo")
            )
            
        elif provider_name == "lm_studio":
            return OpenAICompatibleProvider(
                api_key="lm-studio", # Usually ignored
                base_url=config.get("endpoint", "http://localhost:1234/v1"),
                model=config.get("model", "local-model")
            )
            
        elif provider_name == "xai":
             return OpenAICompatibleProvider(
                api_key=config.get("api_key", ""),
                base_url="https://api.x.ai/v1",
                model=config.get("model", "grok-beta")
            )

        elif provider_name == "azure":
            return AzureProvider(
                endpoint=config.get("endpoint", ""),
                api_key=config.get("api_key", ""),
                api_version=config.get("api_version", "2023-05-15"),
                model=config.get("model", "gpt-35-turbo")
            )
            
        elif provider_name == "bedrock":
            return BedrockProvider(
                region_name=config.get("region", "us-east-1"),
                model=config.get("model", "anthropic.claude-v2")
            )
        
        raise ValueError(f"Unknown provider: {provider_name}")
