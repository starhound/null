from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator, List, Optional, TypedDict


class Message(TypedDict):
    """Chat message format."""
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class ModelInfo:
    """Model information including context limits."""
    name: str
    max_tokens: int = 4096  # Default fallback
    context_window: int = 4096  # Default fallback


# Common model context sizes (approximate)
KNOWN_MODEL_CONTEXTS = {
    # OpenAI
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-3.5-turbo": 16385,
    # Anthropic
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    # Ollama common models
    "llama2": 4096,
    "llama3": 8192,
    "llama3.1": 128000,
    "llama3.2": 128000,
    "mistral": 8192,
    "mixtral": 32768,
    "codellama": 16384,
    "deepseek-coder": 16384,
    "qwen2.5-coder": 32768,
    "phi3": 128000,
    "gemma2": 8192,
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token average)."""
    return len(text) // 4


def get_model_context_size(model_name: str) -> int:
    """Get context size for a model, with fallback to default."""
    model_lower = model_name.lower()

    # Check exact match first
    if model_lower in KNOWN_MODEL_CONTEXTS:
        return KNOWN_MODEL_CONTEXTS[model_lower]

    # Check partial matches (e.g., "llama3.1:8b" matches "llama3.1")
    for known, size in KNOWN_MODEL_CONTEXTS.items():
        if model_lower.startswith(known):
            return size

    # Default fallback
    return 4096


class LLMProvider(ABC):
    model: str = ""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from the LLM.

        Args:
            prompt: Current user prompt
            messages: Conversation history as message array
            system_prompt: System prompt (always separate from messages)
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Return a list of available model names."""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Check if the provider is reachable."""
        pass

    def get_model_info(self) -> ModelInfo:
        """Get model information including context limits."""
        context_size = get_model_context_size(self.model)
        return ModelInfo(
            name=self.model,
            max_tokens=context_size,
            context_window=context_size
        )
