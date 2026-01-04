"""Tests for ai/thinking.py - ThinkingStrategy classes and extraction logic."""

import pytest

from ai.thinking import (
    JSONStructuredStrategy,
    MinimalThinkingStrategy,
    NativeThinkingStrategy,
    XMLTagStrategy,
    get_thinking_strategy,
    list_strategies,
)


class TestXMLTagStrategy:
    """Tests for XMLTagStrategy - extracts <think>...</think> blocks."""

    @pytest.fixture
    def strategy(self):
        """Create an XMLTagStrategy instance."""
        return XMLTagStrategy()

    def test_name(self, strategy):
        """Strategy should have correct name."""
        assert strategy.name == "xml_tags"

    def test_requires_prompting(self, strategy):
        """XML strategy requires prompting."""
        assert strategy.requires_prompting is True

    def test_get_prompt_addition(self, strategy):
        """Should return non-empty prompt addition."""
        prompt = strategy.get_prompt_addition()
        assert "<think>" in prompt
        assert "</think>" in prompt

    def test_extract_simple_thinking(self, strategy):
        """Should extract content from a simple think block."""
        text = "<think>This is my reasoning</think>This is the response."
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "This is my reasoning"
        assert remaining == "This is the response."

    def test_extract_no_thinking(self, strategy):
        """Should return empty thinking when no think tags present."""
        text = "Just a regular response without thinking."
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == ""
        assert remaining == "Just a regular response without thinking."

    def test_extract_multiple_think_blocks(self, strategy):
        """Should extract and combine multiple think blocks."""
        text = "<think>First thought</think>Response part 1<think>Second thought</think>Response part 2"
        thinking, remaining = strategy.extract_thinking(text)
        assert "First thought" in thinking
        assert "Second thought" in thinking
        assert "<think>" not in remaining
        assert "</think>" not in remaining

    def test_extract_multiline_thinking(self, strategy):
        """Should handle multiline think blocks."""
        text = """<think>
        Line 1 of reasoning
        Line 2 of reasoning
        Line 3 of reasoning
        </think>
        Final answer here."""
        thinking, remaining = strategy.extract_thinking(text)
        assert "Line 1" in thinking
        assert "Line 2" in thinking
        assert "Line 3" in thinking
        assert "Final answer" in remaining

    def test_extract_case_insensitive(self, strategy):
        """Should handle different cases of think tags."""
        text = "<THINK>Uppercase thinking</THINK>Response"
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "Uppercase thinking"
        assert remaining == "Response"

    def test_extract_with_whitespace(self, strategy):
        """Should trim whitespace from extracted thinking."""
        text = "<think>   Padded thinking   </think>Response"
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "Padded thinking"

    def test_streaming_complete_block(self, strategy):
        """Streaming extraction should detect complete blocks."""
        text = "<think>Complete thought</think>Response"
        thinking, remaining, complete = strategy.extract_thinking_streaming(text)
        assert thinking == "Complete thought"
        assert remaining == "Response"
        assert complete is True

    def test_streaming_incomplete_block(self, strategy):
        """Streaming extraction should detect incomplete blocks."""
        text = "<think>Incomplete thought still being typed..."
        thinking, remaining, complete = strategy.extract_thinking_streaming(text)
        assert "Incomplete thought" in thinking
        assert complete is False

    def test_streaming_no_think_tag(self, strategy):
        """Streaming extraction with no think tag should return text as remaining."""
        text = "Regular text without thinking"
        thinking, remaining, complete = strategy.extract_thinking_streaming(text)
        assert thinking == ""
        assert remaining == "Regular text without thinking"
        assert complete is False


class TestJSONStructuredStrategy:
    """Tests for JSONStructuredStrategy - uses JSON for thinking."""

    @pytest.fixture
    def strategy(self):
        """Create a JSONStructuredStrategy instance."""
        return JSONStructuredStrategy()

    def test_name(self, strategy):
        """Strategy should have correct name."""
        assert strategy.name == "json_structured"

    def test_requires_prompting(self, strategy):
        """JSON strategy requires prompting."""
        assert strategy.requires_prompting is True

    def test_get_prompt_addition(self, strategy):
        """Should return prompt with JSON format instructions."""
        prompt = strategy.get_prompt_addition()
        assert "thinking" in prompt
        assert "JSON" in prompt

    def test_extract_simple_thinking(self, strategy):
        """Should extract thinking from JSON line."""
        text = '{"thinking": "My analysis of the problem"}\nThe actual response.'
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "My analysis of the problem"
        assert remaining == "The actual response."

    def test_extract_no_thinking(self, strategy):
        """Should return empty thinking when no JSON thinking present."""
        text = "Just a regular response."
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == ""
        assert remaining == "Just a regular response."

    def test_extract_multiple_thinking_lines(self, strategy):
        """Should extract multiple thinking JSON lines."""
        text = '{"thinking": "First thought"}\n{"thinking": "Second thought"}\nFinal response'
        thinking, remaining = strategy.extract_thinking(text)
        assert "First thought" in thinking
        assert "Second thought" in thinking
        assert remaining == "Final response"

    def test_extract_with_trailing_content(self, strategy):
        """Should handle content after JSON on same line."""
        text = '{"thinking": "Analysis"} And then the response continues'
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "Analysis"
        assert "response continues" in remaining

    def test_invalid_json_passthrough(self, strategy):
        """Invalid JSON should be passed through as remaining content."""
        text = '{"thinking": invalid json}\nResponse'
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == ""
        assert '{"thinking": invalid json}' in remaining

    def test_supports_streaming(self, strategy):
        """JSON strategy should support streaming extraction."""
        assert strategy.supports_streaming_extraction() is True


class TestNativeThinkingStrategy:
    """Tests for NativeThinkingStrategy - for models with native thinking."""

    @pytest.fixture
    def strategy(self):
        """Create a NativeThinkingStrategy instance."""
        return NativeThinkingStrategy()

    def test_name(self, strategy):
        """Strategy should have correct name."""
        assert strategy.name == "native"

    def test_requires_prompting(self, strategy):
        """Native strategy should not require prompting."""
        assert strategy.requires_prompting is False

    def test_get_prompt_addition(self, strategy):
        """Native strategy should return empty prompt addition."""
        assert strategy.get_prompt_addition() == ""

    def test_extract_thinking_delegates_to_xml(self, strategy):
        """Native strategy should use XML extraction internally."""
        text = "<think>Native model reasoning</think>Response"
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "Native model reasoning"
        assert remaining == "Response"

    def test_streaming_delegates_to_xml(self, strategy):
        """Streaming extraction should also use XML strategy."""
        text = "<think>Streaming native thought</think>Answer"
        thinking, remaining, complete = strategy.extract_thinking_streaming(text)
        assert thinking == "Streaming native thought"
        assert complete is True


class TestMinimalThinkingStrategy:
    """Tests for MinimalThinkingStrategy - no thinking extraction."""

    @pytest.fixture
    def strategy(self):
        """Create a MinimalThinkingStrategy instance."""
        return MinimalThinkingStrategy()

    def test_name(self, strategy):
        """Strategy should have correct name."""
        assert strategy.name == "minimal"

    def test_requires_prompting(self, strategy):
        """Minimal strategy should not require prompting."""
        assert strategy.requires_prompting is False

    def test_get_prompt_addition(self, strategy):
        """Minimal strategy should return empty prompt addition."""
        assert strategy.get_prompt_addition() == ""

    def test_extract_no_thinking(self, strategy):
        """Minimal strategy should pass through all text as remaining."""
        text = "<think>This would be thinking</think>But minimal ignores it"
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == ""
        assert remaining == text  # Everything passed through

    def test_streaming_no_extraction(self, strategy):
        """Streaming should also pass through without extraction."""
        text = "Any text here"
        thinking, remaining, complete = strategy.extract_thinking_streaming(text)
        assert thinking == ""
        assert remaining == "Any text here"
        assert complete is True


class TestGetThinkingStrategy:
    """Tests for get_thinking_strategy function."""

    def test_override_xml(self):
        """Override should force XML strategy."""
        strategy = get_thinking_strategy("openai", "gpt-4o", override="xml")
        assert isinstance(strategy, XMLTagStrategy)

    def test_override_json(self):
        """Override should force JSON strategy."""
        strategy = get_thinking_strategy("ollama", "llama3", override="json")
        assert isinstance(strategy, JSONStructuredStrategy)

    def test_override_native(self):
        """Override should force native strategy."""
        strategy = get_thinking_strategy("openai", "gpt-4o", override="native")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_override_minimal(self):
        """Override should force minimal strategy."""
        strategy = get_thinking_strategy("openai", "gpt-4o", override="minimal")
        assert isinstance(strategy, MinimalThinkingStrategy)

    def test_override_none(self):
        """Override with 'none' should use minimal strategy."""
        strategy = get_thinking_strategy("openai", "gpt-4o", override="none")
        assert isinstance(strategy, MinimalThinkingStrategy)

    def test_native_deepseek_r1(self):
        """DeepSeek R1 should use native strategy."""
        strategy = get_thinking_strategy("deepseek", "deepseek-r1")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_native_deepseek_reasoner(self):
        """DeepSeek Reasoner should use native strategy."""
        strategy = get_thinking_strategy("deepseek", "deepseek-reasoner")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_native_qwq(self):
        """QwQ models should use native strategy."""
        strategy = get_thinking_strategy("ollama", "qwq:32b")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_native_o1(self):
        """OpenAI o1 models should use native strategy."""
        strategy = get_thinking_strategy("openai", "o1-preview")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_native_o1_mini(self):
        """OpenAI o1-mini should use native strategy."""
        strategy = get_thinking_strategy("openai", "o1-mini")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_native_gemini_25(self):
        """Gemini 2.5 should use native strategy."""
        strategy = get_thinking_strategy("google", "gemini-2.5-pro")
        assert isinstance(strategy, NativeThinkingStrategy)

    def test_minimal_phi(self):
        """Phi models should use minimal strategy."""
        strategy = get_thinking_strategy("ollama", "phi3:latest")
        assert isinstance(strategy, MinimalThinkingStrategy)

    def test_minimal_gemma(self):
        """Gemma models should use minimal strategy."""
        strategy = get_thinking_strategy("ollama", "gemma:7b")
        assert isinstance(strategy, MinimalThinkingStrategy)

    def test_minimal_tinyllama(self):
        """TinyLlama should use minimal strategy."""
        strategy = get_thinking_strategy("ollama", "tinyllama:latest")
        assert isinstance(strategy, MinimalThinkingStrategy)

    def test_json_openai_gpt4(self):
        """OpenAI GPT-4 should use JSON strategy."""
        strategy = get_thinking_strategy("openai", "gpt-4")
        assert isinstance(strategy, JSONStructuredStrategy)

    def test_json_openai_gpt4o(self):
        """OpenAI GPT-4o should use JSON strategy."""
        strategy = get_thinking_strategy("openai", "gpt-4o-mini")
        assert isinstance(strategy, JSONStructuredStrategy)

    def test_json_azure_gpt4(self):
        """Azure GPT-4 should use JSON strategy."""
        strategy = get_thinking_strategy("azure", "gpt-4-turbo")
        assert isinstance(strategy, JSONStructuredStrategy)

    def test_xml_anthropic_claude(self):
        """Anthropic Claude should use XML strategy."""
        strategy = get_thinking_strategy("anthropic", "claude-3-5-sonnet-20241022")
        assert isinstance(strategy, XMLTagStrategy)

    def test_xml_claude_in_name(self):
        """Any model with 'claude' in name should use XML strategy."""
        strategy = get_thinking_strategy("ollama", "claude-proxy")
        assert isinstance(strategy, XMLTagStrategy)

    def test_xml_deepseek_non_r1(self):
        """DeepSeek non-R1 models should use XML strategy."""
        strategy = get_thinking_strategy("deepseek", "deepseek-chat")
        assert isinstance(strategy, XMLTagStrategy)

    def test_xml_default(self):
        """Unknown models should default to XML strategy."""
        strategy = get_thinking_strategy("unknown", "unknown-model")
        assert isinstance(strategy, XMLTagStrategy)

    def test_case_insensitive_provider(self):
        """Provider matching should be case insensitive."""
        strategy = get_thinking_strategy("OpenAI", "gpt-4")
        assert isinstance(strategy, JSONStructuredStrategy)

    def test_case_insensitive_model(self):
        """Model matching should be case insensitive."""
        strategy = get_thinking_strategy("openai", "GPT-4O")
        assert isinstance(strategy, JSONStructuredStrategy)


class TestListStrategies:
    """Tests for list_strategies function."""

    def test_returns_list(self):
        """Should return a list of strategy names."""
        strategies = list_strategies()
        assert isinstance(strategies, list)

    def test_contains_expected_strategies(self):
        """Should contain all expected strategy names."""
        strategies = list_strategies()
        assert "xml_tags" in strategies
        assert "json_structured" in strategies
        assert "native" in strategies
        assert "minimal" in strategies

    def test_count(self):
        """Should return exactly 4 strategies."""
        strategies = list_strategies()
        assert len(strategies) == 4


class TestEdgeCases:
    """Edge case tests for thinking extraction."""

    def test_xml_nested_angle_brackets(self):
        """XML strategy should handle content with angle brackets."""
        strategy = XMLTagStrategy()
        text = "<think>if x < 10 and y > 5</think>Result"
        thinking, remaining = strategy.extract_thinking(text)
        assert "x < 10" in thinking
        assert remaining == "Result"

    def test_xml_empty_think_block(self):
        """XML strategy should handle empty think blocks."""
        strategy = XMLTagStrategy()
        text = "<think></think>Response"
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == ""
        assert remaining == "Response"

    def test_xml_think_only(self):
        """XML strategy should handle response with only thinking."""
        strategy = XMLTagStrategy()
        text = "<think>All thinking, no response</think>"
        thinking, remaining = strategy.extract_thinking(text)
        assert thinking == "All thinking, no response"
        assert remaining == ""

    def test_json_thinking_with_special_chars(self):
        """JSON strategy should handle special characters in thinking."""
        strategy = JSONStructuredStrategy()
        # Note: In actual JSON, quotes would be escaped
        text = '{"thinking": "Analysis with newlines and quotes"}\nResponse'
        thinking, remaining = strategy.extract_thinking(text)
        assert "Analysis" in thinking

    def test_xml_unicode_content(self):
        """XML strategy should handle unicode content."""
        strategy = XMLTagStrategy()
        text = "<think>Thinking with unicode: \u4e2d\u6587 \u65e5\u672c\u8a9e</think>Response"
        thinking, remaining = strategy.extract_thinking(text)
        assert "\u4e2d\u6587" in thinking
        assert remaining == "Response"
