import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import asyncio


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class AgentSession:
    id: str
    started_at: datetime
    ended_at: datetime | None = None
    iterations: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    state: AgentState = AgentState.IDLE
    current_task: str = ""
    errors: list[str] = field(default_factory=list)
    tool_history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def is_active(self) -> bool:
        return self.state not in (AgentState.IDLE, AgentState.CANCELLED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
            "iterations": self.iterations,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "state": self.state.value,
            "current_task": self.current_task,
            "errors": self.errors,
            "tool_history": self.tool_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSession":
        return cls(
            id=data["id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"])
            if data.get("ended_at")
            else None,
            iterations=data.get("iterations", 0),
            tool_calls=data.get("tool_calls", 0),
            tokens_used=data.get("tokens_used", 0),
            state=AgentState(data.get("state", "idle")),
            current_task=data.get("current_task", ""),
            errors=data.get("errors", []),
            tool_history=data.get("tool_history", []),
        )


@dataclass
class AgentStats:
    total_sessions: int = 0
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    total_duration: float = 0.0
    tool_usage: dict[str, int] = field(default_factory=dict)
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_iterations": self.total_iterations,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens": self.total_tokens,
            "total_duration": self.total_duration,
            "tool_usage": self.tool_usage,
            "error_count": self.error_count,
            "avg_iterations_per_session": self.total_iterations
            / max(1, self.total_sessions),
            "avg_tools_per_session": self.total_tool_calls
            / max(1, self.total_sessions),
        }


class AgentManager:
    def __init__(self):
        self._current_session: AgentSession | None = None
        self._session_history: list[AgentSession] = []
        self._stats = AgentStats()
        self._cancel_requested = False
        self._pause_requested = False
        self._max_history = 50

        self._state_callbacks: list[Any] = []

    @property
    def is_active(self) -> bool:
        return self._current_session is not None and self._current_session.is_active

    @property
    def current_session(self) -> AgentSession | None:
        return self._current_session

    @property
    def state(self) -> AgentState:
        if self._current_session:
            return self._current_session.state
        return AgentState.IDLE

    @property
    def stats(self) -> AgentStats:
        return self._stats

    def start_session(self, task: str) -> AgentSession:
        if self._current_session and self._current_session.is_active:
            self.end_session()

        import uuid

        session = AgentSession(
            id=str(uuid.uuid4())[:8],
            started_at=datetime.now(),
            current_task=task,
            state=AgentState.THINKING,
        )
        self._current_session = session
        self._cancel_requested = False
        self._pause_requested = False
        self._notify_state_change()
        return session

    def end_session(self, cancelled: bool = False):
        if not self._current_session:
            return

        session = self._current_session
        session.ended_at = datetime.now()
        session.state = AgentState.CANCELLED if cancelled else AgentState.IDLE

        self._stats.total_sessions += 1
        self._stats.total_iterations += session.iterations
        self._stats.total_tool_calls += session.tool_calls
        self._stats.total_tokens += session.tokens_used
        self._stats.total_duration += session.duration
        self._stats.error_count += len(session.errors)

        self._session_history.append(session)
        if len(self._session_history) > self._max_history:
            self._session_history.pop(0)

        self._current_session = None
        self._notify_state_change()

    def update_state(self, state: AgentState):
        if self._current_session:
            self._current_session.state = state
            self._notify_state_change()

    def record_iteration(self):
        if self._current_session:
            self._current_session.iterations += 1

    def record_tool_call(
        self, tool_name: str, args: str, result: str, success: bool, duration: float
    ):
        if self._current_session:
            self._current_session.tool_calls += 1
            self._current_session.tool_history.append(
                {
                    "tool": tool_name,
                    "args": args[:200],
                    "result": result[:500],
                    "success": success,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self._stats.tool_usage[tool_name] = (
                self._stats.tool_usage.get(tool_name, 0) + 1
            )

            if not success:
                self._current_session.errors.append(f"Tool {tool_name} failed")

    def record_tokens(self, tokens: int):
        if self._current_session:
            self._current_session.tokens_used += tokens

    def record_error(self, error: str):
        if self._current_session:
            self._current_session.errors.append(error)

    def request_cancel(self):
        self._cancel_requested = True
        if self._current_session:
            self._current_session.state = AgentState.CANCELLED
        self._notify_state_change()

    def request_pause(self):
        self._pause_requested = True
        if self._current_session:
            self._current_session.state = AgentState.PAUSED
        self._notify_state_change()

    def resume(self):
        self._pause_requested = False
        if self._current_session and self._current_session.state == AgentState.PAUSED:
            self._current_session.state = AgentState.THINKING
        self._notify_state_change()

    def should_cancel(self) -> bool:
        return self._cancel_requested

    def should_pause(self) -> bool:
        return self._pause_requested

    def get_history(self, limit: int = 10) -> list[AgentSession]:
        return self._session_history[-limit:]

    def get_current_tool_history(self) -> list[dict[str, Any]]:
        if self._current_session:
            return self._current_session.tool_history
        return []

    def get_status(self) -> dict[str, Any]:
        session_info = None
        if self._current_session:
            session_info = {
                "id": self._current_session.id,
                "task": self._current_session.current_task[:100],
                "state": self._current_session.state.value,
                "iterations": self._current_session.iterations,
                "tool_calls": self._current_session.tool_calls,
                "duration": self._current_session.duration,
                "errors": len(self._current_session.errors),
            }

        return {
            "active": self.is_active,
            "state": self.state.value,
            "current_session": session_info,
            "history_count": len(self._session_history),
            "stats": self._stats.to_dict(),
        }

    def clear_history(self):
        self._session_history.clear()

    def reset_stats(self):
        self._stats = AgentStats()

    def add_state_callback(self, callback):
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback):
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _notify_state_change(self):
        for callback in self._state_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(self.state))
                else:
                    callback(self.state)
            except Exception:
                pass

    def _get_sessions_dir(self) -> Path:
        sessions_dir = Path.home() / ".null" / "agent_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

    def save_session(self, session: AgentSession, name: str | None = None) -> Path:
        """Save an agent session to disk."""
        sessions_dir = self._get_sessions_dir()

        if name:
            filename = f"agent-{name}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"agent-{session.id}-{timestamp}.json"

        filepath = sessions_dir / filename
        filepath.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        return filepath

    def save_current_session(self, name: str | None = None) -> Path | None:
        """Save the current session if active."""
        if self._current_session:
            return self.save_session(self._current_session, name)
        return None

    def load_session(self, name_or_id: str) -> AgentSession | None:
        """Load a session by name or ID."""
        sessions_dir = self._get_sessions_dir()

        for pattern in [f"agent-{name_or_id}.json", f"agent-{name_or_id}-*.json"]:
            matches = list(sessions_dir.glob(pattern))
            if matches:
                filepath = sorted(matches, reverse=True)[0]
                try:
                    data = json.loads(filepath.read_text(encoding="utf-8"))
                    return AgentSession.from_dict(data)
                except Exception:
                    return None
        return None

    def list_saved_sessions(self) -> list[dict[str, Any]]:
        """List all saved agent sessions."""
        sessions = []
        sessions_dir = self._get_sessions_dir()

        for filepath in sorted(sessions_dir.glob("agent-*.json"), reverse=True):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                sessions.append(
                    {
                        "id": data.get("id", ""),
                        "task": data.get("current_task", "")[:50],
                        "started_at": data.get("started_at", ""),
                        "iterations": data.get("iterations", 0),
                        "tool_calls": data.get("tool_calls", 0),
                        "path": str(filepath),
                    }
                )
            except Exception:
                pass

        return sessions[:20]

    def delete_saved_session(self, name_or_id: str) -> bool:
        """Delete a saved session."""
        sessions_dir = self._get_sessions_dir()

        for pattern in [f"agent-{name_or_id}.json", f"agent-{name_or_id}-*.json"]:
            for filepath in sessions_dir.glob(pattern):
                filepath.unlink()
                return True
        return False

    def export_session_to_markdown(self, session: AgentSession) -> str:
        """Export session to markdown format for review."""
        lines = [
            f"# Agent Session: {session.id}",
            f"**Task:** {session.current_task}",
            f"**Started:** {session.started_at.isoformat()}",
            f"**Duration:** {session.duration:.1f}s",
            f"**Iterations:** {session.iterations}",
            f"**Tool Calls:** {session.tool_calls}",
            "",
            "## Tool History",
            "",
        ]

        for i, call in enumerate(session.tool_history, 1):
            lines.append(f"### {i}. {call.get('tool', 'Unknown')}")
            lines.append(f"**Args:** `{call.get('args', '')[:100]}`")
            lines.append(f"**Success:** {call.get('success', False)}")
            lines.append(f"**Duration:** {call.get('duration', 0):.2f}s")
            lines.append(f"```\n{call.get('result', '')[:500]}\n```")
            lines.append("")

        if session.errors:
            lines.append("## Errors")
            for error in session.errors:
                lines.append(f"- {error}")

        return "\n".join(lines)
