from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Label, Static

from utils.ssh_client import SSHSession
from widgets.ssh_terminal import SSHTerminal


class ConnectionStatusBar(Static):
    DEFAULT_CSS = """
    ConnectionStatusBar {
        dock: top;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    ConnectionStatusBar .status-connected {
        color: $success;
    }
    ConnectionStatusBar .status-disconnected {
        color: $error;
    }
    ConnectionStatusBar .status-reconnecting {
        color: $warning;
    }
    ConnectionStatusBar .host-info {
        color: $text-muted;
    }
    """

    status: reactive[str] = reactive("disconnected")

    def __init__(self, host: str, port: int, username: str | None = None):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("", id="status-icon")
            yield Label("", id="status-text")
            yield Label("", id="host-info", classes="host-info")

    def on_mount(self) -> None:
        self._update_display()

    def watch_status(self, status: str) -> None:
        self._update_display()

    def _update_display(self) -> None:
        icon_label = self.query_one("#status-icon", Label)
        text_label = self.query_one("#status-text", Label)
        host_label = self.query_one("#host-info", Label)

        status_map = {
            "connected": ("●", "Connected", "status-connected"),
            "disconnected": ("○", "Disconnected", "status-disconnected"),
            "reconnecting": ("◐", "Reconnecting...", "status-reconnecting"),
            "connecting": ("◐", "Connecting...", "status-reconnecting"),
        }

        icon, text, css_class = status_map.get(
            self.status, ("?", self.status, "status-disconnected")
        )

        icon_label.update(f"{icon} ")
        icon_label.set_classes(css_class)
        text_label.update(text)
        text_label.set_classes(css_class)

        user_part = f"{self.username}@" if self.username else ""
        port_part = f":{self.port}" if self.port != 22 else ""
        host_label.update(f"  {user_part}{self.host}{port_part}")


class SSHScreen(Screen):
    BINDINGS: ClassVar[list[BindingType]] = [
        ("ctrl+d", "detach", "Detach Session"),
        ("ctrl+r", "reconnect", "Reconnect"),
    ]

    DEFAULT_CSS = """
    SSHScreen {
        layout: vertical;
    }
    """

    connection_status: reactive[str] = reactive("connecting")

    def __init__(self, session: SSHSession, alias: str):
        super().__init__()
        self.session = session
        self.alias = alias
        self._terminal: SSHTerminal | None = None

    def compose(self) -> ComposeResult:
        yield ConnectionStatusBar(
            host=self.session.hostname,
            port=self.session.port,
            username=self.session.username,
            id="ssh-status-bar",
        )
        yield SSHTerminal(self.session, id="ssh-term")

    def on_mount(self) -> None:
        self._terminal = self.query_one("#ssh-term", SSHTerminal)
        self.session.add_disconnect_callback(self._on_disconnect)

    def watch_connection_status(self, status: str) -> None:
        try:
            status_bar = self.query_one("#ssh-status-bar", ConnectionStatusBar)
            status_bar.status = status
        except Exception:
            pass

    def _on_disconnect(self) -> None:
        self.connection_status = "disconnected"
        self.notify("Connection lost", severity="warning")

    def on_ssh_terminal_connected(self) -> None:
        self.connection_status = "connected"

    def on_ssh_terminal_disconnected(self) -> None:
        self.connection_status = "disconnected"

    async def action_reconnect(self) -> None:
        self.connection_status = "reconnecting"
        self.notify("Attempting to reconnect...")

        success = await self.session.reconnect()
        if success:
            self.connection_status = "connected"
            self.notify(f"Reconnected to {self.alias}", severity="information")
            if self._terminal:
                self._terminal.call_after_refresh(self._terminal._start_ssh)
        else:
            self.connection_status = "disconnected"
            self.notify("Reconnection failed", severity="error")

    def action_detach(self) -> None:
        self.session.remove_disconnect_callback(self._on_disconnect)
        self.session.close()
        self.app.pop_screen()
        self.notify(f"Disconnected from {self.alias}")
