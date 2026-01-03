from textual.app import ComposeResult

from models import BlockState

from .base import BaseBlockWidget
from .parts import BlockBody, BlockFooter, BlockHeader
from .terminal import TerminalBlock


class CommandBlock(BaseBlockWidget):
    """Block widget for CLI commands."""

    def __init__(self, block: BlockState):
        super().__init__(block)
        self.header = BlockHeader(block)
        self.body_widget = BlockBody(block.content_output or "")
        self.footer_widget = BlockFooter(block)
        self._mode = "line"  # "line" or "tui"
        self._terminal_widget: TerminalBlock | None = None

    def compose(self) -> ComposeResult:
        yield self.header
        yield self.body_widget
        if self.footer_widget._has_content():
            yield self.footer_widget

    @property
    def mode(self) -> str:
        """Get the current display mode."""
        return self._mode

    def update_output(self, new_content: str = ""):
        """Update the command output display."""
        if self.body_widget and self._mode == "line":
            self.body_widget.content_text = self.block.content_output

    def switch_to_tui(self) -> TerminalBlock:
        """Switch from line mode to TUI mode.

        Returns the TerminalBlock for feeding data.
        """
        if self._mode == "tui" and self._terminal_widget:
            return self._terminal_widget

        self._mode = "tui"
        self.add_class("mode-tui")

        # Update header icon for TUI
        try:
            icon_lbl = self.header.query_one(".prompt-symbol", Label)
            icon_lbl.update("█")
            icon_lbl.add_class("prompt-symbol-tui")
        except Exception:
            pass

        # Hide line output widget
        self.body_widget.display = False

        # Create and mount terminal widget
        self._terminal_widget = TerminalBlock(block_id=self.block.id, rows=24, cols=120)
        self.mount(self._terminal_widget, before=self.footer_widget)
        # self._terminal_widget.focus()  # User requested no auto-focus

        return self._terminal_widget

    def switch_to_line(self) -> None:
        """Switch from TUI mode back to line mode."""
        if self._mode == "line":
            return

        self._mode = "line"
        self.remove_class("mode-tui")

        # Revert header icon
        try:
            icon_lbl = self.header.query_one(".prompt-symbol", Label)
            icon_lbl.update("❯")
            icon_lbl.remove_class("prompt-symbol-tui")
        except Exception:
            pass

        # Remove terminal widget
        if self._terminal_widget:
            self._terminal_widget.remove()
            self._terminal_widget = None

        # Show line output widget again
        self.body_widget.display = True

    def feed_terminal(self, data: bytes) -> None:
        """Feed raw data to the terminal widget (when in TUI mode)."""
        if self._terminal_widget:
            self._terminal_widget.feed(data)

    def set_loading(self, loading: bool):
        """Set the loading state and update footer."""
        self.block.is_running = loading

        # We keep the TUI mode active even after process exit so the user
        # can still see the final state of the terminal.
        # if not loading and self._mode == "tui":
        #    self.switch_to_line()

        try:
            self.footer_widget.remove()
        except Exception:
            pass

        self.footer_widget = BlockFooter(self.block)
        if self.footer_widget._has_content():
            self.mount(self.footer_widget)
