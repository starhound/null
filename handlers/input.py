"""Input handling for the Null terminal."""

from __future__ import annotations
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from config import Config
from models import BlockState, BlockType
from widgets import BlockWidget, HistoryViewport, InputController, CommandSuggester


class InputHandler:
    """Handles user input processing."""

    def __init__(self, app: "NullApp"):
        self.app = app

    async def handle_submission(self, value: str):
        """Process submitted input."""
        # Hide suggester
        self.app.query_one("#suggester", CommandSuggester).display = False

        if not value.strip():
            return

        input_ctrl = self.app.query_one("#input", InputController)

        # Add to history
        input_ctrl.add_to_history(value)
        Config._get_storage().add_history(value)

        # Route based on input type
        if value.startswith("/"):
            await self.app.command_handler.handle(value)
            input_ctrl.value = ""
        elif input_ctrl.is_ai_mode:
            await self._handle_ai_input(value, input_ctrl)
        else:
            await self._handle_cli_input(value, input_ctrl)

    async def _handle_ai_input(self, text: str, input_ctrl: InputController):
        """Handle AI mode input."""
        # Switching to AI mode ends CLI session
        self.app.current_cli_block = None
        self.app.current_cli_widget = None

        if not self.app.ai_provider:
            self.app.notify("AI Provider not configured. Use /provider.", severity="error")
            self.app.action_select_provider()
            return

        # Create AI block
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input=text,
            content_output=""
        )
        self.app.blocks.append(block)
        input_ctrl.value = ""

        # Mount widget
        history_vp = self.app.query_one("#history", HistoryViewport)
        block_widget = BlockWidget(block)
        await history_vp.mount(block_widget)
        block_widget.scroll_visible()

        # Run AI worker
        self.app._ai_cancelled = False
        self.app._active_worker = self.app.run_worker(
            self.app.execution_handler.execute_ai(text, block, block_widget)
        )

    async def _handle_cli_input(self, cmd: str, input_ctrl: InputController):
        """Handle CLI mode input."""
        input_ctrl.value = ""

        # Handle built-in commands (cd, pwd)
        if await self.handle_builtin(cmd):
            return

        # Check for existing CLI block to append to
        if self.app.current_cli_block and self.app.current_cli_widget:
            await self._append_to_cli_block(cmd)
        else:
            await self._create_cli_block(cmd)

    async def _append_to_cli_block(self, cmd: str):
        """Append command to existing CLI block."""
        block = self.app.current_cli_block
        widget = self.app.current_cli_widget

        if block.content_output:
            block.content_output += "\n"
        block.content_output += f"$ {cmd}\n"
        widget.update_output()
        widget.scroll_visible()

        self.app.run_worker(
            self.app.execution_handler.execute_cli_append(cmd, block, widget)
        )

    async def _create_cli_block(self, cmd: str):
        """Create a new CLI block."""
        block = BlockState(
            type=BlockType.COMMAND,
            content_input=cmd
        )
        self.app.blocks.append(block)

        # Track as current CLI session
        self.app.current_cli_block = block

        # Mount widget
        history_vp = self.app.query_one("#history", HistoryViewport)
        block_widget = BlockWidget(block)
        self.app.current_cli_widget = block_widget
        await history_vp.mount(block_widget)
        block_widget.scroll_visible()

        # Execute command
        self.app.run_worker(
            self.app.execution_handler.execute_cli(block, block_widget)
        )

    async def handle_builtin(self, cmd: str) -> bool:
        """Handle shell builtins. Returns True if handled."""
        cmd_stripped = cmd.strip()

        # Handle cd command
        if cmd_stripped == "cd" or cmd_stripped.startswith("cd "):
            await self._handle_cd(cmd_stripped)
            return True

        # Handle pwd command
        if cmd_stripped == "pwd":
            self.app.current_cli_block = None
            self.app.current_cli_widget = None
            cwd_str = str(Path.cwd())
            await self.app._show_system_output("pwd", cwd_str)
            return True

        return False

    async def _handle_cd(self, cmd: str):
        """Handle cd command."""
        # Reset CLI session
        self.app.current_cli_block = None
        self.app.current_cli_widget = None

        parts = cmd.split(maxsplit=1)
        if len(parts) == 1:
            target = Path.home()
        else:
            path_arg = parts[1].strip()
            # Handle ~ expansion
            if path_arg.startswith("~"):
                if path_arg == "~" or path_arg.startswith("~/"):
                    path_arg = str(Path.home()) + path_arg[1:]
            # Handle - (previous directory)
            if path_arg == "-":
                self.app.notify("cd - not supported", severity="warning")
                return
            target = Path(path_arg)

        try:
            if not target.is_absolute():
                target = Path.cwd() / target
            target = target.resolve()

            if not target.exists():
                self.app.notify(
                    f"cd: no such directory: {parts[1] if len(parts) > 1 else '~'}",
                    severity="error"
                )
                return
            if not target.is_dir():
                self.app.notify(f"cd: not a directory: {parts[1]}", severity="error")
                return

            os.chdir(target)
            self.app._update_prompt()
        except PermissionError:
            self.app.notify(
                f"cd: permission denied: {parts[1] if len(parts) > 1 else '~'}",
                severity="error"
            )
        except Exception as e:
            self.app.notify(f"cd: {e}", severity="error")
