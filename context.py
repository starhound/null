from dataclasses import dataclass

from models import BlockState, BlockType


@dataclass
class ContextInfo:
    """Context information with size metrics."""

    messages: list[dict]  # List of Message dicts
    total_chars: int
    estimated_tokens: int
    message_count: int
    truncated: bool = False


class ContextManager:
    @staticmethod
    def get_context(history_blocks: list[BlockState], limit_chars: int = 4000) -> str:
        """
        Legacy method - builds a text context from the block history.
        Kept for backward compatibility.
        """
        info = ContextManager.build_messages(history_blocks, limit_chars)
        # Convert messages back to text for legacy callers
        buffer = []
        for msg in info.messages:
            if msg["role"] == "user":
                buffer.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                buffer.append(f"Assistant: {msg['content']}")
        return "\n\n".join(buffer)

    @staticmethod
    def build_messages(
        history_blocks: list[BlockState],
        max_tokens: int = 4096,
        reserve_tokens: int = 1024,
    ) -> ContextInfo:
        """
        Build proper message array from block history.

        Args:
            history_blocks: List of BlockState objects
            max_tokens: Model's max context window
            reserve_tokens: Tokens to reserve for response

        Returns:
            ContextInfo with messages and size metrics
        """
        available_tokens = max_tokens - reserve_tokens
        # Rough char limit (4 chars per token estimate)
        char_limit = available_tokens * 4

        messages = []
        current_chars = 0
        truncated = False

        # Build messages in chronological order, but we'll trim from the start if needed
        all_messages = []

        for block in history_blocks:
            if block.type == BlockType.COMMAND:
                # Include command context as user message
                cmd_content = f"[Terminal Command]\n$ {block.content_input}"
                if block.content_output:
                    # Truncate very long command outputs
                    output = block.content_output
                    if len(output) > 2000:
                        output = output[:1000] + "\n...[truncated]...\n" + output[-500:]
                    cmd_content += f"\n{output}"
                all_messages.append({"role": "user", "content": cmd_content})

            elif block.type == BlockType.AI_QUERY:
                all_messages.append({"role": "user", "content": block.content_input})

            elif block.type == BlockType.AI_RESPONSE:
                if block.content_output:
                    all_messages.append(
                        {"role": "assistant", "content": block.content_output}
                    )

        # Now trim from the beginning if we exceed the limit
        total_chars = sum(len(m["content"]) for m in all_messages)

        if total_chars > char_limit:
            truncated = True
            # Remove oldest messages until we fit
            while all_messages and total_chars > char_limit:
                removed = all_messages.pop(0)
                total_chars -= len(removed["content"])

        messages = all_messages
        current_chars = sum(len(m["content"]) for m in messages)

        return ContextInfo(
            messages=messages,
            total_chars=current_chars,
            estimated_tokens=current_chars // 4,
            message_count=len(messages),
            truncated=truncated,
        )

    @staticmethod
    def estimate_total_tokens(
        system_prompt: str, messages: list[dict], current_prompt: str
    ) -> int:
        """Estimate total tokens for a request."""
        total_chars = len(system_prompt) + len(current_prompt)
        total_chars += sum(len(m["content"]) for m in messages)
        return total_chars // 4
