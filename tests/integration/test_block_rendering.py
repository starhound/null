"""Integration tests for block widget rendering.

Tests that block widgets render correctly within the app context.
"""

import pytest

from models import BlockState, BlockType, ToolCallState
from widgets.blocks import (
    AIResponseBlock,
    CommandBlock,
    SystemBlock,
    ToolCallBlock,
    create_block,
)
from widgets.blocks.actions import ActionBar, ActionButton
from widgets.blocks.base import BaseBlockWidget


# Helper to submit commands
async def submit_command(pilot, app, command: str):
    """Submit a command via the input widget."""
    from widgets import InputController

    input_widget = app.query_one("#input", InputController)
    input_widget.text = command
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestBlockFactory:
    """Tests for create_block factory function."""

    def test_create_command_block(self, sample_block_state):
        """create_block returns CommandBlock for COMMAND type."""
        block = create_block(sample_block_state)
        assert isinstance(block, CommandBlock)

    def test_create_ai_block(self, sample_ai_block_state):
        """create_block returns AIResponseBlock for AI_RESPONSE type."""
        block = create_block(sample_ai_block_state)
        assert isinstance(block, AIResponseBlock)

    def test_create_system_block(self):
        """create_block returns SystemBlock for SYSTEM_MSG type."""
        state = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input="system",
            content_output="System message content",
        )
        block = create_block(state)
        assert isinstance(block, SystemBlock)

    def test_create_tool_call_block(self):
        """create_block returns ToolCallBlock for TOOL_CALL type."""
        state = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="tool",
            content_output="Tool output",
            metadata={"tool_name": "read_file", "arguments": '{"path": "/tmp/test"}'},
        )
        block = create_block(state)
        assert isinstance(block, ToolCallBlock)


class TestAIBlockRendering:
    """Tests for AIResponseBlock rendering."""

    def test_ai_block_creates_with_state(self, sample_ai_block_state):
        """AIBlock creates correctly from BlockState."""
        block_widget = AIResponseBlock(sample_ai_block_state)
        assert block_widget.block == sample_ai_block_state
        assert block_widget.header is not None
        assert block_widget.response_widget is not None

    def test_ai_block_with_thinking_tags(self):
        """AIBlock correctly parses <think> tags."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Explain recursion",
            content_output="<think>Let me reason about this...</think>Recursion is when a function calls itself.",
            is_running=False,
        )

        block_widget = AIResponseBlock(state)
        block_widget.update_output()

        assert block_widget.thinking_widget is not None

    def test_ai_block_meta_text_building(self):
        """AIBlock builds metadata text correctly."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="Response",
            metadata={"model": "gpt-4", "tokens": 100, "cost": 0.0015},
        )

        block_widget = AIResponseBlock(state)
        meta_text = block_widget._build_meta_text()

        assert "gpt-4" in meta_text
        assert "100 tok" in meta_text
        assert "$0.0015" in meta_text

    def test_ai_block_truncates_long_model_name(self):
        """AIBlock truncates model names longer than 20 chars."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="Response",
            metadata={"model": "anthropic-claude-3-5-sonnet-20241022"},
        )

        block_widget = AIResponseBlock(state)
        meta_text = block_widget._build_meta_text()

        assert len(meta_text) < 40
        assert "..." in meta_text


class TestCommandBlockRendering:
    """Tests for CommandBlock rendering."""

    def test_command_block_creates_with_state(self, sample_block_state):
        """CommandBlock creates correctly from BlockState."""
        block_widget = CommandBlock(sample_block_state)
        assert block_widget.block == sample_block_state
        assert block_widget.header is not None
        assert block_widget.body_widget is not None

    def test_command_block_update_output(self, sample_block_state):
        """CommandBlock.update_output updates body content."""
        block_widget = CommandBlock(sample_block_state)
        sample_block_state.content_output = "updated output"
        block_widget.update_output()
        assert block_widget.body_widget.content_text == "updated output"

    def test_command_block_mode_defaults_to_line(self, sample_block_state):
        """CommandBlock starts in line mode."""
        block_widget = CommandBlock(sample_block_state)
        assert block_widget.mode == "line"


class TestToolCallBlockRendering:
    """Tests for ToolCallBlock rendering."""

    def test_tool_call_block_creates_with_state(self):
        """ToolCallBlock creates correctly from BlockState."""
        state = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="read_file",
            content_output="File content here",
            metadata={
                "tool_name": "read_file",
                "arguments": '{"path": "/tmp/test.txt"}',
            },
        )
        block_widget = ToolCallBlock(state)
        assert block_widget.block == state
        assert block_widget.header is not None
        assert block_widget.body_widget is not None

    def test_tool_call_block_update_output(self):
        """ToolCallBlock.update_output updates body."""
        state = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="run_command",
            content_output="",
        )
        block_widget = ToolCallBlock(state)
        state.content_output = "Command executed successfully"
        block_widget.update_output()
        assert block_widget.body_widget.content_text == "Command executed successfully"


class TestSystemBlockRendering:
    """Tests for SystemBlock rendering."""

    def test_system_block_creates_with_state(self):
        """SystemBlock creates correctly from BlockState."""
        state = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input="System",
            content_output="Session started. Welcome to Null Terminal.",
        )
        block_widget = SystemBlock(state)
        assert block_widget.block == state
        assert block_widget.header is not None
        assert block_widget.body_widget is not None

    def test_system_block_update_output(self):
        """SystemBlock.update_output updates body."""
        state = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input="System",
            content_output="Initial message",
        )
        block_widget = SystemBlock(state)
        state.content_output = "Updated system message"
        block_widget.update_output()
        assert block_widget.body_widget.content_text == "Updated system message"


class TestBlockActions:
    """Tests for block action buttons (copy, retry, edit, fork)."""

    def test_ai_block_has_action_bar(self):
        """AIResponseBlock includes ActionBar."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="Response",
        )
        block_widget = AIResponseBlock(state)
        assert block_widget.action_bar is not None
        assert isinstance(block_widget.action_bar, ActionBar)

    def test_action_bar_creates_with_block_id(self):
        """ActionBar creates with correct block_id."""
        action_bar = ActionBar(block_id="test-123", show_fork=True, show_edit=True)
        assert action_bar.block_id == "test-123"

    def test_action_bar_show_fork_option(self):
        """ActionBar respects show_fork option."""
        action_bar = ActionBar(block_id="test-123", show_fork=False, show_edit=True)
        assert action_bar.show_fork is False

    def test_action_bar_show_edit_option(self):
        """ActionBar respects show_edit option."""
        action_bar = ActionBar(block_id="test-123", show_fork=True, show_edit=False)
        assert action_bar.show_edit is False

    def test_action_bar_meta_text(self):
        """ActionBar stores meta text."""
        action_bar = ActionBar(block_id="test-123", meta_text="gpt-4 · 100 tok")
        assert action_bar.meta_text == "gpt-4 · 100 tok"


class TestBlockCollapsing:
    """Tests for block collapsing/expanding functionality."""

    def test_ai_block_thinking_widget_exists(self):
        """AIBlock has thinking widget for collapsible reasoning."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="<think>Reasoning here</think>Final answer",
        )
        block_widget = AIResponseBlock(state)
        assert block_widget.thinking_widget is not None

    def test_ai_block_tool_accordion_exists(self):
        """AIBlock has tool accordion for collapsible tool calls."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="Response",
            tool_calls=[
                ToolCallState(
                    id="tool-1",
                    tool_name="read_file",
                    arguments='{"path": "/tmp/test"}',
                    status="success",
                )
            ],
        )
        block_widget = AIResponseBlock(state)
        assert block_widget.tool_accordion is not None


class TestBlockLoadingState:
    """Tests for block loading/running state."""

    def test_command_block_set_loading(self):
        """CommandBlock.set_loading updates running state."""
        state = BlockState(
            type=BlockType.COMMAND,
            content_input="sleep 5",
            content_output="",
            is_running=True,
        )
        block_widget = CommandBlock(state)
        assert state.is_running is True
        block_widget.set_loading(False)
        assert state.is_running is False

    def test_ai_block_set_loading(self):
        """AIResponseBlock.set_loading updates running state."""
        state = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Test",
            content_output="",
            is_running=True,
        )
        block_widget = AIResponseBlock(state)
        assert state.is_running is True
        block_widget.set_loading(False)
        assert state.is_running is False

    def test_base_block_set_exit_code(self):
        """BaseBlockWidget.set_exit_code sets code and stops loading."""
        state = BlockState(
            type=BlockType.COMMAND,
            content_input="false",
            content_output="",
            is_running=True,
        )
        block_widget = BaseBlockWidget(state)
        block_widget.set_exit_code(1)
        assert state.exit_code == 1
        assert state.is_running is False


class TestBlockMessages:
    """Tests for block message types."""

    def test_retry_requested_message(self):
        """RetryRequested message contains block_id."""
        msg = BaseBlockWidget.RetryRequested(block_id="test-block-123")
        assert msg.block_id == "test-block-123"

    def test_edit_requested_message(self):
        """EditRequested message contains block_id and content."""
        msg = BaseBlockWidget.EditRequested(
            block_id="test-block-456", content="original query"
        )
        assert msg.block_id == "test-block-456"
        assert msg.content == "original query"

    def test_copy_requested_message(self):
        """CopyRequested message contains block_id and content."""
        msg = BaseBlockWidget.CopyRequested(
            block_id="test-block-789", content="content to copy"
        )
        assert msg.block_id == "test-block-789"
        assert msg.content == "content to copy"

    def test_fork_requested_message(self):
        """ForkRequested message contains block_id."""
        msg = BaseBlockWidget.ForkRequested(block_id="test-block-abc")
        assert msg.block_id == "test-block-abc"

    def test_view_requested_message(self):
        """ViewRequested message contains block_id and view_type."""
        msg = BaseBlockWidget.ViewRequested(block_id="test-block-def", view_type="json")
        assert msg.block_id == "test-block-def"
        assert msg.view_type == "json"


class TestActionButtonMessages:
    """Tests for ActionButton message handling."""

    def test_action_pressed_message(self):
        """ActionPressed message contains action and block_id."""
        msg = ActionButton.ActionPressed(action="copy", block_id="block-123")
        assert msg.action == "copy"
        assert msg.block_id == "block-123"

    def test_action_bar_update_meta(self):
        """ActionBar.update_meta updates stored text."""
        action_bar = ActionBar(block_id="test-123", meta_text="original")
        action_bar.update_meta("new-model · 200 tok")
        assert action_bar.meta_text == "new-model · 200 tok"
