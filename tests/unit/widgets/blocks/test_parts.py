"""Tests for widgets/blocks/parts.py - Block UI components."""

import pytest
from rich.text import Text

from models import BlockState, BlockType
from widgets.blocks.parts import (
    ANSI_PATTERN,
    MAX_OUTPUT_LINES,
    URL_PATTERN,
    BlockBody,
    BlockFooter,
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
