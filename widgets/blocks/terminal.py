"""Terminal block widget for rendering TUI applications using pyte."""

from textual.widget import Widget
from textual.geometry import Size
from textual.strip import Strip
from textual.message import Message
from textual.events import Key
from rich.segment import Segment
from rich.style import Style as RichStyle

import pyte
from typing import Optional, Callable


class TerminalBlock(Widget):
    """Widget that renders a pyte terminal screen for TUI apps."""

    DEFAULT_CSS = """
    TerminalBlock {
        height: auto;
        min-height: 24;
        background: #1a1b26;
        color: #a9b1d6;
        border: solid $primary 40%;
        overflow: hidden;
    }
    """

    class InputRequested(Message):
        """Message to send input data to the process."""
        def __init__(self, data: bytes, block_id: str):
            super().__init__()
            self.data = data
            self.block_id = block_id

    def __init__(
        self,
        block_id: str,
        rows: int = 24,
        cols: int = 120,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.block_id = block_id
        self._rows = rows
        self._cols = cols
        self.pyte_screen = pyte.Screen(cols, rows)
        self.pyte_stream = pyte.Stream(self.pyte_screen)
        self._refresh_scheduled = False

    def feed(self, data: bytes) -> None:
        """Feed raw terminal data to the pyte emulator."""
        try:
            decoded = data.decode('utf-8', errors='replace')
            self.pyte_stream.feed(decoded)
            self._schedule_refresh()
        except Exception:
            pass

    def _schedule_refresh(self) -> None:
        """Schedule a refresh, avoiding too many rapid refreshes."""
        if not self._refresh_scheduled:
            self._refresh_scheduled = True
            self.call_after_refresh(self._do_refresh)

    def _do_refresh(self) -> None:
        """Perform the actual refresh."""
        self._refresh_scheduled = False
        self.refresh()

    def resize_terminal(self, cols: int, rows: int) -> None:
        """Resize the terminal emulator."""
        self._cols = cols
        self._rows = rows
        self.pyte_screen.resize(rows, cols)
        self.refresh()

    def on_resize(self, event) -> None:
        """Handle widget resize events."""
        if event.size.width > 0:
            self.resize_terminal(event.size.width, self._rows)

    def on_key(self, event: Key) -> None:
        """Forward key events to the process."""
        data = self._key_to_bytes(event)
        if data:
            self.post_message(self.InputRequested(data, self.block_id))
            event.stop()

    def _key_to_bytes(self, event: Key) -> Optional[bytes]:
        """Convert a key event to bytes for the terminal."""
        key = event.key

        # Special key mappings
        key_map = {
            "enter": b"\r",
            "backspace": b"\x7f",
            "tab": b"\t",
            "escape": b"\x1b",
            "up": b"\x1b[A",
            "down": b"\x1b[B",
            "right": b"\x1b[C",
            "left": b"\x1b[D",
            "home": b"\x1b[H",
            "end": b"\x1b[F",
            "page_up": b"\x1b[5~",
            "page_down": b"\x1b[6~",
            "insert": b"\x1b[2~",
            "delete": b"\x1b[3~",
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

        if key in key_map:
            return key_map[key]

        # Handle Ctrl+key combinations
        if key.startswith("ctrl+"):
            char = key[5:]
            if len(char) == 1 and char.isalpha():
                # Ctrl+A = 0x01, Ctrl+B = 0x02, etc.
                return bytes([ord(char.lower()) - ord('a') + 1])

        # Regular character
        if event.character:
            return event.character.encode('utf-8')

        return None

    def render_line(self, y: int) -> Strip:
        """Render a single line of the terminal."""
        width = self.size.width
        if width <= 0:
            return Strip.blank(1)

        if y >= self.pyte_screen.lines:
            return Strip.blank(width)

        segments = []
        line_data = self.pyte_screen.buffer[y]

        current_style = RichStyle.parse("default on default")
        text_accumulator = ""

        for x in range(min(width, self._cols)):
            char = line_data.get(x)
            if char:
                # Map pyte colors to Rich style
                fg = char.fg if char.fg != "default" else "default"
                bg = char.bg if char.bg != "default" else "default"

                style = RichStyle(
                    color=fg,
                    bgcolor=bg,
                    bold=char.bold,
                    italic=char.italics,
                    reverse=char.reverse,
                    underline=char.underscore
                )

                if style != current_style:
                    if text_accumulator:
                        segments.append(Segment(text_accumulator, current_style))
                        text_accumulator = ""
                    current_style = style

                text_accumulator += char.data
            else:
                # Empty space
                default_style = RichStyle.parse("default on default")
                if current_style != default_style:
                    if text_accumulator:
                        segments.append(Segment(text_accumulator, current_style))
                        text_accumulator = ""
                    current_style = default_style
                text_accumulator += " "

        if text_accumulator:
            segments.append(Segment(text_accumulator, current_style))

        # Pad to full width if needed
        total_len = sum(len(s.text) for s in segments)
        if total_len < width:
            segments.append(Segment(" " * (width - total_len)))

        return Strip(segments, width)

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        """Return the height of the terminal content."""
        return self._rows

    def clear(self) -> None:
        """Clear the terminal screen."""
        self.pyte_screen.reset()
        self.refresh()
