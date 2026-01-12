"""Tests for widgets/background_sidebar.py - BackgroundTasksSidebar and TaskItemWidget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.containers import ScrollableContainer
from textual.widgets import Static

from managers.background import BackgroundAgentManager, BackgroundTask, TaskStatus
from widgets.background_sidebar import (
    BackgroundTaskCancelRequested,
    BackgroundTaskSelected,
    BackgroundTasksSidebar,
    NewBackgroundTaskRequested,
    TaskItemWidget,
)

# =============================================================================
# Message Tests
# =============================================================================


class TestBackgroundTaskSelectedMessage:
    def test_carries_task_id(self):
        msg = BackgroundTaskSelected(task_id="task_123")
        assert msg.task_id == "task_123"

    def test_carries_empty_task_id(self):
        msg = BackgroundTaskSelected(task_id="")
        assert msg.task_id == ""

    def test_carries_uuid_task_id(self):
        msg = BackgroundTaskSelected(task_id="a1b2c3d4")
        assert msg.task_id == "a1b2c3d4"

    def test_carries_complex_task_id(self):
        msg = BackgroundTaskSelected(task_id="bg-task-2026-01-11")
        assert msg.task_id == "bg-task-2026-01-11"


class TestBackgroundTaskCancelRequestedMessage:
    def test_carries_task_id(self):
        msg = BackgroundTaskCancelRequested(task_id="task_456")
        assert msg.task_id == "task_456"

    def test_carries_empty_task_id(self):
        msg = BackgroundTaskCancelRequested(task_id="")
        assert msg.task_id == ""

    def test_carries_uuid_task_id(self):
        msg = BackgroundTaskCancelRequested(task_id="xyz789")
        assert msg.task_id == "xyz789"


class TestNewBackgroundTaskRequestedMessage:
    def test_can_instantiate(self):
        msg = NewBackgroundTaskRequested()
        assert isinstance(msg, NewBackgroundTaskRequested)

    def test_is_message_type(self):
        from textual.message import Message

        msg = NewBackgroundTaskRequested()
        assert isinstance(msg, Message)


# =============================================================================
# TaskItemWidget Tests
# =============================================================================


class TestTaskItemWidgetStatusIcons:
    def test_queued_icon(self):
        assert TaskItemWidget.STATUS_ICONS[TaskStatus.QUEUED] == "\u23f3"

    def test_running_icon(self):
        assert TaskItemWidget.STATUS_ICONS[TaskStatus.RUNNING] == "\u25b6"

    def test_completed_icon(self):
        assert TaskItemWidget.STATUS_ICONS[TaskStatus.COMPLETED] == "\u2713"

    def test_failed_icon(self):
        assert TaskItemWidget.STATUS_ICONS[TaskStatus.FAILED] == "\u2717"

    def test_cancelled_icon(self):
        assert TaskItemWidget.STATUS_ICONS[TaskStatus.CANCELLED] == "\u2298"

    def test_all_statuses_have_icons(self):
        for status in TaskStatus:
            assert status in TaskItemWidget.STATUS_ICONS


class TestTaskItemWidgetClassAttributes:
    def test_status_icons_is_dict(self):
        assert isinstance(TaskItemWidget.STATUS_ICONS, dict)

    def test_status_icons_has_5_entries(self):
        assert len(TaskItemWidget.STATUS_ICONS) == 5

    def test_inherits_from_static(self):
        assert issubclass(TaskItemWidget, Static)


class TestTaskItemWidgetFormatDuration:
    @pytest.fixture
    def format_duration_method(self):
        return TaskItemWidget._format_duration

    def test_seconds_format(self, format_duration_method):
        assert format_duration_method(None, 30) == "30s ago"

    def test_seconds_format_zero(self, format_duration_method):
        assert format_duration_method(None, 0) == "0s ago"

    def test_seconds_format_decimal(self, format_duration_method):
        assert format_duration_method(None, 45.7) == "46s ago"

    def test_minutes_format(self, format_duration_method):
        assert format_duration_method(None, 120) == "2m ago"

    def test_minutes_format_boundary(self, format_duration_method):
        assert format_duration_method(None, 60) == "1m ago"

    def test_minutes_format_large(self, format_duration_method):
        assert format_duration_method(None, 3000) == "50m ago"

    def test_hours_format(self, format_duration_method):
        assert format_duration_method(None, 7200) == "2h ago"

    def test_hours_format_boundary(self, format_duration_method):
        assert format_duration_method(None, 3600) == "1h ago"

    def test_hours_format_large(self, format_duration_method):
        assert format_duration_method(None, 36000) == "10h ago"

    def test_59_seconds(self, format_duration_method):
        assert format_duration_method(None, 59) == "59s ago"

    def test_3599_seconds_is_minutes(self, format_duration_method):
        assert format_duration_method(None, 3599) == "60m ago"


# =============================================================================
# BackgroundTasksSidebar Tests
# =============================================================================


class TestBackgroundTasksSidebarDefaultCSS:
    def test_has_default_css(self):
        assert BackgroundTasksSidebar.DEFAULT_CSS is not None
        assert len(BackgroundTasksSidebar.DEFAULT_CSS) > 0

    def test_default_css_contains_width(self):
        assert "width: 30" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_dock(self):
        assert "dock: right" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_border(self):
        assert "border-left" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_sidebar_header_class(self):
        assert ".sidebar-header" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_task_item_class(self):
        assert ".task-item" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_task_running_class(self):
        assert ".task-running" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_task_completed_class(self):
        assert ".task-completed" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_task_failed_class(self):
        assert ".task-failed" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_task_queued_class(self):
        assert ".task-queued" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_task_cancelled_class(self):
        assert ".task-cancelled" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_new_task_btn_id(self):
        assert "#new-task-btn" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_height(self):
        assert "height: 100%" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_background(self):
        assert "background: $surface" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_padding(self):
        assert "padding: 1" in BackgroundTasksSidebar.DEFAULT_CSS

    def test_default_css_contains_hover_state(self):
        assert ".task-item:hover" in BackgroundTasksSidebar.DEFAULT_CSS


class TestBackgroundTasksSidebarInit:
    def test_stores_manager(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)
        assert sidebar.manager is mock_manager

    def test_refresh_timer_initially_none(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)
        assert sidebar._refresh_timer is None

    def test_accepts_kwargs(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(
            mock_manager, id="my-sidebar", classes="custom"
        )
        assert sidebar.id == "my-sidebar"

    def test_inherits_from_static(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)
        assert isinstance(sidebar, Static)

    def test_accepts_name_kwarg(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager, name="test-sidebar")
        assert sidebar.name == "test-sidebar"


class TestBackgroundTasksSidebarOnMount:
    def test_sets_interval_timer(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        with patch.object(sidebar, "set_interval") as mock_set_interval:
            mock_set_interval.return_value = MagicMock()
            sidebar.on_mount()

            mock_set_interval.assert_called_once()
            call_args = mock_set_interval.call_args
            assert call_args[0][0] == 2.0

    def test_stores_timer_reference(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_timer = MagicMock()
        with patch.object(sidebar, "set_interval", return_value=mock_timer):
            sidebar.on_mount()
            assert sidebar._refresh_timer is mock_timer

    def test_interval_calls_refresh_tasks(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        with patch.object(sidebar, "set_interval") as mock_set_interval:
            mock_set_interval.return_value = MagicMock()
            sidebar.on_mount()

            call_args = mock_set_interval.call_args
            callback = call_args[0][1]
            assert callback == sidebar._refresh_tasks


class TestBackgroundTasksSidebarRefreshTasks:
    def test_refresh_queries_task_list(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        sidebar._refresh_tasks()

        sidebar.query_one.assert_called_once_with("#task-list", ScrollableContainer)

    def test_refresh_removes_children(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        sidebar._refresh_tasks()

        mock_container.remove_children.assert_called_once()

    def test_refresh_handles_query_exception(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        sidebar.query_one = MagicMock(side_effect=Exception("Widget not found"))

        sidebar._refresh_tasks()

    def test_refresh_calls_list_tasks_with_limit(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        sidebar._refresh_tasks()

        mock_manager.list_tasks.assert_called_once_with(limit=10)

    def test_refresh_mounts_task_items_for_each_task(self):
        task1 = BackgroundTask(id="t1", goal="Task 1", status=TaskStatus.RUNNING)
        task2 = BackgroundTask(id="t2", goal="Task 2", status=TaskStatus.QUEUED)
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = [task1, task2]
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        mock_widget = MagicMock()
        with patch(
            "widgets.background_sidebar.TaskItemWidget", return_value=mock_widget
        ):
            sidebar._refresh_tasks()

        assert mock_container.mount.call_count == 2

    def test_refresh_no_mounts_for_empty_task_list(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        sidebar._refresh_tasks()

        mock_container.mount.assert_not_called()


class TestBackgroundTasksSidebarOnButtonPressed:
    def test_new_task_button_posts_message(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_event = MagicMock()
        mock_event.button.id = "new-task-btn"

        with patch.object(sidebar, "post_message") as mock_post:
            sidebar.on_button_pressed(mock_event)

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, NewBackgroundTaskRequested)

    def test_other_button_does_nothing(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_event = MagicMock()
        mock_event.button.id = "some-other-button"

        with patch.object(sidebar, "post_message") as mock_post:
            sidebar.on_button_pressed(mock_event)
            mock_post.assert_not_called()

    def test_button_with_none_id_does_nothing(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_event = MagicMock()
        mock_event.button.id = None

        with patch.object(sidebar, "post_message") as mock_post:
            sidebar.on_button_pressed(mock_event)
            mock_post.assert_not_called()


class TestBackgroundTasksSidebarOnClick:
    @pytest.mark.asyncio
    async def test_click_on_task_posts_selected_message(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        task = BackgroundTask(id="clicked-task", goal="Test")
        mock_widget = MagicMock(spec=TaskItemWidget)
        mock_widget.task = task
        mock_widget.region.contains.return_value = True

        sidebar.query = MagicMock(return_value=[mock_widget])

        mock_event = MagicMock()
        mock_event.screen_x = 10
        mock_event.screen_y = 10

        with patch.object(sidebar, "post_message") as mock_post:
            await sidebar.on_click(mock_event)

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, BackgroundTaskSelected)
            assert message.task_id == "clicked-task"

    @pytest.mark.asyncio
    async def test_click_outside_task_does_nothing(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        task = BackgroundTask(id="task1", goal="Test")
        mock_widget = MagicMock(spec=TaskItemWidget)
        mock_widget.task = task
        mock_widget.region.contains.return_value = False

        sidebar.query = MagicMock(return_value=[mock_widget])

        mock_event = MagicMock()
        mock_event.screen_x = 100
        mock_event.screen_y = 100

        with patch.object(sidebar, "post_message") as mock_post:
            await sidebar.on_click(mock_event)
            mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_click_with_no_tasks_does_nothing(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        sidebar.query = MagicMock(return_value=[])

        mock_event = MagicMock()
        mock_event.screen_x = 10
        mock_event.screen_y = 10

        with patch.object(sidebar, "post_message") as mock_post:
            await sidebar.on_click(mock_event)
            mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_click_selects_first_matching_task(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        task1 = BackgroundTask(id="task1", goal="First")
        task2 = BackgroundTask(id="task2", goal="Second")

        mock_widget1 = MagicMock(spec=TaskItemWidget)
        mock_widget1.task = task1
        mock_widget1.region.contains.return_value = True

        mock_widget2 = MagicMock(spec=TaskItemWidget)
        mock_widget2.task = task2
        mock_widget2.region.contains.return_value = True

        sidebar.query = MagicMock(return_value=[mock_widget1, mock_widget2])

        mock_event = MagicMock()
        mock_event.screen_x = 10
        mock_event.screen_y = 10

        with patch.object(sidebar, "post_message") as mock_post:
            await sidebar.on_click(mock_event)

            assert mock_post.call_count == 1
            message = mock_post.call_args[0][0]
            assert message.task_id == "task1"

    @pytest.mark.asyncio
    async def test_click_uses_screen_coordinates(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        sidebar = BackgroundTasksSidebar(mock_manager)

        task = BackgroundTask(id="task1", goal="Test")
        mock_widget = MagicMock(spec=TaskItemWidget)
        mock_widget.task = task
        mock_widget.region.contains.return_value = True

        sidebar.query = MagicMock(return_value=[mock_widget])

        mock_event = MagicMock()
        mock_event.screen_x = 42
        mock_event.screen_y = 99

        with patch.object(sidebar, "post_message"):
            await sidebar.on_click(mock_event)

            mock_widget.region.contains.assert_called_with(42, 99)


class TestBackgroundTasksSidebarIntegration:
    def test_manager_reference_preserved_after_operations(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        original_manager = sidebar.manager

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)
        sidebar._refresh_tasks()

        assert sidebar.manager is original_manager

    def test_empty_task_list_handling(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        sidebar._refresh_tasks()

        mock_container.remove_children.assert_called_once()
        mock_container.mount.assert_not_called()

    def test_multiple_refresh_calls(self):
        mock_manager = MagicMock(spec=BackgroundAgentManager)
        mock_manager.list_tasks.return_value = []
        sidebar = BackgroundTasksSidebar(mock_manager)

        mock_container = MagicMock(spec=ScrollableContainer)
        sidebar.query_one = MagicMock(return_value=mock_container)

        sidebar._refresh_tasks()
        sidebar._refresh_tasks()
        sidebar._refresh_tasks()

        assert mock_manager.list_tasks.call_count == 3
        assert mock_container.remove_children.call_count == 3


# =============================================================================
# BackgroundTask dataclass tests (from managers.background)
# =============================================================================


class TestBackgroundTaskDataclass:
    def test_create_generates_id(self):
        task = BackgroundTask.create("Test goal")
        assert task.id is not None
        assert len(task.id) == 8

    def test_create_sets_goal(self):
        task = BackgroundTask.create("My test goal")
        assert task.goal == "My test goal"

    def test_create_default_status_is_queued(self):
        task = BackgroundTask.create("Test")
        assert task.status == TaskStatus.QUEUED

    def test_duration_with_no_start_is_zero(self):
        task = BackgroundTask(id="t1", goal="Test")
        assert task.duration == 0.0

    def test_log_adds_timestamped_message(self):
        task = BackgroundTask(id="t1", goal="Test")
        task.log("Test message")
        assert len(task.logs) == 1
        assert "Test message" in task.logs[0]
        assert "[" in task.logs[0]

    def test_summary_contains_status_icon(self):
        task = BackgroundTask(id="t1", goal="Test", status=TaskStatus.RUNNING)
        assert "\u25b6" in task.summary

    def test_summary_contains_id(self):
        task = BackgroundTask(id="myid123", goal="Test")
        assert "myid123" in task.summary

    def test_summary_truncates_long_goals(self):
        long_goal = "x" * 50
        task = BackgroundTask(id="t1", goal=long_goal)
        assert "..." in task.summary


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

    def test_all_statuses_count(self):
        assert len(TaskStatus) == 5


# =============================================================================
# BackgroundAgentManager tests
# =============================================================================


class TestBackgroundAgentManagerInit:
    def test_default_max_concurrent(self):
        manager = BackgroundAgentManager()
        assert manager.max_concurrent == 3

    def test_custom_max_concurrent(self):
        manager = BackgroundAgentManager(max_concurrent=5)
        assert manager.max_concurrent == 5

    def test_tasks_initially_empty(self):
        manager = BackgroundAgentManager()
        assert len(manager.tasks) == 0

    def test_running_tasks_initially_empty(self):
        manager = BackgroundAgentManager()
        assert len(manager._running_tasks) == 0


class TestBackgroundAgentManagerProperties:
    def test_active_count_zero_initially(self):
        manager = BackgroundAgentManager()
        assert manager.active_count == 0

    def test_queued_count_zero_initially(self):
        manager = BackgroundAgentManager()
        assert manager.queued_count == 0

    def test_active_count_with_running_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Test", status=TaskStatus.RUNNING)
        manager.tasks["t1"] = task
        assert manager.active_count == 1

    def test_queued_count_with_queued_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Test", status=TaskStatus.QUEUED)
        manager.tasks["t1"] = task
        assert manager.queued_count == 1


class TestBackgroundAgentManagerListTasks:
    def test_list_tasks_empty(self):
        manager = BackgroundAgentManager()
        assert manager.list_tasks() == []

    def test_list_tasks_with_limit(self):
        manager = BackgroundAgentManager()
        for i in range(5):
            task = BackgroundTask(id=f"t{i}", goal=f"Task {i}")
            manager.tasks[f"t{i}"] = task

        result = manager.list_tasks(limit=3)
        assert len(result) == 3

    def test_list_tasks_filters_by_status(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask(id="t1", goal="Task 1", status=TaskStatus.RUNNING)
        task2 = BackgroundTask(id="t2", goal="Task 2", status=TaskStatus.COMPLETED)
        manager.tasks["t1"] = task1
        manager.tasks["t2"] = task2

        result = manager.list_tasks(status=TaskStatus.RUNNING)
        assert len(result) == 1
        assert result[0].id == "t1"


class TestBackgroundAgentManagerGetTask:
    def test_get_task_existing(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Test")
        manager.tasks["t1"] = task

        result = manager.get_task("t1")
        assert result is task

    def test_get_task_nonexistent(self):
        manager = BackgroundAgentManager()
        result = manager.get_task("nonexistent")
        assert result is None


class TestBackgroundAgentManagerGetLogs:
    def test_get_logs_existing_task(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Test")
        task.log("Log entry 1")
        task.log("Log entry 2")
        manager.tasks["t1"] = task

        logs = manager.get_logs("t1")
        assert len(logs) == 2

    def test_get_logs_nonexistent_task(self):
        manager = BackgroundAgentManager()
        logs = manager.get_logs("nonexistent")
        assert logs == []


class TestBackgroundAgentManagerClearCompleted:
    def test_clear_completed_removes_completed_tasks(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask(id="t1", goal="Task 1", status=TaskStatus.COMPLETED)
        task2 = BackgroundTask(id="t2", goal="Task 2", status=TaskStatus.RUNNING)
        manager.tasks["t1"] = task1
        manager.tasks["t2"] = task2

        manager.clear_completed()

        assert "t1" not in manager.tasks
        assert "t2" in manager.tasks

    def test_clear_completed_removes_failed_tasks(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Task 1", status=TaskStatus.FAILED)
        manager.tasks["t1"] = task

        manager.clear_completed()

        assert "t1" not in manager.tasks

    def test_clear_completed_removes_cancelled_tasks(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Task 1", status=TaskStatus.CANCELLED)
        manager.tasks["t1"] = task

        manager.clear_completed()

        assert "t1" not in manager.tasks

    def test_clear_completed_preserves_running_and_queued(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask(id="t1", goal="Task 1", status=TaskStatus.RUNNING)
        task2 = BackgroundTask(id="t2", goal="Task 2", status=TaskStatus.QUEUED)
        manager.tasks["t1"] = task1
        manager.tasks["t2"] = task2

        manager.clear_completed()

        assert len(manager.tasks) == 2


class TestBackgroundAgentManagerGetStatusSummary:
    def test_status_summary_no_tasks(self):
        manager = BackgroundAgentManager()
        assert manager.get_status_summary() == "No tasks"

    def test_status_summary_running_tasks(self):
        manager = BackgroundAgentManager()
        task = BackgroundTask(id="t1", goal="Test", status=TaskStatus.RUNNING)
        manager.tasks["t1"] = task

        summary = manager.get_status_summary()
        assert "1 running" in summary

    def test_status_summary_multiple_statuses(self):
        manager = BackgroundAgentManager()
        task1 = BackgroundTask(id="t1", goal="Test 1", status=TaskStatus.RUNNING)
        task2 = BackgroundTask(id="t2", goal="Test 2", status=TaskStatus.QUEUED)
        task3 = BackgroundTask(id="t3", goal="Test 3", status=TaskStatus.COMPLETED)
        manager.tasks["t1"] = task1
        manager.tasks["t2"] = task2
        manager.tasks["t3"] = task3

        summary = manager.get_status_summary()
        assert "1 running" in summary
        assert "1 queued" in summary
        assert "1 completed" in summary


class TestBackgroundAgentManagerOnComplete:
    def test_on_complete_adds_callback(self):
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
