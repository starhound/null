from dataclasses import dataclass
from typing import Any

from models import BlockState, BlockType


@dataclass
class ContextInfo:
    """Context information with size metrics."""

    messages: list[dict[str, Any]]  # List of Message dicts
    total_chars: int
    estimated_tokens: int
    message_count: int
    truncated: bool = False
    summarized: bool = False
    summary_details: str = ""
    original_message_count: int = 0


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
        keep_recent: int = 5,
    ) -> ContextInfo:
        available_tokens = max_tokens - reserve_tokens
        char_limit = available_tokens * 4

        all_messages = ContextManager._blocks_to_messages(history_blocks)
        original_count = len(all_messages)
        total_chars = sum(len(m["content"]) for m in all_messages)

        if total_chars <= char_limit:
            return ContextInfo(
                messages=all_messages,
                total_chars=total_chars,
                estimated_tokens=total_chars // 4,
                message_count=len(all_messages),
                truncated=False,
                summarized=False,
                original_message_count=original_count,
            )

        result = ContextManager._summarize_context(
            all_messages, char_limit, keep_recent
        )

        final_chars = sum(len(m["content"]) for m in result["messages"])

        return ContextInfo(
            messages=result["messages"],
            total_chars=final_chars,
            estimated_tokens=final_chars // 4,
            message_count=len(result["messages"]),
            truncated=result["truncated"],
            summarized=result["summarized"],
            summary_details=result["summary_details"],
            original_message_count=original_count,
        )

    @staticmethod
    def _blocks_to_messages(history_blocks: list[BlockState]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []

        for block in history_blocks:
            if block.type == BlockType.COMMAND:
                cmd_content = f"[Terminal Command]\n$ {block.content_input}"
                if block.content_output:
                    output = block.content_output
                    if len(output) > 2000:
                        output = output[:1000] + "\n...[truncated]...\n" + output[-500:]
                    cmd_content += f"\n{output}"
                messages.append({"role": "user", "content": cmd_content})

            elif block.type == BlockType.AI_QUERY:
                messages.append({"role": "user", "content": block.content_input})

            elif block.type == BlockType.AI_RESPONSE:
                if block.content_output:
                    messages.append(
                        {"role": "assistant", "content": block.content_output}
                    )

            elif block.type == BlockType.SYSTEM_MSG:
                content = f"[{block.content_input}]\n{block.content_output}"
                messages.append({"role": "user", "content": content})

        return messages

    @staticmethod
    def _summarize_context(
        all_messages: list[dict[str, Any]],
        char_limit: int,
        keep_recent: int,
    ) -> dict[str, Any]:
        if len(all_messages) <= keep_recent:
            while (
                all_messages
                and sum(len(m["content"]) for m in all_messages) > char_limit
            ):
                all_messages.pop(0)
            return {
                "messages": all_messages,
                "truncated": True,
                "summarized": False,
                "summary_details": "",
            }

        recent_messages = all_messages[-keep_recent:]
        older_messages = all_messages[:-keep_recent]

        recent_chars = sum(len(m["content"]) for m in recent_messages)
        available_for_summary = char_limit - recent_chars - 500

        if available_for_summary < 200:
            while (
                recent_messages
                and sum(len(m["content"]) for m in recent_messages) > char_limit
            ):
                recent_messages.pop(0)
            return {
                "messages": recent_messages,
                "truncated": True,
                "summarized": False,
                "summary_details": "",
            }

        summary = ContextManager._generate_summary(
            older_messages, available_for_summary
        )

        summary_message: dict[str, Any] = {
            "role": "user",
            "content": summary["content"],
        }

        return {
            "messages": [summary_message, *recent_messages],
            "truncated": False,
            "summarized": True,
            "summary_details": summary["details"],
        }

    @staticmethod
    def _generate_summary(
        messages: list[dict[str, Any]], max_chars: int
    ) -> dict[str, str]:
        user_topics: list[str] = []
        assistant_points: list[str] = []
        commands_run: list[str] = []

        for msg in messages:
            content = msg["content"]
            role = msg["role"]

            if role == "user":
                if content.startswith("[Terminal Command]"):
                    cmd_line = content.split("\n")[1] if "\n" in content else content
                    cmd = cmd_line.replace("$ ", "").strip()[:50]
                    if cmd:
                        commands_run.append(cmd)
                else:
                    topic = ContextManager._extract_topic(content)
                    if topic:
                        user_topics.append(topic)

            elif role == "assistant":
                point = ContextManager._extract_key_point(content)
                if point:
                    assistant_points.append(point)

        summary_parts = ["[Previous Conversation Summary]"]

        if user_topics:
            unique_topics = list(dict.fromkeys(user_topics))[:8]
            summary_parts.append(f"Topics discussed: {', '.join(unique_topics)}")

        if commands_run:
            unique_cmds = list(dict.fromkeys(commands_run))[:5]
            summary_parts.append(f"Commands executed: {', '.join(unique_cmds)}")

        if assistant_points:
            unique_points = list(dict.fromkeys(assistant_points))[:5]
            summary_parts.append(f"Key points: {'; '.join(unique_points)}")

        summary_parts.append(
            f"({len(messages)} messages summarized to preserve context)"
        )

        full_summary = "\n".join(summary_parts)

        if len(full_summary) > max_chars:
            full_summary = full_summary[: max_chars - 20] + "\n[...]"

        details = f"Summarized {len(messages)} messages"
        if user_topics:
            details += f" covering {len(user_topics)} topics"

        return {"content": full_summary, "details": details}

    @staticmethod
    def _extract_topic(content: str) -> str:
        content = content.strip()
        if not content:
            return ""

        first_line = content.split("\n")[0].strip()

        if first_line.startswith("[") and "]" in first_line:
            first_line = first_line.split("]", 1)[-1].strip()

        if len(first_line) > 60:
            words = first_line[:60].rsplit(" ", 1)[0]
            return words + "..."

        return first_line if len(first_line) > 3 else ""

    @staticmethod
    def _extract_key_point(content: str) -> str:
        content = content.strip()
        if not content:
            return ""

        lines = content.split("\n")
        for line in lines[:5]:
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("```"):
                continue
            if len(line) > 10:
                if len(line) > 80:
                    return line[:77] + "..."
                return line

        return ""

    @staticmethod
    def estimate_total_tokens(
        system_prompt: str, messages: list[dict], current_prompt: str
    ) -> int:
        """Estimate total tokens for a request."""
        total_chars = len(system_prompt) + len(current_prompt)
        total_chars += sum(len(m["content"]) for m in messages)
        return total_chars // 4
