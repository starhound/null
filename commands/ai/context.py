from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin
from models import BlockState, BlockType


class AIContext(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_context(self, args: list[str]):
        from screens.context import ContextScreen

        self.app.push_screen(ContextScreen())

    async def cmd_compact(self, args: list[str]):
        """Summarize context to reduce token usage."""
        if not self.app.blocks:
            self.notify("Nothing to compact", severity="warning")
            return

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        from context import ContextManager

        context_info = ContextManager.build_messages(self.app.blocks)

        if context_info.estimated_tokens < 500:
            self.notify("Context too small to compact", severity="warning")
            return

        self.notify("Compacting context...")

        summary_prompt = """Summarize this conversation concisely. Include:
- Key topics discussed
- Important decisions or conclusions
- Any code/commands that were significant
- Current state/context needed for continuity

Be brief but preserve essential context. Output only the summary."""

        content_parts = []
        for block in self.app.blocks:
            if block.type == BlockType.AI_QUERY:
                content_parts.append(f"User: {block.content_input}")
            elif block.type == BlockType.AI_RESPONSE:
                content_parts.append(f"Assistant: {block.content_output[:1000]}")
            elif block.type == BlockType.COMMAND:
                content_parts.append(f"Command: {block.content_input}")
                if block.content_output:
                    content_parts.append(f"Output: {block.content_output[:500]}")

        context_text = "\n".join(content_parts)

        try:
            summary = ""
            async for chunk in self.app.ai_provider.generate(
                summary_prompt,
                [{"role": "user", "content": context_text}],
                system_prompt="You are a helpful assistant that creates concise conversation summaries.",
            ):
                summary += chunk

            old_token_count = context_info.estimated_tokens
            self.app.blocks = []
            self.app.current_cli_block = None
            self.app.current_cli_widget = None

            try:
                history = self.app.query_one("#history")
                await history.remove_children()
            except Exception:
                pass

            summary_block = BlockState(
                type=BlockType.SYSTEM_MSG,
                content_input="Context Summary",
                content_output=summary,
                is_running=False,
            )
            self.app.blocks.append(summary_block)

            try:
                from widgets import BlockWidget, HistoryViewport

                block_widget = BlockWidget(summary_block)
                history = self.app.query_one("#history", HistoryViewport)
                await history.add_block(block_widget)
            except Exception:
                pass

            new_token_count = len(summary) // 4
            reduction = ((old_token_count - new_token_count) / old_token_count) * 100

            self.app._update_status_bar()
            self.notify(
                f"Compacted: ~{old_token_count} → ~{new_token_count} tokens ({reduction:.0f}% reduction)"
            )

        except Exception as e:
            self.notify(f"Compact failed: {e}", severity="error")
