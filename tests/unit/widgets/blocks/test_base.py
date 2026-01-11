"""Tests for widgets/blocks/base.py - BaseBlockWidget."""

import pytest

from models import BlockState, BlockType
from widgets.blocks.base import BaseBlockWidget


class TestBaseBlockWidgetMessages:
    def test_retry_message_carries_block_id(self):
        msg = BaseBlockWidget.RetryRequested(block_id="block_123")
        assert msg.block_id == "block_123"

    def test_edit_message_carries_block_id_and_content(self):
        msg = BaseBlockWidget.EditRequested(block_id="block_456", content="edited text")
        assert msg.block_id == "block_456"
        assert msg.content == "edited text"

    def test_copy_message_carries_block_id_and_content(self):
        msg = BaseBlockWidget.CopyRequested(block_id="block_789", content="copy me")
        assert msg.block_id == "block_789"
        assert msg.content == "copy me"

    def test_fork_message_carries_block_id(self):
        msg = BaseBlockWidget.ForkRequested(block_id="block_fork")
        assert msg.block_id == "block_fork"

    def test_view_message_carries_block_id_and_view_type(self):
        msg = BaseBlockWidget.ViewRequested(block_id="block_view", view_type="json")
        assert msg.block_id == "block_view"
        assert msg.view_type == "json"

    def test_view_message_supports_different_types(self):
        raw_msg = BaseBlockWidget.ViewRequested(block_id="b1", view_type="raw")
        json_msg = BaseBlockWidget.ViewRequested(block_id="b2", view_type="json")
        table_msg = BaseBlockWidget.ViewRequested(block_id="b3", view_type="table")

        assert raw_msg.view_type == "raw"
        assert json_msg.view_type == "json"
        assert table_msg.view_type == "table"


class TestBaseBlockWidgetLoadingState:
    def test_set_loading_true_updates_block_state(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = BaseBlockWidget(block)

        widget.set_loading(True)

        assert block.is_running is True

    def test_set_loading_false_updates_block_state(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = BaseBlockWidget(block)

        widget.set_loading(False)

        assert block.is_running is False

    def test_loading_state_toggle(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = BaseBlockWidget(block)

        widget.set_loading(True)
        assert block.is_running is True

        widget.set_loading(False)
        assert block.is_running is False


class TestBaseBlockWidgetExitCode:
    def test_set_exit_code_stores_value(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = BaseBlockWidget(block)
        widget.set_loading(True)

        widget.set_exit_code(0)

        assert block.exit_code == 0

    def test_set_exit_code_stops_loading(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = BaseBlockWidget(block)
        widget.set_loading(True)

        widget.set_exit_code(0)

        assert block.is_running is False

    def test_set_exit_code_handles_failure_codes(self):
        block = BlockState(type=BlockType.COMMAND, content_input="bad_cmd")
        widget = BaseBlockWidget(block)
        widget.set_loading(True)

        widget.set_exit_code(127)

        assert block.exit_code == 127
        assert block.is_running is False

    def test_set_exit_code_handles_signal_termination(self):
        block = BlockState(type=BlockType.COMMAND, content_input="long_process")
        widget = BaseBlockWidget(block)
        widget.set_loading(True)

        widget.set_exit_code(137)  # SIGKILL

        assert block.exit_code == 137


class TestBaseBlockWidgetDefaultMethods:
    def test_update_output_does_not_raise(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = BaseBlockWidget(block)
        widget.update_output("new content")

    def test_update_metadata_does_not_raise(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = BaseBlockWidget(block)
        widget.update_metadata()
