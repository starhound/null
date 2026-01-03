import asyncio

import pyte
from rich.segment import Segment
from rich.style import Style as RichStyle
from textual.geometry import Size
from textual.strip import Strip
from textual.widget import Widget

from utils.ssh_client import SSHSession


class SSHTerminal(Widget):
    """A terminal emulator widget for SSH sessions."""

    DEFAULT_CSS = """
    SSHTerminal {
        height: 1fr;
        background: black;
        color: white;
        overflow: hidden;
    }
    """

    def __init__(
        self,
        session: SSHSession,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.session = session
        self.pyte_screen = pyte.Screen(80, 24)
        self.pyte_stream = pyte.Stream(self.pyte_screen)

        self._listen_task = None
        self._stdin = None  # Writer
        self._connected = False

    def on_mount(self):
        """Start the connection when mounted."""
        self.call_after_refresh(self._start_ssh)

    def on_resize(self, event):
        """Handle resize events."""
        cols, lines = event.size
        # Update pyte screen size
        self.pyte_screen.resize(lines, cols)
        # Send resize to SSH channel
        if self.session and self._connected:
            self.session.resize(cols, lines)
        self.refresh()

    async def _start_ssh(self):
        """Connect and start receiving data."""
        try:
            stdin, stdout, stderr = await self.session.start_shell(
                cols=self.size.width, lines=self.size.height
            )
            self._stdin = stdin
            self._connected = True

            # Start listener
            self._listen_task = asyncio.create_task(self._read_loop(stdout))
        except Exception as e:
            self.notify(f"SSH Error: {e}", severity="error")

    async def _read_loop(self, stdout):
        """Read data from SSH and feed to pyte."""
        try:
            while True:
                # Read 1024 chars
                data = await stdout.read(1024)
                if not data:
                    break
                # Feed to pyte
                self.pyte_stream.feed(data)
                self.refresh()
        except Exception as e:
            self.notify(f"Connection lost: {e}")
        finally:
            self._connected = False

    def on_key(self, event):
        """Forward keys to SSH."""
        if not self._connected or not self._stdin:
            return

        # Simple mapping, needs more robust handling for special keys
        char = event.character
        if event.key == "enter":
            char = "\r"
        elif event.key == "backspace":
            char = "\x7f"
        elif event.key == "tab":
            char = "\t"
        elif event.key == "escape":
            char = "\x1b"
        elif event.key == "up":
            char = "\x1b[A"
        elif event.key == "down":
            char = "\x1b[B"
        elif event.key == "right":
            char = "\x1b[C"
        elif event.key == "left":
            char = "\x1b[D"

        if char:
            self._stdin.write(char)

    def render_line(self, y: int) -> Strip:
        """Render a single line of the terminal."""
        width = self.size.width
        if y >= self.pyte_screen.lines:
            return Strip.blank(width)

        # Get the line from pyte buffer
        # Pyte stores as a mapping {x: Char(data, fg, bg, ...)}
        # We need to constructing segments

        segments = []
        line_data = self.pyte_screen.buffer[y]

        # We assume full width for simplicity, iterate 0 to width
        # Pyte's buffer is sparse (it's a dict), waiting for text.
        # Ensure we fill blanks with default style.

        current_style = RichStyle.parse("white on black")
        text_accumulator = ""

        for x in range(width):
            char = line_data.get(x)
            if char:
                # Map pyte attrs to Rich style
                # This is a simplification. Pyte has 'fg', 'bg', 'bold', 'italics' etc.
                # Colors can be 'red', 'green', 'default' or hex.

                fg = char.fg if char.fg != "default" else "white"
                bg = char.bg if char.bg != "default" else "black"

                # Convert pyte color names to standard CSS/Rich names if needed
                # Rich handles standard names.

                style = RichStyle(
                    color=fg,
                    bgcolor=bg,
                    bold=char.bold,
                    italic=char.italics,
                    reverse=char.reverse,
                )

                if style != current_style:
                    if text_accumulator:
                        segments.append(Segment(text_accumulator, current_style))
                        text_accumulator = ""
                    current_style = style

                text_accumulator += char.data
            else:
                # Empty space
                if current_style != RichStyle.parse("white on black"):
                    if text_accumulator:
                        segments.append(Segment(text_accumulator, current_style))
                        text_accumulator = ""
                    current_style = RichStyle.parse("white on black")
                text_accumulator += " "

        if text_accumulator:
            segments.append(Segment(text_accumulator, current_style))

        return Strip(segments, width)

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return self.pyte_screen.lines
