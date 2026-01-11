"""Tests for widgets/blocks/tool_call.py - ToolCallBlock widget."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from models import BlockState, BlockType
from widgets.blocks.tool_call import ToolCallBlock
from widgets.blocks.parts import BlockHeader, BlockMeta, BlockBody
from widgets.blocks.base import BaseBlockWidget


class TestToolCallBlockInitialization:
    """Test ToolCallBlock initialization and constructor behavior."""

    def test_init_creates_widget_with_block(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.block is block

    def test_init_creates_header(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.header is not None
        assert isinstance(widget.header, BlockHeader)

    def test_init_creates_meta(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.meta is not None
        assert isinstance(widget.meta, BlockMeta)

    def test_init_creates_body_widget(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.body_widget is not None
        assert isinstance(widget.body_widget, BlockBody)

    def test_init_body_widget_uses_content_output(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test_tool",
            content_output="Tool execution result",
        )
        widget = ToolCallBlock(block)
        assert widget.body_widget._initial_text == "Tool execution result"

    def test_init_body_widget_handles_empty_output(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.body_widget._initial_text == ""

    def test_init_body_widget_handles_none_output(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test_tool",
            content_output=None,
        )
        # content_output=None should be handled gracefully
        widget = ToolCallBlock(block)
        assert widget.body_widget._initial_text == ""

    def test_init_header_receives_block(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.header.block is block

    def test_init_meta_receives_block(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        assert widget.meta.block is block


class TestToolCallBlockInheritance:
    """Test that ToolCallBlock properly inherits from BaseBlockWidget."""

    def test_inherits_from_base_block_widget(self):
        assert issubclass(ToolCallBlock, BaseBlockWidget)

    def test_has_bindings_from_parent(self):
        # BaseBlockWidget defines BINDINGS for copy, retry, edit, fork
        assert hasattr(ToolCallBlock, "BINDINGS")

    def test_set_loading_works(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        widget.set_loading(True)
        assert block.is_running is True
        widget.set_loading(False)
        assert block.is_running is False

    def test_set_exit_code_works(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        widget.set_loading(True)
        widget.set_exit_code(0)
        assert block.exit_code == 0
        assert block.is_running is False

    def test_set_exit_code_handles_errors(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        widget.set_loading(True)
        widget.set_exit_code(1)
        assert block.exit_code == 1
        assert block.is_running is False


class TestToolCallBlockCompose:
    """Test ToolCallBlock compose method."""

    def test_compose_returns_generator(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_yields_header_first(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        children = list(widget.compose())
        assert len(children) == 3
        assert children[0] is widget.header

    def test_compose_yields_meta_second(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        children = list(widget.compose())
        assert children[1] is widget.meta

    def test_compose_yields_body_third(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        children = list(widget.compose())
        assert children[2] is widget.body_widget

    def test_compose_yields_exactly_three_widgets(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test_tool")
        widget = ToolCallBlock(block)
        children = list(widget.compose())
        assert len(children) == 3


class TestToolCallBlockUpdateOutput:
    """Test ToolCallBlock update_output method."""

    def test_update_output_with_body_widget(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.content_output = "New output"
        widget = ToolCallBlock(block)
        widget.update_output()
        assert widget.body_widget.content_text == "New output"

    def test_update_output_uses_block_content_output(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        block.content_output = "Updated content"
        widget.update_output()
        assert widget.body_widget.content_text == "Updated content"

    def test_update_output_ignores_parameter(self):
        # The method accepts new_content parameter but uses self.block.content_output
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.content_output = "Block content"
        widget = ToolCallBlock(block)
        widget.update_output("This is ignored")
        assert widget.body_widget.content_text == "Block content"

    def test_update_output_handles_empty_content(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.content_output = ""
        widget = ToolCallBlock(block)
        widget.update_output()
        assert widget.body_widget.content_text == ""

    def test_update_output_handles_multiline_content(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.content_output = "Line 1\nLine 2\nLine 3"
        widget = ToolCallBlock(block)
        widget.update_output()
        assert widget.body_widget.content_text == "Line 1\nLine 2\nLine 3"

    def test_update_output_with_none_body_widget(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        widget.body_widget = None
        # Should not raise an exception
        widget.update_output()


class TestToolCallBlockUpdateMetadata:
    """Test ToolCallBlock update_metadata method."""

    def test_update_metadata_updates_meta_block(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            metadata={"provider": "test"},
        )
        widget = ToolCallBlock(block)
        new_block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            metadata={"provider": "updated"},
        )
        widget.block = new_block
        widget.update_metadata()
        assert widget.meta.block is new_block

    def test_update_metadata_with_none_meta(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        widget.meta = None
        # Should not raise an exception
        widget.update_metadata()

    def test_update_metadata_calls_refresh(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        mock_meta = MagicMock()
        widget.meta = mock_meta
        widget.update_metadata()
        mock_meta.refresh.assert_called_once()

    def test_update_metadata_preserves_block_reference(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        widget.update_metadata()
        assert widget.meta.block is block


class TestToolCallBlockWithMetadata:
    """Test ToolCallBlock with various metadata configurations."""

    def test_with_tool_name_metadata(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="run_command",
            metadata={"tool_name": "run_command"},
        )
        widget = ToolCallBlock(block)
        assert widget.block.metadata["tool_name"] == "run_command"

    def test_with_arguments_metadata(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="read_file",
            metadata={
                "tool_name": "read_file",
                "arguments": '{"path": "/tmp/test.txt"}',
            },
        )
        widget = ToolCallBlock(block)
        assert "arguments" in widget.block.metadata
        assert "path" in widget.block.metadata["arguments"]

    def test_with_provider_and_model_metadata(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test_tool",
            metadata={"provider": "openai", "model": "gpt-4"},
        )
        widget = ToolCallBlock(block)
        assert widget.block.metadata["provider"] == "openai"
        assert widget.block.metadata["model"] == "gpt-4"

    def test_with_empty_metadata(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test_tool",
            metadata={},
        )
        widget = ToolCallBlock(block)
        assert widget.block.metadata == {}


class TestToolCallBlockWithToolCalls:
    """Test ToolCallBlock with tool_calls in BlockState."""

    def test_with_tool_calls_list(self):
        from models import ToolCallState

        tool_call = ToolCallState(
            id="tc_1",
            tool_name="read_file",
            arguments='{"path": "/tmp/file.txt"}',
            output="File contents here",
            status="success",
        )
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            tool_calls=[tool_call],
        )
        widget = ToolCallBlock(block)
        assert len(widget.block.tool_calls) == 1
        assert widget.block.tool_calls[0].tool_name == "read_file"

    def test_with_multiple_tool_calls(self):
        from models import ToolCallState

        tool_calls = [
            ToolCallState(id="tc_1", tool_name="read_file"),
            ToolCallState(id="tc_2", tool_name="write_file"),
            ToolCallState(id="tc_3", tool_name="run_command"),
        ]
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            tool_calls=tool_calls,
        )
        widget = ToolCallBlock(block)
        assert len(widget.block.tool_calls) == 3

    def test_with_empty_tool_calls(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            tool_calls=[],
        )
        widget = ToolCallBlock(block)
        assert widget.block.tool_calls == []


class TestToolCallBlockBlockState:
    """Test ToolCallBlock with various BlockState configurations."""

    def test_with_running_state(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.is_running = True
        widget = ToolCallBlock(block)
        assert widget.block.is_running is True

    def test_with_completed_state(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.is_running = False
        block.exit_code = 0
        widget = ToolCallBlock(block)
        assert widget.block.is_running is False
        assert widget.block.exit_code == 0

    def test_with_error_exit_code(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        block.is_running = False
        block.exit_code = 1
        widget = ToolCallBlock(block)
        assert widget.block.exit_code == 1

    def test_with_timestamp(self):
        ts = datetime(2024, 1, 15, 10, 30, 0)
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            timestamp=ts,
        )
        widget = ToolCallBlock(block)
        assert widget.block.timestamp == ts

    def test_with_custom_id(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            id="custom_block_id_123",
        )
        widget = ToolCallBlock(block)
        assert widget.block.id == "custom_block_id_123"


class TestToolCallBlockMessages:
    """Test that ToolCallBlock inherits message functionality from BaseBlockWidget."""

    def test_retry_requested_message_available(self):
        msg = ToolCallBlock.RetryRequested(block_id="test_block")
        assert msg.block_id == "test_block"

    def test_edit_requested_message_available(self):
        msg = ToolCallBlock.EditRequested(block_id="test_block", content="test")
        assert msg.block_id == "test_block"
        assert msg.content == "test"

    def test_copy_requested_message_available(self):
        msg = ToolCallBlock.CopyRequested(block_id="test_block", content="copy me")
        assert msg.block_id == "test_block"
        assert msg.content == "copy me"

    def test_fork_requested_message_available(self):
        msg = ToolCallBlock.ForkRequested(block_id="test_block")
        assert msg.block_id == "test_block"

    def test_view_requested_message_available(self):
        msg = ToolCallBlock.ViewRequested(block_id="test_block", view_type="json")
        assert msg.block_id == "test_block"
        assert msg.view_type == "json"


class TestToolCallBlockContentVariations:
    """Test ToolCallBlock with various content types."""

    def test_with_json_output(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="api_call",
            content_output='{"status": "success", "data": [1, 2, 3]}',
        )
        widget = ToolCallBlock(block)
        assert '"status"' in widget.body_widget._initial_text

    def test_with_long_output(self):
        long_output = "x" * 10000
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            content_output=long_output,
        )
        widget = ToolCallBlock(block)
        assert len(widget.body_widget._initial_text) == 10000

    def test_with_unicode_output(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            content_output="Unicode: \u2603 \u2764 \u2728",
        )
        widget = ToolCallBlock(block)
        assert "\u2603" in widget.body_widget._initial_text

    def test_with_special_characters(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            content_output="Special: <>&\"'`",
        )
        widget = ToolCallBlock(block)
        assert "<>&" in widget.body_widget._initial_text

    def test_with_ansi_codes(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            content_output="\x1b[31mRed text\x1b[0m",
        )
        widget = ToolCallBlock(block)
        assert (
            "Red text" in widget.body_widget._initial_text
            or "\x1b[31m" in widget.body_widget._initial_text
        )


class TestToolCallBlockActions:
    """Test ToolCallBlock action methods inherited from BaseBlockWidget."""

    def test_action_copy_content_uses_content_output(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="test",
            content_output="Copy this content",
        )
        widget = ToolCallBlock(block)
        assert widget.block.content_output == "Copy this content"

    def test_action_edit_block_uses_content_input(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="edit_this_tool",
            content_output="result",
        )
        widget = ToolCallBlock(block)
        assert widget.block.content_input == "edit_this_tool"


class TestToolCallBlockEdgeCases:
    """Test edge cases and error handling."""

    def test_with_very_long_input(self):
        long_input = "a" * 5000
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input=long_input,
        )
        widget = ToolCallBlock(block)
        assert len(widget.block.content_input) == 5000

    def test_with_newlines_in_input(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="line1\nline2\nline3",
        )
        widget = ToolCallBlock(block)
        assert "line1\nline2\nline3" == widget.block.content_input

    def test_widget_has_block_attribute(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget = ToolCallBlock(block)
        assert hasattr(widget, "block")
        assert widget.block is block

    def test_multiple_widgets_same_block(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="test")
        widget1 = ToolCallBlock(block)
        widget2 = ToolCallBlock(block)
        # Both widgets share the same block reference
        assert widget1.block is widget2.block

    def test_multiple_widgets_different_blocks(self):
        block1 = BlockState(type=BlockType.TOOL_CALL, content_input="test1")
        block2 = BlockState(type=BlockType.TOOL_CALL, content_input="test2")
        widget1 = ToolCallBlock(block1)
        widget2 = ToolCallBlock(block2)
        assert widget1.block is not widget2.block
        assert widget1.block.content_input != widget2.block.content_input
