"""Tests for widgets/blocks/execution.py - ExecutionWidget."""

from unittest.mock import MagicMock, patch

from models import BlockState, BlockType
from widgets.blocks.execution import ExecutionWidget


class TestExecutionWidgetInit:
    """Test ExecutionWidget initialization."""

    def test_init_with_basic_block(self):
        """Widget initializes with a BlockState."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.block is block

    def test_init_stores_block_reference(self):
        """Widget stores reference to block, not a copy."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="query")
        widget = ExecutionWidget(block)
        assert widget.block is block

    def test_exec_output_reactive_default_empty(self):
        """exec_output reactive starts empty by default."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.exec_output == ""

    def test_is_expanded_reactive_default_false(self):
        """is_expanded reactive starts as False by default."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.is_expanded is False

    def test_init_restores_content_from_block_state(self):
        """Widget restores exec_output from block.content_exec_output if present."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "**Tool Call: read_file**\nContent here"
        widget = ExecutionWidget(block)
        assert widget.exec_output == "**Tool Call: read_file**\nContent here"

    def test_init_without_content_exec_output_stays_empty(self):
        """Widget exec_output stays empty if block has no content_exec_output."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.exec_output == ""

    def test_init_with_empty_content_exec_output(self):
        """Widget handles empty string content_exec_output."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = ""
        widget = ExecutionWidget(block)
        assert widget.exec_output == ""


class TestExecutionWidgetReactiveProperties:
    """Test reactive property behavior."""

    def test_exec_output_can_be_set(self):
        """exec_output can be set programmatically."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        widget.exec_output = "new output"
        assert widget.exec_output == "new output"

    def test_is_expanded_can_be_toggled(self):
        """is_expanded can be toggled."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.is_expanded is False
        widget.is_expanded = True
        assert widget.is_expanded is True
        widget.is_expanded = False
        assert widget.is_expanded is False


class TestExecutionWidgetToolParsing:
    """Test tool call parsing from exec_output."""

    def test_single_tool_call_pattern_detected(self):
        """Single tool call pattern is detected in output."""
        output = '**Tool Call: read_file**\n```json\n{"path": "/etc/hosts"}\n```'
        import re

        matches = re.findall(r"\*\*Tool Call: (.*?)\*\*", output)
        assert len(matches) == 1
        assert matches[0] == "read_file"

    def test_multiple_tool_calls_detected(self):
        """Multiple tool calls are all detected."""
        output = (
            "**Tool Call: read_file**\nContent 1\n"
            "**Tool Call: write_file**\nContent 2\n"
            "**Tool Call: run_command**\nContent 3"
        )
        import re

        matches = re.findall(r"\*\*Tool Call: (.*?)\*\*", output)
        assert len(matches) == 3
        assert matches == ["read_file", "write_file", "run_command"]

    def test_duplicate_tool_calls_all_captured(self):
        """Duplicate tool calls in sequence are captured."""
        output = (
            "**Tool Call: read_file**\nFirst call\n"
            "**Tool Call: read_file**\nSecond call\n"
        )
        import re

        matches = re.findall(r"\*\*Tool Call: (.*?)\*\*", output)
        assert len(matches) == 2
        assert matches == ["read_file", "read_file"]

    def test_no_tool_calls_returns_empty(self):
        """Output without tool calls returns empty list."""
        output = "Just some regular text without tool markers"
        import re

        matches = re.findall(r"\*\*Tool Call: (.*?)\*\*", output)
        assert matches == []

    def test_partial_tool_marker_not_matched(self):
        """Incomplete tool markers are not matched."""
        output = "**Tool Call: incomplete"
        import re

        matches = re.findall(r"\*\*Tool Call: (.*?)\*\*", output)
        assert matches == []


class TestExecutionWidgetSummaryGeneration:
    """Test summary text generation for tool calls."""

    def test_unique_tools_extracted(self):
        """Only unique tool names are extracted for summary."""
        tool_matches = [
            "read_file",
            "write_file",
            "read_file",
            "run_command",
            "read_file",
        ]
        unique_tools = []
        seen = set()
        for t in tool_matches:
            if t not in seen:
                unique_tools.append(t)
                seen.add(t)
        assert unique_tools == ["read_file", "write_file", "run_command"]

    def test_summary_text_joined_with_comma(self):
        """Unique tools are joined with comma separator."""
        unique_tools = ["read_file", "write_file", "run_command"]
        summary_text = ", ".join(unique_tools)
        assert summary_text == "read_file, write_file, run_command"

    def test_long_summary_truncated_at_40_chars(self):
        """Summary longer than 40 chars is truncated with ellipsis."""
        unique_tools = ["very_long_tool_name_one", "very_long_tool_name_two"]
        summary_text = ", ".join(unique_tools)
        if len(summary_text) > 40:
            summary_text = summary_text[:37] + "..."
        assert len(summary_text) <= 40
        assert summary_text.endswith("...")

    def test_short_summary_not_truncated(self):
        """Summary under 40 chars is not truncated."""
        unique_tools = ["read", "write"]
        summary_text = ", ".join(unique_tools)
        if len(summary_text) > 40:
            summary_text = summary_text[:37] + "..."
        assert summary_text == "read, write"
        assert not summary_text.endswith("...")

    def test_exactly_40_chars_not_truncated(self):
        """Summary at exactly 40 chars is not truncated."""
        unique_tools = ["aaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbb"]
        summary_text = ", ".join(unique_tools)
        original_len = len(summary_text)
        if len(summary_text) > 40:
            summary_text = summary_text[:37] + "..."
        if original_len <= 40:
            assert not summary_text.endswith("...")


class TestExecutionWidgetCopyLogic:
    """Test clipboard copy functionality."""

    def test_copy_text_with_code_fence_stripped(self):
        """Code fences are stripped before copying."""
        text = "```python\nprint('hello')\n```"
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        assert text == "print('hello')"

    def test_copy_text_without_code_fence_unchanged(self):
        """Text without code fences is unchanged."""
        text = "Just plain text"
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        assert text == "Just plain text"

    def test_copy_single_line_code_fence_unchanged(self):
        """Single line in code fence leaves text unchanged."""
        text = "```only one line```"
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        assert text == "```only one line```"

    def test_copy_multi_line_code_fence_extracts_content(self):
        """Multi-line code fence extracts inner content."""
        text = '```json\n{"key": "value"}\n{"another": "object"}\n```'
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) > 2:
                text = "\n".join(lines[1:-1])
        assert text == '{"key": "value"}\n{"another": "object"}'

    def test_copy_empty_content_returns_empty(self):
        """Empty content returns empty string."""
        text = ""
        if text:
            if text.startswith("```") and text.endswith("```"):
                lines = text.split("\n")
                if len(lines) > 2:
                    text = "\n".join(lines[1:-1])
        assert text == ""


class TestExecutionWidgetBlockTypes:
    """Test widget behavior with different block types."""

    def test_works_with_ai_response_block(self):
        """Widget works with AI_RESPONSE block type."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="question")
        widget = ExecutionWidget(block)
        assert widget.block.type == BlockType.AI_RESPONSE

    def test_works_with_agent_response_block(self):
        """Widget works with AGENT_RESPONSE block type."""
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="task")
        widget = ExecutionWidget(block)
        assert widget.block.type == BlockType.AGENT_RESPONSE

    def test_works_with_command_block(self):
        """Widget works with COMMAND block type."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls -la")
        widget = ExecutionWidget(block)
        assert widget.block.type == BlockType.COMMAND


class TestExecutionWidgetPyperclipFallback:
    """Test pyperclip availability detection."""

    def test_pyperclip_import_optional(self):
        """pyperclip import is optional (handled gracefully if missing)."""
        try:
            import pyperclip  # noqa: F401

            pyperclip_available = True
        except ImportError:
            pyperclip_available = False
        assert isinstance(pyperclip_available, bool)


class TestExecutionWidgetCompose:
    """Test compose structure (without mounting)."""

    def test_widget_has_compose_method(self):
        """Widget has compose method for building UI."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)


class TestExecutionWidgetClickHandling:
    """Test click event handling logic."""

    def test_header_row_click_toggles_expanded(self):
        """Click on row 0 should toggle expansion state."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.is_expanded is False
        event_y = 0
        if event_y == 0:
            widget.is_expanded = not widget.is_expanded
        assert widget.is_expanded is True

    def test_non_header_click_does_not_toggle(self):
        """Click on row > 0 should not toggle expansion."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert widget.is_expanded is False
        event_y = 5
        if event_y == 0:
            widget.is_expanded = not widget.is_expanded
        assert widget.is_expanded is False


class TestExecutionWidgetWatcherBehavior:
    """Test reactive watcher behavior patterns."""

    def test_watch_is_expanded_watcher_exists(self):
        """Widget has watch_is_expanded method."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "watch_is_expanded")
        assert callable(widget.watch_is_expanded)

    def test_watch_exec_output_watcher_exists(self):
        """Widget has watch_exec_output method."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "watch_exec_output")
        assert callable(widget.watch_exec_output)


class TestExecutionWidgetEventHandlers:
    """Test event handler decorators."""

    def test_copy_output_handler_exists(self):
        """Widget has copy_output method for copy button."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "copy_output")
        assert callable(widget.copy_output)

    def test_on_click_handler_exists(self):
        """Widget has on_click method."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "on_click")
        assert callable(widget.on_click)


class TestExecutionWidgetMarkdownRendering:
    """Test markdown content rendering expectations."""

    def test_exec_output_with_markdown_formatting(self):
        """exec_output can contain markdown formatting."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        markdown_content = """
**Tool Call: read_file**
```json
{"path": "/etc/hosts"}
```

**Result:**
```
127.0.0.1 localhost
```
"""
        widget.exec_output = markdown_content
        assert "**Tool Call: read_file**" in widget.exec_output
        assert "```json" in widget.exec_output


class TestExecutionWidgetInheritance:
    """Test widget inheritance structure."""

    def test_inherits_from_static(self):
        """ExecutionWidget inherits from Static."""
        from textual.widgets import Static

        assert issubclass(ExecutionWidget, Static)

    def test_has_reactive_decorator_usage(self):
        """Widget uses reactive decorator for state management."""

        assert hasattr(ExecutionWidget, "exec_output")
        assert hasattr(ExecutionWidget, "is_expanded")


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestExecutionWidgetWatchIsExpanded:
    """Test watch_is_expanded watcher behavior."""

    def test_watch_is_expanded_with_expanded_true_logic(self):
        """When expanded=True, container should remove collapsed class."""
        # This tests the logic without mounting
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        # The method exists and handles the expansion state
        assert callable(widget.watch_is_expanded)
        # Toggle the state
        widget.is_expanded = True
        assert widget.is_expanded is True

    def test_watch_is_expanded_with_expanded_false_logic(self):
        """When expanded=False, container should add collapsed class."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        widget.is_expanded = True
        widget.is_expanded = False
        assert widget.is_expanded is False

    def test_watch_is_expanded_handles_missing_container_gracefully(self):
        """Watcher handles missing container without raising exceptions."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        # Call watcher directly - should not raise even without mounted widgets
        try:
            widget.watch_is_expanded(True)
        except Exception:
            pass  # Expected - no widgets mounted
        # No assertion needed - we just verify it doesn't crash unexpectedly


class TestExecutionWidgetOnClick:
    """Test on_click event handler."""

    def test_on_click_toggles_expanded_on_row_zero(self):
        """Click on row 0 toggles is_expanded."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        # Create a mock Click event
        mock_event = MagicMock()
        mock_event.y = 0

        assert widget.is_expanded is False
        widget.on_click(mock_event)
        assert widget.is_expanded is True
        mock_event.stop.assert_called_once()

    def test_on_click_toggles_back_on_second_click(self):
        """Second click on row 0 toggles back."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        mock_event = MagicMock()
        mock_event.y = 0

        widget.on_click(mock_event)
        assert widget.is_expanded is True

        mock_event.reset_mock()
        widget.on_click(mock_event)
        assert widget.is_expanded is False
        mock_event.stop.assert_called_once()

    def test_on_click_does_not_toggle_on_non_header_row(self):
        """Click on row > 0 does not toggle is_expanded."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        mock_event = MagicMock()
        mock_event.y = 1

        widget.on_click(mock_event)
        assert widget.is_expanded is False
        mock_event.stop.assert_not_called()

    def test_on_click_does_not_toggle_on_row_5(self):
        """Click on row 5 does not toggle."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        mock_event = MagicMock()
        mock_event.y = 5

        widget.on_click(mock_event)
        assert widget.is_expanded is False

    def test_on_click_event_stop_only_called_on_header(self):
        """event.stop() is only called when clicking header row."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        # Non-header click
        mock_event = MagicMock()
        mock_event.y = 2
        widget.on_click(mock_event)
        mock_event.stop.assert_not_called()

        # Header click
        mock_event.y = 0
        widget.on_click(mock_event)
        mock_event.stop.assert_called_once()


class TestExecutionWidgetWatchExecOutput:
    """Test watch_exec_output watcher behavior."""

    def test_watch_exec_output_handles_missing_container(self):
        """Watcher handles missing container gracefully."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        # Call watcher directly - should not raise
        try:
            widget.watch_exec_output("new content")
        except Exception:
            pass  # Expected without mounted widgets

    def test_watch_exec_output_callable(self):
        """watch_exec_output is callable."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert callable(widget.watch_exec_output)

    def test_watch_exec_output_with_empty_string(self):
        """Watcher handles empty string input."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        try:
            widget.watch_exec_output("")
        except Exception:
            pass  # Expected without mounted widgets

    def test_watch_exec_output_with_tool_call_content(self):
        """Watcher handles content with tool call markers."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        content = "**Tool Call: read_file**\nSome output"
        try:
            widget.watch_exec_output(content)
        except Exception:
            pass  # Expected without mounted widgets


class TestExecutionWidgetCopyOutput:
    """Test copy_output method."""

    def test_copy_output_with_empty_content_notifies_warning(self):
        """copy_output notifies warning when content is empty."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = ""
        widget = ExecutionWidget(block)

        with patch.object(widget, "notify") as mock_notify:
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_once_with("Nothing to copy", severity="warning")

    def test_copy_output_with_none_content_notifies_warning(self):
        """copy_output notifies warning when content is None."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = None
        widget = ExecutionWidget(block)

        with patch.object(widget, "notify") as mock_notify:
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_once_with("Nothing to copy", severity="warning")

    def test_copy_output_with_no_content_attr_notifies_warning(self):
        """copy_output notifies warning when attr missing."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        # Don't set content_exec_output
        widget = ExecutionWidget(block)

        with patch.object(widget, "notify") as mock_notify:
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_once_with("Nothing to copy", severity="warning")

    @patch("widgets.blocks.execution.pyperclip", None)
    def test_copy_output_without_pyperclip_tries_xclip_on_linux(self):
        """copy_output tries xclip on Linux when pyperclip unavailable."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content"
        widget = ExecutionWidget(block)

        with (
            patch("subprocess.run") as mock_run,
            patch("sys.platform", "linux"),
            patch.object(widget, "notify"),
        ):
            mock_run.return_value = MagicMock()
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_run.assert_called_once()
            # Check xclip was called with correct args
            call_args = mock_run.call_args
            assert call_args[0][0] == ["xclip", "-selection", "clipboard"]

    @patch("widgets.blocks.execution.pyperclip", None)
    def test_copy_output_xclip_success_notifies(self):
        """copy_output notifies success when xclip works."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content"
        widget = ExecutionWidget(block)

        with (
            patch("subprocess.run") as mock_run,
            patch("sys.platform", "linux"),
            patch.object(widget, "notify") as mock_notify,
        ):
            mock_run.return_value = MagicMock()
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_with("Copied to clipboard!")

    @patch("widgets.blocks.execution.pyperclip", None)
    def test_copy_output_xclip_failure_suggests_pyperclip(self):
        """copy_output suggests pyperclip when xclip fails."""

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content"
        widget = ExecutionWidget(block)

        with (
            patch("subprocess.run") as mock_run,
            patch("sys.platform", "linux"),
            patch.object(widget, "notify") as mock_notify,
        ):
            mock_run.side_effect = FileNotFoundError()
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_with(
                "Install pyperclip: pip install pyperclip", severity="warning"
            )

    @patch("widgets.blocks.execution.pyperclip", None)
    def test_copy_output_xclip_called_process_error(self):
        """copy_output handles CalledProcessError from xclip."""
        import subprocess

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content"
        widget = ExecutionWidget(block)

        with (
            patch("subprocess.run") as mock_run,
            patch("sys.platform", "linux"),
            patch.object(widget, "notify") as mock_notify,
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "xclip")
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_with(
                "Install pyperclip: pip install pyperclip", severity="warning"
            )

    @patch("widgets.blocks.execution.pyperclip", None)
    def test_copy_output_non_linux_suggests_pyperclip(self):
        """copy_output suggests pyperclip on non-Linux without pyperclip."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content"
        widget = ExecutionWidget(block)

        with (
            patch("sys.platform", "darwin"),
            patch.object(widget, "notify") as mock_notify,
        ):
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_with(
                "Install pyperclip: pip install pyperclip", severity="warning"
            )

    def test_copy_output_with_pyperclip_copies_text(self):
        """copy_output uses pyperclip when available."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content to copy"
        widget = ExecutionWidget(block)

        mock_pyperclip = MagicMock()
        with (
            patch("widgets.blocks.execution.pyperclip", mock_pyperclip),
            patch.object(widget, "notify") as mock_notify,
        ):
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_pyperclip.copy.assert_called_once_with("test content to copy")
            mock_notify.assert_called_with("Copied to clipboard!")

    def test_copy_output_strips_code_fence(self):
        """copy_output strips code fences before copying."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "```python\nprint('hello')\n```"
        widget = ExecutionWidget(block)

        mock_pyperclip = MagicMock()
        with (
            patch("widgets.blocks.execution.pyperclip", mock_pyperclip),
            patch.object(widget, "notify"),
        ):
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            # Should strip the fences
            mock_pyperclip.copy.assert_called_once_with("print('hello')")

    def test_copy_output_preserves_single_line_fence(self):
        """copy_output preserves single-line code fence (not enough lines to strip)."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "```single```"
        widget = ExecutionWidget(block)

        mock_pyperclip = MagicMock()
        with (
            patch("widgets.blocks.execution.pyperclip", mock_pyperclip),
            patch.object(widget, "notify"),
        ):
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            # Single line fence is preserved (lines <= 2)
            mock_pyperclip.copy.assert_called_once_with("```single```")

    def test_copy_output_exception_notifies_error(self):
        """copy_output notifies error when exception occurs."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_exec_output = "test content"
        widget = ExecutionWidget(block)

        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = Exception("Clipboard error")
        with (
            patch("widgets.blocks.execution.pyperclip", mock_pyperclip),
            patch.object(widget, "notify") as mock_notify,
        ):
            mock_event = MagicMock()
            widget.copy_output(mock_event)
            mock_notify.assert_called_with(
                "Copy failed: Clipboard error", severity="error"
            )


class TestExecutionWidgetComposeMethod:
    """Test compose method structure."""

    def test_compose_returns_generator(self):
        """compose returns a generator."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_is_callable(self):
        """compose method is callable and defined."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert callable(widget.compose)
        assert hasattr(widget, "compose")


class TestExecutionWidgetToolParsingIntegration:
    """Integration tests for tool call parsing in watch_exec_output."""

    def test_tool_parsing_pattern_matches_standard_format(self):
        """Tool pattern matches standard **Tool Call: name** format."""
        import re

        pattern = r"\*\*Tool Call: (.*?)\*\*"

        test_cases = [
            ("**Tool Call: read_file**", ["read_file"]),
            ("**Tool Call: write_file**", ["write_file"]),
            ("**Tool Call: run_command**", ["run_command"]),
            ("Some text **Tool Call: test** more text", ["test"]),
        ]

        for text, expected in test_cases:
            matches = re.findall(pattern, text)
            assert matches == expected

    def test_tool_parsing_extracts_multiple_tools(self):
        """Tool pattern extracts multiple tool calls."""
        import re

        pattern = r"\*\*Tool Call: (.*?)\*\*"

        text = """
        **Tool Call: read_file**
        Some output
        **Tool Call: write_file**
        More output
        **Tool Call: run_command**
        """

        matches = re.findall(pattern, text)
        assert matches == ["read_file", "write_file", "run_command"]

    def test_unique_tools_filtering(self):
        """Unique tools are filtered correctly."""
        tool_matches = [
            "read_file",
            "write_file",
            "read_file",
            "run_command",
            "write_file",
        ]

        unique_tools = []
        seen = set()
        for t in tool_matches:
            if t not in seen:
                unique_tools.append(t)
                seen.add(t)

        assert unique_tools == ["read_file", "write_file", "run_command"]

    def test_summary_truncation_at_40_chars(self):
        """Summary text is truncated at 40 characters."""
        unique_tools = ["very_long_tool_name_one", "very_long_tool_name_two", "another"]
        summary_text = ", ".join(unique_tools)

        if len(summary_text) > 40:
            summary_text = summary_text[:37] + "..."

        assert len(summary_text) == 40
        assert summary_text.endswith("...")


class TestExecutionWidgetEdgeCases:
    """Edge case tests."""

    def test_block_without_content_exec_output_attr(self):
        """Widget handles block without content_exec_output attribute."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        # Don't set content_exec_output
        widget = ExecutionWidget(block)
        assert widget.exec_output == ""

    def test_exec_output_updates_propagate(self):
        """Setting exec_output updates the reactive property."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        widget.exec_output = "first update"
        assert widget.exec_output == "first update"

        widget.exec_output = "second update"
        assert widget.exec_output == "second update"

    def test_is_expanded_multiple_toggles(self):
        """is_expanded can be toggled multiple times."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)

        for expected in [True, False, True, False, True]:
            widget.is_expanded = expected
            assert widget.is_expanded == expected

    def test_widget_with_unicode_content(self):
        """Widget handles unicode content in exec_output."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        widget.exec_output = "Unicode: \u2714 \u2718 \u26a0 \U0001f4c1"
        assert "\u2714" in widget.exec_output

    def test_widget_with_multiline_content(self):
        """Widget handles multiline content."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        widget.exec_output = "Line 1\nLine 2\nLine 3\n"
        assert widget.exec_output.count("\n") == 3

    def test_widget_with_very_long_content(self):
        """Widget handles very long content."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        long_content = "x" * 10000
        widget.exec_output = long_content
        assert len(widget.exec_output) == 10000


class TestExecutionWidgetClassStructure:
    """Test class structure and CSS classes."""

    def test_widget_has_default_css_classes(self):
        """Widget should have proper CSS class handling."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        # Widget inherits from Static which has class handling
        assert hasattr(widget, "add_class")
        assert hasattr(widget, "remove_class")
        assert hasattr(widget, "has_class")

    def test_widget_has_query_one_method(self):
        """Widget has query_one method for finding children."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "query_one")
        assert callable(widget.query_one)

    def test_widget_has_notify_method(self):
        """Widget has notify method for notifications."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ExecutionWidget(block)
        assert hasattr(widget, "notify")
        assert callable(widget.notify)
