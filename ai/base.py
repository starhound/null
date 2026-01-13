from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict


class HealthStatus(Enum):
    """Provider connection health status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CHECKING = "checking"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Health status for an AI provider."""

    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float | None = None  # Last API call latency in milliseconds
    last_check: datetime | None = None  # Timestamp of last health check
    error_message: str | None = None  # Error details if status is ERROR

    @property
    def is_healthy(self) -> bool:
        """Check if provider is in a healthy state."""
        return self.status == HealthStatus.CONNECTED

    @property
    def latency_category(self) -> str:
        """Categorize latency as fast/normal/slow for UI display."""
        if self.latency_ms is None:
            return "unknown"
        if self.latency_ms < 500:
            return "fast"  # Green - under 500ms
        if self.latency_ms < 2000:
            return "normal"  # Yellow - under 2s
        return "slow"  # Red - over 2s

    @property
    def latency_display(self) -> str:
        """Format latency for display (e.g., '150ms' or '2.1s')."""
        if self.latency_ms is None:
            return ""
        if self.latency_ms < 1000:
            return f"{int(self.latency_ms)}ms"
        return f"{self.latency_ms / 1000:.1f}s"


class Message(TypedDict, total=False):
    """Chat message format."""

    role: str  # "system", "user", "assistant", or "tool"
    content: str
    tool_calls: list[dict[str, Any]]  # For assistant messages with tool calls
    tool_call_id: str  # For tool result messages


@dataclass
class ToolCallData:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


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
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass
class StreamChunk:
    """A chunk from the streaming response."""

    text: str = ""
    tool_calls: list[ToolCallData] = field(default_factory=list)
    is_complete: bool = False
    usage: TokenUsage | None = None
    error: str | None = None


# Model pricing per 1M tokens (input_cost, output_cost) in USD
# Updated January 2025
MODEL_PRICING: dict[str, tuple] = {
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
    input_cost: float = (usage.input_tokens / 1_000_000) * input_price
    output_cost: float = (usage.output_tokens / 1_000_000) * output_price
    return input_cost + output_cost


@dataclass
class ModelInfo:
    """Model information including context limits."""

    name: str
    max_tokens: int = 4096  # Default fallback
    context_window: int = 4096  # Default fallback
    supports_tools: bool = True  # Whether model supports tool calling


KNOWN_MODEL_CONTEXTS = {
    # OpenAI GPT-4 family
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-preview": 128000,
    "gpt-4-1106-preview": 128000,
    "gpt-4-0125-preview": 128000,
    "gpt-4-vision-preview": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4o-2024": 128000,
    "gpt-4.1": 1000000,
    "gpt-4.1-mini": 1000000,
    "gpt-4.1-nano": 1000000,
    "gpt-4.5": 128000,
    "gpt-4.5-preview": 128000,
    # OpenAI GPT-3.5 family
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
    "gpt-3.5-turbo-instruct": 4096,
    # OpenAI o-series reasoning models
    "o1": 200000,
    "o1-mini": 128000,
    "o1-preview": 128000,
    "o1-pro": 200000,
    "o3": 200000,
    "o3-mini": 200000,
    "o3-pro": 200000,
    "o4-mini": 200000,
    # OpenAI Codex
    "code-davinci": 8001,
    "codex": 8001,
    # Anthropic Claude 4.x
    "claude-4": 200000,
    "claude-4-opus": 200000,
    "claude-4-sonnet": 200000,
    "claude-sonnet-4": 200000,
    "claude-opus-4": 200000,
    "claude-4.5": 200000,
    "claude-sonnet-4-5": 200000,
    "claude-sonnet-4.5": 200000,
    "claude-opus-4-5": 200000,
    "claude-opus-4.5": 200000,
    # Anthropic Claude 3.x
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3.5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    "claude-3.5-haiku": 200000,
    "claude-3-5-opus": 200000,
    "claude-3.5-opus": 200000,
    # Anthropic Claude 2.x / legacy
    "claude-2": 100000,
    "claude-2.1": 200000,
    "claude-2.0": 100000,
    "claude-instant": 100000,
    "claude-instant-1": 100000,
    "claude-instant-1.2": 100000,
    # Google Gemini 3.x
    "gemini-3": 1000000,
    "gemini-3-pro": 1000000,
    "gemini-3-flash": 1000000,
    "gemini-3-pro-preview": 1000000,
    "gemini-3-flash-preview": 1000000,
    # Google Gemini 2.x
    "gemini-2": 1000000,
    "gemini-2.5": 1000000,
    "gemini-2.5-pro": 1000000,
    "gemini-2.5-flash": 1000000,
    "gemini-2.5-flash-lite": 1000000,
    "gemini-2.0": 1000000,
    "gemini-2.0-pro": 1000000,
    "gemini-2.0-flash": 1000000,
    "gemini-2.0-flash-exp": 1000000,
    "gemini-2.0-flash-lite": 1000000,
    "gemini-2.0-flash-thinking": 1000000,
    # Google Gemini 1.x
    "gemini-1.5-pro": 2000000,
    "gemini-1.5-flash": 1000000,
    "gemini-1.5-flash-8b": 1000000,
    "gemini-1.0-pro": 32768,
    "gemini-1.0-ultra": 32768,
    "gemini-pro": 2000000,
    "gemini-flash": 1000000,
    "gemini-ultra": 32768,
    # Google PaLM / Bard legacy
    "palm-2": 8192,
    "text-bison": 8192,
    "chat-bison": 8192,
    # Mistral AI
    "mistral": 32768,
    "mistral-large": 128000,
    "mistral-large-latest": 128000,
    "mistral-large-2": 128000,
    "mistral-medium": 32768,
    "mistral-medium-latest": 32768,
    "mistral-small": 32768,
    "mistral-small-latest": 32768,
    "mistral-tiny": 32768,
    "mistral-nemo": 128000,
    "mistral-7b": 32768,
    "mistral-8x7b": 32768,
    "mistral-8x22b": 65536,
    "open-mistral-7b": 32768,
    "open-mixtral-8x7b": 32768,
    "open-mixtral-8x22b": 65536,
    "codestral": 32768,
    "codestral-latest": 32768,
    "codestral-mamba": 256000,
    "pixtral": 128000,
    "pixtral-12b": 128000,
    "pixtral-large": 128000,
    "ministral-3b": 128000,
    "ministral-8b": 128000,
    "mixtral": 32768,
    "mixtral-8x7b": 32768,
    "mixtral-8x22b": 65536,
    # Cohere
    "command-r-plus": 128000,
    "command-r-plus-08-2024": 128000,
    "command-r": 128000,
    "command-r-08-2024": 128000,
    "command": 4096,
    "command-light": 4096,
    "command-nightly": 128000,
    "c4ai-aya-23": 8192,
    "c4ai-aya-expanse": 128000,
    # Meta Llama 3.x
    "llama-3": 8192,
    "llama-3-8b": 8192,
    "llama-3-70b": 8192,
    "llama-3.1": 128000,
    "llama-3.1-8b": 128000,
    "llama-3.1-70b": 128000,
    "llama-3.1-405b": 128000,
    "llama-3.2": 128000,
    "llama-3.2-1b": 128000,
    "llama-3.2-3b": 128000,
    "llama-3.2-11b": 128000,
    "llama-3.2-90b": 128000,
    "llama-3.3": 128000,
    "llama-3.3-70b": 128000,
    "llama-3.3-70b-versatile": 128000,
    "llama3": 8192,
    "llama3.1": 128000,
    "llama3.2": 128000,
    "llama3.3": 128000,
    # Meta Llama 2.x
    "llama-2": 4096,
    "llama-2-7b": 4096,
    "llama-2-13b": 4096,
    "llama-2-70b": 4096,
    "llama2": 4096,
    # Meta Llama 4.x
    "llama-4": 128000,
    "llama-4-scout": 10000000,
    "llama-4-maverick": 1000000,
    "llama4": 128000,
    # Meta Code Llama
    "codellama": 16384,
    "codellama-7b": 16384,
    "codellama-13b": 16384,
    "codellama-34b": 16384,
    "codellama-70b": 16384,
    "code-llama": 16384,
    # xAI Grok
    "grok": 131072,
    "grok-beta": 131072,
    "grok-1": 8192,
    "grok-1.5": 128000,
    "grok-2": 131072,
    "grok-2-mini": 131072,
    "grok-3": 131072,
    "grok-3-mini": 131072,
    # DeepSeek
    "deepseek": 64000,
    "deepseek-chat": 64000,
    "deepseek-coder": 64000,
    "deepseek-coder-v2": 128000,
    "deepseek-reasoner": 64000,
    "deepseek-r1": 64000,
    "deepseek-r1-lite": 64000,
    "deepseek-v2": 128000,
    "deepseek-v2.5": 128000,
    "deepseek-v3": 128000,
    # Alibaba Qwen
    "qwen": 32768,
    "qwen-turbo": 131072,
    "qwen-plus": 131072,
    "qwen-max": 32768,
    "qwen-long": 10000000,
    "qwen-vl": 32768,
    "qwen-1.5": 32768,
    "qwen-2": 131072,
    "qwen-2.5": 131072,
    "qwen-2.5-coder": 131072,
    "qwen-2.5-math": 131072,
    "qwen-3": 131072,
    "qwen2": 131072,
    "qwen2.5": 131072,
    "qwen2.5-coder": 131072,
    "qwen3": 131072,
    "qwen3-coder": 131072,
    "qwq": 131072,
    "qwq-32b": 131072,
    # Microsoft Phi
    "phi": 2048,
    "phi-2": 2048,
    "phi-3": 128000,
    "phi-3-mini": 128000,
    "phi-3-small": 128000,
    "phi-3-medium": 128000,
    "phi-3.5": 128000,
    "phi-3.5-mini": 128000,
    "phi-3.5-moe": 128000,
    "phi-4": 16384,
    "phi3": 128000,
    "phi4": 16384,
    # Google Gemma
    "gemma": 8192,
    "gemma-2b": 8192,
    "gemma-7b": 8192,
    "gemma-2": 8192,
    "gemma-2-2b": 8192,
    "gemma-2-9b": 8192,
    "gemma-2-27b": 8192,
    "gemma2": 8192,
    "gemma2-2b": 8192,
    "gemma2-9b": 8192,
    "gemma2-9b-it": 8192,
    "gemma2-27b": 8192,
    "gemma3": 128000,
    "gemma-3": 128000,
    # Yi (01.AI)
    "yi": 32768,
    "yi-6b": 4096,
    "yi-9b": 4096,
    "yi-34b": 32768,
    "yi-large": 32768,
    "yi-1.5": 32768,
    "yi-lightning": 16384,
    "yi-vision": 16384,
    # Nvidia
    "nemotron": 4096,
    "nemotron-4": 4096,
    "nemotron-70b": 32768,
    "llama-3.1-nemotron": 128000,
    "llama-3.3-nemotron": 128000,
    # Amazon
    "amazon-titan": 8192,
    "titan-text": 8192,
    "titan-text-express": 8192,
    "titan-text-lite": 4096,
    "titan-text-premier": 32768,
    "amazon-nova": 300000,
    "nova-pro": 300000,
    "nova-lite": 300000,
    "nova-micro": 128000,
    # Inflection
    "inflection-2.5": 8192,
    "inflection-3": 8192,
    "pi": 8192,
    # Reka
    "reka": 128000,
    "reka-core": 128000,
    "reka-flash": 128000,
    "reka-edge": 128000,
    # AI21 Labs Jamba
    "jamba": 256000,
    "jamba-instruct": 256000,
    "jamba-1.5": 256000,
    "jamba-1.5-mini": 256000,
    "jamba-1.5-large": 256000,
    "j2-ultra": 8192,
    "j2-mid": 8192,
    "j2-light": 8192,
    "jurassic-2": 8192,
    # Databricks DBRX
    "dbrx": 32768,
    "dbrx-instruct": 32768,
    "dbrx-base": 32768,
    # Together AI hosted
    "together": 32768,
    "stripedhyena": 32768,
    "stripedhyena-nous": 32768,
    # Perplexity
    "pplx": 127072,
    "sonar": 127072,
    "sonar-small": 127072,
    "sonar-medium": 127072,
    "sonar-large": 127072,
    "sonar-pro": 200000,
    "sonar-reasoning": 127072,
    # Groq hosted
    "llama-3.1-70b-versatile": 128000,
    "llama-3.1-8b-instant": 128000,
    "llama-guard": 8192,
    "llama3-70b-8192": 8192,
    "llama3-8b-8192": 8192,
    # Writer
    "palmyra": 32768,
    "palmyra-x": 32768,
    "palmyra-x-004": 128000,
    # StarCoder / BigCode
    "starcoder": 8192,
    "starcoder2": 16384,
    "starcoder2-3b": 16384,
    "starcoder2-7b": 16384,
    "starcoder2-15b": 16384,
    "starcoderbase": 8192,
    # WizardLM
    "wizardlm": 4096,
    "wizardlm-2": 32768,
    "wizardcoder": 8192,
    "wizard-vicuna": 2048,
    # Vicuna
    "vicuna": 2048,
    "vicuna-7b": 2048,
    "vicuna-13b": 2048,
    "vicuna-33b": 2048,
    # Falcon
    "falcon": 2048,
    "falcon-7b": 2048,
    "falcon-40b": 2048,
    "falcon-180b": 2048,
    # InternLM
    "internlm": 32768,
    "internlm-7b": 8192,
    "internlm-20b": 16384,
    "internlm2": 32768,
    "internlm2.5": 32768,
    # Baichuan
    "baichuan": 4096,
    "baichuan-7b": 4096,
    "baichuan-13b": 4096,
    "baichuan2": 4096,
    # ChatGLM
    "chatglm": 32768,
    "chatglm-6b": 8192,
    "chatglm2": 32768,
    "chatglm3": 32768,
    "chatglm4": 128000,
    "glm-4": 128000,
    "glm-4-plus": 128000,
    # Zhipu AI
    "zhipu": 128000,
    # Moonshot / Kimi
    "moonshot": 128000,
    "moonshot-v1": 128000,
    "kimi": 128000,
    # Hunyuan (Tencent)
    "hunyuan": 32768,
    "hunyuan-lite": 32768,
    "hunyuan-standard": 32768,
    "hunyuan-pro": 32768,
    # ERNIE (Baidu)
    "ernie": 8192,
    "ernie-bot": 8192,
    "ernie-bot-4": 8192,
    "ernie-4": 128000,
    # MiniMax
    "minimax": 245760,
    "abab": 245760,
    "abab6.5": 245760,
    # Cerebras
    "cerebras": 8192,
    "btlm": 8192,
    # SambaNova
    "samba": 4096,
    "samba-1": 4096,
    # Snowflake Arctic
    "arctic": 4096,
    "snowflake-arctic": 4096,
    # Mamba / State Space
    "mamba": 1000000,
    "mamba-codestral": 256000,
    # OLMo (AI2)
    "olmo": 4096,
    "olmo-7b": 4096,
    "olmo-2": 4096,
    # Anthropic via Antigravity
    "antigravity": 200000,
    # Generic / catch-all patterns
    "opus": 200000,
    "sonnet": 200000,
    "haiku": 200000,
    "turbo": 128000,
    "instruct": 8192,
    "chat": 8192,
    "base": 4096,
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token average)."""
    return len(text) // 4


def get_model_context_size(model_name: str) -> int:
    model_lower = model_name.lower()

    best_match_len = 0
    best_size = 4096
    found = False

    for known, size in KNOWN_MODEL_CONTEXTS.items():
        known_lower = known.lower()
        if known_lower in model_lower:
            if len(known_lower) > best_match_len:
                best_match_len = len(known_lower)
                best_size = size
                found = True

    if found:
        return best_size

    # Default fallback
    return 4096


class LLMProvider(ABC):
    model: str = ""

    async def embed_text(self, text: str) -> list[float] | None:
        """Get vector embedding for text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the vector, or None if not supported/failed
        """
        return None

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Check if the provider is reachable."""
        pass

    async def check_health(self) -> ProviderHealth:
        """Check provider health with latency measurement."""
        import time

        start = time.perf_counter()
        try:
            is_valid = await self.validate_connection()
            elapsed_ms = (time.perf_counter() - start) * 1000

            if is_valid:
                return ProviderHealth(
                    status=HealthStatus.CONNECTED,
                    latency_ms=elapsed_ms,
                    last_check=datetime.now(),
                )
            else:
                return ProviderHealth(
                    status=HealthStatus.DISCONNECTED,
                    latency_ms=elapsed_ms,
                    last_check=datetime.now(),
                )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return ProviderHealth(
                status=HealthStatus.ERROR,
                latency_ms=elapsed_ms,
                last_check=datetime.now(),
                error_message=str(e)[:100],
            )

    async def close(self) -> None:
        """Clean up provider resources. Override in subclasses if needed."""
        return None

    def get_model_info(self) -> ModelInfo:
        """Get model information including context limits."""
        context_size = get_model_context_size(self.model)
        return ModelInfo(
            name=self.model, max_tokens=context_size, context_window=context_size
        )

    def supports_tools(self) -> bool:
        """Check if this provider supports tool calling."""
        return False  # Override in subclasses that support tools

    async def list_models(self) -> list[str]:
        """List available models."""
        return []
