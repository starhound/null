"""Terminal block widget for rendering TUI applications using pyte."""

import pyte
from rich.segment import Segment
from rich.style import Style as RichStyle
from textual.events import Key
from textual.geometry import Size
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

# Refresh debounce interval: 16ms = ~60 FPS
_REFRESH_DEBOUNCE_MS = 16 / 1000  # Convert to seconds for set_timer


class TerminalBlock(Widget):
    """Widget that renders a pyte terminal screen for TUI apps."""

    DEFAULT_CSS = """
    TerminalBlock {
        height: 24;
        max-height: 40;
        background: #1a1b26;
        color: #a9b1d6;
        border: solid $primary 40%;
        overflow: hidden;
    }
    TerminalBlock:focus {
        border: double $accent;
    }
    """

    can_focus = True

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
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.block_id = block_id
        self._rows = rows
        self._cols = cols
        self.pyte_screen = pyte.Screen(cols, rows)
        self.pyte_stream = pyte.Stream(self.pyte_screen)
        self._refresh_scheduled = False
        # Line render cache: maps line number -> (content_hash, Strip)
        self._line_cache: dict[int, tuple[int, Strip]] = {}

    def feed(self, data: bytes) -> None:
        """Feed raw terminal data to the pyte emulator."""
        try:
            decoded = data.decode("utf-8", errors="replace")
            self.pyte_stream.feed(decoded)
            self._schedule_refresh()
        except Exception:
            pass

    def _schedule_refresh(self) -> None:
        """Schedule a refresh with 16ms debouncing (~60 FPS)."""
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        self.set_timer(_REFRESH_DEBOUNCE_MS, self._do_refresh)

    def _do_refresh(self) -> None:
        """Perform the actual refresh and reset the scheduled flag."""
        self._refresh_scheduled = False
        self.refresh()

    def resize_terminal(self, cols: int, rows: int) -> None:
        """Resize the terminal emulator."""
        self._cols = cols
        self._rows = rows
        self.pyte_screen.resize(rows, cols)
        self._line_cache.clear()  # Invalidate cache on resize
        self.refresh()

    def on_resize(self, event) -> None:
        """Handle widget resize events and notify process of new dimensions."""
        new_cols = event.size.width
        new_rows = event.size.height

        if new_cols <= 0 or new_rows <= 0:
            return

        # Only resize if dimensions actually changed
        if new_cols == self._cols and new_rows == self._rows:
            return

        # Update internal dimensions
        self._cols = new_cols
        self._rows = new_rows

        # Resize the pyte screen
        self.pyte_screen.resize(new_rows, new_cols)

        # Clear the line cache since dimensions changed
        self._line_cache.clear()

        # Notify the process of the new PTY size via SIGWINCH
        if self.block_id:
            try:
                app = self.app
                if hasattr(app, "process_manager"):
                    app.process_manager.resize_pty(self.block_id, new_cols, new_rows)
            except Exception:
                pass

        self.refresh()

    def on_key(self, event: Key) -> None:
        """Forward key events to the process."""
        data = self._key_to_bytes(event)
        if data:
            self.post_message(self.InputRequested(data, self.block_id))
            event.stop()

    def on_mouse_down(self, event) -> None:
        """Handle mouse down events."""
        self.focus()
        self._send_mouse_event(event, 0)

    def on_mouse_up(self, event) -> None:
        """Handle mouse up events."""
        self._send_mouse_event(event, 3)

    # def on_mouse_move(self, event) -> None:
    #    """Handle mouse move events (drag)."""
    #    if event.button:
    #        self._send_mouse_event(event, 32) # specialized drag code if needed

    def _send_mouse_event(self, event, button_code: int) -> None:
        """Send mouse event as ANSI sequence."""
        # Allow native selection if Shift is held (standard terminal behavior)
        if event.shift:
            return

        # Check if mouse reporting is enabled in pyte screen
        # modes 1000, 1002, 1006 etc.
        # pyte.modes: 1000 (MOUSE_X10), 1002 (MOUSE_DRAG), 1003 (MOUSE_MOTION), 1006 (MOUSE_SGR)
        # We need to know if the application requested mouse events.

        # Check if any mouse mode is active
        mouse_modes = {1000, 1002, 1003, 1006}
        if not (self.pyte_screen.mode & mouse_modes):
            return

        x = event.x + 1
        y = event.y + 1

        # SGR mouse encoding: \e[<r;c;m
        # button_code: 0=left, 1=middle, 2=right, 3=release

        # Map button to code
        code = 0
        if event.button == 1:
            code = 0  # Left
        elif event.button == 2:
            code = 2  # Right
        elif event.button == 3:
            code = 1  # Middle

        if button_code == 3:  # Release
            action = "m"
        else:
            action = "M"

        # Modifiers
        if event.ctrl:
            code += 16
        if event.shift:
            code += 4
        if event.meta:
            code += 8

        # Protocol: CSI < button ; x ; y M (or m for release)
        seq = f"\x1b[<{code};{x};{y}{action}"

        self.post_message(self.InputRequested(seq.encode(), self.block_id))

    def _key_to_bytes(self, event: Key) -> bytes | None:
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
                return bytes([ord(char.lower()) - ord("a") + 1])

        # Regular character
        if event.character:
            return event.character.encode("utf-8")

        return None

    def _compute_line_hash(self, line_data: dict, width: int) -> int:
        """Compute a hash for a line's content to detect changes."""
        # Build a tuple of character data and attributes for hashing
        line_repr = []
        for x in range(min(width, self._cols)):
            char = line_data.get(x)
            if char:
                line_repr.append(
                    (char.data, char.fg, char.bg, char.bold, char.italics, char.reverse, char.underscore)
                )
            else:
                line_repr.append((" ", "default", "default", False, False, False, False))
        return hash((tuple(line_repr), width))

    def render_line(self, y: int) -> Strip:
        """Render a single line of the terminal with caching."""
        width = self.size.width
        if width <= 0:
            return Strip.blank(1)

        if y >= self.pyte_screen.lines:
            return Strip.blank(width)

        line_data = self.pyte_screen.buffer[y]

        # Check cache
        line_hash = self._compute_line_hash(line_data, width)
        cached = self._line_cache.get(y)
        if cached is not None:
            cached_hash, cached_strip = cached
            if cached_hash == line_hash:
                return cached_strip

        # Build the strip
        segments = []
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
                    underline=char.underscore,
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

        strip = Strip(segments, width)

        # Cache the result
        self._line_cache[y] = (line_hash, strip)

        return strip

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        """Return the height of the terminal content."""
        return self._rows

    def clear(self) -> None:
        """Clear the terminal screen."""
        self.pyte_screen.reset()
        self._line_cache.clear()  # Invalidate cache on reset
        self.refresh()
