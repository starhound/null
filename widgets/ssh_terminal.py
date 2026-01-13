import asyncio
from asyncio import Task
from typing import Any

import pyte
from rich.segment import Segment
from rich.style import Style as RichStyle
from textual.geometry import Size
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from utils.ssh_client import SSHSession


class SSHTerminal(Widget):
    DEFAULT_CSS = """
    SSHTerminal {
        height: 1fr;
        background: black;
        color: white;
        overflow: hidden;
    }
    """

    class Connected(Message):
        pass

    class Disconnected(Message):
        def __init__(self, error: str | None = None):
            super().__init__()
            self.error = error

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

        self._listen_task: Task[Any] | None = None
        self._stdin: Any = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

    @property
    def is_connected(self) -> bool:
        return self._connected

    def on_mount(self) -> None:
        self.call_after_refresh(self._start_ssh)

    def on_resize(self, event: Any) -> None:
        cols, lines = event.size
        self.pyte_screen.resize(lines, cols)
        if self.session and self._connected:
            self.session.resize(cols, lines)
        self.refresh()

    async def _start_ssh(self) -> None:
        try:
            stdin, stdout, _stderr = await self.session.start_shell(
                cols=self.size.width, lines=self.size.height
            )
            self._stdin = stdin
            self._connected = True
            self._reconnect_attempts = 0

            self.post_message(self.Connected())

            self._listen_task = asyncio.create_task(self._read_loop(stdout))
        except Exception as e:
            self.notify(f"SSH Error: {e}", severity="error")
            self.post_message(self.Disconnected(error=str(e)))

    async def _read_loop(self, stdout: Any) -> None:
        try:
            while True:
                data = await stdout.read(4096)
                if not data:
                    break
                self.pyte_stream.feed(data)
                self.refresh()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.notify(f"Connection lost: {e}")
        finally:
            was_connected = self._connected
            self._connected = False
            if was_connected:
                self.post_message(self.Disconnected())

    def on_key(self, event: Any) -> None:
        if not self._connected or not self._stdin:
            return

        char = event.character
        key_map = {
            "enter": "\r",
            "backspace": "\x7f",
            "tab": "\t",
            "escape": "\x1b",
            "up": "\x1b[A",
            "down": "\x1b[B",
            "right": "\x1b[C",
            "left": "\x1b[D",
            "home": "\x1b[H",
            "end": "\x1b[F",
            "pageup": "\x1b[5~",
            "pagedown": "\x1b[6~",
            "insert": "\x1b[2~",
            "delete": "\x1b[3~",
            "f1": "\x1bOP",
            "f2": "\x1bOQ",
            "f3": "\x1bOR",
            "f4": "\x1bOS",
            "f5": "\x1b[15~",
            "f6": "\x1b[17~",
            "f7": "\x1b[18~",
            "f8": "\x1b[19~",
            "f9": "\x1b[20~",
            "f10": "\x1b[21~",
            "f11": "\x1b[23~",
            "f12": "\x1b[24~",
        }

        if event.key in key_map:
            char = key_map[event.key]

        if char:
            self._stdin.write(char)

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if y >= self.pyte_screen.lines:
            return Strip.blank(width)

        segments: list[Segment] = []
        line_data = self.pyte_screen.buffer[y]

        current_style = RichStyle.parse("white on black")
        text_accumulator = ""

        for x in range(width):
            char = line_data.get(x)
            if char:
                fg = char.fg if char.fg != "default" else "white"
                bg = char.bg if char.bg != "default" else "black"

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

    def cancel(self) -> None:
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        self._connected = False
