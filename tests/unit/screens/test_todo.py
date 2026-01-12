"""Tests for the todo dashboard screen."""

from unittest.mock import MagicMock, patch


class TestTodoScreen:
    """Tests for TodoScreen initialization and bindings."""

    def test_init_creates_manager(self):
        """Test that TodoScreen initializes with a TodoManager."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            screen = TodoScreen()
            mock_manager_class.assert_called_once()
            assert screen.manager is not None

    def test_bindings_defined(self):
        """Test that all expected bindings are defined."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            binding_keys = [b.key for b in screen.BINDINGS]
            assert "escape" in binding_keys
            assert "delete" in binding_keys
            assert "space" in binding_keys
            assert "enter" in binding_keys

    def test_binding_actions(self):
        """Test that bindings map to correct actions."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            bindings_map = {b.key: b.action for b in screen.BINDINGS}
            assert bindings_map["escape"] == "dismiss"
            assert bindings_map["delete"] == "delete_task"
            assert bindings_map["space"] == "toggle_status"
            assert bindings_map["enter"] == "add_task"


class TestTodoScreenLoadTasks:
    """Tests for load_tasks method."""

    def test_load_tasks_clears_table(self):
        """Test that load_tasks clears the table first."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = []
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.load_tasks()
            mock_table.clear.assert_called_once()

    def test_load_tasks_displays_pending_icon(self):
        """Test pending tasks show correct icon."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "abc123",
                    "content": "Test task",
                    "status": "pending",
                    "created_at": "2026-01-01T10:00:00",
                }
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.load_tasks()
            mock_table.add_row.assert_called_once()
            call_args = mock_table.add_row.call_args
            assert call_args[0][1] == "☐"

    def test_load_tasks_displays_in_progress_icon(self):
        """Test in_progress tasks show correct icon."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "abc123",
                    "content": "Test task",
                    "status": "in_progress",
                    "created_at": "2026-01-01T10:00:00",
                }
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.load_tasks()
            call_args = mock_table.add_row.call_args
            assert call_args[0][1] == "🔄"

    def test_load_tasks_displays_done_icon(self):
        """Test done tasks show correct icon."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "abc123",
                    "content": "Test task",
                    "status": "done",
                    "created_at": "2026-01-01T10:00:00",
                }
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.load_tasks()
            call_args = mock_table.add_row.call_args
            assert call_args[0][1] == "✅"

    def test_load_tasks_sorts_done_last(self):
        """Test that done tasks are sorted to the end."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "done1",
                    "content": "Done task",
                    "status": "done",
                    "created_at": "2026-01-01T08:00:00",
                },
                {
                    "id": "pending1",
                    "content": "Pending task",
                    "status": "pending",
                    "created_at": "2026-01-01T10:00:00",
                },
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.load_tasks()
            calls = mock_table.add_row.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "pending1"
            assert calls[1][0][0] == "done1"

    def test_load_tasks_formats_created_date(self):
        """Test that created_at is formatted correctly."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "abc123",
                    "content": "Test task",
                    "status": "pending",
                    "created_at": "2026-01-01T10:30:45",
                }
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.load_tasks()
            call_args = mock_table.add_row.call_args
            assert call_args[0][3] == "2026-01-01 10:30"


class TestTodoScreenAddTask:
    """Tests for action_add_task method."""

    def test_add_task_with_content(self):
        """Test adding a task with valid content."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen._refresh_sidebar = MagicMock()
            screen.notify = MagicMock()

            mock_input = MagicMock()
            mock_input.value = "New task"
            screen.query_one = MagicMock(return_value=mock_input)

            screen.action_add_task()

            mock_manager.add.assert_called_once_with("New task")
            assert mock_input.value == ""
            screen.load_tasks.assert_called_once()
            screen._refresh_sidebar.assert_called_once()
            screen.notify.assert_called_once_with("Task added")

    def test_add_task_empty_content(self):
        """Test that empty content is not added."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen.notify = MagicMock()

            mock_input = MagicMock()
            mock_input.value = "   "
            screen.query_one = MagicMock(return_value=mock_input)

            screen.action_add_task()

            mock_manager.add.assert_not_called()
            screen.load_tasks.assert_not_called()

    def test_add_task_strips_whitespace(self):
        """Test that task content is stripped."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen._refresh_sidebar = MagicMock()
            screen.notify = MagicMock()

            mock_input = MagicMock()
            mock_input.value = "  Trimmed task  "
            screen.query_one = MagicMock(return_value=mock_input)

            screen.action_add_task()

            mock_manager.add.assert_called_once_with("Trimmed task")


class TestTodoScreenDeleteTask:
    """Tests for action_delete_task method."""

    def test_delete_task_with_valid_selection(self):
        """Test deleting a task with valid cursor position."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen._refresh_sidebar = MagicMock()

            mock_row_key = MagicMock()
            mock_row_key.value = "task123"
            mock_cell_key = MagicMock()
            mock_cell_key.row_key = mock_row_key

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.cursor_coordinate = MagicMock()
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_delete_task()

            mock_manager.delete.assert_called_once_with("task123")
            screen.load_tasks.assert_called_once()
            screen._refresh_sidebar.assert_called_once()

    def test_delete_task_no_cursor(self):
        """Test delete does nothing when no cursor."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()

            mock_table = MagicMock()
            mock_table.cursor_row = None
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_delete_task()

            mock_manager.delete.assert_not_called()
            screen.load_tasks.assert_not_called()

    def test_delete_task_no_row_key(self):
        """Test delete does nothing when row_key is None."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()

            mock_cell_key = MagicMock()
            mock_cell_key.row_key = None

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_delete_task()

            mock_manager.delete.assert_not_called()

    def test_delete_task_no_row_key_value(self):
        """Test delete does nothing when row_key.value is None."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()

            mock_row_key = MagicMock()
            mock_row_key.value = None
            mock_cell_key = MagicMock()
            mock_cell_key.row_key = mock_row_key

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_delete_task()

            mock_manager.delete.assert_not_called()


class TestTodoScreenToggleStatus:
    """Tests for action_toggle_status method."""

    def test_toggle_pending_to_in_progress(self):
        """Test toggling from pending to in_progress."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {"id": "task1", "status": "pending", "content": "Test"}
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen._refresh_sidebar = MagicMock()

            mock_row_key = MagicMock()
            mock_row_key.value = "task1"
            mock_cell_key = MagicMock()
            mock_cell_key.row_key = mock_row_key

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.cursor_coordinate = MagicMock()
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_toggle_status()

            mock_manager.update_status.assert_called_once_with("task1", "in_progress")

    def test_toggle_in_progress_to_done(self):
        """Test toggling from in_progress to done."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {"id": "task1", "status": "in_progress", "content": "Test"}
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen._refresh_sidebar = MagicMock()

            mock_row_key = MagicMock()
            mock_row_key.value = "task1"
            mock_cell_key = MagicMock()
            mock_cell_key.row_key = mock_row_key

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.cursor_coordinate = MagicMock()
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_toggle_status()

            mock_manager.update_status.assert_called_once_with("task1", "done")

    def test_toggle_done_to_pending(self):
        """Test toggling from done back to pending."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {"id": "task1", "status": "done", "content": "Test"}
            ]
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()
            screen._refresh_sidebar = MagicMock()

            mock_row_key = MagicMock()
            mock_row_key.value = "task1"
            mock_cell_key = MagicMock()
            mock_cell_key.row_key = mock_row_key

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.cursor_coordinate = MagicMock()
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_toggle_status()

            mock_manager.update_status.assert_called_once_with("task1", "pending")

    def test_toggle_no_cursor(self):
        """Test toggle does nothing when no cursor."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()

            mock_table = MagicMock()
            mock_table.cursor_row = None
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_toggle_status()

            mock_manager.update_status.assert_not_called()

    def test_toggle_no_row_key(self):
        """Test toggle returns early when row_key is None."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()

            mock_cell_key = MagicMock()
            mock_cell_key.row_key = None

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_toggle_status()

            mock_manager.update_status.assert_not_called()

    def test_toggle_task_not_found(self):
        """Test toggle does nothing when task not found in manager."""
        with patch("screens.todo.TodoManager") as mock_manager_class:
            from screens.todo import TodoScreen

            mock_manager = MagicMock()
            mock_manager.load.return_value = []
            mock_manager_class.return_value = mock_manager

            screen = TodoScreen()
            screen.load_tasks = MagicMock()

            mock_row_key = MagicMock()
            mock_row_key.value = "nonexistent"
            mock_cell_key = MagicMock()
            mock_cell_key.row_key = mock_row_key

            mock_table = MagicMock()
            mock_table.cursor_row = 0
            mock_table.cursor_coordinate = MagicMock()
            mock_table.coordinate_to_cell_key.return_value = mock_cell_key
            screen.query_one = MagicMock(return_value=mock_table)

            screen.action_toggle_status()

            mock_manager.update_status.assert_not_called()
            screen.load_tasks.assert_not_called()


class TestTodoScreenButtonHandling:
    """Tests for button press handling."""

    def test_add_button_calls_add_task(self):
        """Test add button triggers action_add_task."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            screen.action_add_task = MagicMock()

            mock_button = MagicMock()
            mock_button.id = "add-btn"
            mock_event = MagicMock()
            mock_event.button = mock_button

            screen.on_button_pressed(mock_event)
            screen.action_add_task.assert_called_once()

    def test_close_button_dismisses(self):
        """Test close button dismisses the screen."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            screen.dismiss = MagicMock()

            mock_button = MagicMock()
            mock_button.id = "close-btn"
            mock_event = MagicMock()
            mock_event.button = mock_button

            screen.on_button_pressed(mock_event)
            screen.dismiss.assert_called_once()

    def test_unknown_button_does_nothing(self):
        """Test unknown button does not trigger actions."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            screen.action_add_task = MagicMock()
            screen.dismiss = MagicMock()

            mock_button = MagicMock()
            mock_button.id = "unknown-btn"
            mock_event = MagicMock()
            mock_event.button = mock_button

            screen.on_button_pressed(mock_event)
            screen.action_add_task.assert_not_called()
            screen.dismiss.assert_not_called()


class TestTodoScreenRefreshSidebar:
    """Tests for _refresh_sidebar method."""

    def test_refresh_sidebar_calls_load_todos(self):
        """Test that _refresh_sidebar calls sidebar.load_todos."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            mock_sidebar = MagicMock()
            mock_app = MagicMock()
            mock_app.query_one.return_value = mock_sidebar

            with patch.object(
                type(screen), "app", new_callable=lambda: property(lambda s: mock_app)
            ):
                screen._refresh_sidebar()

            mock_app.query_one.assert_called_once_with("Sidebar")
            mock_sidebar.load_todos.assert_called_once()

    def test_refresh_sidebar_handles_exception(self):
        """Test that _refresh_sidebar handles missing sidebar gracefully."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            mock_app = MagicMock()
            mock_app.query_one.side_effect = Exception("Sidebar not found")

            with patch.object(
                type(screen), "app", new_callable=lambda: property(lambda s: mock_app)
            ):
                screen._refresh_sidebar()


class TestTodoScreenOnMount:
    """Tests for on_mount method."""

    def test_on_mount_adds_columns(self):
        """Test that on_mount adds the correct columns."""
        with patch("screens.todo.TodoManager"):
            from screens.todo import TodoScreen

            screen = TodoScreen()
            screen.load_tasks = MagicMock()

            mock_table = MagicMock()
            screen.query_one = MagicMock(return_value=mock_table)

            screen.on_mount()

            mock_table.add_columns.assert_called_once_with(
                "ID", "Status", "Task", "Created"
            )
            screen.load_tasks.assert_called_once()
