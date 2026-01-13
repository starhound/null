"""Response formatting utilities for AI responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.css.query import NoMatches

from ai.base import Message, TokenUsage, calculate_cost
from ai.token_counter import TokenCounter

if TYPE_CHECKING:
    from app import NullApp
    from models import BlockState
    from widgets import BaseBlockWidget, StatusBar


class ResponseFormatter:
    """Handles formatting and finalizing AI responses."""

    def __init__(self, app: NullApp):
        self.app = app

    def _get_status_bar(self) -> StatusBar | None:
        try:
            from widgets import StatusBar

            return self.app.query_one("#status-bar", StatusBar)
        except Exception:
            return None

    def _get_provider_name(self) -> str:
        if self.app.ai_provider:
            return type(self.app.ai_provider).__name__.lower().replace("provider", "")
        return "default"

    def calculate_token_metadata(
        self,
        usage: TokenUsage | None,
        full_response: str,
        messages: list[Message],
        model_name: str,
        block_state: BlockState,
    ) -> tuple[TokenUsage, float]:
        """Calculate token usage metadata and cost.

        Args:
            usage: Token usage from provider, or None to estimate.
            full_response: The full AI response text.
            messages: Conversation messages for context calculation.
            model_name: Model name for cost calculation.
            block_state: Block state to update with metadata.

        Returns:
            Tuple of (TokenUsage, cost as float).
        """
        if usage:
            input_tokens = usage.input_tokens
            output_tokens = usage.output_tokens
            cost = calculate_cost(usage, model_name)
            block_state.metadata["tokens"] = (
                f"{input_tokens:,} in / {output_tokens:,} out"
            )
            if cost > 0:
                block_state.metadata["cost"] = f"${cost:.4f}"
        else:
            provider = self._get_provider_name()
            counter = TokenCounter(provider=provider, model=model_name)
            response_tokens = counter.count_tokens(full_response)
            context_tokens = counter.count_messages_tokens(messages)
            prefix = "" if counter.is_accurate else "~"
            block_state.metadata["tokens"] = (
                f"{prefix}{response_tokens} out / {prefix}{context_tokens} ctx"
            )
            input_tokens = context_tokens
            output_tokens = response_tokens
            usage = TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)
            cost = calculate_cost(usage, model_name)

        return usage, cost

    def finalize_response(
        self,
        block_state: BlockState,
        widget: BaseBlockWidget,
        full_response: str,
        messages: list[Message],
        max_tokens: int,
        usage: TokenUsage | None = None,
    ) -> None:
        """Finalize the AI response.

        Updates block state, calculates costs, updates status bar,
        and marks the response as complete.

        Args:
            block_state: The block state to finalize.
            widget: The widget to update.
            full_response: The complete response text.
            messages: Conversation messages.
            max_tokens: Maximum token limit.
            usage: Token usage data, or None to estimate.
        """
        from widgets import StatusBar

        block_state.is_running = False
        self.app._active_worker = None

        model_name = self.app.ai_provider.model if self.app.ai_provider else ""

        # Calculate token metadata
        usage, cost = self.calculate_token_metadata(
            usage, full_response, messages, model_name, block_state
        )

        widget.update_metadata()

        try:
            status_bar = self.app.query_one("#status-bar", StatusBar)

            context_chars = sum(len(m.get("content", "")) for m in messages)
            total_context = context_chars + len(full_response)
            limit_chars = max_tokens * 4
            status_bar.set_context(total_context, limit_chars)

            status_bar.add_token_usage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost=cost,
            )
        except (ImportError, NoMatches):
            pass
        except Exception as e:
            self.app.log(f"Error updating status bar: {e}")

        widget.set_loading(False)
        self._finalize_block(block_state)

    def _finalize_block(self, block_state: BlockState) -> None:
        """Mark block as finalized in storage.

        Args:
            block_state: The block state to finalize.
        """
        try:
            from config.storage import Storage

            storage = Storage()
            storage.finalize_block(block_state.id)
        except Exception:
            pass
