from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class AIBackground(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_bg(self, args: list[str]):
        """Background agents. Usage: /bg <goal> | /bg list | /bg status <id> | /bg cancel <id> | /bg logs <id> | /bg clear"""
        from managers.background import BackgroundAgentManager, TaskStatus

        manager: BackgroundAgentManager = (
            getattr(self.app, "background_manager", None) or BackgroundAgentManager()
        )
        if not hasattr(self.app, "background_manager"):
            object.__setattr__(self.app, "background_manager", manager)

        if not args:
            await self._bg_list(manager)
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            await self._bg_list(manager)
        elif subcommand == "status":
            if len(args) > 1:
                await self._bg_status(manager, args[1])
            else:
                self.notify("Usage: /bg status <task_id>", severity="warning")
        elif subcommand == "cancel":
            if len(args) > 1:
                await self._bg_cancel(manager, args[1])
            else:
                self.notify("Usage: /bg cancel <task_id>", severity="warning")
        elif subcommand == "logs":
            if len(args) > 1:
                await self._bg_logs(manager, args[1])
            else:
                self.notify("Usage: /bg logs <task_id>", severity="warning")
        elif subcommand == "clear":
            await self._bg_clear(manager)
        else:
            goal = " ".join(args)
            await self._bg_spawn(manager, goal)

    async def _bg_list(self, manager):
        from managers.background import TaskStatus

        tasks = manager.list_tasks(limit=20)
        if not tasks:
            self.notify("No background tasks")
            return

        lines = [
            f"Background Tasks (active: {manager.active_count}, queued: {manager.queued_count})",
            "",
        ]

        for task in tasks:
            lines.append(task.summary)
            if task.status == TaskStatus.RUNNING:
                lines.append(
                    f"  Progress: {task.progress * 100:.0f}% - {task.current_step}"
                )

        await self.show_output("/bg list", "\n".join(lines))

    async def _bg_status(self, manager, task_id: str):
        from managers.background import TaskStatus

        task = manager.get_task(task_id)
        if not task:
            self.notify(f"Task not found: {task_id}", severity="error")
            return

        lines = [
            f"Task: {task.id}",
            f"Goal: {task.goal}",
            f"Status: {task.status.value}",
            f"Progress: {task.progress * 100:.0f}%",
            f"Duration: {task.duration:.1f}s",
        ]

        if task.current_step:
            lines.append(f"Current: {task.current_step}")
        if task.result:
            lines.append(f"\nResult:\n{task.result[:500]}")
        if task.error:
            lines.append(f"\nError: {task.error}")

        await self.show_output(f"/bg status {task_id}", "\n".join(lines))

    async def _bg_cancel(self, manager, task_id: str):
        if manager.cancel_task(task_id):
            self.notify(f"Cancelled task: {task_id}")
        else:
            self.notify(f"Could not cancel task: {task_id}", severity="error")

    async def _bg_logs(self, manager, task_id: str):
        task = manager.get_task(task_id)
        if not task:
            self.notify(f"Task not found: {task_id}", severity="error")
            return

        if not task.logs:
            self.notify(f"No logs for task: {task_id}")
            return

        await self.show_output(f"/bg logs {task_id}", "\n".join(task.logs[-50:]))

    async def _bg_clear(self, manager):
        count = manager.clear_completed()
        self.notify(f"Cleared {count} completed tasks")

    async def _bg_spawn(self, manager, goal: str):
        if not self.app.ai_provider:
            self.notify("No AI provider configured", severity="error")
            return

        task = await manager.spawn(goal, self.app.ai_provider)
        self.notify(f"Started background task: {task.id}")
