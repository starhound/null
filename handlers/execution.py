"""Execution handlers for AI and CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ai_executor import AIExecutor
from .cli_executor import CLIExecutor

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState
    from widgets import BaseBlockWidget


class ExecutionHandler:
    """Facade for AI and CLI command execution."""

    def __init__(self, app: NullApp):
        self.app = app
        self.ai_executor = AIExecutor(app)
        self.cli_executor = CLIExecutor(app)

    async def execute_ai(
        self, prompt: str, block_state: BlockState, widget: BaseBlockWidget
    ) -> None:
        """Execute AI generation with streaming response and tool support."""
        await self.ai_executor.execute_ai(prompt, block_state, widget)

    async def regenerate_ai(self, block: BlockState, widget: BaseBlockWidget) -> None:
        """Regenerate an AI response block."""
        await self.ai_executor.regenerate_ai(block, widget)

    def run_agent_command(
        self, command: str, ai_block: BlockState, ai_widget: BaseBlockWidget
    ) -> None:
        """Execute a command requested by the AI agent."""
        self.ai_executor.run_agent_command(command, ai_block, ai_widget)

    async def execute_cli(self, block: BlockState, widget: BaseBlockWidget) -> None:
        """Execute a CLI command and stream output."""
        await self.cli_executor.execute_cli(block, widget)

    async def execute_cli_append(
        self, cmd: str, block: BlockState, widget: BaseBlockWidget
    ) -> None:
        """Execute a command and append output to existing CLI block."""
        await self.cli_executor.execute_cli_append(cmd, block, widget)

    async def cancel_tool(self, tool_id: str) -> None:
        await self.ai_executor.cancel_tool(tool_id)
