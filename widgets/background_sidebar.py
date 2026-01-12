from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Button, ProgressBar, Static

from managers.background import BackgroundAgentManager, BackgroundTask, TaskStatus


class BackgroundTaskSelected(Message):
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__()


class BackgroundTaskCancelRequested(Message):
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__()


class NewBackgroundTaskRequested(Message):
    pass


class TaskItemWidget(Static):
    """Widget for a single background task."""

    STATUS_ICONS: ClassVar[dict[TaskStatus, str]] = {
        TaskStatus.QUEUED: "⏳",
        TaskStatus.RUNNING: "▶",
        TaskStatus.COMPLETED: "✓",
        TaskStatus.FAILED: "✗",
        TaskStatus.CANCELLED: "⊘",
    }

    def __init__(self, task: BackgroundTask, **kwargs):
        super().__init__(**kwargs)
        self.task = task

    def compose(self) -> ComposeResult:
        icon = self.STATUS_ICONS.get(self.task.status, "?")
        yield Static(f"{icon} {self.task.goal[:25]}...")

        if self.task.status == TaskStatus.RUNNING:
            yield ProgressBar(total=100, show_eta=False)
            yield Static(f"  {self.task.current_step}")
        elif self.task.status == TaskStatus.COMPLETED:
            yield Static(f"  Completed {self._format_duration(self.task.duration)}")
        elif self.task.status == TaskStatus.FAILED:
            error_msg = self.task.error or "Unknown error"
            yield Static(f"  [red]Failed: {error_msg[:30]}[/red]")

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s ago"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m ago"
        else:
            return f"{seconds / 3600:.0f}h ago"

    def update_task(self, task: BackgroundTask) -> None:
        self.task = task
        self.refresh()


class BackgroundTasksSidebar(Static):
    """Sidebar widget showing background agent tasks."""

    DEFAULT_CSS = """
    BackgroundTasksSidebar {
        width: 30;
        height: 100%;
        dock: right;
        border-left: solid $primary;
        background: $surface;
        padding: 1;
    }

    .sidebar-header {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    .task-item {
        margin-bottom: 1;
        padding: 0 1;
        height: auto;
    }

    .task-item:hover {
        background: $primary-darken-3;
    }

    .task-running {
        border-left: solid $warning;
    }

    .task-completed {
        border-left: solid $success;
    }

    .task-failed {
        border-left: solid $error;
    }

    .task-queued {
        border-left: solid $text-muted;
    }

    .task-cancelled {
        border-left: solid $error-darken-2;
    }

    #new-task-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, manager: BackgroundAgentManager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
        self._refresh_timer: Timer | None = None

    def on_mount(self) -> None:
        self._refresh_timer = self.set_interval(2.0, self._refresh_tasks)

    def compose(self) -> ComposeResult:
        yield Static("🔄 Background Tasks", classes="sidebar-header")

        with ScrollableContainer(id="task-list"):
            for task in self.manager.list_tasks(limit=10):
                yield TaskItemWidget(
                    task, classes=f"task-item task-{task.status.value}"
                )

        yield Button("+ New Task", id="new-task-btn")

    def _refresh_tasks(self) -> None:
        """Refresh task display."""
        try:
            task_list = self.query_one("#task-list", ScrollableContainer)
            task_list.remove_children()

            for task in self.manager.list_tasks(limit=10):
                task_list.mount(
                    TaskItemWidget(task, classes=f"task-item task-{task.status.value}")
                )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-task-btn":
            self.post_message(NewBackgroundTaskRequested())

    async def on_click(self, event) -> None:
        for widget in self.query(TaskItemWidget):
            if widget.region.contains(event.screen_x, event.screen_y):
                self.post_message(BackgroundTaskSelected(widget.task.id))
                break
