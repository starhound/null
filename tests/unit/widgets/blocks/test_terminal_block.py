"""Tests for widgets/blocks/terminal.py - TerminalBlock widget.

Tests the pyte-based terminal emulator widget with mocked PTY operations.
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from rich.style import Style as RichStyle
from textual.events import Key
from textual.geometry import Size
from textual.strip import Strip


# Mock pyte before importing TerminalBlock
@pytest.fixture(autouse=True)
def mock_pyte():
    """Mock pyte module to avoid real terminal emulation."""
    with patch("widgets.blocks.terminal.pyte") as mock_pyte_module:
        # Create mock screen
        mock_screen = MagicMock()
        mock_screen.lines = 24
        mock_screen.columns = 120
        mock_screen.buffer = {}
        mock_screen.mode = set()
        mock_screen.history = MagicMock()

        # Mock HistoryScreen class
        mock_pyte_module.HistoryScreen.return_value = mock_screen
        mock_pyte_module.Stream.return_value = MagicMock()

        yield mock_pyte_module


@pytest.fixture
def mock_settings():
    """Mock settings for terminal."""
    with patch("widgets.blocks.terminal.get_settings") as mock_get:
        settings = MagicMock()
        settings.terminal.scrollback_lines = 1000
        settings.terminal.bold_is_bright = True
        mock_get.return_value = settings
        yield settings


@pytest.fixture
def terminal_block(mock_settings):
    """Create a TerminalBlock instance for testing."""
    from widgets.blocks.terminal import TerminalBlock

    return TerminalBlock(block_id="test-block-123")


class TestTerminalBlockInit:
    """Tests for TerminalBlock initialization."""

    def test_init_with_block_id(self, mock_settings):
        """TerminalBlock initializes with block_id correctly."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="my-block")

        assert widget.block_id == "my-block"

    def test_init_with_default_dimensions(self, mock_settings):
        """TerminalBlock uses default 24x120 dimensions."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test")

        assert widget._rows == 24
        assert widget._cols == 120

    def test_init_with_custom_dimensions(self, mock_settings):
        """TerminalBlock accepts custom rows and cols."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test", rows=40, cols=80)

        assert widget._rows == 40
        assert widget._cols == 80

    def test_init_with_name(self, mock_settings):
        """TerminalBlock accepts name parameter."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test", name="my-terminal")

        assert widget.name == "my-terminal"

    def test_init_with_id(self, mock_settings):
        """TerminalBlock accepts id parameter."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test", id="terminal-widget")

        assert widget.id == "terminal-widget"

    def test_init_with_classes(self, mock_settings):
        """TerminalBlock accepts classes parameter."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test", classes="focused active")

        assert "focused" in widget.classes
        assert "active" in widget.classes

    def test_init_creates_pyte_screen(self, mock_settings):
        """TerminalBlock creates a pyte HistoryScreen."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test")

        assert widget.pyte_screen is not None

    def test_init_creates_pyte_stream(self, mock_settings):
        """TerminalBlock creates a pyte Stream."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test")

        assert widget.pyte_stream is not None

    def test_init_refresh_not_scheduled(self, mock_settings):
        """TerminalBlock starts with no refresh scheduled."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test")

        assert widget._refresh_scheduled is False

    def test_init_line_cache_empty(self, mock_settings):
        """TerminalBlock starts with empty line cache."""
        from widgets.blocks.terminal import TerminalBlock

        widget = TerminalBlock(block_id="test")

        assert widget._line_cache == {}

    def test_init_uses_settings_scrollback(self, mock_settings):
        """TerminalBlock uses scrollback_lines from settings."""
        from widgets.blocks.terminal import TerminalBlock

        with patch("widgets.blocks.terminal.pyte") as mock_pyte:
            mock_pyte.HistoryScreen.return_value = MagicMock()
            mock_pyte.Stream.return_value = MagicMock()

            TerminalBlock(block_id="test", cols=80, rows=24)

            # Verify HistoryScreen was called with correct history param
            mock_pyte.HistoryScreen.assert_called_once()
            call_args = mock_pyte.HistoryScreen.call_args
            assert call_args[1]["history"] == 1000  # from mock_settings

    def test_can_focus_is_true(self, mock_settings):
        """TerminalBlock can receive focus."""
        from widgets.blocks.terminal import TerminalBlock

        assert TerminalBlock.can_focus is True


class TestTerminalBlockFeed:
    """Tests for TerminalBlock.feed method."""

    def test_feed_decodes_utf8(self, terminal_block):
        """feed decodes bytes as UTF-8."""
        terminal_block.pyte_stream.feed = MagicMock()

        with patch.object(terminal_block, "_schedule_refresh"):
            terminal_block.feed(b"Hello, World!")

        terminal_block.pyte_stream.feed.assert_called_once_with("Hello, World!")

    def test_feed_handles_decode_errors(self, terminal_block):
        """feed handles invalid UTF-8 with replacement."""
        terminal_block.pyte_stream.feed = MagicMock()

        with patch.object(terminal_block, "_schedule_refresh"):
            # Invalid UTF-8 sequence
            terminal_block.feed(b"\xff\xfe")

        # Should not raise, uses errors='replace'
        terminal_block.pyte_stream.feed.assert_called_once()

    def test_feed_schedules_refresh(self, terminal_block):
        """feed schedules a refresh after feeding data."""
        with patch.object(terminal_block, "_schedule_refresh") as mock_schedule:
            terminal_block.feed(b"test")

        mock_schedule.assert_called_once()

    def test_feed_handles_exception_silently(self, terminal_block):
        """feed catches exceptions without re-raising."""
        terminal_block.pyte_stream.feed = MagicMock(side_effect=Exception("pyte error"))

        # Should not raise
        terminal_block.feed(b"test")

    def test_feed_with_empty_data(self, terminal_block):
        """feed handles empty bytes."""
        terminal_block.pyte_stream.feed = MagicMock()

        with patch.object(terminal_block, "_schedule_refresh"):
            terminal_block.feed(b"")

        terminal_block.pyte_stream.feed.assert_called_once_with("")

    def test_feed_with_ansi_escape_sequences(self, terminal_block):
        """feed passes ANSI escape sequences to pyte."""
        terminal_block.pyte_stream.feed = MagicMock()

        with patch.object(terminal_block, "_schedule_refresh"):
            terminal_block.feed(b"\x1b[31mRed Text\x1b[0m")

        terminal_block.pyte_stream.feed.assert_called_once_with(
            "\x1b[31mRed Text\x1b[0m"
        )

    def test_feed_with_unicode_characters(self, terminal_block):
        """feed handles Unicode characters correctly."""
        terminal_block.pyte_stream.feed = MagicMock()

        with patch.object(terminal_block, "_schedule_refresh"):
            terminal_block.feed("こんにちは".encode("utf-8"))

        terminal_block.pyte_stream.feed.assert_called_once_with("こんにちは")


class TestTerminalBlockScheduleRefresh:
    """Tests for TerminalBlock._schedule_refresh method."""

    def test_schedule_refresh_sets_flag(self, terminal_block):
        """_schedule_refresh sets the scheduled flag."""
        with patch.object(terminal_block, "set_timer"):
            terminal_block._schedule_refresh()

        assert terminal_block._refresh_scheduled is True

    def test_schedule_refresh_calls_set_timer(self, terminal_block):
        """_schedule_refresh calls set_timer with debounce interval."""
        with patch.object(terminal_block, "set_timer") as mock_timer:
            terminal_block._schedule_refresh()

        mock_timer.assert_called_once()
        # First arg is the delay (16ms / 1000 = 0.016s)
        assert mock_timer.call_args[0][0] == pytest.approx(0.016, abs=0.001)

    def test_schedule_refresh_debounces(self, terminal_block):
        """_schedule_refresh only schedules once when called multiple times."""
        with patch.object(terminal_block, "set_timer") as mock_timer:
            terminal_block._schedule_refresh()
            terminal_block._schedule_refresh()
            terminal_block._schedule_refresh()

        # Should only be called once due to debouncing
        mock_timer.assert_called_once()


class TestTerminalBlockDoRefresh:
    """Tests for TerminalBlock._do_refresh method."""

    def test_do_refresh_clears_flag(self, terminal_block):
        """_do_refresh clears the scheduled flag."""
        terminal_block._refresh_scheduled = True

        with patch.object(terminal_block, "refresh"):
            terminal_block._do_refresh()

        assert terminal_block._refresh_scheduled is False

    def test_do_refresh_calls_refresh(self, terminal_block):
        """_do_refresh calls the widget's refresh method."""
        with patch.object(terminal_block, "refresh") as mock_refresh:
            terminal_block._do_refresh()

        mock_refresh.assert_called_once()


class TestTerminalBlockResizeTerminal:
    """Tests for TerminalBlock.resize_terminal method."""

    def test_resize_updates_dimensions(self, terminal_block):
        """resize_terminal updates internal dimensions."""
        terminal_block.resize_terminal(cols=100, rows=30)

        assert terminal_block._cols == 100
        assert terminal_block._rows == 30

    def test_resize_calls_pyte_resize(self, terminal_block):
        """resize_terminal calls pyte screen resize."""
        terminal_block.resize_terminal(cols=100, rows=30)

        terminal_block.pyte_screen.resize.assert_called_once_with(30, 100)

    def test_resize_clears_line_cache(self, terminal_block):
        """resize_terminal clears the line cache."""
        terminal_block._line_cache = {0: ("hash", MagicMock())}

        terminal_block.resize_terminal(cols=100, rows=30)

        assert terminal_block._line_cache == {}

    def test_resize_calls_refresh(self, terminal_block):
        """resize_terminal calls refresh."""
        with patch.object(terminal_block, "refresh") as mock_refresh:
            terminal_block.resize_terminal(cols=100, rows=30)

        mock_refresh.assert_called_once()


class TestTerminalBlockOnResize:
    """Tests for TerminalBlock.on_resize event handler."""

    def test_on_resize_updates_dimensions(self, terminal_block):
        """on_resize updates internal dimensions from event."""
        event = MagicMock()
        event.size.width = 80
        event.size.height = 40

        with patch.object(terminal_block, "refresh"):
            terminal_block.on_resize(event)

        assert terminal_block._cols == 80
        assert terminal_block._rows == 40

    def test_on_resize_ignores_zero_width(self, terminal_block):
        """on_resize ignores events with zero width."""
        terminal_block._cols = 120
        terminal_block._rows = 24

        event = MagicMock()
        event.size.width = 0
        event.size.height = 40

        terminal_block.on_resize(event)

        assert terminal_block._cols == 120  # unchanged

    def test_on_resize_ignores_zero_height(self, terminal_block):
        """on_resize ignores events with zero height."""
        terminal_block._cols = 120
        terminal_block._rows = 24

        event = MagicMock()
        event.size.width = 80
        event.size.height = 0

        terminal_block.on_resize(event)

        assert terminal_block._rows == 24  # unchanged

    def test_on_resize_ignores_negative_dimensions(self, terminal_block):
        """on_resize ignores events with negative dimensions."""
        terminal_block._cols = 120
        terminal_block._rows = 24

        event = MagicMock()
        event.size.width = -10
        event.size.height = 40

        terminal_block.on_resize(event)

        assert terminal_block._cols == 120  # unchanged

    def test_on_resize_ignores_unchanged_dimensions(self, terminal_block):
        """on_resize does nothing if dimensions haven't changed."""
        terminal_block._cols = 120
        terminal_block._rows = 24

        event = MagicMock()
        event.size.width = 120
        event.size.height = 24

        with patch.object(terminal_block.pyte_screen, "resize") as mock_resize:
            terminal_block.on_resize(event)

        mock_resize.assert_not_called()

    def test_on_resize_notifies_process_manager(self, terminal_block):
        """on_resize notifies process_manager of new PTY size."""
        mock_app = MagicMock()
        mock_app.process_manager = MagicMock()

        event = MagicMock()
        event.size.width = 100
        event.size.height = 50

        with patch.object(
            type(terminal_block),
            "app",
            new_callable=PropertyMock,
            return_value=mock_app,
        ):
            with patch.object(terminal_block, "refresh"):
                terminal_block.on_resize(event)

        mock_app.process_manager.resize_pty.assert_called_once_with(
            "test-block-123", 100, 50
        )

    def test_on_resize_handles_missing_process_manager(self, terminal_block):
        """on_resize handles app without process_manager."""
        mock_app = MagicMock(spec=[])

        event = MagicMock()
        event.size.width = 100
        event.size.height = 50

        with patch.object(
            type(terminal_block),
            "app",
            new_callable=PropertyMock,
            return_value=mock_app,
        ):
            with patch.object(terminal_block, "refresh"):
                terminal_block.on_resize(event)

    def test_on_resize_clears_line_cache(self, terminal_block):
        """on_resize clears line cache on dimension change."""
        terminal_block._line_cache = {0: ("hash", MagicMock())}

        event = MagicMock()
        event.size.width = 100
        event.size.height = 50

        with patch.object(terminal_block, "refresh"):
            terminal_block.on_resize(event)

        assert terminal_block._line_cache == {}


class TestTerminalBlockInputRequestedMessage:
    """Tests for TerminalBlock.InputRequested message."""

    def test_input_requested_message_init(self, mock_settings):
        """InputRequested message initializes correctly."""
        from widgets.blocks.terminal import TerminalBlock

        msg = TerminalBlock.InputRequested(data=b"test", block_id="block-1")

        assert msg.data == b"test"
        assert msg.block_id == "block-1"

    def test_input_requested_with_empty_data(self, mock_settings):
        """InputRequested handles empty data."""
        from widgets.blocks.terminal import TerminalBlock

        msg = TerminalBlock.InputRequested(data=b"", block_id="block-1")

        assert msg.data == b""

    def test_input_requested_with_escape_sequence(self, mock_settings):
        """InputRequested handles ANSI escape sequences."""
        from widgets.blocks.terminal import TerminalBlock

        msg = TerminalBlock.InputRequested(data=b"\x1b[A", block_id="block-1")

        assert msg.data == b"\x1b[A"


class TestTerminalBlockOnKey:
    """Tests for TerminalBlock.on_key event handler."""

    def test_on_key_posts_input_message(self, terminal_block):
        """on_key posts InputRequested message for regular keys."""
        event = MagicMock(spec=Key)
        event.key = "a"
        event.character = "a"

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block.on_key(event)

        mock_post.assert_called_once()
        msg = mock_post.call_args[0][0]
        assert msg.data == b"a"
        assert msg.block_id == "test-block-123"

    def test_on_key_stops_event_propagation(self, terminal_block):
        """on_key stops event from propagating."""
        event = MagicMock(spec=Key)
        event.key = "enter"
        event.character = None

        with patch.object(terminal_block, "post_message"):
            terminal_block.on_key(event)

        event.stop.assert_called_once()

    def test_on_key_ignores_unmapped_keys(self, terminal_block):
        """on_key does not post message for unmapped keys."""
        event = MagicMock(spec=Key)
        event.key = "unknown_key"
        event.character = None

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block.on_key(event)

        mock_post.assert_not_called()


class TestTerminalBlockKeyToBytes:
    """Tests for TerminalBlock._key_to_bytes method."""

    def test_key_to_bytes_enter(self, terminal_block):
        """_key_to_bytes maps enter to carriage return."""
        event = MagicMock(spec=Key)
        event.key = "enter"
        event.character = None

        result = terminal_block._key_to_bytes(event)

        assert result == b"\r"

    def test_key_to_bytes_backspace(self, terminal_block):
        """_key_to_bytes maps backspace to DEL."""
        event = MagicMock(spec=Key)
        event.key = "backspace"
        event.character = None

        result = terminal_block._key_to_bytes(event)

        assert result == b"\x7f"

    def test_key_to_bytes_tab(self, terminal_block):
        """_key_to_bytes maps tab correctly."""
        event = MagicMock(spec=Key)
        event.key = "tab"
        event.character = None

        result = terminal_block._key_to_bytes(event)

        assert result == b"\t"

    def test_key_to_bytes_escape(self, terminal_block):
        """_key_to_bytes maps escape correctly."""
        event = MagicMock(spec=Key)
        event.key = "escape"
        event.character = None

        result = terminal_block._key_to_bytes(event)

        assert result == b"\x1b"

    def test_key_to_bytes_arrow_keys(self, terminal_block):
        """_key_to_bytes maps arrow keys to ANSI sequences."""
        test_cases = [
            ("up", b"\x1b[A"),
            ("down", b"\x1b[B"),
            ("right", b"\x1b[C"),
            ("left", b"\x1b[D"),
        ]

        for key, expected in test_cases:
            event = MagicMock(spec=Key)
            event.key = key
            event.character = None

            result = terminal_block._key_to_bytes(event)

            assert result == expected, f"Failed for key: {key}"

    def test_key_to_bytes_home_end(self, terminal_block):
        """_key_to_bytes maps home/end keys."""
        event = MagicMock(spec=Key)
        event.key = "home"
        event.character = None

        assert terminal_block._key_to_bytes(event) == b"\x1b[H"

        event.key = "end"
        assert terminal_block._key_to_bytes(event) == b"\x1b[F"

    def test_key_to_bytes_page_keys(self, terminal_block):
        """_key_to_bytes maps page up/down keys."""
        event = MagicMock(spec=Key)
        event.key = "page_up"
        event.character = None

        assert terminal_block._key_to_bytes(event) == b"\x1b[5~"

        event.key = "page_down"
        assert terminal_block._key_to_bytes(event) == b"\x1b[6~"

    def test_key_to_bytes_insert_delete(self, terminal_block):
        """_key_to_bytes maps insert/delete keys."""
        event = MagicMock(spec=Key)
        event.key = "insert"
        event.character = None

        assert terminal_block._key_to_bytes(event) == b"\x1b[2~"

        event.key = "delete"
        assert terminal_block._key_to_bytes(event) == b"\x1b[3~"

    def test_key_to_bytes_function_keys(self, terminal_block):
        """_key_to_bytes maps function keys F1-F12."""
        function_keys = {
            "f1": b"\x1bOP",
            "f2": b"\x1bOQ",
            "f3": b"\x1bOR",
            "f4": b"\x1bOS",
            "f5": b"\x1b[15~",
            "f6": b"\x1b[17~",
            "f7": b"\x1b[18~",
            "f8": b"\x1b[19~",
            "f9": b"\x1b[20~",
            "f10": b"\x1b[21~",
            "f11": b"\x1b[23~",
            "f12": b"\x1b[24~",
        }

        for key, expected in function_keys.items():
            event = MagicMock(spec=Key)
            event.key = key
            event.character = None

            result = terminal_block._key_to_bytes(event)

            assert result == expected, f"Failed for key: {key}"

    def test_key_to_bytes_ctrl_combinations(self, terminal_block):
        """_key_to_bytes maps Ctrl+letter combinations."""
        # Ctrl+A = 0x01, Ctrl+C = 0x03, Ctrl+Z = 0x1A
        test_cases = [
            ("ctrl+a", bytes([1])),
            ("ctrl+c", bytes([3])),
            ("ctrl+d", bytes([4])),
            ("ctrl+z", bytes([26])),
        ]

        for key, expected in test_cases:
            event = MagicMock(spec=Key)
            event.key = key
            event.character = None

            result = terminal_block._key_to_bytes(event)

            assert result == expected, f"Failed for key: {key}"

    def test_key_to_bytes_regular_character(self, terminal_block):
        """_key_to_bytes returns UTF-8 encoded character."""
        event = MagicMock(spec=Key)
        event.key = "a"
        event.character = "a"

        result = terminal_block._key_to_bytes(event)

        assert result == b"a"

    def test_key_to_bytes_unicode_character(self, terminal_block):
        """_key_to_bytes handles Unicode characters."""
        event = MagicMock(spec=Key)
        event.key = "あ"
        event.character = "あ"

        result = terminal_block._key_to_bytes(event)

        assert result == "あ".encode("utf-8")

    def test_key_to_bytes_unmapped_key_returns_none(self, terminal_block):
        """_key_to_bytes returns None for unmapped keys."""
        event = MagicMock(spec=Key)
        event.key = "unknown_special_key"
        event.character = None

        result = terminal_block._key_to_bytes(event)

        assert result is None


class TestTerminalBlockMouseEvents:
    """Tests for TerminalBlock mouse event handlers."""

    def test_on_mouse_down_focuses_widget(self, terminal_block):
        """on_mouse_down focuses the widget."""
        event = MagicMock()
        event.shift = False
        event.button = 1
        event.x = 10
        event.y = 5
        event.ctrl = False
        event.meta = False

        terminal_block.pyte_screen.mode = set()

        with patch.object(terminal_block, "focus") as mock_focus:
            with patch.object(terminal_block, "_send_mouse_event"):
                terminal_block.on_mouse_down(event)

        mock_focus.assert_called_once()

    def test_on_mouse_down_sends_mouse_event(self, terminal_block):
        """on_mouse_down sends mouse event with button code 0."""
        event = MagicMock()
        event.shift = False

        with patch.object(terminal_block, "focus"):
            with patch.object(terminal_block, "_send_mouse_event") as mock_send:
                terminal_block.on_mouse_down(event)

        mock_send.assert_called_once_with(event, 0)

    def test_on_mouse_up_sends_release_event(self, terminal_block):
        """on_mouse_up sends mouse event with button code 3 (release)."""
        event = MagicMock()
        event.shift = False

        with patch.object(terminal_block, "_send_mouse_event") as mock_send:
            terminal_block.on_mouse_up(event)

        mock_send.assert_called_once_with(event, 3)

    def test_send_mouse_event_respects_shift_for_selection(self, terminal_block):
        """_send_mouse_event allows native selection when Shift is held."""
        event = MagicMock()
        event.shift = True

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 0)

        mock_post.assert_not_called()

    def test_send_mouse_event_respects_mouse_mode(self, terminal_block):
        """_send_mouse_event only sends when mouse mode is active."""
        event = MagicMock()
        event.shift = False
        event.button = 1
        event.x = 10
        event.y = 5
        event.ctrl = False
        event.meta = False

        # No mouse mode active
        terminal_block.pyte_screen.mode = set()

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 0)

        mock_post.assert_not_called()

    def test_send_mouse_event_posts_when_mouse_mode_active(self, terminal_block):
        """_send_mouse_event posts message when mouse mode is enabled."""
        event = MagicMock()
        event.shift = False
        event.button = 1
        event.x = 10
        event.y = 5
        event.ctrl = False
        event.meta = False

        # Set mouse mode 1000 (MOUSE_X10)
        terminal_block.pyte_screen.mode = {1000}

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 0)

        mock_post.assert_called_once()

    def test_send_mouse_event_uses_sgr_encoding(self, terminal_block):
        """_send_mouse_event uses SGR mouse encoding."""
        event = MagicMock()
        event.shift = False
        event.button = 1  # Left button
        event.x = 10
        event.y = 5
        event.ctrl = False
        event.meta = False

        terminal_block.pyte_screen.mode = {1006}

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 0)

        msg = mock_post.call_args[0][0]
        # SGR format: \x1b[<button;x;y M
        assert msg.data == b"\x1b[<0;11;6M"  # 0-indexed coords become 1-indexed

    def test_send_mouse_event_release_uses_m_suffix(self, terminal_block):
        """_send_mouse_event uses 'm' suffix for button release."""
        event = MagicMock()
        event.shift = False
        event.button = 1
        event.x = 10
        event.y = 5
        event.ctrl = False
        event.meta = False

        terminal_block.pyte_screen.mode = {1006}

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 3)  # Release

        msg = mock_post.call_args[0][0]
        assert msg.data.endswith(b"m")

    def test_send_mouse_event_handles_right_button(self, terminal_block):
        """_send_mouse_event handles right mouse button."""
        event = MagicMock()
        event.shift = False
        event.button = 2  # Right button in Textual
        event.x = 10
        event.y = 5
        event.ctrl = False
        event.meta = False

        terminal_block.pyte_screen.mode = {1006}

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 0)

        msg = mock_post.call_args[0][0]
        # Right button is code 2 in protocol
        assert b"<2;" in msg.data

    def test_send_mouse_event_handles_modifiers(self, terminal_block):
        """_send_mouse_event includes modifier keys in button code."""
        event = MagicMock()
        event.shift = False
        event.button = 1
        event.x = 10
        event.y = 5
        event.ctrl = True
        event.meta = False

        terminal_block.pyte_screen.mode = {1006}

        with patch.object(terminal_block, "post_message") as mock_post:
            terminal_block._send_mouse_event(event, 0)

        msg = mock_post.call_args[0][0]
        # Ctrl adds 16 to button code: 0 + 16 = 16
        assert b"<16;" in msg.data


class TestTerminalBlockToBrightColor:
    """Tests for TerminalBlock._to_bright_color method."""

    def test_bright_color_converts_standard_colors(self, terminal_block):
        """_to_bright_color converts colors 0-7 to 8-15."""
        for i in range(8):
            result = terminal_block._to_bright_color(str(i))
            assert result == str(i + 8)

    def test_bright_color_preserves_already_bright(self, terminal_block):
        """_to_bright_color preserves colors 8-15."""
        for i in range(8, 16):
            result = terminal_block._to_bright_color(str(i))
            assert result == str(i)

    def test_bright_color_preserves_256_colors(self, terminal_block):
        """_to_bright_color preserves 256-color palette colors."""
        result = terminal_block._to_bright_color("200")
        assert result == "200"

    def test_bright_color_preserves_default(self, terminal_block):
        """_to_bright_color preserves 'default' color."""
        result = terminal_block._to_bright_color("default")
        assert result == "default"

    def test_bright_color_handles_non_numeric(self, terminal_block):
        """_to_bright_color handles non-numeric colors."""
        result = terminal_block._to_bright_color("red")
        assert result == "red"

        result = terminal_block._to_bright_color("#ff0000")
        assert result == "#ff0000"


class TestTerminalBlockComputeLineHash:
    """Tests for TerminalBlock._compute_line_hash method."""

    def test_compute_line_hash_empty_line(self, terminal_block):
        """_compute_line_hash handles empty line data."""
        line_data = {}

        hash1 = terminal_block._compute_line_hash(line_data, 80, True)
        hash2 = terminal_block._compute_line_hash(line_data, 80, True)

        assert hash1 == hash2

    def test_compute_line_hash_different_widths(self, terminal_block):
        """_compute_line_hash produces different hashes for different widths."""
        line_data = {}

        hash1 = terminal_block._compute_line_hash(line_data, 80, True)
        hash2 = terminal_block._compute_line_hash(line_data, 100, True)

        assert hash1 != hash2

    def test_compute_line_hash_different_bold_is_bright(self, terminal_block):
        """_compute_line_hash produces different hashes for bold_is_bright setting."""
        line_data = {}

        hash1 = terminal_block._compute_line_hash(line_data, 80, True)
        hash2 = terminal_block._compute_line_hash(line_data, 80, False)

        assert hash1 != hash2

    def test_compute_line_hash_with_character_data(self, terminal_block):
        """_compute_line_hash incorporates character attributes."""
        char1 = MagicMock()
        char1.data = "A"
        char1.fg = "default"
        char1.bg = "default"
        char1.bold = False
        char1.italics = False
        char1.reverse = False
        char1.underscore = False

        char2 = MagicMock()
        char2.data = "B"
        char2.fg = "default"
        char2.bg = "default"
        char2.bold = False
        char2.italics = False
        char2.reverse = False
        char2.underscore = False

        line_data1 = {0: char1}
        line_data2 = {0: char2}

        hash1 = terminal_block._compute_line_hash(line_data1, 80, True)
        hash2 = terminal_block._compute_line_hash(line_data2, 80, True)

        assert hash1 != hash2


class TestTerminalBlockRenderLine:
    """Tests for TerminalBlock.render_line method."""

    def test_render_line_returns_strip(self, terminal_block):
        """render_line returns a Strip object."""
        terminal_block.pyte_screen.buffer = {0: {}}
        terminal_block.pyte_screen.lines = 24

        with patch.object(
            type(terminal_block),
            "size",
            new_callable=PropertyMock,
            return_value=Size(80, 24),
        ):
            result = terminal_block.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_blank_for_zero_width(self, terminal_block):
        """render_line returns blank strip for zero width."""
        with patch.object(
            type(terminal_block),
            "size",
            new_callable=PropertyMock,
            return_value=Size(0, 24),
        ):
            result = terminal_block.render_line(0)

        assert isinstance(result, Strip)

    def test_render_line_blank_for_out_of_range(self, terminal_block):
        """render_line returns blank strip for y beyond screen lines."""
        terminal_block.pyte_screen.lines = 24

        with patch.object(
            type(terminal_block),
            "size",
            new_callable=PropertyMock,
            return_value=Size(80, 24),
        ):
            result = terminal_block.render_line(30)

        assert isinstance(result, Strip)

    def test_render_line_uses_cache(self, terminal_block):
        """render_line returns cached strip when hash matches."""
        terminal_block.pyte_screen.buffer = {0: {}}
        terminal_block.pyte_screen.lines = 24

        cached_strip = Strip([])

        with patch.object(
            type(terminal_block),
            "size",
            new_callable=PropertyMock,
            return_value=Size(80, 24),
        ):
            with patch.object(terminal_block, "_compute_line_hash", return_value=12345):
                terminal_block._line_cache[0] = (12345, cached_strip)

                result = terminal_block.render_line(0)

        assert result is cached_strip

    def test_render_line_updates_cache(self, terminal_block):
        """render_line updates cache with new strip."""
        terminal_block.pyte_screen.buffer = {0: {}}
        terminal_block.pyte_screen.lines = 24
        terminal_block._line_cache = {}

        with patch.object(
            type(terminal_block),
            "size",
            new_callable=PropertyMock,
            return_value=Size(80, 24),
        ):
            with patch("widgets.blocks.terminal.get_settings") as mock_settings:
                mock_settings.return_value.terminal.bold_is_bright = True
                terminal_block.render_line(0)

        assert 0 in terminal_block._line_cache


class TestTerminalBlockGetContentHeight:
    """Tests for TerminalBlock.get_content_height method."""

    def test_get_content_height_returns_rows(self, terminal_block):
        """get_content_height returns the configured rows."""
        terminal_block._rows = 30

        result = terminal_block.get_content_height(Size(80, 24), Size(80, 24), 80)

        assert result == 30

    def test_get_content_height_with_different_rows(self, terminal_block):
        """get_content_height reflects _rows value."""
        terminal_block._rows = 50

        result = terminal_block.get_content_height(Size(100, 50), Size(100, 50), 100)

        assert result == 50


class TestTerminalBlockClear:
    """Tests for TerminalBlock.clear method."""

    def test_clear_resets_pyte_screen(self, terminal_block):
        """clear calls pyte_screen.reset()."""
        terminal_block.clear()

        terminal_block.pyte_screen.reset.assert_called_once()

    def test_clear_clears_line_cache(self, terminal_block):
        """clear clears the line cache."""
        terminal_block._line_cache = {
            0: ("hash", MagicMock()),
            1: ("hash2", MagicMock()),
        }

        terminal_block.clear()

        assert terminal_block._line_cache == {}

    def test_clear_calls_refresh(self, terminal_block):
        """clear calls refresh."""
        with patch.object(terminal_block, "refresh") as mock_refresh:
            terminal_block.clear()

        mock_refresh.assert_called_once()


class TestTerminalBlockInheritance:
    """Tests for TerminalBlock inheritance."""

    def test_inherits_from_widget(self, mock_settings):
        """TerminalBlock inherits from Widget."""
        from textual.widget import Widget
        from widgets.blocks.terminal import TerminalBlock

        assert issubclass(TerminalBlock, Widget)

    def test_has_can_focus_true(self, mock_settings):
        """TerminalBlock has can_focus set to True."""
        from widgets.blocks.terminal import TerminalBlock

        assert TerminalBlock.can_focus is True


class TestTerminalBlockIntegration:
    """Integration-style tests for TerminalBlock behavior."""

    def test_feed_and_refresh_cycle(self, terminal_block):
        """Test the feed -> schedule_refresh -> do_refresh cycle."""
        terminal_block._refresh_scheduled = False

        with patch.object(terminal_block, "set_timer") as mock_timer:
            with patch.object(terminal_block, "refresh"):
                terminal_block.feed(b"Hello")

                # Should have scheduled a refresh
                assert terminal_block._refresh_scheduled is True
                mock_timer.assert_called_once()

                # Simulate timer firing
                terminal_block._do_refresh()

                # Flag should be cleared
                assert terminal_block._refresh_scheduled is False

    def test_resize_preserves_block_id(self, terminal_block):
        """Resize operations preserve block_id."""
        original_id = terminal_block.block_id

        with patch.object(terminal_block, "refresh"):
            terminal_block.resize_terminal(100, 40)

        assert terminal_block.block_id == original_id

    def test_multiple_feeds_debounce_refresh(self, terminal_block):
        """Multiple rapid feeds should debounce to single refresh."""
        with patch.object(terminal_block, "set_timer") as mock_timer:
            terminal_block.feed(b"line 1\n")
            terminal_block.feed(b"line 2\n")
            terminal_block.feed(b"line 3\n")

        # Should only schedule one refresh due to debouncing
        mock_timer.assert_called_once()
