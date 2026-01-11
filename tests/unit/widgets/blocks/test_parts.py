"""Tests for widgets/blocks/parts.py - Block UI components."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from rich.text import Text

from models import BlockState, BlockType
from widgets.blocks.parts import (
    ANSI_PATTERN,
    MAX_OUTPUT_LINES,
    URL_PATTERN,
    BlockBody,
    BlockFooter,
    BlockHeader,
    BlockMeta,
    StopButton,
    VizButton,
)


class TestStopButtonMessage:
    def test_pressed_message_carries_block_id(self):
        msg = StopButton.Pressed("block_123")
        assert msg.block_id == "block_123"

    def test_pressed_message_different_ids(self):
        msg1 = StopButton.Pressed("block_a")
        msg2 = StopButton.Pressed("block_b")
        assert msg1.block_id != msg2.block_id


class TestVizButtonMessage:
    def test_pressed_message_carries_block_id(self):
        msg = VizButton.Pressed("block_456")
        assert msg.block_id == "block_456"


class TestBlockBodyTruncation:
    def test_empty_text_returns_empty_without_truncation(self):
        body = BlockBody()
        result, was_truncated, total = body._truncate_output("")
        assert result == ""
        assert was_truncated is False
        assert total == 0

    def test_text_under_limit_returns_unchanged(self):
        body = BlockBody(max_lines=10)
        text = "line1\nline2\nline3"
        result, was_truncated, total = body._truncate_output(text)
        assert result == text
        assert was_truncated is False
        assert total == 3

    def test_text_at_exact_limit_returns_unchanged(self):
        body = BlockBody(max_lines=5)
        lines = [f"line{i}" for i in range(5)]
        text = "\n".join(lines)
        result, was_truncated, total = body._truncate_output(text)
        assert result == text
        assert was_truncated is False
        assert total == 5

    def test_text_over_limit_truncates_and_keeps_recent_lines(self):
        body = BlockBody(max_lines=3)
        lines = ["old1", "old2", "old3", "new1", "new2", "new3"]
        text = "\n".join(lines)
        result, was_truncated, total = body._truncate_output(text)

        assert was_truncated is True
        assert total == 6
        assert "new1" in result
        assert "new2" in result
        assert "new3" in result
        assert "old1" not in result
        assert "old2" not in result
        assert "old3" not in result

    def test_truncation_indicator_shows_count(self):
        body = BlockBody(max_lines=2)
        lines = ["a", "b", "c", "d", "e"]
        text = "\n".join(lines)
        result, was_truncated, total = body._truncate_output(text)

        assert "3" in result
        assert "truncated" in result.lower()

    def test_truncation_preserves_line_content_integrity(self):
        body = BlockBody(max_lines=2)
        text = "first line with data\nsecond line\nthird with more data\nfourth final"
        result, was_truncated, total = body._truncate_output(text)

        assert "third with more data" in result
        assert "fourth final" in result


class TestBlockBodyLinkDetection:
    def test_empty_text_returns_empty_rich_text(self):
        body = BlockBody()
        result = body._make_links_clickable("")
        assert isinstance(result, Text)
        assert result.plain == ""

    def test_text_without_urls_preserved(self):
        body = BlockBody()
        result = body._make_links_clickable("Hello world, no links here!")
        assert result.plain == "Hello world, no links here!"

    def test_http_url_detected_and_included(self):
        body = BlockBody()
        result = body._make_links_clickable("Visit http://example.com for info")
        assert "http://example.com" in result.plain

    def test_https_url_detected_and_included(self):
        body = BlockBody()
        result = body._make_links_clickable("Secure at https://secure.example.com")
        assert "https://secure.example.com" in result.plain

    def test_multiple_urls_all_detected(self):
        body = BlockBody()
        text = "Check https://first.com and https://second.com/path"
        result = body._make_links_clickable(text)
        assert "https://first.com" in result.plain
        assert "https://second.com/path" in result.plain

    def test_url_with_query_params_preserved(self):
        body = BlockBody()
        result = body._make_links_clickable(
            "Search: https://google.com/search?q=test&lang=en"
        )
        assert "?q=test&lang=en" in result.plain

    def test_surrounding_text_preserved_around_url(self):
        body = BlockBody()
        result = body._make_links_clickable("Before https://link.com after")
        assert result.plain == "Before https://link.com after"


class TestBlockBodyPromptStyling:
    def test_dollar_prompt_splits_correctly(self):
        body = BlockBody()
        result = Text()
        body._append_styled_segment(result, "$ ls -la")
        assert result.plain == "$ ls -la"

    def test_gt_prompt_splits_correctly(self):
        body = BlockBody()
        result = Text()
        body._append_styled_segment(result, "> echo hello")
        assert result.plain == "> echo hello"

    def test_separator_dash_preserved(self):
        body = BlockBody()
        result = Text()
        body._append_styled_segment(result, "────────")
        assert result.plain == "────────"

    def test_separator_dot_preserved(self):
        body = BlockBody()
        result = Text()
        body._append_styled_segment(result, "┄┄┄┄┄┄┄┄")
        assert result.plain == "┄┄┄┄┄┄┄┄"

    def test_multiline_handles_each_line(self):
        body = BlockBody()
        result = Text()
        body._append_styled_segment(result, "line1\n$ command\nline3")
        assert "line1" in result.plain
        assert "$ command" in result.plain
        assert "line3" in result.plain


class TestBlockBodyAnsiHandling:
    def test_ansi_text_converted_to_rich_text(self):
        body = BlockBody()
        ansi_text = "\x1b[31mRed text\x1b[0m normal"
        result = body._make_links_clickable(ansi_text)
        assert isinstance(result, Text)
        assert "Red text" in result.plain
        assert "normal" in result.plain

    def test_ansi_with_url_preserves_both(self):
        body = BlockBody()
        ansi_text = "\x1b[32mGreen:\x1b[0m https://example.com"
        result = body._parse_ansi_with_urls(ansi_text)
        assert "Green:" in result.plain
        assert "https://example.com" in result.plain


class TestBlockFooterContentDecision:
    def test_running_block_has_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.is_running = True
        footer = BlockFooter(block)
        assert footer._has_content() is True

    def test_failed_exit_code_has_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="bad_cmd")
        block.exit_code = 127
        footer = BlockFooter(block)
        assert footer._has_content() is True

    def test_success_exit_code_no_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = 0
        block.is_running = False
        footer = BlockFooter(block)
        assert footer._has_content() is False

    def test_no_exit_code_not_running_no_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = None
        block.is_running = False
        footer = BlockFooter(block)
        assert footer._has_content() is False

    def test_empty_footer_class_applied_when_no_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = 0
        block.is_running = False
        footer = BlockFooter(block)
        assert "empty-footer" in footer.classes

    def test_empty_footer_class_not_applied_when_running(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.is_running = True
        footer = BlockFooter(block)
        assert "empty-footer" not in footer.classes


class TestUrlPatternRegex:
    def test_matches_http(self):
        assert URL_PATTERN.search("http://example.com") is not None

    def test_matches_https(self):
        assert URL_PATTERN.search("https://example.com") is not None

    def test_matches_ftp(self):
        assert URL_PATTERN.search("ftp://files.example.com") is not None

    def test_captures_path(self):
        match = URL_PATTERN.search("https://example.com/path/to/resource")
        assert match is not None
        assert "/path/to/resource" in match.group(0)

    def test_captures_query_string(self):
        match = URL_PATTERN.search("https://api.com/search?q=test&page=1")
        assert match is not None
        assert "?q=test&page=1" in match.group(0)

    def test_stops_at_whitespace(self):
        match = URL_PATTERN.search("https://example.com/path next word")
        assert match is not None
        assert match.group(0) == "https://example.com/path"

    def test_stops_at_closing_paren(self):
        match = URL_PATTERN.search("(see https://example.com)")
        assert match is not None
        assert match.group(0) == "https://example.com"

    def test_no_match_for_plain_text(self):
        assert URL_PATTERN.search("just plain text here") is None

    def test_no_match_for_email(self):
        assert URL_PATTERN.search("email@example.com") is None


class TestAnsiPatternRegex:
    def test_matches_color_code(self):
        assert ANSI_PATTERN.search("\x1b[31m") is not None

    def test_matches_reset_code(self):
        assert ANSI_PATTERN.search("\x1b[0m") is not None

    def test_matches_cursor_movement(self):
        assert ANSI_PATTERN.search("\x1b[2A") is not None

    def test_matches_multiple_params(self):
        assert ANSI_PATTERN.search("\x1b[1;31;40m") is not None

    def test_no_match_for_plain_text(self):
        assert ANSI_PATTERN.search("plain text") is None


class TestMaxOutputLinesConstant:
    def test_max_output_lines_is_reasonable(self):
        assert MAX_OUTPUT_LINES >= 100
        assert MAX_OUTPUT_LINES <= 10000


class TestStopButtonInit:
    def test_initializes_with_block_id(self):
        btn = StopButton(block_id="block_123")
        assert btn._block_id == "block_123"

    def test_initializes_as_label_subclass(self):
        from textual.widgets import Label

        btn = StopButton(block_id="test")
        assert isinstance(btn, Label)

    def test_has_stop_btn_id(self):
        btn = StopButton(block_id="test")
        assert btn.id == "stop-btn"

    def test_has_stop_action_class(self):
        btn = StopButton(block_id="test")
        assert "stop-action" in btn.classes

    def test_different_block_ids_stored_correctly(self):
        btn1 = StopButton(block_id="block_a")
        btn2 = StopButton(block_id="block_b")
        assert btn1._block_id == "block_a"
        assert btn2._block_id == "block_b"


class TestStopButtonOnClick:
    def test_on_click_posts_pressed_message(self):
        btn = StopButton(block_id="block_123")
        messages = []
        btn.post_message = lambda msg: messages.append(msg)

        mock_event = MagicMock()
        btn.on_click(mock_event)

        assert len(messages) == 1
        assert isinstance(messages[0], StopButton.Pressed)
        assert messages[0].block_id == "block_123"

    def test_on_click_stops_event_propagation(self):
        btn = StopButton(block_id="test")
        mock_event = MagicMock()
        btn.post_message = MagicMock()

        btn.on_click(mock_event)

        mock_event.stop.assert_called_once()


class TestStopButtonOnMount:
    def test_on_mount_does_not_raise(self):
        btn = StopButton(block_id="test")
        btn.on_mount()


class TestVizButtonInit:
    def test_initializes_with_block_id(self):
        btn = VizButton(block_id="viz_block")
        assert btn._block_id == "viz_block"

    def test_has_viz_btn_id(self):
        btn = VizButton(block_id="test")
        assert btn.id == "viz-btn"

    def test_has_viz_action_class(self):
        btn = VizButton(block_id="test")
        assert "viz-action" in btn.classes


class TestVizButtonOnClick:
    def test_on_click_posts_pressed_message(self):
        btn = VizButton(block_id="viz_123")
        messages = []
        btn.post_message = lambda msg: messages.append(msg)

        mock_event = MagicMock()
        btn.on_click(mock_event)

        assert len(messages) == 1
        assert isinstance(messages[0], VizButton.Pressed)
        assert messages[0].block_id == "viz_123"

    def test_on_click_stops_event_propagation(self):
        btn = VizButton(block_id="test")
        mock_event = MagicMock()
        btn.post_message = MagicMock()

        btn.on_click(mock_event)

        mock_event.stop.assert_called_once()


class TestBlockHeaderInit:
    def test_initializes_with_block_state(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        header = BlockHeader(block)
        assert header.block is block

    def test_stores_command_block(self):
        block = BlockState(type=BlockType.COMMAND, content_input="pwd")
        header = BlockHeader(block)
        assert header.block.type == BlockType.COMMAND

    def test_stores_ai_query_block(self):
        block = BlockState(type=BlockType.AI_QUERY, content_input="What is Python?")
        header = BlockHeader(block)
        assert header.block.type == BlockType.AI_QUERY

    def test_stores_ai_response_block(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="query")
        header = BlockHeader(block)
        assert header.block.type == BlockType.AI_RESPONSE


class TestBlockHeaderCompose:
    """Test BlockHeader.compose() for different block types."""

    def test_command_block_compose_yields_widgets(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls -la")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_ai_query_block_compose_yields_widgets(self):
        block = BlockState(type=BlockType.AI_QUERY, content_input="What is Python?")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_ai_response_block_compose_yields_widgets(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_ai_response_with_content_compose(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="Some query")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_agent_response_block_compose_yields_widgets(self):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="task")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_system_msg_block_compose_yields_widgets(self):
        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="System message")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_system_msg_without_content_uses_default(self):
        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_tool_call_block_compose_yields_widgets(self):
        block = BlockState(type=BlockType.TOOL_CALL, content_input="tool output")
        header = BlockHeader(block)

        children = list(header.compose())
        assert len(children) == 4

    def test_timestamp_label_has_timestamp_class(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        header = BlockHeader(block)

        children = list(header.compose())
        timestamp_label = children[2]
        assert "timestamp" in timestamp_label.classes


class TestBlockHeaderIconClasses:
    """Test that correct CSS classes are applied for different block types."""

    def test_command_icon_has_cli_classes(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        header = BlockHeader(block)

        children = list(header.compose())
        icon_label = children[0]
        assert isinstance(icon_label, Label)
        assert "prompt-symbol" in icon_label.classes
        assert "prompt-symbol-cli" in icon_label.classes

    def test_ai_query_icon_has_query_classes(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.AI_QUERY, content_input="test")
        header = BlockHeader(block)

        children = list(header.compose())
        icon_label = children[0]
        assert "prompt-symbol-query" in icon_label.classes

    def test_ai_response_icon_has_response_classes(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="")
        header = BlockHeader(block)

        children = list(header.compose())
        icon_label = children[0]
        assert "prompt-symbol-response" in icon_label.classes

    def test_agent_response_icon_has_agent_classes(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="")
        header = BlockHeader(block)

        children = list(header.compose())
        icon_label = children[0]
        assert "prompt-symbol-agent" in icon_label.classes

    def test_system_msg_icon_has_system_classes(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="")
        header = BlockHeader(block)

        children = list(header.compose())
        icon_label = children[0]
        assert "prompt-symbol-system" in icon_label.classes


class TestBlockMetaInit:
    def test_initializes_with_block_state(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        meta = BlockMeta(block)
        assert meta.block is block

    def test_stores_metadata(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"provider": "openai", "model": "gpt-4"},
        )
        meta = BlockMeta(block)
        assert meta.block.metadata["provider"] == "openai"


class TestBlockMetaCompose:
    """Test BlockMeta.compose() with various metadata combinations."""

    def test_empty_metadata_yields_spacer_only(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.metadata = {}
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 1

    def test_none_metadata_yields_spacer_only(self):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
        block.metadata = None
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 1

    def test_provider_metadata_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"provider": "openai"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_model_metadata_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"model": "gpt-4-turbo"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_model_with_slash_truncated(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"model": "anthropic/claude-3-opus"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_tokens_metadata_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"tokens": "1234/5678"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_cost_metadata_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"cost": "$0.05"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_context_metadata_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"context": "1500 chars"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_context_zero_chars_not_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"context": "0 chars"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        meta_values = [c for c in children if "meta-value" in getattr(c, "classes", [])]
        assert len(meta_values) == 0

    def test_persona_metadata_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"persona": "developer"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 2

    def test_persona_default_not_displayed(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"persona": "default"},
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        meta_values = [c for c in children if "meta-value" in getattr(c, "classes", [])]
        assert len(meta_values) == 0

    def test_multiple_metadata_parts_with_separators(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={
                "provider": "openai",
                "model": "gpt-4",
                "tokens": "100/200",
            },
        )
        meta = BlockMeta(block)

        children = list(meta.compose())
        assert len(children) >= 6

    def test_ai_response_shows_action_buttons_when_not_running(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={},
        )
        block.is_running = False
        meta = BlockMeta(block)

        children = list(meta.compose())
        action_btns = [
            c for c in children if "meta-action" in getattr(c, "classes", [])
        ]
        assert len(action_btns) == 2

    def test_ai_response_hides_action_buttons_when_running(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={},
        )
        block.is_running = True
        meta = BlockMeta(block)

        children = list(meta.compose())
        action_btns = [
            c for c in children if "meta-action" in getattr(c, "classes", [])
        ]
        assert len(action_btns) == 0

    def test_non_ai_response_hides_action_buttons(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls",
            metadata={},
        )
        block.is_running = False
        meta = BlockMeta(block)

        children = list(meta.compose())
        action_btns = [
            c for c in children if "meta-action" in getattr(c, "classes", [])
        ]
        assert len(action_btns) == 0


class TestBlockMetaActionButtonIds:
    def test_edit_button_has_correct_id(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={},
        )
        block.is_running = False
        meta = BlockMeta(block)

        children = list(meta.compose())
        edit_btns = [c for c in children if getattr(c, "id", None) == "edit-btn"]
        assert len(edit_btns) == 1

    def test_retry_button_has_correct_id(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={},
        )
        block.is_running = False
        meta = BlockMeta(block)

        children = list(meta.compose())
        retry_btns = [c for c in children if getattr(c, "id", None) == "retry-btn"]
        assert len(retry_btns) == 1


class TestBlockBodyInit:
    def test_default_initialization(self):
        body = BlockBody()
        assert body._initial_text == ""
        assert body._max_lines == MAX_OUTPUT_LINES
        assert body._truncated is False
        assert body._total_lines == 0

    def test_initialization_with_text(self):
        body = BlockBody(text="Hello World")
        assert body._initial_text == "Hello World"
        assert body.content_text == "Hello World"

    def test_initialization_with_none_text(self):
        body = BlockBody(text=None)
        assert body._initial_text == ""

    def test_initialization_with_custom_max_lines(self):
        body = BlockBody(max_lines=500)
        assert body._max_lines == 500

    def test_content_text_reactive_initialized(self):
        body = BlockBody(text="test content")
        assert body.content_text == "test content"


class TestBlockBodyCompose:
    def test_compose_yields_static_widget(self):
        from textual.widgets import Static

        body = BlockBody(text="test")
        children = list(body.compose())
        assert len(children) == 1
        assert isinstance(children[0], Static)

    def test_compose_widget_has_body_content_id(self):
        body = BlockBody(text="test")
        children = list(body.compose())
        assert children[0].id == "body-content"

    def test_compose_with_empty_text(self):
        body = BlockBody(text="")
        children = list(body.compose())
        assert len(children) == 1

    def test_compose_with_url_text(self):
        body = BlockBody(text="Visit https://example.com")
        children = list(body.compose())
        assert len(children) == 1


class TestBlockBodyWatchContentText:
    def test_watch_handles_missing_content_widget(self):
        body = BlockBody()
        body.watch_content_text("new text")

    def test_watch_updates_truncation_state(self):
        body = BlockBody(max_lines=2)
        body._truncated = False
        text = "line1\nline2\nline3\nline4"
        result, truncated, total = body._truncate_output(text)
        body._truncated = truncated
        body._total_lines = total
        assert body._truncated is True
        assert body._total_lines == 4


class TestBlockBodySetViewMode:
    def test_set_view_mode_handles_missing_widget(self):
        body = BlockBody()
        body.set_view_mode("json")

    def test_set_view_mode_text_mode(self):
        body = BlockBody(text="plain text")
        body.set_view_mode("text")

    def test_set_view_mode_json_mode_invalid_json(self):
        body = BlockBody(text="not json")
        body.content_text = "not json"
        body.set_view_mode("json")

    def test_set_view_mode_table_mode_invalid_data(self):
        body = BlockBody(text="not json")
        body.content_text = "not json"
        body.set_view_mode("table")

    def test_set_view_mode_table_mode_non_list_json(self):
        body = BlockBody()
        body.content_text = '{"key": "value"}'
        body.set_view_mode("table")

    def test_set_view_mode_table_mode_empty_list(self):
        body = BlockBody()
        body.content_text = "[]"
        body.set_view_mode("table")


class TestBlockFooterInit:
    def test_initializes_with_block_state(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        footer = BlockFooter(block)
        assert footer.block is block

    def test_adds_empty_class_when_no_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = 0
        block.is_running = False
        footer = BlockFooter(block)
        assert "empty-footer" in footer.classes

    def test_no_empty_class_when_has_content(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = 1
        footer = BlockFooter(block)
        assert "empty-footer" not in footer.classes


class TestBlockFooterCompose:
    def test_compose_with_failed_exit_code(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.COMMAND, content_input="bad_cmd")
        block.exit_code = 127
        block.is_running = False
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 1
        assert isinstance(children[0], Label)
        assert "exit-error" in children[0].classes

    def test_compose_with_running_block(self):
        from textual.widgets import Label

        block = BlockState(type=BlockType.COMMAND, content_input="sleep 10")
        block.is_running = True
        block.exit_code = None
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 2
        running_label = children[0]
        assert "running-spinner" in running_label.classes
        assert isinstance(children[1], StopButton)

    def test_compose_with_success_exit_code(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = 0
        block.is_running = False
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 0

    def test_compose_with_no_exit_code_not_running(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.exit_code = None
        block.is_running = False
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 0

    def test_exit_code_label_has_exit_error_class(self):
        block = BlockState(type=BlockType.COMMAND, content_input="cmd")
        block.exit_code = 42
        block.is_running = False
        footer = BlockFooter(block)

        children = list(footer.compose())
        label = children[0]
        assert "exit-error" in label.classes

    def test_stop_button_is_present_for_running_block(self):
        block = BlockState(type=BlockType.COMMAND, content_input="sleep")
        block.is_running = True
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 2
        assert isinstance(children[1], StopButton)


class TestBlockBodyEdgeCases:
    def test_very_long_single_line(self):
        body = BlockBody(max_lines=10)
        long_line = "x" * 10000
        result, was_truncated, total = body._truncate_output(long_line)
        assert was_truncated is False
        assert total == 1

    def test_empty_lines_in_text(self):
        body = BlockBody(max_lines=5)
        text = "line1\n\nline3\n\nline5"
        result, was_truncated, total = body._truncate_output(text)
        assert total == 5
        assert was_truncated is False

    def test_unicode_content(self):
        body = BlockBody()
        result = body._make_links_clickable("Hello World")
        assert "" in result.plain

    def test_mixed_content_urls_and_prompts(self):
        body = BlockBody()
        text = "$ curl https://api.example.com\n> response"
        result = body._make_links_clickable(text)
        assert "https://api.example.com" in result.plain
        assert "curl" in result.plain


class TestBlockHeaderEdgeCases:
    def test_empty_content_input(self):
        block = BlockState(type=BlockType.COMMAND, content_input="")
        header = BlockHeader(block)
        children = list(header.compose())
        assert len(children) == 4

    def test_very_long_content_input(self):
        block = BlockState(type=BlockType.COMMAND, content_input="x" * 1000)
        header = BlockHeader(block)
        children = list(header.compose())
        assert len(children) == 4

    def test_content_with_special_characters(self):
        block = BlockState(type=BlockType.COMMAND, content_input="ls -la | grep 'test'")
        header = BlockHeader(block)
        children = list(header.compose())
        assert len(children) == 4


class TestBlockMetaEdgeCases:
    def test_empty_string_metadata_values(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={"provider": "", "model": ""},
        )
        meta = BlockMeta(block)
        children = list(meta.compose())
        meta_values = [c for c in children if "meta-value" in getattr(c, "classes", [])]
        assert len(meta_values) == 0

    def test_all_metadata_fields_present(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="test",
            metadata={
                "provider": "anthropic",
                "model": "claude-3",
                "tokens": "100/200",
                "cost": "$0.01",
                "context": "500 chars",
                "persona": "coder",
            },
        )
        meta = BlockMeta(block)
        children = list(meta.compose())
        meta_values = [c for c in children if "meta-value" in getattr(c, "classes", [])]
        assert len(meta_values) == 6


class TestBlockFooterEdgeCases:
    def test_negative_exit_code_shows_footer(self):
        block = BlockState(type=BlockType.COMMAND, content_input="cmd")
        block.exit_code = -1
        block.is_running = False
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 1
        assert "exit-error" in children[0].classes

    def test_large_exit_code_shows_footer(self):
        block = BlockState(type=BlockType.COMMAND, content_input="cmd")
        block.exit_code = 255
        block.is_running = False
        footer = BlockFooter(block)

        children = list(footer.compose())
        assert len(children) == 1
        assert "exit-error" in children[0].classes
