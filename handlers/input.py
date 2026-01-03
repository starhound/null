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

        # Determine block type based on agent mode setting
        ai_config = self.app.config.get("ai", {})
        agent_mode = ai_config.get("agent_mode", False)
        use_tools = self.app.ai_provider.supports_tools()

        # Use AGENT_RESPONSE for agent mode with tool-supporting providers
        if agent_mode and use_tools:
            block_type = BlockType.AGENT_RESPONSE
        else:
            block_type = BlockType.AI_RESPONSE

        # Create AI/Agent block
        block = BlockState(
            type=block_type,
            content_input=text,
            content_output=""
        )
        self.app.blocks.append(block)
        input_ctrl.value = ""

        # Mount widget - BlockWidget factory creates correct widget type
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

        # Check if there's a running process that needs input (like sudo)
        if self._send_to_running_process(cmd):
            return

        # Handle built-in commands (cd, pwd)
        if await self.handle_builtin(cmd):
            return

        # Check for existing CLI block to append to
        # Only append if the current block is NOT a TUI block
        is_tui = False
        if self.app.current_cli_block:
             info = self.app.process_manager.get(self.app.current_cli_block.id)
             if info and info.is_tui:
                 is_tui = True

        # Heuristic: Known TUI commands should always start a new block
        # to ensure a clean window and proper mouse handling
        tui_heuristic = ["top", "htop", "vim", "vi", "nano", "less", "more", "man", "mc", "tmux"]
        cmd_base = cmd.split(" ")[0]
        if cmd_base in tui_heuristic:
            is_tui = True  # Force new block

        if self.app.current_cli_block and self.app.current_cli_widget and not is_tui:
            await self._append_to_cli_block(cmd)
        else:
            await self._create_cli_block(cmd)

    def _send_to_running_process(self, text: str) -> bool:
        """Send input to a running process if one exists.

        Returns True if input was sent, False otherwise.
        """
        # If we have a current CLI block, check if it's running
        if self.app.current_cli_block and self.app.current_cli_block.id:
            block_id = self.app.current_cli_block.id
            if self.app.process_manager.is_running(block_id):
                 info = self.app.process_manager.get(block_id)
                 # Don't send input if it's a TUI (handled via raw keys)
                 if info and info.is_tui:
                     return False
                 
                 # Send input to this process
                 return self.app.process_manager.send_input(block_id, (text + "\n").encode('utf-8'))

        return False

    # Unicode box-drawing rule for separating command chains
    COMMAND_SEPARATOR = "┄" * 40

    async def _append_to_cli_block(self, cmd: str):
        """Append command to existing CLI block."""
        block = self.app.current_cli_block
        widget = self.app.current_cli_widget

        if block.content_output:
            # Add visual separator between command chains
            block.content_output += f"\n{self.COMMAND_SEPARATOR}\n\n"
        block.content_output += f"❯ {cmd}\n"
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

        # Handle clear/cls/reset - these would mess up the TUI
        if cmd_stripped in ("clear", "cls", "reset"):
            self.app.current_cli_block = None
            self.app.current_cli_widget = None
            self.app.action_clear_history()
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
