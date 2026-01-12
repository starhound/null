from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class ErrorCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_fix(self, args: list[str]):
        """Fix last error. Usage: /fix [error_text]"""
        from managers.error_detector import ErrorDetector

        error_text = ""
        if args:
            error_text = " ".join(args)
        else:
            # Check for error in last block
            detector = ErrorDetector()
            if self.app.blocks:
                last_block = self.app.blocks[-1]
                if last_block.content_output:
                    errors = detector.detect(last_block.content_output)
                    if errors:
                        error_text = errors[0]

        if not error_text:
            self.notify("No error detected to fix", severity="warning")
            return

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        await self._show_fix_for_error(error_text)

    async def _show_fix_for_error(self, error: str):
        prompt = f"""Analyze this error and provide a fix.
Error:
{error}

Explain the cause briefly, then provide the corrected code or command in a markdown code block.
"""
        from models import BlockState, BlockType
        from widgets.blocks import create_block
        from widgets.history import HistoryViewport

        block = BlockState(
            type=BlockType.AI_RESPONSE, content_input="/fix", content_output=""
        )
        self.app.blocks.append(block)

        history_vp = self.app.query_one("#history", HistoryViewport)
        block_widget = create_block(block)
        await history_vp.add_block(block_widget)
        block_widget.scroll_visible()

        self.app.run_worker(
            self.app.execution_handler.execute_ai(prompt, block, block_widget)
        )

    async def cmd_watch(self, args: list[str]):
        """Toggle error watch mode."""
        if args and args[0] == "stop":
            # Logic to stop watch mode would go here
            self.notify("Watch mode stopped")
        else:
            self.notify("Watch mode enabled (not fully implemented)")
