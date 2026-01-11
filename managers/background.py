from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai.base import LLMProvider


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    id: str
    goal: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: str | None = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)
    current_step: str = ""

    @classmethod
    def create(cls, goal: str) -> BackgroundTask:
        return cls(
            id=str(uuid.uuid4())[:8],
            goal=goal,
        )

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

    @property
    def duration(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def summary(self) -> str:
        status_icon = {
            TaskStatus.QUEUED: "⏳",
            TaskStatus.RUNNING: "▶",
            TaskStatus.COMPLETED: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.CANCELLED: "⊘",
        }.get(self.status, "?")

        return f"{status_icon} {self.id}: {self.goal[:40]}{'...' if len(self.goal) > 40 else ''}"


class BackgroundAgentManager:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.tasks: dict[str, BackgroundTask] = {}
        self._running_tasks: dict[str, asyncio.Task[None]] = {}
        self._on_complete_callbacks: list[Any] = []

    @property
    def active_count(self) -> int:
        return sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)

    @property
    def queued_count(self) -> int:
        return sum(1 for t in self.tasks.values() if t.status == TaskStatus.QUEUED)

    async def spawn(
        self,
        goal: str,
        provider: LLMProvider,
        tools: list[dict[str, Any]] | None = None,
    ) -> BackgroundTask:
        task = BackgroundTask.create(goal)
        self.tasks[task.id] = task

        if self.active_count < self.max_concurrent:
            await self._start_task(task, provider, tools)
        else:
            task.log("Task queued - waiting for available slot")

        return task

    async def _start_task(
        self,
        task: BackgroundTask,
        provider: LLMProvider,
        tools: list[dict[str, Any]] | None = None,
    ):
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.log("Task started")

        async_task = asyncio.create_task(self._run_task(task, provider, tools))
        self._running_tasks[task.id] = async_task

    async def _run_task(
        self,
        task: BackgroundTask,
        provider: LLMProvider,
        tools: list[dict[str, Any]] | None = None,
    ):
        try:
            task.current_step = "Analyzing goal..."
            task.progress = 0.1
            task.log("Analyzing goal")

            prompt = f"""You are an autonomous agent working on a background task.

Goal: {task.goal}

Work step by step to complete this goal. Be thorough but efficient.
Report what you're doing at each step."""

            response = ""
            async for chunk in provider.generate(prompt, []):  # type: ignore[attr-defined]
                response += chunk
                task.progress = min(0.9, task.progress + 0.05)

            task.result = response
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.completed_at = datetime.now()
            task.log("Task completed successfully")

            for callback in self._on_complete_callbacks:
                try:
                    callback(task)
                except Exception:
                    pass

        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.log("Task cancelled")
            raise

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            task.log(f"Task failed: {e}")

        finally:
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]

            await self._process_queue(provider, tools)

    async def _process_queue(
        self,
        provider: LLMProvider,
        tools: list[dict[str, Any]] | None = None,
    ):
        if self.active_count >= self.max_concurrent:
            return

        for task in self.tasks.values():
            if task.status == TaskStatus.QUEUED:
                await self._start_task(task, provider, tools)
                break

    async def cancel(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.QUEUED:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.log("Task cancelled before starting")
            return True

        if task.status == TaskStatus.RUNNING:
            async_task = self._running_tasks.get(task_id)
            if async_task:
                async_task.cancel()
                try:
                    await async_task
                except asyncio.CancelledError:
                    pass
            return True

        return False

    def get_task(self, task_id: str) -> BackgroundTask | None:
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 20,
    ) -> list[BackgroundTask]:
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks.sort(key=lambda t: t.started_at or datetime.min, reverse=True)
        return tasks[:limit]

    def get_logs(self, task_id: str) -> list[str]:
        task = self.tasks.get(task_id)
        return task.logs if task else []

    def on_complete(self, callback: Any):
        self._on_complete_callbacks.append(callback)

    def clear_completed(self):
        to_remove = [
            tid
            for tid, task in self.tasks.items()
            if task.status
            in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        for tid in to_remove:
            del self.tasks[tid]

    def get_status_summary(self) -> str:
        running = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
        queued = sum(1 for t in self.tasks.values() if t.status == TaskStatus.QUEUED)
        completed = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED
        )
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

        parts = []
        if running:
            parts.append(f"{running} running")
        if queued:
            parts.append(f"{queued} queued")
        if completed:
            parts.append(f"{completed} completed")
        if failed:
            parts.append(f"{failed} failed")

        return ", ".join(parts) if parts else "No tasks"
