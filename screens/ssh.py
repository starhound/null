from textual.screen import Screen
from textual.app import ComposeResult
from widgets.ssh_terminal import SSHTerminal
from utils.ssh_client import SSHSession

class SSHScreen(Screen):
    """Screen for interactive SSH session."""
    
    BINDINGS = [
        ("ctrl+d", "detach", "Detach Session")
    ]

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
