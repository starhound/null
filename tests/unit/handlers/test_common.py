"""Tests for handlers/common.py - UIBuffer class."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_app():
    """Create a mock NullApp with a mock timer."""
    app = MagicMock()
    mock_timer = MagicMock()
    app.set_interval.return_value = mock_timer
    return app


@pytest.fixture
def callback():
    """Create a mock callback function."""
    return MagicMock()


@pytest.fixture
def ui_buffer(mock_app, callback):
    """Create a UIBuffer instance for testing."""
    from handlers.common import UIBuffer

    return UIBuffer(mock_app, callback)


class TestUIBufferInitialization:
    """Tests for UIBuffer initialization."""

    def test_initializes_with_app_and_callback(self, mock_app, callback):
        """UIBuffer stores app and callback references."""
        from handlers.common import UIBuffer

        buffer = UIBuffer(mock_app, callback)

        assert buffer.app is mock_app
        assert buffer.callback is callback

    def test_initializes_empty_buffer(self, ui_buffer):
        """UIBuffer starts with an empty buffer list."""
        assert ui_buffer.buffer == []

    def test_initializes_timer_with_default_interval(self, mock_app, callback):
        """UIBuffer sets up a timer with default 16ms interval."""
        from handlers.common import UIBuffer

        UIBuffer(mock_app, callback)

        mock_app.set_interval.assert_called_once()
        call_args = mock_app.set_interval.call_args
        assert call_args[0][0] == 0.016  # Default interval

    def test_initializes_timer_with_custom_interval(self, mock_app, callback):
        """UIBuffer accepts a custom timer interval."""
        from handlers.common import UIBuffer

        UIBuffer(mock_app, callback, interval=0.05)

        call_args = mock_app.set_interval.call_args
        assert call_args[0][0] == 0.05

    def test_first_write_flag_is_true(self, ui_buffer):
        """UIBuffer starts with _first_write flag set to True."""
        assert ui_buffer._first_write is True


class TestUIBufferWrite:
    """Tests for UIBuffer.write() method."""

    def test_write_appends_to_buffer(self, ui_buffer, callback):
        """write() appends data to the internal buffer."""
        # After first write, it flushes, so buffer will be empty
        ui_buffer.write("hello")
        # First write triggers flush, buffer cleared
        assert ui_buffer.buffer == []

        # Second write should append without immediate flush
        ui_buffer.write("world")
        assert ui_buffer.buffer == ["world"]

    def test_first_write_flushes_immediately(self, ui_buffer, callback):
        """First write triggers an immediate flush."""
        ui_buffer.write("first")

        callback.assert_called_once_with("first")
        assert ui_buffer._first_write is False

    def test_subsequent_writes_do_not_flush_immediately(self, ui_buffer, callback):
        """Writes after the first do not immediately flush (unless threshold hit)."""
        ui_buffer.write("first")  # This flushes
        callback.reset_mock()

        ui_buffer.write("second")

        callback.assert_not_called()
        assert ui_buffer.buffer == ["second"]

    def test_flush_on_count_threshold(self, ui_buffer, callback):
        """Flush is triggered when buffer exceeds 20 items."""
        ui_buffer.write("first")  # Flushes immediately (first write)
        callback.reset_mock()

        # Write 20 more items - should not trigger flush until 21st
        for i in range(20):
            ui_buffer.write(f"item{i}")

        # The 20th write should not trigger flush yet (buffer has 20 items)
        # Actually, condition is > 20, so 21 items trigger flush
        assert callback.call_count == 0
        assert len(ui_buffer.buffer) == 20

        # The 21st write triggers flush
        ui_buffer.write("trigger")

        callback.assert_called_once()
        assert ui_buffer.buffer == []

    def test_flush_on_size_threshold(self, ui_buffer, callback):
        """Flush is triggered when buffer content exceeds 1000 characters."""
        ui_buffer.write("first")  # Flushes immediately (first write)
        callback.reset_mock()

        # Write data that totals less than 1000 chars
        ui_buffer.write("x" * 500)
        assert callback.call_count == 0

        # Add more to exceed 1000 chars
        ui_buffer.write("y" * 600)  # Total now 1100 chars

        callback.assert_called_once()
        # Check the callback received the combined content
        assert "x" * 500 in callback.call_args[0][0]
        assert "y" * 600 in callback.call_args[0][0]


class TestUIBufferFlush:
    """Tests for UIBuffer.flush() method."""

    def test_flush_calls_callback_with_joined_content(self, ui_buffer, callback):
        """flush() joins buffer content and passes to callback."""
        ui_buffer.buffer = ["hello", " ", "world"]

        ui_buffer.flush()

        callback.assert_called_once_with("hello world")

    def test_flush_clears_buffer(self, ui_buffer, callback):
        """flush() clears the buffer after calling callback."""
        ui_buffer.buffer = ["content"]

        ui_buffer.flush()

        assert ui_buffer.buffer == []

    def test_flush_does_nothing_on_empty_buffer(self, ui_buffer, callback):
        """flush() does not call callback if buffer is empty."""
        ui_buffer.buffer = []

        ui_buffer.flush()

        callback.assert_not_called()

    def test_flush_handles_multiple_chunks(self, ui_buffer, callback):
        """flush() correctly joins multiple buffer entries."""
        ui_buffer.buffer = ["line1\n", "line2\n", "line3"]

        ui_buffer.flush()

        callback.assert_called_once_with("line1\nline2\nline3")


class TestUIBufferStop:
    """Tests for UIBuffer.stop() method."""

    def test_stop_stops_timer(self, ui_buffer, mock_app):
        """stop() stops the internal timer."""
        ui_buffer.stop()

        ui_buffer.timer.stop.assert_called_once()

    def test_stop_flushes_remaining_content(self, ui_buffer, callback):
        """stop() flushes any remaining buffered content."""
        # Skip first write behavior
        ui_buffer._first_write = False
        ui_buffer.buffer = ["remaining", " content"]

        ui_buffer.stop()

        callback.assert_called_once_with("remaining content")

    def test_stop_with_empty_buffer(self, ui_buffer, callback, mock_app):
        """stop() handles empty buffer gracefully."""
        ui_buffer.buffer = []

        ui_buffer.stop()

        ui_buffer.timer.stop.assert_called_once()
        callback.assert_not_called()


class TestUIBufferTimerIntegration:
    """Tests for timer-based flush behavior."""

    def test_timer_callback_is_flush(self, mock_app, callback):
        """Timer is configured to call flush() periodically."""
        from handlers.common import UIBuffer

        buffer = UIBuffer(mock_app, callback)

        # Verify set_interval was called with flush method
        call_args = mock_app.set_interval.call_args
        assert call_args[0][1] == buffer.flush

    def test_timer_stores_reference(self, ui_buffer, mock_app):
        """UIBuffer stores the timer reference for later stopping."""
        expected_timer = mock_app.set_interval.return_value
        assert ui_buffer.timer is expected_timer
