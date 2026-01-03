from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path
import uuid
import json


class BlockType(Enum):
    COMMAND = "command"
    AI_RESPONSE = "ai"
    AI_QUERY = "ai_query"
    SYSTEM_MSG = "system"
    TOOL_CALL = "tool_call"


@dataclass
class ToolCallState:
    """State for a single tool call in agent mode."""
    id: str
    tool_name: str
    arguments: str = ""
    output: str = ""
    status: str = "pending"  # pending, running, success, error
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Serialize tool call to dictionary."""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "output": self.output,
            "status": self.status,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCallState":
        """Deserialize tool call from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            tool_name=data["tool_name"],
            arguments=data.get("arguments", ""),
            output=data.get("output", ""),
            status=data.get("status", "pending"),
            duration=data.get("duration", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
        )


@dataclass
class AgentIteration:
    """Represents one think → action cycle in agent mode.

    Each iteration contains:
    - thinking: The model's reasoning for this cycle
    - tool_calls: Tools executed during this iteration
    - response_fragment: Any text response generated
    - status: Current state of the iteration
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    iteration_number: int = 0
    thinking: str = ""
    tool_calls: List[ToolCallState] = field(default_factory=list)
    response_fragment: str = ""
    status: str = "pending"  # pending, thinking, executing, waiting_approval, complete
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0

    def to_dict(self) -> dict:
        """Serialize iteration to dictionary."""
        return {
            "id": self.id,
            "iteration_number": self.iteration_number,
            "thinking": self.thinking,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "response_fragment": self.response_fragment,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentIteration":
        """Deserialize iteration from dictionary."""
        tool_calls_data = data.get("tool_calls", [])
        tool_calls = [ToolCallState.from_dict(tc) for tc in tool_calls_data]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            iteration_number=data.get("iteration_number", 0),
            thinking=data.get("thinking", ""),
            tool_calls=tool_calls,
            response_fragment=data.get("response_fragment", ""),
            status=data.get("status", "pending"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            duration=data.get("duration", 0.0)
        )


@dataclass
class BlockState:
    type: BlockType
    content_input: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    content_output: str = ""
    exit_code: Optional[int] = None
    is_running: bool = True
    metadata: Dict = field(default_factory=dict)
    content_thinking: str = ""
    content_exec_output: str = ""
    tool_calls: List["ToolCallState"] = field(default_factory=list)
    iterations: List["AgentIteration"] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize block to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "content_input": self.content_input,
            "content_output": self.content_output,
            "content_thinking": self.content_thinking,
            "content_exec_output": self.content_exec_output,
            "exit_code": self.exit_code,
            "is_running": self.is_running,
            "metadata": self.metadata,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "iterations": [it.to_dict() for it in self.iterations]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlockState":
        """Deserialize block from dictionary."""
        tool_calls_data = data.get("tool_calls", [])
        tool_calls = [ToolCallState.from_dict(tc) for tc in tool_calls_data]

        iterations_data = data.get("iterations", [])
        iterations = [AgentIteration.from_dict(it) for it in iterations_data]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=BlockType(data["type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content_input=data.get("content_input", ""),
            content_output=data.get("content_output", ""),
            content_thinking=data.get("content_thinking", ""),
            content_exec_output=data.get("content_exec_output", ""),
            exit_code=data.get("exit_code"),
            is_running=data.get("is_running", False),
            metadata=data.get("metadata", {}),
            tool_calls=tool_calls,
            iterations=iterations
        )


def export_to_json(blocks: List[BlockState]) -> str:
    """Export blocks to JSON string."""
    data = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "blocks": [block.to_dict() for block in blocks]
    }
    return json.dumps(data, indent=2)


def export_to_markdown(blocks: List[BlockState]) -> str:
    """Export blocks to formatted markdown."""
    lines = []

    # Header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"# Null Session - {timestamp}")
    lines.append("")

    for block in blocks:
        ts = block.timestamp.strftime("%H:%M:%S")

        if block.type == BlockType.COMMAND:
            lines.append(f"## Command [{ts}]")
            lines.append("")
            lines.append(f"```bash")
            lines.append(f"$ {block.content_input}")
            lines.append("```")
            if block.content_output:
                lines.append("")
                lines.append("**Output:**")
                lines.append("```")
                lines.append(block.content_output.rstrip())
                lines.append("```")
            if block.exit_code is not None and block.exit_code != 0:
                lines.append(f"*Exit code: {block.exit_code}*")
            lines.append("")

        elif block.type == BlockType.AI_RESPONSE:
            lines.append(f"## AI Conversation [{ts}]")
            lines.append("")
            lines.append(f"**User:** {block.content_input}")
            lines.append("")
            if block.content_output:
                lines.append(f"**Assistant:**")
                lines.append("")
                lines.append(block.content_output.rstrip())
            if block.content_exec_output:
                lines.append("")
                lines.append("**Executed:**")
                lines.append(block.content_exec_output.rstrip())
            if block.metadata:
                meta_parts = []
                if "model" in block.metadata:
                    meta_parts.append(f"Model: {block.metadata['model']}")
                if "tokens" in block.metadata:
                    meta_parts.append(f"Tokens: {block.metadata['tokens']}")
                if meta_parts:
                    lines.append("")
                    lines.append(f"*{' | '.join(meta_parts)}*")
            lines.append("")

        elif block.type == BlockType.AI_QUERY:
            lines.append(f"**User [{ts}]:** {block.content_input}")
            lines.append("")

        elif block.type == BlockType.TOOL_CALL:
            lines.append(f"## Tool Call [{ts}]")
            lines.append("")
            if block.metadata and "tool_name" in block.metadata:
                lines.append(f"**Tool:** {block.metadata['tool_name']}")
                if "arguments" in block.metadata:
                    lines.append("")
                    lines.append("**Arguments:**")
                    lines.append("```json")
                    lines.append(block.metadata['arguments'])
                    lines.append("```")
            if block.content_output:
                lines.append("")
                lines.append(block.content_output.rstrip())
            if block.exit_code is not None:
                status = "success" if block.exit_code == 0 else "error"
                lines.append(f"*Status: {status}*")
            lines.append("")

    lines.append("---")
    lines.append("*Exported from Null Terminal*")

    return "\n".join(lines)


def save_export(blocks: List[BlockState], format: str = "md") -> Path:
    """Save export to file and return path."""
    export_dir = Path.home() / ".null" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if format == "json":
        filename = f"null-export-{timestamp}.json"
        content = export_to_json(blocks)
    else:
        filename = f"null-export-{timestamp}.md"
        content = export_to_markdown(blocks)

    filepath = export_dir / filename
    filepath.write_text(content, encoding="utf-8")

    return filepath
