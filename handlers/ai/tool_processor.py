"""Tool call processing utilities."""

from __future__ import annotations

import json
from typing import Any

from ai.base import Message


def build_assistant_tool_message(
    response_text: str,
    tool_calls: list[Any],
) -> Message:
    return {
        "role": "assistant",
        "content": response_text,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
            for tc in tool_calls
        ],
    }


def build_tool_result_message(tool_call_id: str, content: str) -> Message:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def append_tool_messages(
    messages: list[Message],
    response_text: str,
    tool_calls: list[Any],
    tool_results: list[Any],
) -> None:
    messages.append(build_assistant_tool_message(response_text, tool_calls))
    for result in tool_results:
        messages.append(build_tool_result_message(result.tool_call_id, result.content))
