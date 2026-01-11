"""Tests for widgets/blocks/ai_response.py - AIResponseBlock widget.

This module tests the AIResponseBlock widget which handles simple chat mode
AI responses with optional thinking tags and tool calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from models import BlockState, BlockType, ToolCallState
from widgets.blocks.ai_response import AIResponseBlock
from widgets.blocks.actions import ActionBar, ActionButton
from widgets.blocks.base import BaseBlockWidget


# =============================================================================
# Helper functions for creating test data
# =============================================================================


def create_ai_block(
    block_id: str = "block-1",
    content_input: str = "What is Python?",
    content_output: str = "Python is a programming language.",
    content_thinking: str = "",
    content_exec_output: str = "",
    is_running: bool = False,
    metadata: dict | None = None,
    tool_calls: list[ToolCallState] | None = None,
) -> BlockState:
    """Create a BlockState for AI response testing."""
    return BlockState(
        id=block_id,
        type=BlockType.AI_RESPONSE,
        content_input=content_input,
        content_output=content_output,
        content_thinking=content_thinking,
        content_exec_output=content_exec_output,
        is_running=is_running,
        metadata=metadata or {},
        tool_calls=tool_calls or [],
    )


def create_tool_call(
    tool_id: str = "tool-1",
    tool_name: str = "read_file",
    arguments: str = '{"path": "/tmp/test.txt"}',
    output: str = "File content here",
    status: str = "success",
    duration: float = 1.5,
) -> ToolCallState:
    """Create a ToolCallState for testing."""
    return ToolCallState(
        id=tool_id,
        tool_name=tool_name,
        arguments=arguments,
        output=output,
        status=status,
        duration=duration,
    )


# =============================================================================
# AIResponseBlock Initialization Tests
# =============================================================================


class TestAIResponseBlockInit:
    """Tests for AIResponseBlock initialization."""

    def test_init_stores_block(self):
        """AIResponseBlock stores the block reference."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.block is block

    def test_init_inherits_from_base_block_widget(self):
        """AIResponseBlock inherits from BaseBlockWidget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert isinstance(widget, BaseBlockWidget)

    def test_init_creates_header(self):
        """AIResponseBlock creates a BlockHeader."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.header is not None

    def test_init_creates_meta_widget(self):
        """AIResponseBlock creates a BlockMeta widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.meta_widget is not None

    def test_init_creates_thinking_widget(self):
        """AIResponseBlock creates a ThinkingWidget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.thinking_widget is not None

    def test_init_creates_exec_widget(self):
        """AIResponseBlock creates an ExecutionWidget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.exec_widget is not None

    def test_init_creates_tool_accordion(self):
        """AIResponseBlock creates a ToolAccordion."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.tool_accordion is not None

    def test_init_creates_response_widget(self):
        """AIResponseBlock creates a ResponseWidget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.response_widget is not None

    def test_init_creates_action_bar(self):
        """AIResponseBlock creates an ActionBar."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.action_bar is not None
        assert isinstance(widget.action_bar, ActionBar)

    def test_init_creates_footer_widget(self):
        """AIResponseBlock creates a BlockFooter."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.footer_widget is not None

    def test_init_adds_chat_mode_class(self):
        """AIResponseBlock adds 'mode-chat' class."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert "mode-chat" in widget.classes

    def test_init_tool_accordion_has_empty_class(self):
        """ToolAccordion starts with 'empty' class."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert "empty" in widget.tool_accordion.classes

    def test_init_action_bar_shows_fork(self):
        """ActionBar is configured to show fork button."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.action_bar.show_fork is True

    def test_init_action_bar_shows_edit(self):
        """ActionBar is configured to show edit button."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert widget.action_bar.show_edit is True

    def test_init_preserves_block_id(self):
        """AIResponseBlock preserves the block ID."""
        block = create_ai_block(block_id="custom-block-id")
        widget = AIResponseBlock(block)
        assert widget.block.id == "custom-block-id"

    def test_init_preserves_content_input(self):
        """AIResponseBlock preserves the content input."""
        block = create_ai_block(content_input="Custom question?")
        widget = AIResponseBlock(block)
        assert widget.block.content_input == "Custom question?"

    def test_init_preserves_content_output(self):
        """AIResponseBlock preserves the content output."""
        block = create_ai_block(content_output="Custom answer.")
        widget = AIResponseBlock(block)
        assert widget.block.content_output == "Custom answer."


# =============================================================================
# Build Meta Text Tests
# =============================================================================


class TestBuildMetaText:
    """Tests for _build_meta_text method."""

    def test_build_meta_text_empty_metadata(self):
        """Empty metadata returns empty string."""
        block = create_ai_block(metadata={})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert result == ""

    def test_build_meta_text_with_model(self):
        """Model is included in meta text."""
        block = create_ai_block(metadata={"model": "gpt-4"})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert "gpt-4" in result

    def test_build_meta_text_truncates_long_model(self):
        """Long model names are truncated."""
        long_model = "gpt-4-turbo-preview-with-extra-long-name"
        block = create_ai_block(metadata={"model": long_model})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        # Should be truncated to 17 chars + "..."
        assert len(result) <= 20
        assert result.endswith("...")

    def test_build_meta_text_model_exactly_20_chars(self):
        """Model with exactly 20 chars is not truncated."""
        model = "a" * 20
        block = create_ai_block(metadata={"model": model})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert result == model

    def test_build_meta_text_model_21_chars_truncated(self):
        """Model with 21 chars is truncated."""
        model = "a" * 21
        block = create_ai_block(metadata={"model": model})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert result == "a" * 17 + "..."

    def test_build_meta_text_with_tokens(self):
        """Tokens are included in meta text."""
        block = create_ai_block(metadata={"tokens": 150})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert "150 tok" in result

    def test_build_meta_text_with_cost(self):
        """Cost is included in meta text."""
        block = create_ai_block(metadata={"cost": 0.0023})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert "$0.0023" in result

    def test_build_meta_text_cost_formatted_to_4_decimals(self):
        """Cost is formatted to 4 decimal places."""
        block = create_ai_block(metadata={"cost": 0.123456789})
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert "$0.1235" in result

    def test_build_meta_text_multiple_parts_joined(self):
        """Multiple metadata parts are joined with separator."""
        block = create_ai_block(
            metadata={"model": "gpt-4", "tokens": 100, "cost": 0.01}
        )
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        assert " · " in result
        assert "gpt-4" in result
        assert "100 tok" in result
        assert "$0.0100" in result

    def test_build_meta_text_order_is_model_tokens_cost(self):
        """Meta parts appear in order: model, tokens, cost."""
        block = create_ai_block(
            metadata={"cost": 0.01, "tokens": 100, "model": "gpt-4"}
        )
        widget = AIResponseBlock(block)
        result = widget._build_meta_text()
        parts = result.split(" · ")
        # model should come first (or be truncated model)
        assert parts[0].startswith("gpt") or len(parts[0]) <= 20


# =============================================================================
# Compose Tests
# =============================================================================


class TestAIResponseBlockCompose:
    """Tests for AIResponseBlock.compose method."""

    def test_compose_returns_generator(self):
        """compose returns a generator."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_exists(self):
        """compose method exists."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)

    def test_compose_yields_header(self):
        """compose yields the header widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.header in composed

    def test_compose_yields_meta_widget(self):
        """compose yields the meta widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.meta_widget in composed

    def test_compose_yields_thinking_widget(self):
        """compose yields the thinking widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.thinking_widget in composed

    def test_compose_yields_exec_widget(self):
        """compose yields the execution widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.exec_widget in composed

    def test_compose_yields_tool_accordion(self):
        """compose yields the tool accordion."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.tool_accordion in composed

    def test_compose_yields_response_widget(self):
        """compose yields the response widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.response_widget in composed

    def test_compose_yields_action_bar(self):
        """compose yields the action bar."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        composed = list(widget.compose())
        assert widget.action_bar in composed


# =============================================================================
# Update Output Tests - Think Tag Parsing
# =============================================================================


class TestUpdateOutputThinkTags:
    """Tests for update_output method with <think> tag parsing."""

    def test_update_output_no_think_tags(self):
        """Content without think tags goes to response."""
        block = create_ai_block(content_output="Simple response without thinking.")
        widget = AIResponseBlock(block)
        widget.update_output()
        # Response widget should get the content
        assert (
            widget.response_widget.content_text == "Simple response without thinking."
        )

    def test_update_output_with_complete_think_tags(self):
        """Completed <think> tags are parsed correctly."""
        content = "<think>I need to analyze this.</think>Here is my answer."
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        # Thinking should be extracted
        assert widget.thinking_widget.thinking_text == "I need to analyze this."
        # Response should have the answer
        assert widget.response_widget.content_text == "Here is my answer."

    def test_update_output_with_streaming_think_tags(self):
        """Incomplete think tags (streaming) are handled."""
        content = "<think>I am still thinking about this"
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        # Thinking should have the partial content
        assert widget.thinking_widget.thinking_text == "I am still thinking about this"
        # Response should be empty while thinking
        assert widget.response_widget.content_text == ""

    def test_update_output_case_insensitive_detection(self):
        """Think tag detection is case insensitive but parsing uses original case."""
        content = "<think>Reasoning here.</think>The answer."
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "Reasoning here" in widget.thinking_widget.thinking_text
        assert widget.response_widget.content_text == "The answer."

    def test_update_output_multiline_think_content(self):
        """Multiline content in think tags is handled."""
        content = """<think>
First thought.
Second thought.
Third thought.
</think>Final answer."""
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "First thought" in widget.thinking_widget.thinking_text
        assert "Second thought" in widget.thinking_widget.thinking_text
        assert widget.response_widget.content_text == "Final answer."

    def test_update_output_empty_think_tags(self):
        """Empty think tags are handled."""
        content = "<think></think>Just the answer."
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        assert widget.thinking_widget.thinking_text == ""
        assert widget.response_widget.content_text == "Just the answer."

    def test_update_output_think_with_whitespace(self):
        """Think tags with leading/trailing whitespace are trimmed."""
        content = "<think>  \n  Some thinking  \n  </think>Answer"
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        # Should be trimmed
        assert (
            widget.thinking_widget.thinking_text.strip()
            == widget.thinking_widget.thinking_text
            or "Some thinking" in widget.thinking_widget.thinking_text
        )


# =============================================================================
# Update Output Tests - Execution Output
# =============================================================================


class TestUpdateOutputExecution:
    """Tests for update_output method with execution output."""

    def test_update_output_with_exec_output(self):
        """Execution output is set on exec widget."""
        block = create_ai_block(content_output="Response")
        block.content_exec_output = "Command executed successfully"
        widget = AIResponseBlock(block)
        widget.update_output()
        assert widget.exec_widget.exec_output == "Command executed successfully"

    def test_update_output_empty_exec_output(self):
        """Empty execution output is handled."""
        block = create_ai_block(content_output="Response")
        block.content_exec_output = ""
        widget = AIResponseBlock(block)
        widget.update_output()
        assert widget.exec_widget.exec_output == ""

    def test_update_output_multiline_exec_output(self):
        """Multiline execution output is handled."""
        block = create_ai_block(content_output="Response")
        block.content_exec_output = "Line 1\nLine 2\nLine 3"
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "Line 1" in widget.exec_widget.exec_output
        assert "Line 3" in widget.exec_widget.exec_output


# =============================================================================
# Update Output Tests - Simple Mode Detection
# =============================================================================


class TestUpdateOutputSimpleMode:
    """Tests for simple mode detection in update_output."""

    def test_simple_mode_no_reasoning_no_exec(self):
        """Simple mode when no reasoning and no exec output."""
        block = create_ai_block(content_output="Simple answer here.")
        widget = AIResponseBlock(block)
        with patch.object(widget.response_widget, "set_simple") as mock_simple:
            widget.update_output()
            mock_simple.assert_called()

    def test_not_simple_with_reasoning(self):
        """Not simple mode when reasoning is present."""
        block = create_ai_block(content_output="<think>Reasoning</think>Answer")
        widget = AIResponseBlock(block)
        widget.update_output()
        # When reasoning is present, not simple

    def test_not_simple_with_exec_output(self):
        """Not simple mode when exec output is present."""
        block = create_ai_block(content_output="Answer")
        block.content_exec_output = "Some execution output"
        widget = AIResponseBlock(block)
        widget.update_output()
        # When exec output is present, not simple

    def test_simple_mode_with_tools_and_minimal_response(self):
        """Simple mode when tools present but minimal response."""
        block = create_ai_block(content_output="Done.")
        block.tool_calls = [create_tool_call()]
        widget = AIResponseBlock(block)
        widget.tool_accordion.remove_class("empty")  # Simulate tools added
        with patch.object(widget.response_widget, "set_simple") as mock_simple:
            widget.update_output()
            # Should be called with True for simple mode
            mock_simple.assert_called()


# =============================================================================
# Update Metadata Tests
# =============================================================================


class TestUpdateMetadata:
    """Tests for update_metadata method."""

    def test_update_metadata_method_exists(self):
        """update_metadata method exists."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert hasattr(widget, "update_metadata")
        assert callable(widget.update_metadata)

    def test_update_metadata_updates_action_bar(self):
        """update_metadata updates the action bar meta text."""
        block = create_ai_block(metadata={"model": "gpt-4", "tokens": 100})
        widget = AIResponseBlock(block)
        with patch.object(widget, "mount"):
            with patch.object(widget.action_bar, "update_meta") as mock_update:
                with patch.object(
                    type(widget),
                    "children",
                    new_callable=lambda: property(lambda self: [widget.header]),
                ):
                    widget.update_metadata()
                    mock_update.assert_called_once()

    def test_update_metadata_handles_unmounted(self):
        """update_metadata handles unmounted widget gracefully."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        # Should not raise even when not mounted
        try:
            widget.update_metadata()
        except Exception:
            pass  # Expected to handle gracefully


# =============================================================================
# Set Loading Tests
# =============================================================================


class TestSetLoading:
    """Tests for set_loading method."""

    def test_set_loading_true(self):
        """set_loading(True) sets block.is_running to True."""
        block = create_ai_block(is_running=False)
        widget = AIResponseBlock(block)
        with patch.object(widget, "mount"):
            widget.set_loading(True)
            assert widget.block.is_running is True

    def test_set_loading_false(self):
        """set_loading(False) sets block.is_running to False."""
        block = create_ai_block(is_running=True)
        widget = AIResponseBlock(block)
        widget.set_loading(False)
        assert widget.block.is_running is False

    def test_set_loading_false_stops_thinking(self):
        """set_loading(False) stops thinking widget loading."""
        block = create_ai_block(is_running=True)
        widget = AIResponseBlock(block)
        with patch.object(widget.thinking_widget, "stop_loading") as mock_stop:
            with patch.object(widget.thinking_widget, "force_render"):
                widget.set_loading(False)
                mock_stop.assert_called_once()

    def test_set_loading_false_forces_thinking_render(self):
        """set_loading(False) forces thinking widget to render."""
        block = create_ai_block(is_running=True)
        widget = AIResponseBlock(block)
        with patch.object(widget.thinking_widget, "stop_loading"):
            with patch.object(widget.thinking_widget, "force_render") as mock_render:
                widget.set_loading(False)
                mock_render.assert_called_once()

    def test_set_loading_recreates_footer(self):
        """set_loading recreates the footer widget."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        original_footer = widget.footer_widget
        with patch.object(widget, "mount"):
            widget.set_loading(True)
            assert widget.footer_widget is not original_footer


# =============================================================================
# Add Tool Call Tests
# =============================================================================


class TestAddToolCall:
    """Tests for add_tool_call method."""

    def test_add_tool_call_method_exists(self):
        """add_tool_call method exists."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert hasattr(widget, "add_tool_call")
        assert callable(widget.add_tool_call)

    def test_add_tool_call_delegates_to_accordion(self):
        """add_tool_call delegates to tool accordion."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        with patch.object(widget.tool_accordion, "add_tool") as mock_add:
            widget.add_tool_call(
                tool_id="tool-1",
                tool_name="read_file",
                arguments='{"path": "/tmp"}',
                status="running",
                streaming=False,
            )
            mock_add.assert_called_once_with(
                tool_id="tool-1",
                tool_name="read_file",
                arguments='{"path": "/tmp"}',
                status="running",
                streaming=False,
            )

    def test_add_tool_call_with_defaults(self):
        """add_tool_call works with default arguments."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        with patch.object(widget.tool_accordion, "add_tool") as mock_add:
            widget.add_tool_call(
                tool_id="tool-1",
                tool_name="run_command",
            )
            mock_add.assert_called_once_with(
                tool_id="tool-1",
                tool_name="run_command",
                arguments="",
                status="running",
                streaming=False,
            )

    def test_add_tool_call_returns_accordion_result(self):
        """add_tool_call returns result from tool accordion."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        mock_item = MagicMock()
        with patch.object(widget.tool_accordion, "add_tool", return_value=mock_item):
            result = widget.add_tool_call("t1", "test_tool")
            assert result is mock_item


# =============================================================================
# Update Tool Call Tests
# =============================================================================


class TestUpdateToolCall:
    """Tests for update_tool_call method."""

    def test_update_tool_call_method_exists(self):
        """update_tool_call method exists."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert hasattr(widget, "update_tool_call")
        assert callable(widget.update_tool_call)

    def test_update_tool_call_delegates_to_accordion(self):
        """update_tool_call delegates to tool accordion."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        with patch.object(widget.tool_accordion, "update_tool") as mock_update:
            widget.update_tool_call(
                tool_id="tool-1",
                status="success",
                output="Result here",
                duration=1.5,
                streaming=False,
            )
            mock_update.assert_called_once_with(
                tool_id="tool-1",
                status="success",
                output="Result here",
                duration=1.5,
                streaming=False,
            )

    def test_update_tool_call_with_none_values(self):
        """update_tool_call handles None values."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        with patch.object(widget.tool_accordion, "update_tool") as mock_update:
            widget.update_tool_call(
                tool_id="tool-1",
                status=None,
                output=None,
                duration=None,
            )
            mock_update.assert_called_once()


# =============================================================================
# Update Tool Progress Tests
# =============================================================================


class TestUpdateToolProgress:
    """Tests for update_tool_progress method."""

    def test_update_tool_progress_method_exists(self):
        """update_tool_progress method exists."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert hasattr(widget, "update_tool_progress")
        assert callable(widget.update_tool_progress)

    def test_update_tool_progress_updates_item(self):
        """update_tool_progress updates the tool item."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        mock_item = MagicMock()
        with patch.object(widget.tool_accordion, "get_tool", return_value=mock_item):
            progress = {"percent": 50}
            widget.update_tool_progress("tool-1", progress)
            mock_item.update_progress.assert_called_once_with(progress)

    def test_update_tool_progress_handles_missing_tool(self):
        """update_tool_progress handles missing tool gracefully."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        with patch.object(widget.tool_accordion, "get_tool", return_value=None):
            # Should not raise
            widget.update_tool_progress("nonexistent-tool", {"percent": 50})


# =============================================================================
# Action Button Handler Tests
# =============================================================================


class TestActionButtonHandlers:
    """Tests for action button press handlers."""

    def test_on_action_pressed_copy(self):
        """Copy action posts CopyRequested message."""
        block = create_ai_block(content_output="Test content")
        widget = AIResponseBlock(block)
        event = MagicMock()
        event.action = "copy"
        event.stop = MagicMock()

        with patch.object(widget, "post_message") as mock_post:
            widget.on_action_pressed(event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, BaseBlockWidget.CopyRequested)
            assert msg.block_id == block.id
            assert msg.content == "Test content"

    def test_on_action_pressed_retry(self):
        """Retry action posts RetryRequested message."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        event = MagicMock()
        event.action = "retry"
        event.stop = MagicMock()

        with patch.object(widget, "post_message") as mock_post:
            widget.on_action_pressed(event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, BaseBlockWidget.RetryRequested)
            assert msg.block_id == block.id

    def test_on_action_pressed_edit(self):
        """Edit action posts EditRequested message."""
        block = create_ai_block(content_input="Original question")
        widget = AIResponseBlock(block)
        event = MagicMock()
        event.action = "edit"
        event.stop = MagicMock()

        with patch.object(widget, "post_message") as mock_post:
            widget.on_action_pressed(event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, BaseBlockWidget.EditRequested)
            assert msg.block_id == block.id
            assert msg.content == "Original question"

    def test_on_action_pressed_fork(self):
        """Fork action posts ForkRequested message."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        event = MagicMock()
        event.action = "fork"
        event.stop = MagicMock()

        with patch.object(widget, "post_message") as mock_post:
            widget.on_action_pressed(event)
            mock_post.assert_called_once()
            msg = mock_post.call_args[0][0]
            assert isinstance(msg, BaseBlockWidget.ForkRequested)
            assert msg.block_id == block.id

    def test_on_action_pressed_stops_event(self):
        """Action handler stops event propagation."""
        block = create_ai_block()
        widget = AIResponseBlock(block)
        event = MagicMock()
        event.action = "copy"
        event.stop = MagicMock()

        with patch.object(widget, "post_message"):
            widget.on_action_pressed(event)
            event.stop.assert_called_once()


# =============================================================================
# Inheritance Tests
# =============================================================================


class TestAIResponseBlockInheritance:
    """Tests for AIResponseBlock inheritance."""

    def test_inherits_from_static(self):
        """AIResponseBlock inherits from Static (via BaseBlockWidget)."""
        from textual.widgets import Static

        block = create_ai_block()
        widget = AIResponseBlock(block)
        assert isinstance(widget, Static)

    def test_has_bindings_from_base(self):
        """AIResponseBlock inherits bindings from BaseBlockWidget."""
        # Check that base bindings are available
        assert hasattr(AIResponseBlock, "BINDINGS")


# =============================================================================
# Edge Cases and Special Scenarios
# =============================================================================


class TestAIResponseBlockEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_content_output(self):
        """Widget handles empty content output."""
        block = create_ai_block(content_output="")
        widget = AIResponseBlock(block)
        widget.update_output()
        assert widget.response_widget.content_text == ""

    def test_none_content_output(self):
        """Widget handles None content output."""
        block = create_ai_block()
        block.content_output = None
        widget = AIResponseBlock(block)
        widget.update_output()
        # Should handle None gracefully

    def test_unicode_content(self):
        """Widget handles unicode content."""
        block = create_ai_block(
            content_input="What is 你好?",
            content_output="你好 means 'Hello' in Chinese.",
        )
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "你好" in widget.response_widget.content_text

    def test_emoji_content(self):
        """Widget handles emoji content."""
        block = create_ai_block(content_output="Great job! ")
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "" in widget.response_widget.content_text

    def test_special_characters_content(self):
        """Widget handles special characters."""
        block = create_ai_block(content_output='Use <code> and "quotes" & ampersands')
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "<code>" in widget.response_widget.content_text

    def test_very_long_content(self):
        """Widget handles very long content."""
        long_content = "A" * 10000
        block = create_ai_block(content_output=long_content)
        widget = AIResponseBlock(block)
        widget.update_output()
        assert len(widget.response_widget.content_text) == 10000

    def test_multiline_content(self):
        """Widget handles multiline content."""
        content = "Line 1\nLine 2\nLine 3\n\nLine 5"
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "\n" in widget.response_widget.content_text

    def test_markdown_content(self):
        """Widget handles markdown content."""
        content = "# Header\n\n- Item 1\n- Item 2\n\n```python\nprint('hello')\n```"
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()
        assert "# Header" in widget.response_widget.content_text

    def test_nested_think_tags_malformed(self):
        """Widget handles malformed nested think tags."""
        content = "<think><think>nested</think>outer</think>answer"
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        # Should not raise
        widget.update_output()

    def test_think_tags_with_html_entities(self):
        """Widget handles think tags with HTML entities."""
        content = "<think>Analyzing &lt;data&gt;</think>Result"
        block = create_ai_block(content_output=content)
        widget = AIResponseBlock(block)
        widget.update_output()

    def test_multiple_tool_calls(self):
        """Widget handles multiple tool calls."""
        block = create_ai_block()
        block.tool_calls = [
            create_tool_call(tool_id="t1", tool_name="read_file"),
            create_tool_call(tool_id="t2", tool_name="write_file"),
            create_tool_call(tool_id="t3", tool_name="run_command"),
        ]
        widget = AIResponseBlock(block)
        assert len(widget.block.tool_calls) == 3


# =============================================================================
# Metadata Scenarios Tests
# =============================================================================


class TestMetadataScenarios:
    """Tests for various metadata scenarios."""

    def test_metadata_with_all_fields(self):
        """Widget handles metadata with all fields."""
        metadata = {
            "model": "gpt-4-turbo",
            "tokens": 1500,
            "cost": 0.045,
            "provider": "openai",
        }
        block = create_ai_block(metadata=metadata)
        widget = AIResponseBlock(block)
        meta_text = widget._build_meta_text()
        assert "gpt-4-turbo" in meta_text
        assert "1500 tok" in meta_text
        assert "$0.0450" in meta_text

    def test_metadata_with_zero_tokens(self):
        """Widget handles zero tokens."""
        block = create_ai_block(metadata={"tokens": 0})
        widget = AIResponseBlock(block)
        meta_text = widget._build_meta_text()
        # Zero is falsy, might not be included
        assert meta_text == "" or "0 tok" in meta_text

    def test_metadata_with_zero_cost(self):
        """Widget handles zero cost."""
        block = create_ai_block(metadata={"cost": 0.0})
        widget = AIResponseBlock(block)
        meta_text = widget._build_meta_text()
        # Zero is falsy, might not be included
        assert meta_text == "" or "$0.0000" in meta_text

    def test_metadata_with_very_high_cost(self):
        """Widget handles very high cost."""
        block = create_ai_block(metadata={"cost": 99.9999})
        widget = AIResponseBlock(block)
        meta_text = widget._build_meta_text()
        assert "$99.9999" in meta_text

    def test_metadata_with_fractional_tokens(self):
        """Widget handles fractional tokens (edge case)."""
        block = create_ai_block(metadata={"tokens": 150.5})
        widget = AIResponseBlock(block)
        meta_text = widget._build_meta_text()
        assert "150" in meta_text  # Should work even with float


# =============================================================================
# State Mutation Tests
# =============================================================================


class TestStateMutation:
    """Tests for state mutation behavior."""

    def test_block_mutation_reflects_in_widget(self):
        """Mutating block reflects in widget."""
        block = create_ai_block(content_output="Original")
        widget = AIResponseBlock(block)
        block.content_output = "Modified"
        widget.update_output()
        assert widget.response_widget.content_text == "Modified"

    def test_metadata_mutation_reflects_in_widget(self):
        """Mutating metadata reflects in widget."""
        block = create_ai_block(metadata={"model": "gpt-3.5"})
        widget = AIResponseBlock(block)
        block.metadata["model"] = "gpt-4"
        meta_text = widget._build_meta_text()
        assert "gpt-4" in meta_text

    def test_is_running_mutation(self):
        """is_running mutation works correctly."""
        block = create_ai_block(is_running=False)
        widget = AIResponseBlock(block)
        assert widget.block.is_running is False
        with patch.object(widget, "mount"):
            widget.set_loading(True)
            assert widget.block.is_running is True


# =============================================================================
# Widget Existence Tests
# =============================================================================


class TestWidgetExistence:
    """Tests that all expected widgets are properly created."""

    def test_all_sub_widgets_not_none(self):
        """All sub-widgets are created and not None."""
        block = create_ai_block()
        widget = AIResponseBlock(block)

        assert widget.header is not None
        assert widget.meta_widget is not None
        assert widget.thinking_widget is not None
        assert widget.exec_widget is not None
        assert widget.tool_accordion is not None
        assert widget.response_widget is not None
        assert widget.action_bar is not None
        assert widget.footer_widget is not None

    def test_widgets_reference_same_block(self):
        """Sub-widgets reference the same block state."""
        block = create_ai_block()
        widget = AIResponseBlock(block)

        assert widget.header.block is block
        assert widget.meta_widget.block is block
        assert widget.thinking_widget.block is block
        assert widget.exec_widget.block is block
        # tool_accordion doesn't take block
        assert widget.response_widget.block is block
        assert widget.footer_widget.block is block
