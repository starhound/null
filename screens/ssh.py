from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.screen import Screen

from utils.ssh_client import SSHSession
from widgets.ssh_terminal import SSHTerminal


class SSHScreen(Screen):
    """Screen for interactive SSH session."""

    BINDINGS: ClassVar[list[BindingType]] = [("ctrl+d", "detach", "Detach Session")]

    def __init__(self, session: SSHSession, alias: str):
        super().__init__()
        self.session = session
        self.alias = alias

    def compose(self) -> ComposeResult:
        yield SSHTerminal(self.session, id="ssh-term")

    def action_detach(self):
        """Detach from session and return to main app."""
        # Clean up connection
        self.session.close()
        self.app.pop_screen()
        self.app.push_message(f"Disconnected from {self.alias}")
