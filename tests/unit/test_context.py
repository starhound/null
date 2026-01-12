"""Unit tests for context.py - ContextInfo and ContextManager."""

from context import ContextInfo, ContextManager
from models import BlockState, BlockType


class TestContextInfo:
    """Tests for the ContextInfo dataclass."""

    def test_default_values(self):
        """Test ContextInfo with default truncated value."""
        info = ContextInfo(
            messages=[{"role": "user", "content": "hello"}],
            total_chars=5,
            estimated_tokens=1,
            message_count=1,
        )
        assert info.truncated is False

    def test_explicit_truncated(self):
        """Test ContextInfo with explicit truncated=True."""
        info = ContextInfo(
            messages=[],
            total_chars=0,
            estimated_tokens=0,
            message_count=0,
            truncated=True,
        )
        assert info.truncated is True

    def test_all_fields_stored(self):
        """Test that all fields are properly stored."""
        messages = [
            {"role": "user", "content": "test1"},
            {"role": "assistant", "content": "test2"},
        ]
        info = ContextInfo(
            messages=messages,
            total_chars=100,
            estimated_tokens=25,
            message_count=2,
            truncated=False,
        )
        assert info.messages == messages
        assert info.total_chars == 100
        assert info.estimated_tokens == 25
        assert info.message_count == 2


class TestContextManagerGetContext:
    """Tests for ContextManager.get_context() legacy method."""

    def test_empty_history(self):
        """Test with empty history blocks."""
        result = ContextManager.get_context([])
        assert result == ""

    def test_single_ai_query(self):
        """Test context with single AI query block."""
        block = BlockState(
            type=BlockType.AI_QUERY,
            content_input="What is Python?",
        )
        result = ContextManager.get_context([block])
        assert "User: What is Python?" in result

    def test_single_ai_response(self):
        """Test context with single AI response block."""
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="",
            content_output="Python is a programming language.",
        )
        result = ContextManager.get_context([block])
        assert "Assistant: Python is a programming language." in result

    def test_query_response_pair(self):
        """Test context with query and response pair."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="Hello"),
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="Hi there!",
            ),
        ]
        result = ContextManager.get_context(blocks)
        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result

    def test_command_block_included(self):
        """Test that command blocks are converted to user messages."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls -la",
            content_output="file1.txt\nfile2.txt",
        )
        result = ContextManager.get_context([block])
        # Command blocks become user messages, check the context contains relevant info
        assert "User:" in result

    def test_multiple_conversations(self):
        """Test context with multiple conversation turns."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="First question"),
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="First answer",
            ),
            BlockState(type=BlockType.AI_QUERY, content_input="Second question"),
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="Second answer",
            ),
        ]
        result = ContextManager.get_context(blocks)
        assert "First question" in result
        assert "First answer" in result
        assert "Second question" in result
        assert "Second answer" in result


class TestContextManagerBuildMessages:
    """Tests for ContextManager.build_messages()."""

    def test_empty_history(self):
        """Test with empty history blocks."""
        info = ContextManager.build_messages([])
        assert info.messages == []
        assert info.total_chars == 0
        assert info.estimated_tokens == 0
        assert info.message_count == 0
        assert info.truncated is False

    def test_ai_query_creates_user_message(self):
        """Test AI_QUERY block creates user role message."""
        block = BlockState(
            type=BlockType.AI_QUERY,
            content_input="What is Python?",
        )
        info = ContextManager.build_messages([block])
        assert len(info.messages) == 1
        assert info.messages[0]["role"] == "user"
        assert info.messages[0]["content"] == "What is Python?"

    def test_ai_response_creates_assistant_message(self):
        """Test AI_RESPONSE block creates assistant role message."""
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="",
            content_output="Python is great.",
        )
        info = ContextManager.build_messages([block])
        assert len(info.messages) == 1
        assert info.messages[0]["role"] == "assistant"
        assert info.messages[0]["content"] == "Python is great."

    def test_ai_response_without_output_skipped(self):
        """Test AI_RESPONSE without output is skipped."""
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="query",
            content_output="",
        )
        info = ContextManager.build_messages([block])
        assert len(info.messages) == 0

    def test_command_block_creates_user_message(self):
        """Test COMMAND block creates user message with terminal context."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls",
            content_output="file.txt",
        )
        info = ContextManager.build_messages([block])
        assert len(info.messages) == 1
        assert info.messages[0]["role"] == "user"
        assert "[Terminal Command]" in info.messages[0]["content"]
        assert "$ ls" in info.messages[0]["content"]
        assert "file.txt" in info.messages[0]["content"]

    def test_command_without_output(self):
        """Test COMMAND block without output."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="clear",
            content_output="",
        )
        info = ContextManager.build_messages([block])
        assert len(info.messages) == 1
        assert "$ clear" in info.messages[0]["content"]

    def test_command_long_output_truncated(self):
        """Test very long command output is truncated."""
        long_output = "x" * 3000  # > 2000 chars
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat bigfile",
            content_output=long_output,
        )
        info = ContextManager.build_messages([block])
        content = info.messages[0]["content"]
        assert "...[truncated]..." in content
        # Should have first 1000 and last 500 chars
        assert len(content) < len(long_output)

    def test_system_msg_creates_user_message(self):
        """Test SYSTEM_MSG block creates user message."""
        block = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input="RAG Results",
            content_output="Found 3 relevant files.",
        )
        info = ContextManager.build_messages([block])
        assert len(info.messages) == 1
        assert info.messages[0]["role"] == "user"
        assert "[RAG Results]" in info.messages[0]["content"]
        assert "Found 3 relevant files." in info.messages[0]["content"]

    def test_message_count_accurate(self):
        """Test message_count matches actual messages."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="q1"),
            BlockState(
                type=BlockType.AI_RESPONSE, content_input="", content_output="a1"
            ),
            BlockState(type=BlockType.AI_QUERY, content_input="q2"),
        ]
        info = ContextManager.build_messages(blocks)
        assert info.message_count == 3
        assert len(info.messages) == 3

    def test_total_chars_calculated(self):
        """Test total_chars is sum of all message content lengths."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="hello"),  # 5 chars
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="world",  # 5 chars
            ),
        ]
        info = ContextManager.build_messages(blocks)
        assert info.total_chars == 10

    def test_estimated_tokens_calculation(self):
        """Test estimated_tokens is total_chars // 4."""
        blocks = [
            BlockState(
                type=BlockType.AI_QUERY, content_input="a" * 100
            ),  # 100 chars = 25 tokens
        ]
        info = ContextManager.build_messages(blocks)
        assert info.estimated_tokens == 25

    def test_truncation_when_exceeds_limit(self):
        """Test messages are truncated from beginning when exceeding limit."""
        # Create blocks that exceed the default limit
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="old message 1" * 100),
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="old response 1" * 100,
            ),
            BlockState(type=BlockType.AI_QUERY, content_input="recent message"),
        ]
        # Use small max_tokens to force truncation
        info = ContextManager.build_messages(blocks, max_tokens=100, reserve_tokens=50)
        # Available: 50 tokens * 4 = 200 chars
        assert info.truncated is True
        # Recent message should be kept
        assert any("recent message" in m["content"] for m in info.messages)

    def test_no_truncation_within_limit(self):
        """Test no truncation when within limit."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="short"),
        ]
        info = ContextManager.build_messages(
            blocks, max_tokens=1000, reserve_tokens=100
        )
        assert info.truncated is False
        assert info.message_count == 1

    def test_chronological_order_preserved(self):
        """Test messages maintain chronological order."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="first"),
            BlockState(type=BlockType.AI_QUERY, content_input="second"),
            BlockState(type=BlockType.AI_QUERY, content_input="third"),
        ]
        info = ContextManager.build_messages(blocks, max_tokens=10000)
        assert info.messages[0]["content"] == "first"
        assert info.messages[1]["content"] == "second"
        assert info.messages[2]["content"] == "third"

    def test_oldest_removed_first_on_truncation(self):
        """Test oldest messages are removed first when truncating."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="OLDEST" + "x" * 500),
            BlockState(type=BlockType.AI_QUERY, content_input="MIDDLE" + "y" * 500),
            BlockState(type=BlockType.AI_QUERY, content_input="NEWEST"),
        ]
        # Force truncation with small limit
        info = ContextManager.build_messages(blocks, max_tokens=200, reserve_tokens=50)
        # NEWEST should be preserved
        assert any("NEWEST" in m["content"] for m in info.messages)

    def test_default_parameters(self):
        """Test default max_tokens and reserve_tokens."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="test"),
        ]
        # Should use defaults: max_tokens=4096, reserve_tokens=1024
        info = ContextManager.build_messages(blocks)
        assert info.truncated is False

    def test_tool_call_block_not_included(self):
        """Test TOOL_CALL blocks are not directly added to messages."""
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="run_command",
            content_output="output",
        )
        info = ContextManager.build_messages([block])
        # TOOL_CALL is not handled in build_messages, should result in empty
        assert len(info.messages) == 0

    def test_agent_response_block_not_included(self):
        """Test AGENT_RESPONSE blocks are not directly added to messages."""
        block = BlockState(
            type=BlockType.AGENT_RESPONSE,
            content_input="task",
            content_output="completed",
        )
        info = ContextManager.build_messages([block])
        # AGENT_RESPONSE is not in the handled types
        assert len(info.messages) == 0


class TestContextManagerEstimateTotalTokens:
    """Tests for ContextManager.estimate_total_tokens()."""

    def test_empty_inputs(self):
        """Test with empty strings and no messages."""
        result = ContextManager.estimate_total_tokens("", [], "")
        assert result == 0

    def test_system_prompt_only(self):
        """Test with only system prompt."""
        result = ContextManager.estimate_total_tokens("a" * 40, [], "")
        assert result == 10  # 40 chars / 4

    def test_current_prompt_only(self):
        """Test with only current prompt."""
        result = ContextManager.estimate_total_tokens("", [], "b" * 80)
        assert result == 20  # 80 chars / 4

    def test_messages_only(self):
        """Test with only messages."""
        messages = [
            {"role": "user", "content": "c" * 100},
            {"role": "assistant", "content": "d" * 100},
        ]
        result = ContextManager.estimate_total_tokens("", messages, "")
        assert result == 50  # 200 chars / 4

    def test_all_components(self):
        """Test with system prompt, messages, and current prompt."""
        messages = [
            {"role": "user", "content": "hello"},  # 5 chars
        ]
        result = ContextManager.estimate_total_tokens(
            "system",  # 6 chars
            messages,
            "current",  # 7 chars
        )
        # Total: 6 + 5 + 7 = 18 chars -> 4 tokens
        assert result == 4

    def test_token_rounding(self):
        """Test token estimation rounds down."""
        # 7 chars -> 1 token (7 // 4 = 1)
        result = ContextManager.estimate_total_tokens("a" * 7, [], "")
        assert result == 1

    def test_realistic_scenario(self):
        """Test with realistic prompt sizes."""
        system_prompt = "You are a helpful assistant." * 10  # ~290 chars
        messages = [
            {"role": "user", "content": "Explain Python in detail."},
            {
                "role": "assistant",
                "content": "Python is a programming language..." * 20,
            },
        ]
        current = "What about JavaScript?"
        result = ContextManager.estimate_total_tokens(system_prompt, messages, current)
        # Should be a reasonable number
        assert result > 100
        assert result < 500


class TestContextManagerIntegration:
    """Integration tests combining multiple methods."""

    def test_get_context_uses_build_messages(self):
        """Test that get_context internally uses build_messages."""
        blocks = [
            BlockState(type=BlockType.AI_QUERY, content_input="test query"),
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="test response",
            ),
        ]
        # Both methods should produce consistent results
        context_str = ContextManager.get_context(blocks)
        info = ContextManager.build_messages(blocks)

        # The string context should contain the message contents
        for msg in info.messages:
            assert (
                msg["content"] in context_str
                or msg["content"].split()[0] in context_str
            )

    def test_full_conversation_flow(self):
        """Test a full conversation with commands and AI interactions."""
        blocks = [
            # User runs a command
            BlockState(
                type=BlockType.COMMAND,
                content_input="pwd",
                content_output="/home/user",
            ),
            # User asks AI
            BlockState(
                type=BlockType.AI_QUERY,
                content_input="What directory am I in?",
            ),
            # AI responds
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="You are in /home/user",
            ),
            # System message (e.g., RAG)
            BlockState(
                type=BlockType.SYSTEM_MSG,
                content_input="Context",
                content_output="Additional context here",
            ),
            # Follow-up query
            BlockState(
                type=BlockType.AI_QUERY,
                content_input="Can you explain more?",
            ),
        ]

        info = ContextManager.build_messages(blocks)

        # Should have 5 messages (command, query, response, system, query)
        assert info.message_count == 5
        assert info.total_chars > 0
        assert info.estimated_tokens > 0

        # Verify roles
        roles = [m["role"] for m in info.messages]
        assert roles == ["user", "user", "assistant", "user", "user"]

    def test_edge_case_all_empty_outputs(self):
        """Test with blocks that have empty outputs."""
        blocks = [
            BlockState(
                type=BlockType.AI_RESPONSE,
                content_input="",
                content_output="",  # Empty output - should be skipped
            ),
            BlockState(
                type=BlockType.COMMAND,
                content_input="echo",
                content_output="",  # Empty output - should still be included
            ),
        ]
        info = ContextManager.build_messages(blocks)
        # AI response without output is skipped, command is included
        assert info.message_count == 1
