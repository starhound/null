from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, List, Optional, TypedDict, Any, Dict, Union


class Message(TypedDict, total=False):
    """Chat message format."""
    role: str  # "system", "user", "assistant", or "tool"
    content: str
    tool_calls: List[Dict[str, Any]]  # For assistant messages with tool calls
    tool_call_id: str  # For tool result messages


@dataclass
class ToolCallData:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class TokenUsage:
    """Token usage information from an API response."""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens
        )


@dataclass
class StreamChunk:
    """A chunk from the streaming response."""
    text: str = ""
    tool_calls: List[ToolCallData] = field(default_factory=list)
    is_complete: bool = False
    usage: Optional[TokenUsage] = None


# Model pricing per 1M tokens (input_cost, output_cost) in USD
# Updated January 2025
MODEL_PRICING: Dict[str, tuple] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    "o1-preview": (15.00, 60.00),
    # Anthropic Claude
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    # Google Gemini
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-flash-8b": (0.0375, 0.15),
    "gemini-2.0-flash": (0.10, 0.40),
    # Mistral
    "mistral-large": (2.00, 6.00),
    "mistral-medium": (2.70, 8.10),
    "mistral-small": (0.20, 0.60),
    "codestral": (0.20, 0.60),
    "mixtral-8x7b": (0.70, 0.70),
    "mixtral-8x22b": (2.00, 6.00),
    # xAI Grok
    "grok-2": (2.00, 10.00),
    "grok-beta": (5.00, 15.00),
    # DeepSeek
    "deepseek-chat": (0.14, 0.28),
    "deepseek-coder": (0.14, 0.28),
    "deepseek-reasoner": (0.55, 2.19),
    # Cohere
    "command-r-plus": (2.50, 10.00),
    "command-r": (0.50, 1.50),
    "command": (1.00, 2.00),
    # Groq (hosted, often free tier or very cheap)
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "gemma2-9b-it": (0.20, 0.20),
}


def get_model_pricing(model_name: str) -> tuple:
    """Get pricing for a model (input_cost, output_cost) per 1M tokens.

    Returns (0, 0) for unknown/local models.
    """
    model_lower = model_name.lower()

    # Check exact match first
    if model_lower in MODEL_PRICING:
        return MODEL_PRICING[model_lower]

    # Check partial matches (e.g., "claude-3-5-sonnet-20241022" matches "claude-3-5-sonnet")
    for known, pricing in MODEL_PRICING.items():
        if model_lower.startswith(known) or known in model_lower:
            return pricing

    # Local/unknown models - no cost
    return (0.0, 0.0)


def calculate_cost(usage: TokenUsage, model_name: str) -> float:
    """Calculate cost in USD for token usage."""
    input_price, output_price = get_model_pricing(model_name)
    input_cost = (usage.input_tokens / 1_000_000) * input_price
    output_cost = (usage.output_tokens / 1_000_000) * output_price
    return input_cost + output_cost


@dataclass
class ModelInfo:
    """Model information including context limits."""
    name: str
    max_tokens: int = 4096  # Default fallback
    context_window: int = 4096  # Default fallback
    supports_tools: bool = True  # Whether model supports tool calling


# Common model context sizes (approximate)
KNOWN_MODEL_CONTEXTS = {
    # OpenAI
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-3.5-turbo": 16385,
    "o1": 200000,
    "o1-mini": 128000,
    "o1-preview": 128000,
    # Anthropic
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    # Google Gemini
    "gemini-2.5-pro": 1000000,
    "gemini-2.5-flash": 1000000,
    "gemini-2.0-flash": 1000000,
    "gemini-2.0-flash-lite": 1000000,
    "gemini-1.5-pro": 2000000,
    "gemini-1.5-flash": 1000000,
    "gemini-1.5-flash-8b": 1000000,
    "gemini-1.0-pro": 32768,
    "gemini-flash": 1000000,
    "gemini-pro": 2000000,
    # Mistral
    "mistral-large": 128000,
    "mistral-medium": 32768,
    "mistral-small": 32768,
    "codestral": 32768,
    "mixtral-8x7b": 32768,
    "mixtral-8x22b": 65536,
    # Cohere
    "command-r-plus": 128000,
    "command-r": 128000,
    "command": 4096,
    # Groq (hosted models)
    "llama-3.3-70b-versatile": 128000,
    "llama-3.1-70b-versatile": 128000,
    "llama-3.1-8b-instant": 128000,
    "gemma2-9b-it": 8192,
    # xAI Grok
    "grok-beta": 131072,
    "grok-2": 131072,
    # DeepSeek
    "deepseek-chat": 64000,
    "deepseek-coder": 64000,
    "deepseek-reasoner": 64000,
    # Ollama / Local common models
    "llama2": 4096,
    "llama3": 8192,
    "llama3.1": 128000,
    "llama3.2": 128000,
    "llama3.3": 128000,
    "mistral": 8192,
    "mixtral": 32768,
    "codellama": 16384,
    "deepseek-coder": 16384,
    # Qwen models
    "qwen": 32768,
    "qwen2": 32768,
    "qwen2.5": 32768,
    "qwen2.5-coder": 32768,
    "qwen3": 40000,
    "qwen3-coder": 40000,
    # Other local models  
    "phi3": 128000,
    "phi4": 16384,
    "gemma2": 8192,
    "gemma": 8192,
    "starcoder": 8192,
    "codestral": 32768,
    "yi": 32768,
    "internlm": 32768,
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token average)."""
    return len(text) // 4


def get_model_context_size(model_name: str) -> int:
    """Get context size for a model, with fallback to default."""
    model_lower = model_name.lower()

    # Find the longest matching prefix (most specific match)
    best_match_len = 0
    best_size = 4096
    found = False

    for known, size in KNOWN_MODEL_CONTEXTS.items():
        # Check if model name starts with the known key OR if known key is contained in model name
        # (e.g. "my-qwen3-coder" contains "qwen3-coder")
        if known in model_lower:
            if len(known) > best_match_len:
                best_match_len = len(known)
                best_size = size
                found = True

    if found:
        return best_size

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
        """Stream text response from the LLM (legacy interface).

        Args:
            prompt: Current user prompt
            messages: Conversation history as message array
            system_prompt: System prompt (always separate from messages)
        """
        pass

    async def generate_with_tools(
        self,
        prompt: str,
        messages: List[Message],
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream response with tool calling support.

        Args:
            prompt: Current user prompt
            messages: Conversation history as message array
            tools: Available tools in OpenAI format
            system_prompt: System prompt (always separate from messages)

        Yields:
            StreamChunk with text and/or tool_calls
        """
        # Default implementation: fall back to regular generate (no tools)
        async for text in self.generate(prompt, messages, system_prompt):
            yield StreamChunk(text=text)

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

    def supports_tools(self) -> bool:
        """Check if this provider supports tool calling."""
        return False  # Override in subclasses that support tools
