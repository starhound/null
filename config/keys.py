"""Configuration key definitions and sensitive key registry."""

# Keys that should be encrypted in storage
SENSITIVE_KEYS = {
    "ai.openai.api_key",
    "ai.azure.api_key",
    "ai.xai.api_key",
    "ai.bedrock.secret_key",
    "ai.lm_studio.api_key",
    "ai.anthropic.api_key",
    "ai.google.api_key",
    "ai.cohere.api_key",
    "ai.together.api_key",
    "ai.groq.api_key",
    "ai.mistral.api_key",
    "ai.deepseek.api_key",
    "ai.openrouter.api_key",
    "ai.fireworks.api_key",
    "ai.perplexity.api_key",
    "ai.nvidia.api_key",
    "ai.huggingface.api_key",
    "ai.cloudflare.api_key",
}


def is_sensitive_key(key: str) -> bool:
    """Check if a configuration key should be encrypted.

    Args:
        key: The configuration key to check.

    Returns:
        True if the key should be encrypted, False otherwise.
    """
    if key in SENSITIVE_KEYS:
        return True
    # Pattern matching for any key ending with api_key or secret_key
    return key.endswith(".api_key") or key.endswith(".secret_key")


# Common key patterns for type-safe access
class ConfigKeys:
    """Constants for commonly used configuration keys."""

    THEME = "theme"
    SHELL = "shell"
    DISCLAIMER_ACCEPTED = "disclaimer_accepted"

    # AI settings
    AI_PROVIDER = "ai.provider"
    AI_AGENT_MODE = "ai.agent_mode"
    AI_ACTIVE_PROMPT = "ai.active_prompt"

    @staticmethod
    def ai_model(provider: str) -> str:
        """Get the model key for a provider."""
        return f"ai.{provider}.model"

    @staticmethod
    def ai_api_key(provider: str) -> str:
        """Get the API key for a provider."""
        return f"ai.{provider}.api_key"

    @staticmethod
    def ai_endpoint(provider: str) -> str:
        """Get the endpoint key for a provider."""
        return f"ai.{provider}.endpoint"

    @staticmethod
    def ai_region(provider: str) -> str:
        """Get the region key for a provider."""
        return f"ai.{provider}.region"
