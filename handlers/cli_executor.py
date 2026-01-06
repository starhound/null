"""CLI Execution Handler."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from config import get_settings
from executor import ExecutionEngine
from widgets.blocks import CommandBlock
from .common import UIBuffer

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState
    from widgets import BaseBlockWidget


class CLIExecutor:
    """Handles CLI command execution."""

    def __init__(self, app: NullApp):
        self.app = app
        self._current_exec_task: asyncio.Task | None = None

    async def execute_cli(self, block: BlockState, widget: BaseBlockWidget) -> None:
        """Execute a CLI command and stream output."""
        await self._execute_cli_internal(block.content_input, block, widget)

    async def execute_cli_append(
        self, cmd: str, block: BlockState, widget: BaseBlockWidget
    ) -> None:
        """Execute a command and append output to existing CLI block."""
        await self._execute_cli_internal(cmd, block, widget, is_append=True)

    async def _execute_cli_internal(
        self,
        cmd: str,
        block: BlockState,
        widget: BaseBlockWidget,
        is_append: bool = False,
    ) -> None:
        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        buffer = UIBuffer(self.app, update_callback)

        def mode_callback(mode: str, data: bytes):
            if not isinstance(widget, CommandBlock):
                return

            if mode == "enter":
                widget.switch_to_tui()
                widget.feed_terminal(data)
                self.app.process_manager.set_tui_mode(block.id, True)
            elif mode == "exit":
                widget.switch_to_line()
                self.app.process_manager.set_tui_mode(block.id, False)

        def raw_callback(data: bytes):
            if isinstance(widget, CommandBlock):
                widget.feed_terminal(data)

        executor = ExecutionEngine()
        ready_event = asyncio.Event()

        exec_task = asyncio.create_task(
            executor.run_command_and_get_rc(
                cmd,
                buffer.write,
                mode_callback=mode_callback,
                raw_callback=raw_callback,
                ready_event=ready_event,
            )
        )
        self._current_exec_task = exec_task

        await ready_event.wait()
        if executor.pid:
            self.app.process_manager.register(
                block_id=block.id,
                pid=executor.pid,
                command=cmd,
                master_fd=executor.master_fd,
                executor=executor,
            )

        try:
            exit_code = await exec_task
        finally:
            buffer.stop()
            self.app.process_manager.unregister(block.id)

        if not is_append:
            if hasattr(widget, "set_exit_code"):
                getattr(widget, "set_exit_code")(exit_code)
        elif exit_code != 0:
            block.content_output += f"\n[exit: {exit_code}]\n"
            widget.update_output()

        if get_settings().terminal.auto_save_session:
            self.app._auto_save()
