"""Tests for widgets/blocks/response.py - ResponseWidget."""

from models import BlockState, BlockType
from widgets.blocks.response import ResponseWidget


class TestResponseWidgetInitialization:
    """Test ResponseWidget initialization and basic properties."""

    def test_initialization_stores_block_reference(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)
        assert widget.block is block

    def test_initialization_with_different_block_types(self):
        ai_block = BlockState(type=BlockType.AI_RESPONSE, content_input="q1")
        agent_block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="q2")

        ai_widget = ResponseWidget(ai_block)
        agent_widget = ResponseWidget(agent_block)

        assert ai_widget.block.type == BlockType.AI_RESPONSE
        assert agent_widget.block.type == BlockType.AGENT_RESPONSE

    def test_initial_content_text_is_empty(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)
        assert widget.content_text == ""

    def test_block_with_metadata_preserved(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"model": "gpt-4", "tokens": 100},
        )
        widget = ResponseWidget(block)
        assert widget.block.metadata["model"] == "gpt-4"
        assert widget.block.metadata["tokens"] == 100


class TestResponseWidgetReactiveContent:
    """Test the reactive content_text property."""

    def test_content_text_is_reactive(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Check that content_text is a reactive property (settable and tracks changes)
        widget.content_text = "new content"
        assert widget.content_text == "new content"

    def test_content_text_can_be_set_to_empty_string(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        widget.content_text = "some content"
        widget.content_text = ""
        assert widget.content_text == ""

    def test_content_text_handles_multiline(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        multiline = "Line 1\nLine 2\nLine 3"
        widget.content_text = multiline
        assert widget.content_text == multiline

    def test_content_text_handles_markdown(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        markdown_content = (
            "# Header\n\n**Bold** and *italic*\n\n```python\nprint('code')\n```"
        )
        widget.content_text = markdown_content
        assert widget.content_text == markdown_content

    def test_content_text_handles_unicode(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        unicode_content = "Unicode: 你好 🚀 Ñ ü ß"
        widget.content_text = unicode_content
        assert widget.content_text == unicode_content

    def test_content_text_handles_long_content(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        long_content = "x" * 10000
        widget.content_text = long_content
        assert len(widget.content_text) == 10000


class TestResponseWidgetSetSimple:
    """Test the set_simple method for toggling display modes."""

    def test_set_simple_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)
        assert hasattr(widget, "set_simple")
        assert callable(widget.set_simple)

    def test_set_simple_accepts_boolean(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Should not raise
        widget.set_simple(True)
        widget.set_simple(False)

    def test_set_simple_handles_unmounted_widget_gracefully(self):
        """set_simple should not raise when widget is not mounted."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Should not raise even when not mounted (container query will fail)
        widget.set_simple(True)
        widget.set_simple(False)


class TestResponseWidgetWatchContentText:
    """Test the watch_content_text watcher method."""

    def test_watch_content_text_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)
        assert hasattr(widget, "watch_content_text")
        assert callable(widget.watch_content_text)

    def test_watch_content_text_handles_unmounted_gracefully(self):
        """Watcher should not raise when widget is not mounted."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Should not raise even when query_one fails
        widget.watch_content_text("some new text")
        widget.watch_content_text("")

    def test_watch_content_text_with_empty_string(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Should handle empty string without raising
        widget.watch_content_text("")

    def test_watch_content_text_with_content(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Should handle content without raising
        widget.watch_content_text("Some response text")


class TestResponseWidgetCompose:
    """Test the compose method structure."""

    def test_compose_returns_generator(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)
        result = widget.compose()

        # compose() should return a generator (ComposeResult)
        assert hasattr(result, "__iter__")

    def test_compose_method_is_generator_function(self):
        import inspect

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        assert inspect.isgeneratorfunction(widget.compose) or hasattr(
            widget.compose(), "__iter__"
        )


class TestResponseWidgetBlockStateIntegration:
    """Test integration between ResponseWidget and BlockState."""

    def test_widget_maintains_block_reference_integrity(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="original")
        widget = ResponseWidget(block)

        # Modify block through widget reference
        widget.block.content_output = "modified output"

        assert block.content_output == "modified output"

    def test_widget_with_running_block(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ResponseWidget(block)

        assert widget.block.is_running is True

    def test_widget_with_completed_block(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = False
        block.content_output = "Final answer"
        widget = ResponseWidget(block)

        assert widget.block.is_running is False
        assert widget.block.content_output == "Final answer"

    def test_widget_preserves_block_id(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE, content_input="test", id="custom-id-123"
        )
        widget = ResponseWidget(block)

        assert widget.block.id == "custom-id-123"

    def test_widget_preserves_block_timestamp(self):
        from datetime import datetime

        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        block = BlockState(
            type=BlockType.AI_RESPONSE, content_input="test", timestamp=timestamp
        )
        widget = ResponseWidget(block)

        assert widget.block.timestamp == timestamp


class TestResponseWidgetInheritance:
    """Test ResponseWidget inheritance from Static."""

    def test_inherits_from_static(self):
        from textual.widgets import Static

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        assert isinstance(widget, Static)

    def test_has_standard_static_attributes(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Static widget should have these standard attributes/methods
        assert hasattr(widget, "update")
        assert hasattr(widget, "render")


class TestResponseWidgetEdgeCases:
    """Test edge cases and error handling."""

    def test_content_with_special_characters(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        special_content = "Special chars: < > & \" ' \\ / \t \r \n"
        widget.content_text = special_content
        assert widget.content_text == special_content

    def test_content_with_ansi_codes(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        ansi_content = "\x1b[31mRed\x1b[0m and \x1b[32mGreen\x1b[0m"
        widget.content_text = ansi_content
        assert widget.content_text == ansi_content

    def test_content_with_html_like_tags(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        html_content = "<div>Not HTML</div> <script>alert('x')</script>"
        widget.content_text = html_content
        assert widget.content_text == html_content

    def test_watch_content_text_exception_handling(self):
        """Verify watcher handles exceptions gracefully (wrapped in try/except)."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Multiple calls should not accumulate errors
        for _ in range(10):
            widget.watch_content_text("test content")
            widget.watch_content_text("")

    def test_set_simple_exception_handling(self):
        """Verify set_simple handles exceptions gracefully (wrapped in try/except)."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ResponseWidget(block)

        # Multiple calls should not raise
        for _ in range(10):
            widget.set_simple(True)
            widget.set_simple(False)


class TestResponseWidgetBlockTypes:
    """Test ResponseWidget with various BlockType values."""

    def test_with_ai_response_block_type(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="question")
        widget = ResponseWidget(block)
        assert widget.block.type == BlockType.AI_RESPONSE

    def test_with_agent_response_block_type(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="task")
        widget = ResponseWidget(block)
        assert widget.block.type == BlockType.AGENT_RESPONSE

    def test_with_command_block_type(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = ResponseWidget(block)
        assert widget.block.type == BlockType.COMMAND

    def test_with_system_msg_block_type(self):
        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="system")
        widget = ResponseWidget(block)
        assert widget.block.type == BlockType.SYSTEM_MSG
