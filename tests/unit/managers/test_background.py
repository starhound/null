import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from managers.background import (
    BackgroundAgentManager,
    BackgroundTask,
    TaskStatus,
)


class TestTaskStatusEnum:
    def test_queued_value(self):
        assert TaskStatus.QUEUED.value == "queued"

    def test_running_value(self):
        assert TaskStatus.RUNNING.value == "running"

    def test_completed_value(self):
        assert TaskStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert TaskStatus.FAILED.value == "failed"

    def test_cancelled_value(self):
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_all_statuses_exist(self):
        statuses = [
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]
        assert len(statuses) == 5


class TestBackgroundTaskCreate:
    def test_create_basic(self):
        task = BackgroundTask.create("Test goal")
        assert task.goal == "Test goal"
        assert task.status == TaskStatus.QUEUED
        assert task.progress == 0.0
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None
        assert task.logs == []
        assert task.current_step == ""

    def test_create_generates_id(self):
        task = BackgroundTask.create("Goal")
        assert task.id is not None
        assert len(task.id) == 8
        assert isinstance(task.id, str)

    def test_create_unique_ids(self):
        task1 = BackgroundTask.create("Goal 1")
        task2 = BackgroundTask.create("Goal 2")
        assert task1.id != task2.id

    def test_create_with_long_goal(self):
        long_goal = "x" * 200
        task = BackgroundTask.create(long_goal)
        assert task.goal == long_goal


class TestBackgroundTaskLog:
    def test_log_single_message(self):
        task = BackgroundTask.create("Goal")
        task.log("Test message")
        assert len(task.logs) == 1
        assert "Test message" in task.logs[0]
        assert "[" in task.logs[0]
        assert "]" in task.logs[0]

    def test_log_multiple_messages(self):
        task = BackgroundTask.create("Goal")
        task.log("Message 1")
        task.log("Message 2")
        task.log("Message 3")
        assert len(task.logs) == 3

    def test_log_includes_timestamp(self):
        task = BackgroundTask.create("Goal")
        task.log("Timestamped message")
        log_entry = task.logs[0]
        assert "[" in log_entry
        assert "]" in log_entry
        assert ":" in log_entry

    def test_log_format(self):
        task = BackgroundTask.create("Goal")
        task.log("Test")
        log_entry = task.logs[0]
        assert log_entry.startswith("[")
        assert "] Test" in log_entry

    def test_log_empty_message(self):
        task = BackgroundTask.create("Goal")
        task.log("")
        assert len(task.logs) == 1
        assert task.logs[0].endswith("] ")


class TestBackgroundTaskDuration:
    def test_duration_no_started_at(self):
        task = BackgroundTask.create("Goal")
        assert task.duration == 0.0

    def test_duration_with_started_at_no_completed_at(self):
        task = BackgroundTask.create("Goal")
        task.started_at = datetime.now() - timedelta(seconds=5)
        duration = task.duration
        assert 4.0 < duration < 6.0

    def test_duration_with_both_timestamps(self):
        task = BackgroundTask.create("Goal")
        task.started_at = datetime.now() - timedelta(seconds=10)
        task.completed_at = task.started_at + timedelta(seconds=5)
        assert 4.9 < task.duration < 5.1

    def test_duration_zero_when_same_time(self):
        task = BackgroundTask.create("Goal")
        now = datetime.now()
        task.started_at = now
        task.completed_at = now
        assert task.duration == 0.0

    def test_duration_fractional_seconds(self):
        task = BackgroundTask.create("Goal")
        task.started_at = datetime.now()
        task.completed_at = task.started_at + timedelta(milliseconds=500)
        assert 0.4 < task.duration < 0.6


class TestBackgroundTaskSummary:
    def test_summary_queued(self):
        task = BackgroundTask.create("Test goal")
        task.status = TaskStatus.QUEUED
        summary = task.summary
        assert "⏳" in summary
        assert task.id in summary
        assert "Test goal" in summary

    def test_summary_running(self):
        task = BackgroundTask.create("Test goal")
        task.status = TaskStatus.RUNNING
        summary = task.summary
        assert "▶" in summary
        assert task.id in summary

    def test_summary_completed(self):
        task = BackgroundTask.create("Test goal")
        task.status = TaskStatus.COMPLETED
        summary = task.summary
        assert "✓" in summary
        assert task.id in summary

    def test_summary_failed(self):
        task = BackgroundTask.create("Test goal")
        task.status = TaskStatus.FAILED
        summary = task.summary
        assert "✗" in summary
        assert task.id in summary

    def test_summary_cancelled(self):
        task = BackgroundTask.create("Test goal")
        task.status = TaskStatus.CANCELLED
        summary = task.summary
        assert "⊘" in summary
        assert task.id in summary

    def test_summary_truncates_long_goal(self):
        long_goal = "x" * 100
        task = BackgroundTask.create(long_goal)
        summary = task.summary
        assert "..." in summary
        assert len(summary) < len(long_goal)

    def test_summary_no_truncation_short_goal(self):
        task = BackgroundTask.create("Short")
        summary = task.summary
        assert "..." not in summary
        assert "Short" in summary

    def test_summary_exactly_40_chars(self):
        goal = "x" * 40
        task = BackgroundTask.create(goal)
        summary = task.summary
        assert "..." not in summary

    def test_summary_41_chars_truncated(self):
        goal = "x" * 41
        task = BackgroundTask.create(goal)
        summary = task.summary
        assert "..." in summary


class TestBackgroundAgentManagerInit:
    def test_init_default_max_concurrent(self):
        manager = BackgroundAgentManager()
        assert manager.max_concurrent == 3

    def test_init_custom_max_concurrent(self):
        manager = BackgroundAgentManager(max_concurrent=5)
        assert manager.max_concurrent == 5

    def test_init_max_concurrent_one(self):
        manager = BackgroundAgentManager(max_concurrent=1)
        assert manager.max_concurrent == 1

    def test_init_empty_tasks(self):
        manager = BackgroundAgentManager()
        assert manager.tasks == {}

    def test_init_empty_running_tasks(self):
        manager = BackgroundAgentManager()
        assert manager._running_tasks == {}

    def test_init_empty_callbacks(self):
        manager = BackgroundAgentManager()
        assert manager._on_complete_callbacks == []


class TestBackgroundAgentManagerActiveCount:
    def test_active_count_empty(self):
        manager = BackgroundAgentManager()
        assert manager.active_count == 0

    def test_active_count_single_running(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.RUNNING
        manager.tasks[task.id] = task
        assert manager.active_count == 1

    def test_active_count_multiple_running(self):
        manager = BackgroundAgentManager()
        for i in range(3):
            task = BackgroundTask.create(f"Goal {i}")
            task.status = TaskStatus.RUNNING
            manager.tasks[task.id] = task
        assert manager.active_count == 3

    def test_active_count_ignores_queued(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.QUEUED
        manager.tasks[task.id] = task
        assert manager.active_count == 0

    def test_active_count_ignores_completed(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.COMPLETED
        manager.tasks[task.id] = task
        assert manager.active_count == 0

    def test_active_count_mixed_statuses(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.RUNNING
        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.QUEUED
        task3 = BackgroundTask.create("Goal 3")
        task3.status = TaskStatus.COMPLETED
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2
        manager.tasks[task3.id] = task3
        assert manager.active_count == 1


class TestBackgroundAgentManagerQueuedCount:
    def test_queued_count_empty(self):
        manager = BackgroundAgentManager()
        assert manager.queued_count == 0

    def test_queued_count_single(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.QUEUED
        manager.tasks[task.id] = task
        assert manager.queued_count == 1

    def test_queued_count_multiple(self):
        manager = BackgroundAgentManager()
        for i in range(3):
            task = BackgroundTask.create(f"Goal {i}")
            task.status = TaskStatus.QUEUED
            manager.tasks[task.id] = task
        assert manager.queued_count == 3

    def test_queued_count_ignores_running(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.RUNNING
        manager.tasks[task.id] = task
        assert manager.queued_count == 0

    def test_queued_count_mixed_statuses(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.RUNNING
        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.QUEUED
        task3 = BackgroundTask.create("Goal 3")
        task3.status = TaskStatus.QUEUED
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2
        manager.tasks[task3.id] = task3
        assert manager.queued_count == 2


@pytest.mark.asyncio
class TestBackgroundAgentManagerSpawn:
    async def test_spawn_under_limit_starts_immediately(self):
        manager = BackgroundAgentManager(max_concurrent=3)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        task = await manager.spawn("Test goal", mock_provider)
        assert task.goal == "Test goal"
        assert task.id in manager.tasks
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    async def test_spawn_at_limit_queues_task(self):
        manager = BackgroundAgentManager(max_concurrent=1)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            await asyncio.sleep(0.1)
            yield "response"

        mock_provider.generate = mock_generate

        task1 = await manager.spawn("Goal 1", mock_provider)
        task2 = await manager.spawn("Goal 2", mock_provider)

        assert task1.status == TaskStatus.RUNNING
        assert task2.status == TaskStatus.QUEUED

    async def test_spawn_returns_task(self):
        manager = BackgroundAgentManager()
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        task = await manager.spawn("Goal", mock_provider)
        assert isinstance(task, BackgroundTask)
        assert task.goal == "Goal"

    async def test_spawn_adds_to_tasks(self):
        manager = BackgroundAgentManager()
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        task = await manager.spawn("Goal", mock_provider)
        assert task.id in manager.tasks
        assert manager.tasks[task.id] == task

    async def test_spawn_with_tools(self):
        manager = BackgroundAgentManager()
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        tools = [{"name": "test_tool", "description": "Test"}]
        task = await manager.spawn("Goal", mock_provider, tools=tools)
        assert task.id in manager.tasks


@pytest.mark.asyncio
class TestBackgroundAgentManagerStartTask:
    async def test_start_task_sets_status_running(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        await manager._start_task(task, mock_provider)
        assert task.status == TaskStatus.RUNNING

    async def test_start_task_sets_started_at(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        before = datetime.now()
        await manager._start_task(task, mock_provider)
        after = datetime.now()

        assert task.started_at is not None
        assert before <= task.started_at <= after

    async def test_start_task_creates_asyncio_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        await manager._start_task(task, mock_provider)
        assert task.id in manager._running_tasks
        assert isinstance(manager._running_tasks[task.id], asyncio.Task)

    async def test_start_task_logs_message(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        await manager._start_task(task, mock_provider)
        assert len(task.logs) > 0
        assert "Task started" in task.logs[0]


@pytest.mark.asyncio
class TestBackgroundAgentManagerRunTask:
    async def test_run_task_success_path(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response chunk 1"
            yield " response chunk 2"

        mock_provider.generate = mock_generate

        await manager._run_task(task, mock_provider)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "response chunk 1 response chunk 2"
        assert task.completed_at is not None
        assert task.progress == 1.0

    async def test_run_task_sets_progress(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            for i in range(5):
                yield f"chunk {i}"

        mock_provider.generate = mock_generate

        await manager._run_task(task, mock_provider)
        assert task.progress == 1.0

    async def test_run_task_exception_path(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            if False:
                yield
            raise ValueError("Test error")

        mock_provider.generate = mock_generate

        await manager._run_task(task, mock_provider)
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error"
        assert task.completed_at is not None

    async def test_run_task_cancelled_path(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            await asyncio.sleep(10)
            yield "response"

        mock_provider.generate = mock_generate

        async_task = asyncio.create_task(manager._run_task(task, mock_provider))
        await asyncio.sleep(0.01)
        async_task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await async_task

        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    async def test_run_task_removes_from_running_tasks(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        manager._running_tasks[task.id] = asyncio.current_task()
        await manager._run_task(task, mock_provider)
        assert task.id not in manager._running_tasks

    async def test_run_task_calls_on_complete_callbacks(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()
        callback = MagicMock()
        manager.on_complete(callback)

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        await manager._run_task(task, mock_provider)
        callback.assert_called_once_with(task)

    async def test_run_task_callback_exception_ignored(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        def bad_callback(t):
            raise RuntimeError("Callback error")

        manager.on_complete(bad_callback)

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        await manager._run_task(task, mock_provider)
        assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
class TestBackgroundAgentManagerProcessQueue:
    async def test_process_queue_starts_queued_task(self):
        manager = BackgroundAgentManager(max_concurrent=2)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.RUNNING
        manager.tasks[task1.id] = task1
        manager._running_tasks[task1.id] = asyncio.current_task()

        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.QUEUED
        manager.tasks[task2.id] = task2

        await manager._process_queue(mock_provider)
        assert task2.status == TaskStatus.RUNNING

    async def test_process_queue_respects_limit(self):
        manager = BackgroundAgentManager(max_concurrent=1)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.RUNNING
        manager.tasks[task1.id] = task1
        manager._running_tasks[task1.id] = asyncio.current_task()

        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.QUEUED
        manager.tasks[task2.id] = task2

        await manager._process_queue(mock_provider)
        assert task2.status == TaskStatus.QUEUED

    async def test_process_queue_no_queued_tasks(self):
        manager = BackgroundAgentManager()
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.RUNNING
        manager.tasks[task.id] = task

        await manager._process_queue(mock_provider)
        assert task.status == TaskStatus.RUNNING


@pytest.mark.asyncio
class TestBackgroundAgentManagerCancel:
    async def test_cancel_queued_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.QUEUED
        manager.tasks[task.id] = task

        result = await manager.cancel(task.id)
        assert result is True
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    async def test_cancel_running_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.RUNNING

        async def long_task():
            await asyncio.sleep(10)

        async_task = asyncio.create_task(long_task())
        manager.tasks[task.id] = task
        manager._running_tasks[task.id] = async_task

        result = await manager.cancel(task.id)
        assert result is True
        assert async_task.cancelled()

    async def test_cancel_completed_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.COMPLETED
        manager.tasks[task.id] = task

        result = await manager.cancel(task.id)
        assert result is False

    async def test_cancel_failed_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.FAILED
        manager.tasks[task.id] = task

        result = await manager.cancel(task.id)
        assert result is False

    async def test_cancel_nonexistent_task(self):
        manager = BackgroundAgentManager()
        result = await manager.cancel("nonexistent")
        assert result is False

    async def test_cancel_logs_message(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.QUEUED
        manager.tasks[task.id] = task

        await manager.cancel(task.id)
        assert len(task.logs) > 0
        assert "cancelled" in task.logs[0].lower()


class TestBackgroundAgentManagerGetTask:
    def test_get_task_exists(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        manager.tasks[task.id] = task

        found = manager.get_task(task.id)
        assert found == task

    def test_get_task_not_exists(self):
        manager = BackgroundAgentManager()
        found = manager.get_task("nonexistent")
        assert found is None

    def test_get_task_multiple_tasks(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task2 = BackgroundTask.create("Goal 2")
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2

        found = manager.get_task(task1.id)
        assert found == task1


class TestBackgroundAgentManagerListTasks:
    def test_list_tasks_empty(self):
        manager = BackgroundAgentManager()
        tasks = manager.list_tasks()
        assert tasks == []

    def test_list_tasks_all(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task2 = BackgroundTask.create("Goal 2")
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2

        tasks = manager.list_tasks()
        assert len(tasks) == 2

    def test_list_tasks_with_status_filter(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.RUNNING
        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.QUEUED
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2

        running_tasks = manager.list_tasks(status=TaskStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0] == task1

    def test_list_tasks_with_limit(self):
        manager = BackgroundAgentManager()
        for i in range(5):
            task = BackgroundTask.create(f"Goal {i}")
            manager.tasks[task.id] = task

        tasks = manager.list_tasks(limit=2)
        assert len(tasks) == 2

    def test_list_tasks_sorted_by_started_at(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.started_at = datetime.now() - timedelta(seconds=10)
        task2 = BackgroundTask.create("Goal 2")
        task2.started_at = datetime.now()
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2

        tasks = manager.list_tasks()
        assert tasks[0] == task2
        assert tasks[1] == task1

    def test_list_tasks_none_started_at_last(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.started_at = datetime.now()
        task2 = BackgroundTask.create("Goal 2")
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2

        tasks = manager.list_tasks()
        assert tasks[0] == task1
        assert tasks[1] == task2

    def test_list_tasks_default_limit(self):
        manager = BackgroundAgentManager()
        for i in range(30):
            task = BackgroundTask.create(f"Goal {i}")
            manager.tasks[task.id] = task

        tasks = manager.list_tasks()
        assert len(tasks) == 20


class TestBackgroundAgentManagerGetLogs:
    def test_get_logs_exists(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.log("Message 1")
        task.log("Message 2")
        manager.tasks[task.id] = task

        logs = manager.get_logs(task.id)
        assert len(logs) == 2
        assert "Message 1" in logs[0]
        assert "Message 2" in logs[1]

    def test_get_logs_not_exists(self):
        manager = BackgroundAgentManager()
        logs = manager.get_logs("nonexistent")
        assert logs == []

    def test_get_logs_empty_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        manager.tasks[task.id] = task

        logs = manager.get_logs(task.id)
        assert logs == []


class TestBackgroundAgentManagerOnComplete:
    def test_on_complete_registers_callback(self):
        manager = BackgroundAgentManager()
        callback = MagicMock()
        manager.on_complete(callback)
        assert callback in manager._on_complete_callbacks

    def test_on_complete_multiple_callbacks(self):
        manager = BackgroundAgentManager()
        callback1 = MagicMock()
        callback2 = MagicMock()
        manager.on_complete(callback1)
        manager.on_complete(callback2)
        assert len(manager._on_complete_callbacks) == 2

    @pytest.mark.asyncio
    async def test_on_complete_callback_executed(self):
        manager = BackgroundAgentManager()
        callback = MagicMock()
        manager.on_complete(callback)

        task = BackgroundTask.create("Goal")
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "response"

        mock_provider.generate = mock_generate

        await manager._run_task(task, mock_provider)
        callback.assert_called_once()


class TestBackgroundAgentManagerClearCompleted:
    def test_clear_completed_removes_completed(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.COMPLETED
        manager.tasks[task.id] = task

        manager.clear_completed()
        assert task.id not in manager.tasks

    def test_clear_completed_removes_failed(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.FAILED
        manager.tasks[task.id] = task

        manager.clear_completed()
        assert task.id not in manager.tasks

    def test_clear_completed_removes_cancelled(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.CANCELLED
        manager.tasks[task.id] = task

        manager.clear_completed()
        assert task.id not in manager.tasks

    def test_clear_completed_keeps_running(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.RUNNING
        manager.tasks[task.id] = task

        manager.clear_completed()
        assert task.id in manager.tasks

    def test_clear_completed_keeps_queued(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.QUEUED
        manager.tasks[task.id] = task

        manager.clear_completed()
        assert task.id in manager.tasks

    def test_clear_completed_mixed_statuses(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.COMPLETED
        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.RUNNING
        task3 = BackgroundTask.create("Goal 3")
        task3.status = TaskStatus.FAILED
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2
        manager.tasks[task3.id] = task3

        manager.clear_completed()
        assert task1.id not in manager.tasks
        assert task2.id in manager.tasks
        assert task3.id not in manager.tasks

    def test_clear_completed_empty(self):
        manager = BackgroundAgentManager()
        manager.clear_completed()
        assert manager.tasks == {}


class TestBackgroundAgentManagerGetStatusSummary:
    def test_get_status_summary_empty(self):
        manager = BackgroundAgentManager()
        summary = manager.get_status_summary()
        assert summary == "No tasks"

    def test_get_status_summary_running_only(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.RUNNING
        manager.tasks[task.id] = task

        summary = manager.get_status_summary()
        assert "1 running" in summary

    def test_get_status_summary_queued_only(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.QUEUED
        manager.tasks[task.id] = task

        summary = manager.get_status_summary()
        assert "1 queued" in summary

    def test_get_status_summary_completed_only(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.COMPLETED
        manager.tasks[task.id] = task

        summary = manager.get_status_summary()
        assert "1 completed" in summary

    def test_get_status_summary_failed_only(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.FAILED
        manager.tasks[task.id] = task

        summary = manager.get_status_summary()
        assert "1 failed" in summary

    def test_get_status_summary_multiple_statuses(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask.create("Goal 1")
        task1.status = TaskStatus.RUNNING
        task2 = BackgroundTask.create("Goal 2")
        task2.status = TaskStatus.QUEUED
        task3 = BackgroundTask.create("Goal 3")
        task3.status = TaskStatus.COMPLETED
        manager.tasks[task1.id] = task1
        manager.tasks[task2.id] = task2
        manager.tasks[task3.id] = task3

        summary = manager.get_status_summary()
        assert "1 running" in summary
        assert "1 queued" in summary
        assert "1 completed" in summary

    def test_get_status_summary_multiple_counts(self):
        manager = BackgroundAgentManager()
        for i in range(2):
            task = BackgroundTask.create(f"Goal {i}")
            task.status = TaskStatus.RUNNING
            manager.tasks[task.id] = task

        for i in range(3):
            task = BackgroundTask.create(f"Goal {i}")
            task.status = TaskStatus.QUEUED
            manager.tasks[task.id] = task

        summary = manager.get_status_summary()
        assert "2 running" in summary
        assert "3 queued" in summary

    def test_get_status_summary_cancelled_not_shown(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask.create("Goal")
        task.status = TaskStatus.CANCELLED
        manager.tasks[task.id] = task

        summary = manager.get_status_summary()
        assert "cancelled" not in summary
        assert summary == "No tasks"


@pytest.mark.asyncio
class TestBackgroundAgentManagerIntegration:
    async def test_spawn_and_complete_workflow(self):
        manager = BackgroundAgentManager(max_concurrent=2)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            yield "result"

        mock_provider.generate = mock_generate

        task = await manager.spawn("Test goal", mock_provider)
        await asyncio.sleep(0.1)

        assert task.status == TaskStatus.COMPLETED
        assert task.result == "result"

    async def test_queue_and_process_workflow(self):
        manager = BackgroundAgentManager(max_concurrent=1)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            await asyncio.sleep(0.05)
            yield "result"

        mock_provider.generate = mock_generate

        task1 = await manager.spawn("Goal 1", mock_provider)
        task2 = await manager.spawn("Goal 2", mock_provider)

        assert task1.status == TaskStatus.RUNNING
        assert task2.status == TaskStatus.QUEUED

        await asyncio.sleep(0.2)

        assert task1.status == TaskStatus.COMPLETED
        assert task2.status == TaskStatus.COMPLETED

    async def test_cancel_and_process_queue(self):
        manager = BackgroundAgentManager(max_concurrent=1)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            await asyncio.sleep(0.1)
            yield "result"

        mock_provider.generate = mock_generate

        task1 = await manager.spawn("Goal 1", mock_provider)
        task2 = await manager.spawn("Goal 2", mock_provider)

        await asyncio.sleep(0.01)
        await manager.cancel(task1.id)
        await asyncio.sleep(0.15)

        assert task1.status == TaskStatus.CANCELLED
        assert task2.status == TaskStatus.COMPLETED

    async def test_multiple_concurrent_tasks(self):
        manager = BackgroundAgentManager(max_concurrent=3)
        mock_provider = MagicMock()

        async def mock_generate(*args, **kwargs):
            await asyncio.sleep(0.05)
            yield "result"

        mock_provider.generate = mock_generate

        tasks = []
        for i in range(5):
            task = await manager.spawn(f"Goal {i}", mock_provider)
            tasks.append(task)

        assert manager.active_count == 3
        assert manager.queued_count == 2

        await asyncio.sleep(0.15)

        assert all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING) for t in tasks
        )
