"""Thinking strategy system for model-specific reasoning extraction.

Different LLM families handle "thinking" or "reasoning" differently:
- DeepSeek-R1, QwQ: Native <think> tags, no prompting needed
- OpenAI o1/o3: Native reasoning, hidden from output
- GPT-4/Claude: Can be prompted to use structured thinking
- Local models: Best with explicit XML tag prompting
"""

import json
import re
from abc import ABC, abstractmethod


class ThinkingStrategy(ABC):
    """Base strategy for extracting thinking from model responses."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier."""
        pass

    @property
    def requires_prompting(self) -> bool:
        """Whether this strategy needs system prompt additions."""
        return True

    @abstractmethod
    def get_prompt_addition(self) -> str:
        """Additional system prompt text to encourage thinking output."""
        pass

    @abstractmethod
    def extract_thinking(self, text: str) -> tuple[str, str]:
        """Extract thinking content from response.

        Returns:
            Tuple of (thinking_content, remaining_content)
        """
        pass

    def supports_streaming_extraction(self) -> bool:
        """Whether thinking can be extracted during streaming."""
        return True

    def extract_thinking_streaming(self, text: str) -> tuple[str, str, bool]:
        """Extract thinking during streaming.

        Returns:
            Tuple of (thinking_so_far, remaining_so_far, thinking_complete)
        """
        thinking, remaining = self.extract_thinking(text)
        # If we found thinking content, check if it's complete
        thinking_complete = bool(thinking and remaining)
        return thinking, remaining, thinking_complete


class XMLTagStrategy(ThinkingStrategy):
    """Uses <think>...</think> XML tags for reasoning.

    Best for: Claude, DeepSeek (non-R1), Ollama models, general use
    """

    name = "xml_tags"

    # Pattern matches <think>content</think> with flexible whitespace
    THINK_PATTERN = re.compile(r"<think>\s*(.*?)\s*</think>", re.DOTALL | re.IGNORECASE)

    # Pattern for incomplete/streaming think tags
    INCOMPLETE_PATTERN = re.compile(r"<think>\s*(.*?)$", re.DOTALL | re.IGNORECASE)

    def get_prompt_addition(self) -> str:
        return """
Before responding, think through the problem step by step inside <think> tags:
<think>
Your step-by-step reasoning here...
</think>

Then provide your response or tool calls. Always use the think tags to show your reasoning process.
"""

    def extract_thinking(self, text: str) -> tuple[str, str]:
        # Try to find complete think blocks
        matches = list(self.THINK_PATTERN.finditer(text))

        if matches:
            # Collect all thinking content
            thinking_parts = [m.group(1).strip() for m in matches]
            thinking = "\n\n".join(thinking_parts)

            # Remove all think blocks from text
            remaining = self.THINK_PATTERN.sub("", text).strip()
            return thinking, remaining

        return "", text

    def extract_thinking_streaming(self, text: str) -> tuple[str, str, bool]:
        # Check for complete think blocks first
        complete_match = self.THINK_PATTERN.search(text)
        if complete_match:
            thinking, remaining = self.extract_thinking(text)
            return thinking, remaining, True

        # Check for incomplete/ongoing think block
        incomplete_match = self.INCOMPLETE_PATTERN.search(text)
        if incomplete_match:
            thinking = incomplete_match.group(1).strip()
            return thinking, "", False

        return "", text, False


class JSONStructuredStrategy(ThinkingStrategy):
    """Uses JSON structured output for thinking.

    Best for: GPT-4, GPT-4o, models with good JSON compliance
    """

    name = "json_structured"

    def get_prompt_addition(self) -> str:
        return """
Before each action, output your reasoning as a JSON object on its own line:
{"thinking": "your step-by-step analysis here"}

Then proceed with your response or tool calls. The thinking JSON should be on a separate line from your main response.
"""

    def extract_thinking(self, text: str) -> tuple[str, str]:
        lines = text.split("\n")
        thinking_parts: list[str] = []
        remaining_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Try to parse as thinking JSON
            if stripped.startswith('{"thinking"'):
                try:
                    # Handle potential trailing content
                    json_end = stripped.find("}") + 1
                    if json_end > 0:
                        json_str = stripped[:json_end]
                        data = json.loads(json_str)
                        if "thinking" in data:
                            thinking_parts.append(data["thinking"])
                            # Keep any content after the JSON
                            after_json = stripped[json_end:].strip()
                            if after_json:
                                remaining_lines.append(after_json)
                            continue
                except json.JSONDecodeError:
                    pass

            remaining_lines.append(line)

        thinking = "\n".join(thinking_parts)
        remaining = "\n".join(remaining_lines).strip()
        return thinking, remaining

    def supports_streaming_extraction(self) -> bool:
        # JSON extraction works better on complete lines
        return True


class NativeThinkingStrategy(ThinkingStrategy):
    """For models with native thinking support.

    Best for: DeepSeek-R1, QwQ, o1, o3 (reasoning models)
    These models naturally output <think> tags without prompting.
    """

    name = "native"

    @property
    def requires_prompting(self) -> bool:
        return False

    def get_prompt_addition(self) -> str:
        # Native thinking models don't need prompting
        return ""

    def extract_thinking(self, text: str) -> tuple[str, str]:
        # These models use <think> tags natively, delegate to XML strategy
        return XMLTagStrategy().extract_thinking(text)

    def extract_thinking_streaming(self, text: str) -> tuple[str, str, bool]:
        return XMLTagStrategy().extract_thinking_streaming(text)


class MinimalThinkingStrategy(ThinkingStrategy):
    """Lightweight strategy for models that don't support structured thinking well.

    Best for: Small local models, older models, or when thinking overhead is unwanted
    """

    name = "minimal"

    @property
    def requires_prompting(self) -> bool:
        return False

    def get_prompt_addition(self) -> str:
        return ""

    def extract_thinking(self, text: str) -> tuple[str, str]:
        # No extraction, pass through as-is
        return "", text

    def extract_thinking_streaming(self, text: str) -> tuple[str, str, bool]:
        return "", text, True


# Model patterns that indicate native thinking support
NATIVE_THINKING_MODELS = [
    "deepseek-r1",
    "deepseek-reasoner",
    "qwq",
    "qwen-qwq",
    "o1",
    "o1-preview",
    "o1-mini",
    "o3",
    "o3-mini",
    "gemini-2.5",  # Gemini 2.5 has native thinking
]

# Provider/model combinations that work well with JSON structured output
JSON_PREFERRED_PATTERNS = [
    ("openai", "gpt-4"),
    ("openai", "gpt-4o"),
    ("openai", "gpt-4-turbo"),
    ("azure", "gpt-4"),
    ("azure", "gpt-4o"),
]

# Models that don't handle thinking well
MINIMAL_THINKING_PATTERNS = [
    "phi",
    "gemma",
    "tinyllama",
    "stablelm",
    "orca-mini",
]


def get_thinking_strategy(
    provider: str, model: str, override: str | None = None
) -> ThinkingStrategy:
    """Get appropriate thinking strategy for provider/model combination.

    Args:
        provider: The AI provider name (e.g., 'openai', 'anthropic', 'ollama')
        model: The model name/identifier
        override: Optional strategy name to force a specific strategy

    Returns:
        ThinkingStrategy instance appropriate for the model
    """
    # Allow manual override
    if override:
        strategies = {
            "xml": XMLTagStrategy(),
            "xml_tags": XMLTagStrategy(),
            "json": JSONStructuredStrategy(),
            "json_structured": JSONStructuredStrategy(),
            "native": NativeThinkingStrategy(),
            "minimal": MinimalThinkingStrategy(),
            "none": MinimalThinkingStrategy(),
        }
        return strategies.get(override.lower(), XMLTagStrategy())

    model_lower = model.lower()
    provider_lower = provider.lower()

    # Check for native thinking models first
    for pattern in NATIVE_THINKING_MODELS:
        if pattern in model_lower:
            return NativeThinkingStrategy()

    # Check for models that work poorly with thinking prompts
    for pattern in MINIMAL_THINKING_PATTERNS:
        if pattern in model_lower:
            return MinimalThinkingStrategy()

    # Check for JSON-preferred combinations
    for prov, mod_pattern in JSON_PREFERRED_PATTERNS:
        if provider_lower == prov and mod_pattern in model_lower:
            return JSONStructuredStrategy()

    # OpenAI models generally work well with JSON
    if provider_lower == "openai" and "gpt" in model_lower:
        return JSONStructuredStrategy()

    # Anthropic Claude works well with XML tags
    if provider_lower == "anthropic" or "claude" in model_lower:
        return XMLTagStrategy()

    # DeepSeek non-R1 models work with XML
    if provider_lower == "deepseek" or "deepseek" in model_lower:
        return XMLTagStrategy()

    # Default: XML tags (most universally compatible)
    return XMLTagStrategy()


def list_strategies() -> list[str]:
    """Return list of available strategy names."""
    return ["xml_tags", "json_structured", "native", "minimal"]
