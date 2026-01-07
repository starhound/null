"""Common utilities for handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app import NullApp
    from textual.timer import Timer


class UIBuffer:
    def __init__(
        self,
        app: NullApp,
        callback: Callable[[str], None],
        interval: float = 0.016,
    ) -> None:
        self.app = app
        self.callback = callback
        self.buffer: list[str] = []
        self.timer: Timer = self.app.set_interval(interval, self.flush)
        self._first_write = True

    def write(self, data: str) -> None:
        self.buffer.append(data)

        if self._first_write:
            self.flush()
            self._first_write = False
            return

        if len(self.buffer) > 20 or sum(len(c) for c in self.buffer) > 1000:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            chunk = "".join(self.buffer)
            self.buffer.clear()
            self.callback(chunk)

    def stop(self) -> None:
        self.timer.stop()
        self.flush()
