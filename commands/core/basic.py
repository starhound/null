from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class BasicCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_help(self, args: list[str]):
        """Show help screen."""
        from screens import HelpScreen

        self.app.push_screen(HelpScreen())

    async def cmd_status(self, args: list[str]):
        """Show system status."""
        import platform
        import sys
        from datetime import datetime

        lines = [
            "Null Terminal Status",
            "=" * 20,
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Python: {sys.version.split()[0]}",
            f"Platform: {platform.system()} {platform.release()}",
            f"CWD: {Path.cwd()}",
            "",
            "Components:",
            f"  AI Provider: {self.app.ai_provider.name if self.app.ai_provider else 'None'}",
            f"  History: {len(self.app.blocks)} blocks",
        ]

        await self.show_output("/status", "\n".join(lines))

    async def cmd_clear(self, args: list[str]):
        """Clear history and context."""
        self.app.blocks = []
        self.app.current_cli_block = None
        self.app.current_cli_widget = None

        try:
            history = self.app.query_one("#history")
            await history.remove_children()
        except Exception:
            pass

        try:
            status_bar = self.app.query_one("#status-bar")
            if hasattr(status_bar, "reset_token_usage"):
                status_bar.reset_token_usage()
        except Exception:
            pass

        self.notify("History cleared")

    async def cmd_quit(self, args: list[str]):
        """Quit application."""
        self.app.exit()

    async def cmd_exit(self, args: list[str]):
        """Quit application."""
        self.app.exit()

    async def cmd_reload(self, args: list[str]):
        """Reload configuration."""
        from config import Config, get_settings

        try:
            # Reload config files
            self.app.config = Config.load_all()

            # Reload settings
            settings = get_settings()
            settings.load()

            # Update status bar
            self.app._update_status_bar()

            self.notify("Configuration reloaded")
        except Exception as e:
            self.notify(f"Reload failed: {e}", severity="error")

    async def cmd_map(self, args: list[str]):
        """Show project architecture."""
        path = args[0] if args else "."
        from managers.architecture import ArchitectureManager

        arch = ArchitectureManager()
        result = await arch.analyze(path)
        await self.show_output("/map", result)

    async def cmd_cmd(self, args: list[str]):
        """Translate natural language to shell command."""
        if not args:
            self.notify("Usage: /cmd <description>", severity="warning")
            return

        description = " ".join(args)

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        from managers.nl2shell import NL2Shell

        manager = NL2Shell()
        cmd = await manager.translate(description, self.app.ai_provider)

        if cmd:
            # Insert into input buffer instead of executing
            input_ctrl = self.app.query_one("#input")
            input_ctrl.text = cmd
            input_ctrl.focus()
        else:
            self.notify("Could not generate command", severity="error")

    async def cmd_explain(self, args: list[str]):
        """Explain a shell command."""
        if not args:
            self.notify("Usage: /explain <command>", severity="warning")
            return

        command = " ".join(args)

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        prompt = f"Explain this shell command in detail:\n\n`{command}`"

        # Create block for explanation
        from models import BlockState, BlockType
        from widgets.blocks import create_block
        from widgets.history import HistoryViewport

        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input=f"/explain {command}",
            content_output="",
        )
        self.app.blocks.append(block)

        history_vp = self.app.query_one("#history", HistoryViewport)
        block_widget = create_block(block)
        await history_vp.add_block(block_widget)
        block_widget.scroll_visible()

        self.app.run_worker(
            self.app.execution_handler.execute_ai(prompt, block, block_widget)
        )
