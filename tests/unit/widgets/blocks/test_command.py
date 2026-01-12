"""Tests for widgets/blocks/command.py - CommandBlock widget."""

import json
from unittest.mock import MagicMock, patch

from models import BlockState, BlockType
from widgets.blocks.command import CommandBlock
from widgets.blocks.parts import VizButton


class TestCommandBlockInit:
    """Tests for CommandBlock initialization."""

    def test_init_with_block_state(self):
        """CommandBlock initializes with BlockState correctly."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls -la")
        widget = CommandBlock(block)

        assert widget.block is block
        assert widget._mode == "line"
        assert widget._terminal_widget is None

    def test_init_creates_header(self):
        """CommandBlock creates a BlockHeader on init."""
        block = BlockState(type=BlockType.COMMAND, content_input="echo test")
        widget = CommandBlock(block)

        assert widget.header is not None
        assert widget.header.block is block

    def test_init_creates_body_widget(self):
        """CommandBlock creates a BlockBody on init."""
        block = BlockState(
            type=BlockType.COMMAND, content_input="ls", content_output="file1\nfile2"
        )
        widget = CommandBlock(block)

        assert widget.body_widget is not None

    def test_init_creates_footer_widget(self):
        """CommandBlock creates a BlockFooter on init."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        assert widget.footer_widget is not None
        assert widget.footer_widget.block is block

    def test_init_with_empty_content_output(self):
        """CommandBlock handles empty content_output on init."""
        block = BlockState(
            type=BlockType.COMMAND, content_input="ls", content_output=""
        )
        widget = CommandBlock(block)

        assert widget.body_widget is not None

    def test_init_with_none_content_output(self):
        """CommandBlock handles None content_output on init."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        block.content_output = None
        widget = CommandBlock(block)

        assert widget.body_widget is not None


class TestCommandBlockMode:
    """Tests for CommandBlock mode property."""

    def test_mode_default_is_line(self):
        """Default mode is 'line'."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        assert widget.mode == "line"

    def test_mode_returns_current_mode(self):
        """mode property returns the current internal mode."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        widget._mode = "tui"
        assert widget.mode == "tui"

        widget._mode = "viz"
        assert widget.mode == "viz"


class TestCommandBlockUpdateOutput:
    """Tests for CommandBlock.update_output method."""

    def test_update_output_in_line_mode(self):
        """update_output updates body_widget content in line mode."""
        block = BlockState(
            type=BlockType.COMMAND, content_input="ls", content_output="initial"
        )
        widget = CommandBlock(block)

        block.content_output = "updated output"
        widget.update_output()

        assert widget.body_widget.content_text == "updated output"

    def test_update_output_ignores_tui_mode(self):
        """update_output does nothing in TUI mode."""
        block = BlockState(
            type=BlockType.COMMAND, content_input="vim", content_output=""
        )
        widget = CommandBlock(block)
        widget._mode = "tui"
        widget.body_widget.content_text = "original"

        block.content_output = "new content"
        widget.update_output()

        # In TUI mode, body_widget content shouldn't change through update_output
        assert widget.body_widget.content_text == "original"

    def test_update_output_with_empty_content(self):
        """update_output handles empty content."""
        block = BlockState(
            type=BlockType.COMMAND, content_input="ls", content_output=""
        )
        widget = CommandBlock(block)
        widget.update_output()

        assert widget.body_widget.content_text == ""


class TestCommandBlockCheckForViz:
    """Tests for CommandBlock._check_for_viz method."""

    def test_check_for_viz_with_short_content(self):
        """_check_for_viz skips content shorter than 10 chars."""
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = CommandBlock(block)

        # Should not raise any error
        widget._check_for_viz("short")

    def test_check_for_viz_with_none_content(self):
        """_check_for_viz handles None content."""
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = CommandBlock(block)

        widget._check_for_viz(None)

    def test_check_for_viz_with_empty_content(self):
        """_check_for_viz handles empty content."""
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = CommandBlock(block)

        widget._check_for_viz("")

    def test_check_for_viz_detects_json_object(self):
        """_check_for_viz detects valid JSON object."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz('{"key": "value", "count": 42}')
            mock_show.assert_called_once()

    def test_check_for_viz_detects_json_array(self):
        """_check_for_viz detects valid JSON array."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz('[1, 2, 3, "test", null]')
            mock_show.assert_called_once()

    def test_check_for_viz_ignores_invalid_json(self):
        """_check_for_viz ignores invalid JSON starting with { or [."""
        block = BlockState(type=BlockType.COMMAND, content_input="echo test")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz("{not valid json at all}")
            mock_show.assert_not_called()

    def test_check_for_viz_ignores_plain_text(self):
        """_check_for_viz ignores plain text output."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz("file1\nfile2\nfile3")
            mock_show.assert_not_called()

    def test_check_for_viz_handles_whitespace_padding(self):
        """_check_for_viz handles JSON with whitespace padding."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz('  \n  {"key": "value"}  \n  ')
            mock_show.assert_called_once()


class TestCommandBlockVizButtonEvent:
    """Tests for CommandBlock.on_viz_button_pressed event handler."""

    def test_viz_button_ignores_other_block_ids(self):
        """on_viz_button_pressed ignores events from other blocks."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        block.id = "block-1"
        widget = CommandBlock(block)
        widget._mode = "line"

        event = VizButton.Pressed("block-2")
        widget.on_viz_button_pressed(event)

        # Mode should remain unchanged
        assert widget._mode == "line"

    def test_viz_button_toggles_to_viz_mode(self):
        """on_viz_button_pressed toggles from line to viz mode."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        block.id = "block-1"
        widget = CommandBlock(block)
        widget._mode = "line"

        with patch.object(widget.body_widget, "set_view_mode") as mock_set_view:
            event = VizButton.Pressed("block-1")
            widget.on_viz_button_pressed(event)

            assert widget._mode == "viz"
            mock_set_view.assert_called_once_with("json")

    def test_viz_button_toggles_back_to_line_mode(self):
        """on_viz_button_pressed toggles from viz back to line mode."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        block.id = "block-1"
        widget = CommandBlock(block)
        widget._mode = "viz"

        with patch.object(widget.body_widget, "set_view_mode") as mock_set_view:
            event = VizButton.Pressed("block-1")
            widget.on_viz_button_pressed(event)

            assert widget._mode == "line"
            mock_set_view.assert_called_once_with("text")


class TestCommandBlockSwitchToTui:
    """Tests for CommandBlock.switch_to_tui method."""

    def test_switch_to_tui_changes_mode(self):
        """switch_to_tui sets mode to 'tui'."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        # Mock mount to avoid actual widget mounting
        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            widget.switch_to_tui()

        assert widget._mode == "tui"

    def test_switch_to_tui_returns_terminal_widget(self):
        """switch_to_tui returns a TerminalBlock instance."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            result = widget.switch_to_tui()

        assert result is not None
        assert widget._terminal_widget is result

    def test_switch_to_tui_hides_body_widget(self):
        """switch_to_tui hides the body_widget."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)
        widget.body_widget.display = True

        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            widget.switch_to_tui()

        assert widget.body_widget.display is False

    def test_switch_to_tui_adds_mode_class(self):
        """switch_to_tui adds 'mode-tui' CSS class."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        with (
            patch.object(widget, "mount"),
            patch.object(widget, "add_class") as mock_add,
        ):
            widget.switch_to_tui()

        mock_add.assert_called_once_with("mode-tui")

    def test_switch_to_tui_returns_existing_terminal(self):
        """switch_to_tui returns existing terminal if already in TUI mode."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            first_terminal = widget.switch_to_tui()
            second_terminal = widget.switch_to_tui()

        assert first_terminal is second_terminal

    def test_switch_to_tui_creates_terminal_with_correct_params(self):
        """switch_to_tui creates TerminalBlock with correct block_id."""
        block = BlockState(type=BlockType.COMMAND, content_input="htop")
        block.id = "test-block-123"
        widget = CommandBlock(block)

        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            terminal = widget.switch_to_tui()

        assert terminal.block_id == "test-block-123"


class TestCommandBlockSwitchToLine:
    """Tests for CommandBlock.switch_to_line method."""

    def test_switch_to_line_changes_mode(self):
        """switch_to_line sets mode to 'line'."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)
        widget._mode = "tui"

        with patch.object(widget, "remove_class"):
            widget.switch_to_line()

        assert widget._mode == "line"

    def test_switch_to_line_shows_body_widget(self):
        """switch_to_line shows the body_widget."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)
        widget._mode = "tui"
        widget.body_widget.display = False

        with patch.object(widget, "remove_class"):
            widget.switch_to_line()

        assert widget.body_widget.display is True

    def test_switch_to_line_removes_terminal_widget(self):
        """switch_to_line removes the terminal widget."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        # Set up TUI mode with a mock terminal
        widget._mode = "tui"
        mock_terminal = MagicMock()
        widget._terminal_widget = mock_terminal

        with patch.object(widget, "remove_class"):
            widget.switch_to_line()

        mock_terminal.remove.assert_called_once()
        assert widget._terminal_widget is None

    def test_switch_to_line_removes_mode_class(self):
        """switch_to_line removes 'mode-tui' CSS class."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)
        widget._mode = "tui"

        with patch.object(widget, "remove_class") as mock_remove:
            widget.switch_to_line()

        mock_remove.assert_called_once_with("mode-tui")

    def test_switch_to_line_noop_if_already_line_mode(self):
        """switch_to_line does nothing if already in line mode."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)
        widget._mode = "line"

        # Should not try to remove class or modify terminal
        with patch.object(widget, "remove_class") as mock_remove:
            widget.switch_to_line()

        mock_remove.assert_not_called()


class TestCommandBlockFeedTerminal:
    """Tests for CommandBlock.feed_terminal method."""

    def test_feed_terminal_with_no_terminal(self):
        """feed_terminal does nothing when no terminal widget exists."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        # Should not raise any error
        widget.feed_terminal(b"test data")

    def test_feed_terminal_passes_data_to_terminal(self):
        """feed_terminal passes data to terminal widget."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        mock_terminal = MagicMock()
        widget._terminal_widget = mock_terminal

        widget.feed_terminal(b"Hello, world!")

        mock_terminal.feed.assert_called_once_with(b"Hello, world!")

    def test_feed_terminal_handles_empty_data(self):
        """feed_terminal handles empty data."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        mock_terminal = MagicMock()
        widget._terminal_widget = mock_terminal

        widget.feed_terminal(b"")

        mock_terminal.feed.assert_called_once_with(b"")


class TestCommandBlockSetLoading:
    """Tests for CommandBlock.set_loading method."""

    def test_set_loading_true_updates_block_state(self):
        """set_loading(True) sets block.is_running to True."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)
        block.is_running = False

        with patch.object(
            widget.footer_widget, "remove", side_effect=Exception("not mounted")
        ):
            with patch.object(widget, "mount"):
                widget.set_loading(True)

        assert block.is_running is True

    def test_set_loading_false_updates_block_state(self):
        """set_loading(False) sets block.is_running to False."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)
        block.is_running = True

        with patch.object(
            widget.footer_widget, "remove", side_effect=Exception("not mounted")
        ):
            with patch.object(widget, "mount"):
                widget.set_loading(False)

        assert block.is_running is False

    def test_set_loading_recreates_footer_widget(self):
        """set_loading recreates the footer widget."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)
        original_footer = widget.footer_widget

        with patch.object(original_footer, "remove"):
            with patch.object(widget, "mount"):
                widget.set_loading(False)

        assert widget.footer_widget is not original_footer

    def test_set_loading_handles_remove_exception(self):
        """set_loading handles exception when removing footer."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        with patch.object(
            widget.footer_widget, "remove", side_effect=Exception("fail")
        ):
            with patch.object(widget, "mount"):
                # Should not raise
                widget.set_loading(True)


class TestCommandBlockInheritance:
    """Tests for CommandBlock inheritance from BaseBlockWidget."""

    def test_inherits_from_base_block_widget(self):
        """CommandBlock inherits from BaseBlockWidget."""
        from widgets.blocks.base import BaseBlockWidget

        assert issubclass(CommandBlock, BaseBlockWidget)

    def test_has_block_attribute(self):
        """CommandBlock has block attribute from BaseBlockWidget."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)

        assert hasattr(widget, "block")
        assert widget.block is block

    def test_inherits_set_exit_code(self):
        """CommandBlock inherits set_exit_code from BaseBlockWidget."""
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = CommandBlock(block)
        widget.block.is_running = True

        widget.set_exit_code(0)

        assert block.exit_code == 0
        assert block.is_running is False

    def test_inherits_set_exit_code_with_error(self):
        """CommandBlock handles error exit codes."""
        block = BlockState(type=BlockType.COMMAND, content_input="bad_cmd")
        widget = CommandBlock(block)
        widget.block.is_running = True

        with patch.object(
            widget.footer_widget, "remove", side_effect=Exception("not mounted")
        ):
            with patch.object(widget, "mount"):
                widget.set_exit_code(127)

        assert block.exit_code == 127


class TestCommandBlockJsonDetection:
    """Additional tests for JSON detection edge cases."""

    def test_nested_json_object(self):
        """_check_for_viz detects nested JSON objects."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat config.json")
        widget = CommandBlock(block)

        nested_json = json.dumps(
            {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "settings": {"timeout": 30},
                }
            }
        )

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz(nested_json)
            mock_show.assert_called_once()

    def test_json_array_of_objects(self):
        """_check_for_viz detects array of objects."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat users.json")
        widget = CommandBlock(block)

        json_array = json.dumps([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz(json_array)
            mock_show.assert_called_once()

    def test_json_with_unicode(self):
        """_check_for_viz handles JSON with unicode characters."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz('{"message": "Hello, \u4e16\u754c!"}')
            mock_show.assert_called_once()

    def test_truncated_json_not_detected(self):
        """_check_for_viz ignores truncated/incomplete JSON."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = CommandBlock(block)

        with patch.object(widget, "_show_viz_button") as mock_show:
            widget._check_for_viz('{"key": "value", "incomplete":')
            mock_show.assert_not_called()


class TestCommandBlockModeTransitions:
    """Tests for mode transition edge cases."""

    def test_line_to_tui_to_line_cycle(self):
        """CommandBlock can cycle through mode transitions."""
        block = BlockState(type=BlockType.COMMAND, content_input="vim")
        widget = CommandBlock(block)

        assert widget.mode == "line"

        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            widget.switch_to_tui()
            assert widget.mode == "tui"

        with patch.object(widget, "remove_class"):
            if widget._terminal_widget:
                widget._terminal_widget.remove = MagicMock()
            widget.switch_to_line()
            assert widget.mode == "line"

    def test_viz_mode_does_not_affect_tui_switch(self):
        """Switching to TUI from viz mode works correctly."""
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = CommandBlock(block)
        widget._mode = "viz"

        with patch.object(widget, "mount"), patch.object(widget, "add_class"):
            widget.switch_to_tui()

        assert widget.mode == "tui"
