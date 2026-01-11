"""Tests for widgets/blocks/tool_accordion.py - Tool accordion components."""

from unittest.mock import patch

import pytest

from tools.streaming import ToolProgress, ToolStatus
from widgets.blocks.tool_accordion import (
    ToolAccordion,
    ToolAccordionItem,
    ToolHeader,
    ToolOutput,
)


# =============================================================================
# ToolHeader Tests
# =============================================================================


class TestToolHeaderInit:
    def test_initializes_with_tool_name(self):
        header = ToolHeader(tool_name="run_command")
        assert header.tool_name == "run_command"

    def test_default_status_is_pending(self):
        header = ToolHeader(tool_name="test_tool")
        assert header.status == "pending"

    def test_can_set_initial_status(self):
        header = ToolHeader(tool_name="test_tool", status="running")
        assert header.status == "running"

    def test_default_duration_is_zero(self):
        header = ToolHeader(tool_name="test_tool")
        assert header.duration == 0.0

    def test_can_set_initial_duration(self):
        header = ToolHeader(tool_name="test_tool", duration=2.5)
        assert header.duration == 2.5

    def test_default_expanded_is_false(self):
        header = ToolHeader(tool_name="test_tool")
        assert header.expanded is False

    def test_can_set_initial_expanded(self):
        header = ToolHeader(tool_name="test_tool", expanded=True)
        assert header.expanded is True

    def test_spinner_index_starts_at_zero(self):
        header = ToolHeader(tool_name="test_tool")
        assert header._spinner_index == 0

    def test_spinner_timer_starts_none(self):
        header = ToolHeader(tool_name="test_tool")
        assert header._spinner_timer is None

    def test_elapsed_timer_starts_none(self):
        header = ToolHeader(tool_name="test_tool")
        assert header._elapsed_timer is None


class TestToolHeaderSpinnerFrames:
    def test_spinner_frames_defined(self):
        assert len(ToolHeader.SPINNER_FRAMES) > 0

    def test_spinner_frames_are_single_characters(self):
        for frame in ToolHeader.SPINNER_FRAMES:
            assert len(frame) == 1

    def test_spinner_frames_is_class_variable(self):
        h1 = ToolHeader(tool_name="t1")
        h2 = ToolHeader(tool_name="t2")
        assert h1.SPINNER_FRAMES is h2.SPINNER_FRAMES


class TestToolHeaderGetStatusIcon:
    def test_pending_returns_circle(self):
        header = ToolHeader(tool_name="test", status="pending")
        assert header._get_status_icon() == "○"

    def test_running_returns_spinner_frame(self):
        header = ToolHeader(tool_name="test", status="running")
        icon = header._get_status_icon()
        assert icon == ToolHeader.SPINNER_FRAMES[0]

    def test_success_returns_checkmark(self):
        header = ToolHeader(tool_name="test", status="success")
        assert header._get_status_icon() == "󰄬"

    def test_error_returns_x(self):
        header = ToolHeader(tool_name="test", status="error")
        assert header._get_status_icon() == "✗"

    def test_cancelled_returns_circle_slash(self):
        header = ToolHeader(tool_name="test", status="cancelled")
        assert header._get_status_icon() == "⊘"

    def test_unknown_status_returns_default(self):
        header = ToolHeader(tool_name="test", status="unknown_status")
        assert header._get_status_icon() == "○"


class TestToolHeaderUpdateStatus:
    def test_update_status_changes_status(self):
        header = ToolHeader(tool_name="test", status="pending")
        header.update_status("running")
        assert header.status == "running"

    def test_update_status_changes_duration(self):
        header = ToolHeader(tool_name="test")
        header.update_status("success", duration=5.5)
        assert header.duration == 5.5

    def test_update_status_to_error(self):
        header = ToolHeader(tool_name="test", status="running")
        header.update_status("error", duration=1.2)
        assert header.status == "error"
        assert header.duration == 1.2

    def test_update_status_to_cancelled(self):
        header = ToolHeader(tool_name="test", status="running")
        header.update_status("cancelled", duration=3.0)
        assert header.status == "cancelled"


class TestToolHeaderUpdateProgress:
    def test_update_progress_with_none_does_not_raise(self):
        header = ToolHeader(tool_name="test")
        header.update_progress(None)

    def test_update_progress_with_value_does_not_raise(self):
        header = ToolHeader(tool_name="test")
        header.update_progress(0.5)


class TestToolHeaderSetExpanded:
    def test_set_expanded_true(self):
        header = ToolHeader(tool_name="test", expanded=False)
        header.set_expanded(True)
        assert header.expanded is True

    def test_set_expanded_false(self):
        header = ToolHeader(tool_name="test", expanded=True)
        header.set_expanded(False)
        assert header.expanded is False

    def test_set_expanded_toggle(self):
        header = ToolHeader(tool_name="test", expanded=False)
        header.set_expanded(True)
        header.set_expanded(False)
        assert header.expanded is False


# =============================================================================
# ToolOutput Tests
# =============================================================================


class TestToolOutputInit:
    def test_default_arguments_empty(self):
        output = ToolOutput()
        assert output.arguments == ""

    def test_can_set_initial_arguments(self):
        output = ToolOutput(arguments='{"key": "value"}')
        assert output.arguments == '{"key": "value"}'

    def test_default_output_empty(self):
        output = ToolOutput()
        assert output.output == ""

    def test_can_set_initial_output(self):
        output = ToolOutput(output="Command executed successfully")
        assert output.output == "Command executed successfully"

    def test_default_streaming_false(self):
        output = ToolOutput()
        assert output.streaming is False

    def test_can_set_initial_streaming(self):
        output = ToolOutput(streaming=True)
        assert output.streaming is True

    def test_auto_scroll_defaults_true(self):
        output = ToolOutput()
        assert output._auto_scroll is True


class TestToolOutputUpdateOutput:
    def test_update_output_changes_output(self):
        output = ToolOutput(output="initial")
        output.update_output("updated")
        assert output.output == "updated"

    def test_update_output_changes_streaming(self):
        output = ToolOutput(streaming=False)
        output.update_output("data", streaming=True)
        assert output.streaming is True

    def test_update_output_with_empty_string(self):
        output = ToolOutput(output="some content")
        output.update_output("")
        assert output.output == ""

    def test_update_output_multiple_times(self):
        output = ToolOutput()
        output.update_output("first")
        output.update_output("second")
        output.update_output("third")
        assert output.output == "third"


class TestToolOutputShowHide:
    def test_show_adds_visible_class(self):
        output = ToolOutput()
        output.show()
        assert "visible" in output.classes

    def test_hide_removes_visible_class(self):
        output = ToolOutput()
        output.add_class("visible")
        output.hide()
        assert "visible" not in output.classes

    def test_show_then_hide(self):
        output = ToolOutput()
        output.show()
        output.hide()
        assert "visible" not in output.classes

    def test_multiple_show_calls_safe(self):
        output = ToolOutput()
        output.show()
        output.show()
        output.show()
        assert "visible" in output.classes


class TestToolOutputStreaming:
    def test_streaming_reactive_property(self):
        output = ToolOutput()
        output.streaming = True
        assert output.streaming is True

    def test_streaming_false_by_default(self):
        output = ToolOutput()
        assert output.streaming is False


# =============================================================================
# ToolAccordionItem Tests
# =============================================================================


class TestToolAccordionItemInit:
    def test_initializes_with_tool_id(self):
        item = ToolAccordionItem(tool_id="tool_123", tool_name="run_command")
        assert item.tool_id == "tool_123"

    def test_initializes_with_tool_name(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="read_file")
        assert item.tool_name == "read_file"

    def test_default_arguments_empty(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item.arguments == ""

    def test_can_set_initial_arguments(self):
        item = ToolAccordionItem(
            tool_id="t1", tool_name="test", arguments='{"path": "/tmp"}'
        )
        assert item.arguments == '{"path": "/tmp"}'

    def test_default_output_empty(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item.output == ""

    def test_can_set_initial_output(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test", output="Done")
        assert item.output == "Done"

    def test_default_status_pending(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item.status == "pending"

    def test_can_set_initial_status(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test", status="running")
        assert item.status == "running"

    def test_default_duration_zero(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item.duration == 0.0

    def test_can_set_initial_duration(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test", duration=3.5)
        assert item.duration == 3.5

    def test_default_streaming_false(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item.streaming is False

    def test_can_set_initial_streaming(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test", streaming=True)
        assert item.streaming is True

    def test_expanded_reactive_defaults_false(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item.expanded is False

    def test_header_starts_none(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item._header is None

    def test_output_panel_starts_none(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        assert item._output_panel is None


class TestToolAccordionItemCancelMessage:
    def test_cancel_message_carries_tool_id(self):
        msg = ToolAccordionItem.CancelRequested("tool_abc")
        assert msg.tool_id == "tool_abc"

    def test_cancel_message_different_ids(self):
        msg1 = ToolAccordionItem.CancelRequested("tool_1")
        msg2 = ToolAccordionItem.CancelRequested("tool_2")
        assert msg1.tool_id != msg2.tool_id


class TestToolAccordionItemUpdateStatus:
    def test_update_status_changes_status(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.update_status("success")
        assert item.status == "success"

    def test_update_status_changes_duration(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.update_status("success", duration=2.5)
        assert item.duration == 2.5

    def test_update_status_to_error(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test", status="running")
        item.update_status("error", duration=1.0)
        assert item.status == "error"
        assert item.duration == 1.0


class TestToolAccordionItemUpdateOutput:
    def test_update_output_changes_output(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.update_output("new output")
        assert item.output == "new output"

    def test_update_output_changes_streaming(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.update_output("streaming data", streaming=True)
        assert item.streaming is True

    def test_update_output_multiple_times(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.update_output("first")
        item.update_output("second")
        item.update_output("final")
        assert item.output == "final"


class TestToolAccordionItemUpdateProgress:
    def test_update_progress_changes_status(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        progress = ToolProgress(
            status=ToolStatus.RUNNING, output="running...", elapsed=1.5
        )
        item.update_progress(progress)
        assert item.status == "running"

    def test_update_progress_changes_output(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        progress = ToolProgress(
            status=ToolStatus.RUNNING, output="data chunk", elapsed=0.5
        )
        item.update_progress(progress)
        assert item.output == "data chunk"

    def test_update_progress_with_completed_status(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        progress = ToolProgress(
            status=ToolStatus.COMPLETED, output="done!", elapsed=5.0
        )
        item.update_progress(progress)
        assert item.status == "completed"

    def test_update_progress_with_failed_status(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        progress = ToolProgress(
            status=ToolStatus.FAILED, output="error occurred", elapsed=2.0
        )
        item.update_progress(progress)
        assert item.status == "failed"


class TestToolAccordionItemExpanded:
    def test_expanded_can_be_set_true(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.expanded = True
        assert item.expanded is True

    def test_expanded_can_be_set_false(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.expanded = True
        item.expanded = False
        assert item.expanded is False

    def test_expanded_toggle(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.expanded = True
        item.expanded = not item.expanded
        assert item.expanded is False


# =============================================================================
# ToolAccordion Tests
# =============================================================================


class TestToolAccordionInit:
    def test_initializes_with_empty_tools_dict(self):
        accordion = ToolAccordion()
        assert accordion._tools == {}

    def test_can_set_id(self):
        accordion = ToolAccordion(id="my-accordion")
        assert accordion.id == "my-accordion"

    def test_can_set_classes(self):
        accordion = ToolAccordion(classes="custom-class")
        assert "custom-class" in accordion.classes


class TestToolAccordionAddTool:
    @patch.object(ToolAccordion, "mount")
    def test_add_tool_returns_item(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(tool_id="t1", tool_name="run_command")
        assert isinstance(item, ToolAccordionItem)

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_stores_in_dict(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="run_command")
        assert "t1" in accordion._tools

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_with_arguments(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(
            tool_id="t1", tool_name="read_file", arguments='{"path": "/etc/passwd"}'
        )
        assert item.arguments == '{"path": "/etc/passwd"}'

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_with_status(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(tool_id="t1", tool_name="test", status="pending")
        assert item.status == "pending"

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_default_status_running(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(tool_id="t1", tool_name="test")
        assert item.status == "running"

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_with_streaming(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(tool_id="t1", tool_name="test", streaming=True)
        assert item.streaming is True

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_streaming_expands_item(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(tool_id="t1", tool_name="test", streaming=True)
        assert item.expanded is True

    @patch.object(ToolAccordion, "mount")
    def test_add_multiple_tools(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="tool1")
        accordion.add_tool(tool_id="t2", tool_name="tool2")
        accordion.add_tool(tool_id="t3", tool_name="tool3")
        assert len(accordion._tools) == 3

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_removes_empty_class(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_class("empty")
        accordion.add_tool(tool_id="t1", tool_name="test")
        assert "empty" not in accordion.classes

    @patch.object(ToolAccordion, "mount")
    def test_add_tool_calls_mount(self, mock_mount):
        accordion = ToolAccordion()
        item = accordion.add_tool(tool_id="t1", tool_name="test")
        mock_mount.assert_called_once_with(item)


class TestToolAccordionUpdateTool:
    @patch.object(ToolAccordion, "mount")
    def test_update_tool_status(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        accordion.update_tool(tool_id="t1", status="success")
        assert accordion._tools["t1"].status == "success"

    @patch.object(ToolAccordion, "mount")
    def test_update_tool_output(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        accordion.update_tool(tool_id="t1", output="result data")
        assert accordion._tools["t1"].output == "result data"

    @patch.object(ToolAccordion, "mount")
    def test_update_tool_duration(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        accordion.update_tool(tool_id="t1", status="success", duration=3.5)
        assert accordion._tools["t1"].duration == 3.5

    @patch.object(ToolAccordion, "mount")
    def test_update_tool_streaming(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        accordion.update_tool(tool_id="t1", output="data", streaming=True)
        assert accordion._tools["t1"].streaming is True

    def test_update_nonexistent_tool_does_not_raise(self):
        accordion = ToolAccordion()
        accordion.update_tool(tool_id="nonexistent", status="success")

    @patch.object(ToolAccordion, "mount")
    def test_update_tool_partial_update(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        accordion.update_tool(tool_id="t1", status="error")
        assert accordion._tools["t1"].status == "error"
        assert accordion._tools["t1"].output == ""


class TestToolAccordionGetTool:
    @patch.object(ToolAccordion, "mount")
    def test_get_existing_tool(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        item = accordion.get_tool("t1")
        assert item is not None
        assert item.tool_id == "t1"

    def test_get_nonexistent_tool_returns_none(self):
        accordion = ToolAccordion()
        item = accordion.get_tool("nonexistent")
        assert item is None

    @patch.object(ToolAccordion, "mount")
    def test_get_tool_after_multiple_adds(self, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="first")
        accordion.add_tool(tool_id="t2", tool_name="second")
        accordion.add_tool(tool_id="t3", tool_name="third")

        item = accordion.get_tool("t2")
        assert item is not None
        assert item.tool_name == "second"


class TestToolAccordionClear:
    @patch.object(ToolAccordion, "mount")
    @patch.object(ToolAccordionItem, "remove")
    def test_clear_empties_tools_dict(self, mock_remove, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test1")
        accordion.add_tool(tool_id="t2", tool_name="test2")
        accordion.clear()
        assert len(accordion._tools) == 0

    @patch.object(ToolAccordion, "mount")
    @patch.object(ToolAccordionItem, "remove")
    def test_clear_adds_empty_class(self, mock_remove, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test")
        accordion.clear()
        assert "empty" in accordion.classes

    def test_clear_on_empty_accordion(self):
        accordion = ToolAccordion()
        accordion.clear()
        assert len(accordion._tools) == 0
        assert "empty" in accordion.classes

    @patch.object(ToolAccordion, "mount")
    @patch.object(ToolAccordionItem, "remove")
    def test_clear_calls_remove_on_items(self, mock_remove, mock_mount):
        accordion = ToolAccordion()
        accordion.add_tool(tool_id="t1", tool_name="test1")
        accordion.add_tool(tool_id="t2", tool_name="test2")
        accordion.clear()
        assert mock_remove.call_count == 2


# =============================================================================
# ToolProgress Integration Tests
# =============================================================================


class TestToolProgressIntegration:
    def test_tool_progress_pending_status_value(self):
        progress = ToolProgress(status=ToolStatus.PENDING, output="")
        assert progress.status.value == "pending"

    def test_tool_progress_running_status_value(self):
        progress = ToolProgress(status=ToolStatus.RUNNING, output="")
        assert progress.status.value == "running"

    def test_tool_progress_completed_status_value(self):
        progress = ToolProgress(status=ToolStatus.COMPLETED, output="")
        assert progress.status.value == "completed"

    def test_tool_progress_failed_status_value(self):
        progress = ToolProgress(status=ToolStatus.FAILED, output="")
        assert progress.status.value == "failed"

    def test_tool_progress_cancelled_status_value(self):
        progress = ToolProgress(status=ToolStatus.CANCELLED, output="")
        assert progress.status.value == "cancelled"

    def test_tool_progress_is_complete_for_completed(self):
        progress = ToolProgress(status=ToolStatus.COMPLETED, output="")
        assert progress.is_complete is True

    def test_tool_progress_is_complete_for_failed(self):
        progress = ToolProgress(status=ToolStatus.FAILED, output="")
        assert progress.is_complete is True

    def test_tool_progress_is_complete_for_cancelled(self):
        progress = ToolProgress(status=ToolStatus.CANCELLED, output="")
        assert progress.is_complete is True

    def test_tool_progress_is_not_complete_for_running(self):
        progress = ToolProgress(status=ToolStatus.RUNNING, output="")
        assert progress.is_complete is False

    def test_tool_progress_is_not_complete_for_pending(self):
        progress = ToolProgress(status=ToolStatus.PENDING, output="")
        assert progress.is_complete is False


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    def test_tool_name_with_special_characters(self):
        header = ToolHeader(tool_name="run_command::subprocess")
        assert header.tool_name == "run_command::subprocess"

    def test_tool_name_with_unicode(self):
        header = ToolHeader(tool_name="tool_with_emoji_")
        assert "tool_with_emoji" in header.tool_name

    def test_empty_tool_name(self):
        header = ToolHeader(tool_name="")
        assert header.tool_name == ""

    def test_very_long_tool_name(self):
        long_name = "a" * 1000
        header = ToolHeader(tool_name=long_name)
        assert header.tool_name == long_name

    def test_arguments_with_nested_json(self):
        args = '{"nested": {"deep": {"value": 123}}}'
        output = ToolOutput(arguments=args)
        assert output.arguments == args

    def test_output_with_newlines(self):
        text = "line1\nline2\nline3"
        output = ToolOutput(output=text)
        assert output.output == text

    def test_output_with_ansi_codes(self):
        text = "\x1b[31mred\x1b[0m"
        output = ToolOutput(output=text)
        assert output.output == text

    def test_duration_negative_value(self):
        header = ToolHeader(tool_name="test", duration=-1.0)
        assert header.duration == -1.0

    def test_duration_very_large_value(self):
        header = ToolHeader(tool_name="test", duration=999999.99)
        assert header.duration == 999999.99

    def test_multiple_status_updates(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test")
        item.update_status("pending")
        item.update_status("running")
        item.update_status("success")
        assert item.status == "success"


class TestToolAccordionItemWithClasses:
    def test_can_set_custom_classes(self):
        item = ToolAccordionItem(
            tool_id="t1", tool_name="test", classes="custom highlight"
        )
        assert "custom" in item.classes
        assert "highlight" in item.classes

    def test_can_set_custom_id(self):
        item = ToolAccordionItem(tool_id="t1", tool_name="test", id="my-custom-id")
        assert item.id == "my-custom-id"
