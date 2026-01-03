"""Session management commands: session, export."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from config import Config
from widgets import BlockWidget, HistoryViewport, StatusBar

from .base import CommandMixin


class SessionCommands(CommandMixin):
    """Session management commands."""

    def __init__(self, app: NullApp):
        self.app = app

    async def cmd_export(self, args: list[str]):
        """Export conversation."""
        format = args[0] if args else "md"
        if format not in ("md", "json", "markdown"):
            self.notify("Usage: /export [md|json]", severity="error")
            return
        if format == "markdown":
            format = "md"
        self.app._do_export(format)

    async def cmd_session(self, args: list[str]):
        """Session management."""
        if not args:
            self.notify(
                "Usage: /session [save|load|list|new] [name]", severity="warning"
            )
            return

        subcommand = args[0]
        name = args[1] if len(args) > 1 else None
        storage = Config._get_storage()

        if subcommand == "save":
            filepath = storage.save_session(self.app.blocks, name)
            self.notify(f"Session saved to {filepath}")

        elif subcommand == "load":
            await self._session_load(name, storage)

        elif subcommand == "list":
            await self._session_list(storage)

        elif subcommand == "new":
            self.app.blocks = []
            self.app.current_cli_block = None
            self.app.current_cli_widget = None
            storage.clear_current_session()
            history = self.app.query_one("#history", HistoryViewport)
            await history.remove_children()
            # Reset token usage for new session
            status_bar = self.app.query_one("#status-bar", StatusBar)
            status_bar.reset_token_usage()
            self.notify("Started new session")

        else:
            self.notify("Usage: /session [save|load|list|new] [name]", severity="error")

    async def _session_load(self, name: str | None, storage):
        """Load a session by name or show selection."""
        if name:
            blocks = storage.load_session(name)
            if blocks:
                self.app.blocks = blocks
                self.app.current_cli_block = None
                self.app.current_cli_widget = None
                history = self.app.query_one("#history", HistoryViewport)
                await history.remove_children()
                for block in self.app.blocks:
                    block.is_running = False
                    block_widget = BlockWidget(block)
                    await history.mount(block_widget)
                history.scroll_end(animate=False)
                # Reset token usage when loading a session (no history of past tokens)
                status_bar = self.app.query_one("#status-bar", StatusBar)
                status_bar.reset_token_usage()
                self.notify(f"Loaded session: {name}")
            else:
                self.notify(f"Session not found: {name}", severity="error")
        else:
            sessions = storage.list_sessions()
            if sessions:
                names = [s["name"] for s in sessions]

                def on_select(selected):
                    if selected:
                        self.app.call_later(
                            lambda: self.app.run_worker(
                                self.cmd_session(["load", selected])
                            )
                        )

                from screens import SelectionListScreen

                self.app.push_screen(
                    SelectionListScreen("Load Session", names), on_select
                )
            else:
                self.notify("No saved sessions found", severity="warning")

    async def _session_list(self, storage):
        """List all saved sessions."""
        sessions = storage.list_sessions()
        if sessions:
            lines = []
            for s in sessions:
                saved_at = s.get("saved_at", "")[:16].replace("T", " ")
                blocks = s.get("block_count", 0)
                lines.append(f"  {s['name']:20} {saved_at:16} ({blocks} blocks)")
            content = "\n".join(lines)
            await self.show_output("/session list", content)
        else:
            self.notify("No saved sessions", severity="warning")
