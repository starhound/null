"""Tests for widgets/blocks/iteration.py - IterationWidget and related components."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from models import AgentIteration, ToolCallState
from widgets.blocks.iteration import (
    IterationHeader,
    IterationSeparator,
    IterationWidget,
    ThinkingSection,
    ToolCallItem,
)


# =============================================================================
# IterationHeader Tests
# =============================================================================


class TestIterationHeaderInit:
    """Tests for IterationHeader initialization."""

    def test_init_stores_iteration(self):
        """IterationHeader stores the provided iteration."""
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        header = IterationHeader(iteration)
        assert header.iteration is iteration

    def test_init_spinner_index_starts_at_zero(self):
        """Spinner index starts at 0."""
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        header = IterationHeader(iteration)
        assert header._spinner_index == 0

    def test_init_spinner_timer_is_none(self):
        """Spinner timer is None initially."""
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        header = IterationHeader(iteration)
        assert header._spinner_timer is None

    def test_init_with_different_iteration_numbers(self):
        """Header can be created with various iteration numbers."""
        for num in [1, 5, 10, 100]:
            iteration = AgentIteration(id=f"iter-{num}", iteration_number=num)
            header = IterationHeader(iteration)
            assert header.iteration.iteration_number == num


class TestIterationHeaderSpinnerFrames:
    """Tests for IterationHeader spinner animation frames."""

    def test_spinner_frames_class_var_exists(self):
        """SPINNER_FRAMES class variable exists."""
        assert hasattr(IterationHeader, "SPINNER_FRAMES")

    def test_spinner_frames_is_list(self):
        """SPINNER_FRAMES is a list."""
        assert isinstance(IterationHeader.SPINNER_FRAMES, list)

    def test_spinner_frames_has_8_elements(self):
        """SPINNER_FRAMES has 8 animation frames."""
        assert len(IterationHeader.SPINNER_FRAMES) == 8

    def test_spinner_frames_all_strings(self):
        """All spinner frames are strings."""
        for frame in IterationHeader.SPINNER_FRAMES:
            assert isinstance(frame, str)

    def test_spinner_frames_all_unique(self):
        """All spinner frames are unique."""
        frames = IterationHeader.SPINNER_FRAMES
        assert len(frames) == len(set(frames))


class TestIterationHeaderGetStatusIcon:
    """Tests for IterationHeader._get_status_icon method."""

    def test_pending_status_icon(self):
        """Pending status shows empty circle."""
        iteration = AgentIteration(id="iter-1", status="pending")
        header = IterationHeader(iteration)
        assert header._get_status_icon() == "○"

    def test_thinking_status_icon(self):
        """Thinking status shows first spinner frame."""
        iteration = AgentIteration(id="iter-1", status="thinking")
        header = IterationHeader(iteration)
        assert header._get_status_icon() == IterationHeader.SPINNER_FRAMES[0]

    def test_executing_status_icon(self):
        """Executing status shows half-filled circle."""
        iteration = AgentIteration(id="iter-1", status="executing")
        header = IterationHeader(iteration)
        assert header._get_status_icon() == "◐"

    def test_waiting_approval_status_icon(self):
        """Waiting approval status shows pause icon."""
        iteration = AgentIteration(id="iter-1", status="waiting_approval")
        header = IterationHeader(iteration)
        assert header._get_status_icon() == "⏸"

    def test_complete_status_icon(self):
        """Complete status shows filled circle."""
        iteration = AgentIteration(id="iter-1", status="complete")
        header = IterationHeader(iteration)
        assert header._get_status_icon() == "●"

    def test_unknown_status_defaults_to_pending(self):
        """Unknown status defaults to pending icon."""
        iteration = AgentIteration(id="iter-1", status="unknown_status")
        header = IterationHeader(iteration)
        assert header._get_status_icon() == "○"


class TestIterationHeaderUpdateStatus:
    """Tests for IterationHeader.update_status method."""

    def test_update_status_changes_iteration_status(self):
        """update_status updates the iteration status."""
        iteration = AgentIteration(id="iter-1", status="pending")
        header = IterationHeader(iteration)
        header.update_status("thinking")
        assert header.iteration.status == "thinking"

    def test_update_status_changes_duration(self):
        """update_status updates the iteration duration."""
        iteration = AgentIteration(id="iter-1", status="pending", duration=0.0)
        header = IterationHeader(iteration)
        header.update_status("complete", 2.5)
        assert header.iteration.duration == 2.5

    def test_update_status_to_complete(self):
        """update_status can change to complete status."""
        iteration = AgentIteration(id="iter-1", status="thinking")
        header = IterationHeader(iteration)
        header.update_status("complete", 1.0)
        assert header.iteration.status == "complete"

    def test_update_status_default_duration_zero(self):
        """update_status defaults duration to 0.0."""
        iteration = AgentIteration(id="iter-1", status="pending")
        header = IterationHeader(iteration)
        header.update_status("thinking")
        assert header.iteration.duration == 0.0


class TestIterationHeaderInheritance:
    """Tests for IterationHeader inheritance."""

    def test_inherits_from_static(self):
        """IterationHeader inherits from Static."""
        from textual.widgets import Static

        assert issubclass(IterationHeader, Static)

    def test_instance_is_static(self):
        """IterationHeader instance is a Static."""
        from textual.widgets import Static

        iteration = AgentIteration(id="iter-1")
        header = IterationHeader(iteration)
        assert isinstance(header, Static)


# =============================================================================
# ThinkingSection Tests
# =============================================================================


class TestThinkingSectionInit:
    """Tests for ThinkingSection initialization."""

    def test_init_default_content_empty(self):
        """Default content is empty string."""
        section = ThinkingSection()
        assert section.content == ""

    def test_init_default_collapsed_true(self):
        """Default collapsed state is True."""
        section = ThinkingSection()
        assert section.collapsed is True

    def test_init_with_content(self):
        """ThinkingSection can be initialized with content."""
        section = ThinkingSection(content="Test reasoning")
        assert section.content == "Test reasoning"

    def test_init_with_collapsed_false(self):
        """ThinkingSection can be initialized expanded."""
        section = ThinkingSection(collapsed=False)
        assert section.collapsed is False

    def test_init_combined_parameters(self):
        """ThinkingSection can be initialized with both params."""
        section = ThinkingSection(content="Thinking...", collapsed=False)
        assert section.content == "Thinking..."
        assert section.collapsed is False


class TestThinkingSectionCollapsedReactive:
    """Tests for ThinkingSection collapsed reactive property."""

    def test_collapsed_is_reactive(self):
        """collapsed is a reactive property."""
        from textual.reactive import Reactive

        assert hasattr(ThinkingSection, "collapsed")

    def test_collapsed_can_be_toggled(self):
        """collapsed can be toggled."""
        section = ThinkingSection(collapsed=True)
        section.collapsed = False
        assert section.collapsed is False

    def test_collapsed_toggle_back(self):
        """collapsed can be toggled back."""
        section = ThinkingSection(collapsed=False)
        section.collapsed = True
        assert section.collapsed is True


class TestThinkingSectionUpdateContent:
    """Tests for ThinkingSection.update_content method."""

    def test_update_content_changes_content(self):
        """update_content updates the content attribute."""
        section = ThinkingSection(content="old")
        section.update_content("new content")
        assert section.content == "new content"

    def test_update_content_from_empty(self):
        """update_content can set content from empty."""
        section = ThinkingSection()
        section.update_content("reasoning text")
        assert section.content == "reasoning text"

    def test_update_content_empty_preserves_existing(self):
        """update_content with empty string preserves existing content."""
        section = ThinkingSection(content="existing")
        section.update_content("")
        assert section.content == "existing"

    def test_update_content_overwrites_with_new(self):
        """update_content overwrites with new non-empty content."""
        section = ThinkingSection(content="old content")
        section.update_content("new reasoning")
        assert section.content == "new reasoning"


class TestThinkingSectionInheritance:
    """Tests for ThinkingSection inheritance."""

    def test_inherits_from_static(self):
        """ThinkingSection inherits from Static."""
        from textual.widgets import Static

        assert issubclass(ThinkingSection, Static)


# =============================================================================
# ToolCallItem Tests
# =============================================================================


class TestToolCallItemInit:
    """Tests for ToolCallItem initialization."""

    def test_init_stores_tool_call(self):
        """ToolCallItem stores the provided tool call."""
        tool = ToolCallState(id="tool-1", tool_name="read_file")
        item = ToolCallItem(tool)
        assert item.tool_call is tool

    def test_init_spinner_index_starts_at_zero(self):
        """Spinner index starts at 0."""
        tool = ToolCallState(id="tool-1", tool_name="test")
        item = ToolCallItem(tool)
        assert item._spinner_index == 0

    def test_init_spinner_timer_is_none(self):
        """Spinner timer is None initially."""
        tool = ToolCallState(id="tool-1", tool_name="test")
        item = ToolCallItem(tool)
        assert item._spinner_timer is None

    def test_init_with_various_tool_names(self):
        """ToolCallItem can be created with various tool names."""
        for name in ["read_file", "write_file", "run_command", "search"]:
            tool = ToolCallState(id=f"tool-{name}", tool_name=name)
            item = ToolCallItem(tool)
            assert item.tool_call.tool_name == name


class TestToolCallItemSpinnerFrames:
    """Tests for ToolCallItem spinner animation frames."""

    def test_spinner_frames_class_var_exists(self):
        """SPINNER_FRAMES class variable exists."""
        assert hasattr(ToolCallItem, "SPINNER_FRAMES")

    def test_spinner_frames_matches_header(self):
        """ToolCallItem SPINNER_FRAMES matches IterationHeader."""
        assert ToolCallItem.SPINNER_FRAMES == IterationHeader.SPINNER_FRAMES


class TestToolCallItemGetStatusIcon:
    """Tests for ToolCallItem._get_status_icon method."""

    def test_pending_status_icon(self):
        """Pending status shows empty circle."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="pending")
        item = ToolCallItem(tool)
        assert item._get_status_icon() == "○"

    def test_running_status_icon(self):
        """Running status shows first spinner frame."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="running")
        item = ToolCallItem(tool)
        assert item._get_status_icon() == ToolCallItem.SPINNER_FRAMES[0]

    def test_success_status_icon(self):
        """Success status shows checkmark."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="success")
        item = ToolCallItem(tool)
        assert item._get_status_icon() == "󰄬"

    def test_error_status_icon(self):
        """Error status shows X mark."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="error")
        item = ToolCallItem(tool)
        assert item._get_status_icon() == "✗"

    def test_unknown_status_defaults_to_pending(self):
        """Unknown status defaults to pending icon."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="unknown")
        item = ToolCallItem(tool)
        assert item._get_status_icon() == "○"


class TestToolCallItemUpdateStatus:
    """Tests for ToolCallItem.update_status method."""

    def test_update_status_changes_tool_status(self):
        """update_status updates the tool call status."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="pending")
        item = ToolCallItem(tool)
        item.update_status("running")
        assert item.tool_call.status == "running"

    def test_update_status_changes_duration(self):
        """update_status updates the tool call duration."""
        tool = ToolCallState(id="tool-1", tool_name="test", duration=0.0)
        item = ToolCallItem(tool)
        item.update_status("success", 1.5)
        assert item.tool_call.duration == 1.5

    def test_update_status_to_success(self):
        """update_status can change to success status."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="running")
        item = ToolCallItem(tool)
        item.update_status("success", 0.5)
        assert item.tool_call.status == "success"

    def test_update_status_to_error(self):
        """update_status can change to error status."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="running")
        item = ToolCallItem(tool)
        item.update_status("error", 0.1)
        assert item.tool_call.status == "error"

    def test_update_status_default_duration_zero(self):
        """update_status defaults duration to 0.0."""
        tool = ToolCallState(id="tool-1", tool_name="test")
        item = ToolCallItem(tool)
        item.update_status("success")
        assert item.tool_call.duration == 0.0


class TestToolCallItemInheritance:
    """Tests for ToolCallItem inheritance."""

    def test_inherits_from_static(self):
        """ToolCallItem inherits from Static."""
        from textual.widgets import Static

        assert issubclass(ToolCallItem, Static)


# =============================================================================
# IterationSeparator Tests
# =============================================================================


class TestIterationSeparatorInit:
    """Tests for IterationSeparator initialization."""

    def test_init_stores_iteration_number(self):
        """IterationSeparator stores the iteration number."""
        separator = IterationSeparator(iteration_number=1)
        assert separator.iteration_number == 1

    def test_init_with_various_numbers(self):
        """IterationSeparator can be created with various numbers."""
        for num in [1, 2, 5, 10, 99]:
            separator = IterationSeparator(iteration_number=num)
            assert separator.iteration_number == num


class TestIterationSeparatorInheritance:
    """Tests for IterationSeparator inheritance."""

    def test_inherits_from_static(self):
        """IterationSeparator inherits from Static."""
        from textual.widgets import Static

        assert issubclass(IterationSeparator, Static)


# =============================================================================
# IterationWidget Tests
# =============================================================================


class TestIterationWidgetInit:
    """Tests for IterationWidget initialization."""

    def test_init_stores_iteration(self):
        """IterationWidget stores the provided iteration."""
        iteration = AgentIteration(id="iter-1", iteration_number=1)
        widget = IterationWidget(iteration)
        assert widget.iteration is iteration

    def test_init_default_show_thinking_true(self):
        """Default show_thinking is True."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        assert widget.show_thinking is True

    def test_init_show_thinking_can_be_false(self):
        """show_thinking can be set to False."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration, show_thinking=False)
        assert widget.show_thinking is False

    def test_init_header_is_none(self):
        """_header is None before compose."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        assert widget._header is None

    def test_init_thinking_is_none(self):
        """_thinking is None before compose."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        assert widget._thinking is None

    def test_init_tool_widgets_empty_dict(self):
        """_tool_widgets starts as empty dict."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        assert widget._tool_widgets == {}


class TestIterationWidgetUpdateStatus:
    """Tests for IterationWidget.update_status method."""

    def test_update_status_changes_iteration_status(self):
        """update_status updates the iteration status."""
        iteration = AgentIteration(id="iter-1", status="pending")
        widget = IterationWidget(iteration)
        widget.update_status("thinking")
        assert widget.iteration.status == "thinking"

    def test_update_status_changes_duration(self):
        """update_status updates the iteration duration."""
        iteration = AgentIteration(id="iter-1", duration=0.0)
        widget = IterationWidget(iteration)
        widget.update_status("complete", 3.5)
        assert widget.iteration.duration == 3.5

    def test_update_status_calls_header_when_set(self):
        """update_status calls header.update_status when header exists."""
        iteration = AgentIteration(id="iter-1", status="pending")
        widget = IterationWidget(iteration)
        mock_header = MagicMock()
        widget._header = mock_header
        widget.update_status("thinking", 1.0)
        mock_header.update_status.assert_called_once_with("thinking", 1.0)

    def test_update_status_no_header_no_error(self):
        """update_status handles missing header gracefully."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        widget.update_status("complete", 1.0)


class TestIterationWidgetUpdateThinking:
    """Tests for IterationWidget.update_thinking method."""

    def test_update_thinking_changes_iteration_thinking(self):
        """update_thinking updates the iteration thinking content."""
        iteration = AgentIteration(id="iter-1", thinking="")
        widget = IterationWidget(iteration)
        widget.update_thinking("I'm reasoning about this...")
        assert widget.iteration.thinking == "I'm reasoning about this..."

    def test_update_thinking_calls_section_when_exists(self):
        """update_thinking calls _thinking.update_content when section exists."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        mock_thinking = MagicMock()
        widget._thinking = mock_thinking
        widget.update_thinking("New reasoning")
        mock_thinking.update_content.assert_called_once_with("New reasoning")

    def test_update_thinking_no_section_with_show_thinking_false(self):
        """update_thinking doesn't create section when show_thinking=False."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration, show_thinking=False)
        widget.update_thinking("reasoning")
        assert widget._thinking is None
        assert widget.iteration.thinking == "reasoning"


class TestIterationWidgetAddToolCall:
    """Tests for IterationWidget.add_tool_call method."""

    def test_add_tool_call_returns_widget(self):
        """add_tool_call returns a ToolCallItem."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        tool = ToolCallState(id="tool-1", tool_name="read_file")
        result = widget.add_tool_call(tool)
        assert isinstance(result, ToolCallItem)

    def test_add_tool_call_stores_in_dict(self):
        """add_tool_call stores widget in _tool_widgets dict."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        tool = ToolCallState(id="tool-123", tool_name="write_file")
        result = widget.add_tool_call(tool)
        assert widget._tool_widgets["tool-123"] is result

    def test_add_multiple_tool_calls(self):
        """Multiple tool calls can be added."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        tools = [ToolCallState(id=f"tool-{i}", tool_name=f"tool_{i}") for i in range(5)]
        for tool in tools:
            widget.add_tool_call(tool)
        assert len(widget._tool_widgets) == 5


class TestIterationWidgetUpdateToolCall:
    """Tests for IterationWidget.update_tool_call method."""

    def test_update_tool_call_updates_widget_status(self):
        """update_tool_call calls widget.update_status."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        tool = ToolCallState(id="tool-1", tool_name="test")
        tool_widget = widget.add_tool_call(tool)

        with patch.object(tool_widget, "update_status") as mock_update:
            widget.update_tool_call("tool-1", status="success", duration=0.5)
            mock_update.assert_called_once_with("success", 0.5)

    def test_update_tool_call_unknown_id_no_error(self):
        """update_tool_call handles unknown tool id gracefully."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        widget.update_tool_call("unknown-tool", status="error")

    def test_update_tool_call_none_status_no_update(self):
        """update_tool_call with None status doesn't call update."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        tool = ToolCallState(id="tool-1", tool_name="test")
        tool_widget = widget.add_tool_call(tool)

        with patch.object(tool_widget, "update_status") as mock_update:
            widget.update_tool_call("tool-1", status=None, duration=0.5)
            mock_update.assert_not_called()


class TestIterationWidgetUpdateResponse:
    """Tests for IterationWidget.update_response method."""

    def test_update_response_changes_iteration_response(self):
        """update_response updates the iteration response_fragment."""
        iteration = AgentIteration(id="iter-1", response_fragment="")
        widget = IterationWidget(iteration)
        widget.update_response("Here is my response")
        assert widget.iteration.response_fragment == "Here is my response"

    def test_update_response_with_markdown(self):
        """update_response handles markdown content."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)
        widget.update_response("# Heading\n\n- Item 1\n- Item 2")
        assert "# Heading" in widget.iteration.response_fragment


class TestIterationWidgetInheritance:
    """Tests for IterationWidget inheritance."""

    def test_inherits_from_static(self):
        """IterationWidget inherits from Static."""
        from textual.widgets import Static

        assert issubclass(IterationWidget, Static)


class TestIterationWidgetWithToolCalls:
    """Tests for IterationWidget with tool calls in iteration."""

    def test_widget_with_existing_tool_calls(self):
        """Widget created with iteration containing tool calls."""
        tool1 = ToolCallState(id="tool-1", tool_name="read_file")
        tool2 = ToolCallState(id="tool-2", tool_name="write_file")
        iteration = AgentIteration(
            id="iter-1", iteration_number=1, tool_calls=[tool1, tool2]
        )
        widget = IterationWidget(iteration)
        assert len(iteration.tool_calls) == 2

    def test_widget_preserves_tool_call_data(self):
        """Widget preserves tool call data."""
        tool = ToolCallState(
            id="tool-1",
            tool_name="run_command",
            arguments='{"cmd": "ls"}',
            status="success",
            duration=0.3,
        )
        iteration = AgentIteration(id="iter-1", tool_calls=[tool])
        widget = IterationWidget(iteration)
        assert widget.iteration.tool_calls[0].tool_name == "run_command"
        assert widget.iteration.tool_calls[0].status == "success"


class TestIterationWidgetWithThinking:
    """Tests for IterationWidget with thinking content."""

    def test_widget_with_thinking_content(self):
        """Widget created with iteration containing thinking."""
        iteration = AgentIteration(
            id="iter-1",
            thinking="Let me analyze this problem...",
            status="thinking",
        )
        widget = IterationWidget(iteration)
        assert widget.iteration.thinking == "Let me analyze this problem..."

    def test_widget_show_thinking_false_preserves_data(self):
        """Widget with show_thinking=False still preserves thinking data."""
        iteration = AgentIteration(id="iter-1", thinking="Analysis...")
        widget = IterationWidget(iteration, show_thinking=False)
        assert widget.iteration.thinking == "Analysis..."
        assert widget.show_thinking is False


class TestIterationWidgetEdgeCases:
    """Tests for IterationWidget edge cases."""

    def test_empty_iteration(self):
        """Widget handles minimal iteration."""
        iteration = AgentIteration(id="minimal")
        widget = IterationWidget(iteration)
        assert widget.iteration.id == "minimal"
        assert widget.iteration.iteration_number == 0
        assert widget.iteration.thinking == ""

    def test_iteration_with_all_fields(self):
        """Widget handles iteration with all fields populated."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="success")
        iteration = AgentIteration(
            id="full-iter",
            iteration_number=3,
            thinking="Deep reasoning here",
            tool_calls=[tool],
            response_fragment="Final answer",
            status="complete",
            duration=5.5,
        )
        widget = IterationWidget(iteration)
        assert widget.iteration.id == "full-iter"
        assert widget.iteration.iteration_number == 3
        assert widget.iteration.thinking == "Deep reasoning here"
        assert len(widget.iteration.tool_calls) == 1
        assert widget.iteration.response_fragment == "Final answer"
        assert widget.iteration.status == "complete"
        assert widget.iteration.duration == 5.5


# =============================================================================
# Integration Tests (No App Context)
# =============================================================================


class TestIterationWidgetToolWorkflow:
    """Tests for typical tool call workflows."""

    def test_add_and_update_tool(self):
        """Add tool and update its status."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)

        tool = ToolCallState(id="tool-1", tool_name="read_file", status="pending")
        tool_widget = widget.add_tool_call(tool)

        with patch.object(tool_widget, "update_status"):
            widget.update_tool_call("tool-1", status="running")

        with patch.object(tool_widget, "update_status") as mock:
            widget.update_tool_call("tool-1", status="success", duration=0.5)
            mock.assert_called_with("success", 0.5)

    def test_multiple_tools_different_statuses(self):
        """Multiple tools can have different statuses."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)

        tool1 = ToolCallState(id="t1", tool_name="read_file", status="success")
        tool2 = ToolCallState(id="t2", tool_name="write_file", status="error")
        tool3 = ToolCallState(id="t3", tool_name="run_command", status="pending")

        widget.add_tool_call(tool1)
        widget.add_tool_call(tool2)
        widget.add_tool_call(tool3)

        assert len(widget._tool_widgets) == 3


class TestIterationLifecycle:
    """Tests for iteration lifecycle transitions."""

    def test_pending_to_thinking_to_executing_to_complete(self):
        """Iteration can transition through all statuses."""
        iteration = AgentIteration(id="iter-1", status="pending")
        widget = IterationWidget(iteration)

        statuses = ["pending", "thinking", "executing", "complete"]

        for status in statuses:
            widget.update_status(status)
            assert widget.iteration.status == status

    def test_status_with_duration_tracking(self):
        """Duration is tracked during status updates."""
        iteration = AgentIteration(id="iter-1", status="pending")
        widget = IterationWidget(iteration)

        widget.update_status("thinking", 0.0)
        widget.update_status("executing", 1.0)
        widget.update_status("complete", 2.5)

        assert widget.iteration.duration == 2.5


class TestThinkingSectionWorkflow:
    """Tests for thinking section workflow."""

    def test_update_thinking_multiple_times(self):
        """Thinking can be updated multiple times."""
        iteration = AgentIteration(id="iter-1")
        widget = IterationWidget(iteration)

        widget.update_thinking("First thought")
        assert widget.iteration.thinking == "First thought"

        widget.update_thinking("Second thought")
        assert widget.iteration.thinking == "Second thought"

        widget.update_thinking("Final reasoning")
        assert widget.iteration.thinking == "Final reasoning"


class TestToolCallItemWorkflow:
    """Tests for tool call item lifecycle."""

    def test_tool_status_transitions(self):
        """Tool can transition through statuses."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="pending")
        item = ToolCallItem(tool)

        item.update_status("running")
        assert item.tool_call.status == "running"

        item.update_status("success", 0.5)
        assert item.tool_call.status == "success"
        assert item.tool_call.duration == 0.5

    def test_tool_error_status(self):
        """Tool can end in error status."""
        tool = ToolCallState(id="tool-1", tool_name="test", status="running")
        item = ToolCallItem(tool)

        item.update_status("error", 0.1)
        assert item.tool_call.status == "error"
        assert item.tool_call.duration == 0.1
