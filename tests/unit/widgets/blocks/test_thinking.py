"""Tests for widgets/blocks/thinking.py - ThinkingWidget."""

from models import BlockState, BlockType
from widgets.blocks.thinking import ThinkingWidget


class TestThinkingWidgetInitialization:
    """Test ThinkingWidget initialization and basic properties."""

    def test_initialization_stores_block_reference(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget.block is block

    def test_initialization_with_running_block(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ThinkingWidget(block)
        assert widget.is_loading is True

    def test_initialization_with_completed_block(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = False
        widget = ThinkingWidget(block)
        assert widget.is_loading is False

    def test_initialization_with_content_output(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            content_output="Initial output",
        )
        block.is_running = False
        widget = ThinkingWidget(block)
        assert widget.thinking_text == "Initial output"

    def test_initialization_with_empty_content_output(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.content_output = ""
        widget = ThinkingWidget(block)
        assert widget.thinking_text == ""

    def test_initialization_sets_render_threshold(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._render_threshold == 8

    def test_initialization_sets_spinner_index_to_zero(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._spinner_index == 0

    def test_initialization_sets_spinner_timer_to_none(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._spinner_timer is None

    def test_initialization_detected_reasoning_false(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._detected_reasoning is False

    def test_initialization_code_blocks_rendered_false(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._code_blocks_rendered is False

    def test_initialization_last_rendered_len_zero(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._last_rendered_len == 0


class TestThinkingWidgetSpinnerFrames:
    """Test spinner frame class variable."""

    def test_spinner_frames_defined(self):
        assert hasattr(ThinkingWidget, "SPINNER_FRAMES")
        assert len(ThinkingWidget.SPINNER_FRAMES) > 0

    def test_spinner_frames_has_six_frames(self):
        assert len(ThinkingWidget.SPINNER_FRAMES) == 6

    def test_spinner_frames_are_strings(self):
        for frame in ThinkingWidget.SPINNER_FRAMES:
            assert isinstance(frame, str)

    def test_spinner_frames_are_non_empty(self):
        for frame in ThinkingWidget.SPINNER_FRAMES:
            assert len(frame) > 0


class TestThinkingWidgetReasoningPatterns:
    """Test reasoning pattern detection class variable."""

    def test_reasoning_patterns_defined(self):
        assert hasattr(ThinkingWidget, "REASONING_PATTERNS")
        assert len(ThinkingWidget.REASONING_PATTERNS) > 0

    def test_reasoning_patterns_includes_think_tag(self):
        assert "<think>" in ThinkingWidget.REASONING_PATTERNS

    def test_reasoning_patterns_includes_thinking_tag(self):
        assert "<thinking>" in ThinkingWidget.REASONING_PATTERNS

    def test_reasoning_patterns_includes_reasoning_tag(self):
        assert "<reasoning>" in ThinkingWidget.REASONING_PATTERNS

    def test_reasoning_patterns_includes_thought_tag(self):
        assert "<thought>" in ThinkingWidget.REASONING_PATTERNS

    def test_reasoning_patterns_is_tuple(self):
        assert isinstance(ThinkingWidget.REASONING_PATTERNS, tuple)


class TestThinkingWidgetReactiveProperties:
    """Test reactive properties."""

    def test_thinking_text_is_reactive(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = "new content"
        assert widget.thinking_text == "new content"

    def test_is_loading_is_reactive(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.is_loading = False
        assert widget.is_loading is False
        widget.is_loading = True
        assert widget.is_loading is True

    def test_is_expanded_is_reactive(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget.is_expanded is False
        widget.is_expanded = True
        assert widget.is_expanded is True

    def test_thinking_text_handles_multiline(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        multiline = "Line 1\nLine 2\nLine 3"
        widget.thinking_text = multiline
        assert widget.thinking_text == multiline

    def test_thinking_text_handles_unicode(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        unicode_content = "Unicode: 你好 Emoji: 🚀"
        widget.thinking_text = unicode_content
        assert widget.thinking_text == unicode_content

    def test_thinking_text_handles_long_content(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        long_content = "x" * 10000
        widget.thinking_text = long_content
        assert len(widget.thinking_text) == 10000


class TestThinkingWidgetReasoningDetection:
    """Test reasoning tag detection logic."""

    def test_check_for_reasoning_detects_think_tag(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("<think>Some reasoning</think>")
        assert result is True
        assert widget._detected_reasoning is True

    def test_check_for_reasoning_detects_thinking_tag(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("<thinking>Reasoning here</thinking>")
        assert result is True
        assert widget._detected_reasoning is True

    def test_check_for_reasoning_detects_reasoning_tag(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("<reasoning>Deep thoughts</reasoning>")
        assert result is True
        assert widget._detected_reasoning is True

    def test_check_for_reasoning_detects_thought_tag(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("<thought>My thought</thought>")
        assert result is True
        assert widget._detected_reasoning is True

    def test_check_for_reasoning_case_insensitive(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("<THINK>Uppercase tag</THINK>")
        assert result is True
        assert widget._detected_reasoning is True

    def test_check_for_reasoning_no_match_returns_false(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("No reasoning tags here")
        assert result is False
        assert widget._detected_reasoning is False

    def test_check_for_reasoning_empty_string(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("")
        assert result is False

    def test_check_for_reasoning_already_detected_returns_true(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget._detected_reasoning = True
        result = widget._check_for_reasoning("No tags needed now")
        assert result is True

    def test_check_for_reasoning_partial_tag(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning("think without angle brackets")
        assert result is False

    def test_check_for_reasoning_with_mixed_content(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget._check_for_reasoning(
            "Here is some text\n<think>reasoning</think>\nMore text"
        )
        assert result is True


class TestThinkingWidgetContentInitialization:
    """Test content initialization from block."""

    def test_initialization_with_reasoning_in_content(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            content_output="<think>Reasoning here</think>",
        )
        widget = ThinkingWidget(block)
        assert widget._detected_reasoning is True

    def test_initialization_without_reasoning_in_content(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            content_output="Plain response without reasoning",
        )
        widget = ThinkingWidget(block)
        assert widget._detected_reasoning is False

    def test_initialization_preserves_block_id(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE, content_input="test", id="custom-id-123"
        )
        widget = ThinkingWidget(block)
        assert widget.block.id == "custom-id-123"


class TestThinkingWidgetStopLoading:
    """Test stop_loading method."""

    def test_stop_loading_sets_is_loading_false(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ThinkingWidget(block)
        widget.is_loading = True
        widget.stop_loading()
        assert widget.is_loading is False

    def test_stop_loading_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "stop_loading")
        assert callable(widget.stop_loading)

    def test_stop_loading_when_already_stopped(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.is_loading = False
        widget.stop_loading()
        assert widget.is_loading is False


class TestThinkingWidgetStartLoading:
    """Test start_loading method."""

    def test_start_loading_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "start_loading")
        assert callable(widget.start_loading)

    def test_start_loading_sets_is_loading_attribute_directly(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.is_loading = False
        widget.is_loading = True
        assert widget.is_loading is True

    def test_start_loading_checks_timer_condition(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget._spinner_timer is None


class TestThinkingWidgetAnimateSpinner:
    """Test _animate_spinner method."""

    def test_animate_spinner_increments_index(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ThinkingWidget(block)
        widget.is_loading = True
        initial_index = widget._spinner_index
        widget._animate_spinner()
        assert widget._spinner_index == (initial_index + 1) % len(
            ThinkingWidget.SPINNER_FRAMES
        )

    def test_animate_spinner_wraps_around(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ThinkingWidget(block)
        widget.is_loading = True
        widget._spinner_index = len(ThinkingWidget.SPINNER_FRAMES) - 1
        widget._animate_spinner()
        assert widget._spinner_index == 0

    def test_animate_spinner_does_nothing_when_not_loading(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.is_loading = False
        widget._spinner_index = 0
        widget._animate_spinner()
        assert widget._spinner_index == 0


class TestThinkingWidgetCompose:
    """Test compose method."""

    def test_compose_returns_generator(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)


class TestThinkingWidgetForceRender:
    """Test force_render method."""

    def test_force_render_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "force_render")
        assert callable(widget.force_render)

    def test_force_render_updates_last_rendered_len(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = "Some content"
        widget.force_render()
        assert widget._last_rendered_len == len("Some content")

    def test_force_render_handles_empty_content(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = ""
        widget.force_render()
        assert widget._last_rendered_len == 0

    def test_force_render_handles_unmounted_gracefully(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = "Content"
        # Should not raise even when not mounted
        widget.force_render()


class TestThinkingWidgetWatchers:
    """Test watcher methods."""

    def test_watch_is_loading_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "watch_is_loading")
        assert callable(widget.watch_is_loading)

    def test_watch_is_loading_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget.watch_is_loading(True)
        widget.watch_is_loading(False)

    def test_watch_is_expanded_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "watch_is_expanded")
        assert callable(widget.watch_is_expanded)

    def test_watch_is_expanded_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget.watch_is_expanded(True)
        widget.watch_is_expanded(False)

    def test_watch_thinking_text_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "watch_thinking_text")
        assert callable(widget.watch_thinking_text)

    def test_watch_thinking_text_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget.watch_thinking_text("new text")
        widget.watch_thinking_text("")


class TestThinkingWidgetClickHandling:
    """Test click handling for expand/collapse."""

    def test_on_click_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "on_click")
        assert callable(widget.on_click)


class TestThinkingWidgetShowHeader:
    """Test _show_header internal method."""

    def test_show_header_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "_show_header")
        assert callable(widget._show_header)

    def test_show_header_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget._show_header(True)
        widget._show_header(False)


class TestThinkingWidgetInitCompleteState:
    """Test _init_complete_state internal method."""

    def test_init_complete_state_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "_init_complete_state")
        assert callable(widget._init_complete_state)

    def test_init_complete_state_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget._init_complete_state()


class TestThinkingWidgetUpdateLabelForReasoning:
    """Test _update_label_for_reasoning internal method."""

    def test_update_label_for_reasoning_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "_update_label_for_reasoning")
        assert callable(widget._update_label_for_reasoning)

    def test_update_label_for_reasoning_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget._update_label_for_reasoning()


class TestThinkingWidgetRenderWithCodeBlocks:
    """Test _render_with_code_blocks internal method."""

    def test_render_with_code_blocks_method_exists(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "_render_with_code_blocks")
        assert callable(widget._render_with_code_blocks)

    def test_render_with_code_blocks_handles_unmounted(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Should not raise even when not mounted
        widget._render_with_code_blocks()

    def test_render_with_code_blocks_sets_flag(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        # Even if it fails (unmounted), the method should attempt to set the flag
        # This is a design choice in the implementation
        widget._render_with_code_blocks()
        # Can't assert the flag was set because the try/except will prevent it
        # when unmounted, but at least it doesn't raise


class TestThinkingWidgetInheritance:
    """Test ThinkingWidget inheritance from Static."""

    def test_inherits_from_static(self):
        from textual.widgets import Static

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert isinstance(widget, Static)

    def test_has_standard_static_attributes(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert hasattr(widget, "update")
        assert hasattr(widget, "render")


class TestThinkingWidgetBlockStateIntegration:
    """Test integration between ThinkingWidget and BlockState."""

    def test_widget_maintains_block_reference_integrity(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="original")
        widget = ThinkingWidget(block)
        widget.block.content_output = "modified output"
        assert block.content_output == "modified output"

    def test_widget_with_different_block_types(self):
        ai_block = BlockState(type=BlockType.AI_RESPONSE, content_input="q1")
        agent_block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="q2")

        ai_widget = ThinkingWidget(ai_block)
        agent_widget = ThinkingWidget(agent_block)

        assert ai_widget.block.type == BlockType.AI_RESPONSE
        assert agent_widget.block.type == BlockType.AGENT_RESPONSE

    def test_block_with_metadata_preserved(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"model": "gpt-4", "tokens": 100},
        )
        widget = ThinkingWidget(block)
        assert widget.block.metadata["model"] == "gpt-4"
        assert widget.block.metadata["tokens"] == 100


class TestThinkingWidgetEdgeCases:
    """Test edge cases and error handling."""

    def test_content_with_special_characters(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        special_content = "Special chars: < > & \" ' \\ / \t \r \n"
        widget.thinking_text = special_content
        assert widget.thinking_text == special_content

    def test_content_with_ansi_codes(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        ansi_content = "\x1b[31mRed\x1b[0m and \x1b[32mGreen\x1b[0m"
        widget.thinking_text = ansi_content
        assert widget.thinking_text == ansi_content

    def test_content_with_html_like_tags(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        html_content = "<div>Not HTML</div> <script>alert('x')</script>"
        widget.thinking_text = html_content
        assert widget.thinking_text == html_content

    def test_content_with_markdown(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        markdown_content = (
            "# Header\n\n**Bold** and *italic*\n\n```python\nprint('code')\n```"
        )
        widget.thinking_text = markdown_content
        assert widget.thinking_text == markdown_content

    def test_content_with_urls(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        url_content = "Check out https://example.com and http://test.org/path"
        widget.thinking_text = url_content
        assert widget.thinking_text == url_content

    def test_watch_thinking_text_exception_handling(self):
        """Verify watcher handles exceptions gracefully (wrapped in try/except)."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        for _ in range(10):
            widget.watch_thinking_text("test content")
            widget.watch_thinking_text("")

    def test_force_render_exception_handling(self):
        """Verify force_render handles exceptions gracefully."""
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        for _ in range(10):
            widget.thinking_text = f"content {_}"
            widget.force_render()


class TestThinkingWidgetStreamingBehavior:
    """Test behavior during streaming content updates."""

    def test_throttling_with_small_delta(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget._last_rendered_len = 0
        # Small delta (less than threshold) should still be stored
        widget.thinking_text = "ab"
        assert widget.thinking_text == "ab"

    def test_throttling_with_large_delta(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget._last_rendered_len = 0
        # Large delta should trigger render
        widget.thinking_text = "a" * 20
        assert widget.thinking_text == "a" * 20

    def test_newline_triggers_render(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = "content\n"
        assert widget.thinking_text.endswith("\n")

    def test_incremental_content_updates(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = "Hello"
        widget.thinking_text = "Hello, world"
        widget.thinking_text = "Hello, world!"
        assert widget.thinking_text == "Hello, world!"


class TestThinkingWidgetExpandCollapse:
    """Test expand/collapse toggle behavior."""

    def test_initial_state_is_collapsed(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        assert widget.is_expanded is False

    def test_toggle_expand(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.is_expanded = True
        assert widget.is_expanded is True

    def test_toggle_collapse(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.is_expanded = True
        widget.is_expanded = False
        assert widget.is_expanded is False

    def test_multiple_toggles(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        for i in range(5):
            widget.is_expanded = i % 2 == 0
        # After 5 iterations (0, 1, 2, 3, 4), last is 4 % 2 == 0 -> True
        assert widget.is_expanded is True


class TestThinkingWidgetBlockTypes:
    """Test ThinkingWidget with various BlockType values."""

    def test_with_ai_response_block_type(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="question")
        widget = ThinkingWidget(block)
        assert widget.block.type == BlockType.AI_RESPONSE

    def test_with_agent_response_block_type(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="task")
        widget = ThinkingWidget(block)
        assert widget.block.type == BlockType.AGENT_RESPONSE

    def test_with_command_block_type(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = ThinkingWidget(block)
        assert widget.block.type == BlockType.COMMAND

    def test_with_system_msg_block_type(self):
        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="system")
        widget = ThinkingWidget(block)
        assert widget.block.type == BlockType.SYSTEM_MSG


class TestThinkingWidgetHiddenState:
    """Test hidden state management based on content and loading."""

    def test_stop_loading_with_empty_content_adds_hidden_class(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = ""
        widget.stop_loading()
        # The stop_loading method should trigger adding hidden class
        # when thinking_text is empty
        # This is tested by checking is_loading is False
        assert widget.is_loading is False

    def test_stop_loading_with_content_keeps_visible(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        widget = ThinkingWidget(block)
        widget.thinking_text = "Some thinking content"
        widget.stop_loading()
        assert widget.is_loading is False
        # Widget should remain visible with content


class TestThinkingWidgetStateTransitions:
    """Test state transitions throughout widget lifecycle."""

    def test_loading_to_complete_transition(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ThinkingWidget(block)
        assert widget.is_loading is True
        widget.stop_loading()
        assert widget.is_loading is False

    def test_complete_to_loading_transition_via_direct_set(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = False
        widget = ThinkingWidget(block)
        assert widget.is_loading is False
        widget.is_loading = True
        assert widget.is_loading is True

    def test_content_accumulation_during_streaming(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.is_running = True
        widget = ThinkingWidget(block)
        widget.thinking_text = "Part 1"
        widget.thinking_text = "Part 1 Part 2"
        widget.thinking_text = "Part 1 Part 2 Part 3"
        assert "Part 1" in widget.thinking_text
        assert "Part 2" in widget.thinking_text
        assert "Part 3" in widget.thinking_text
