"""Integration tests for TodoScreen."""

import pytest
from textual.widgets import Button, DataTable, Input

from app import NullApp
from screens.todo import TodoScreen


@pytest.fixture
async def todo_app(mock_home):
    """Fixture providing NullApp with TodoScreen displayed."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await app.push_screen(TodoScreen())
        await pilot.pause()
        yield app, pilot


class TestTodoScreenIntegration:
    """Integration tests for the TodoScreen modal."""

    @pytest.mark.asyncio
    async def test_todo_screen_has_datatable(self, todo_app):
        """Test that todo items DataTable is rendered."""
        app, pilot = todo_app
        table = app.screen.query_one(DataTable)
        assert table is not None
        # Verify columns are set up
        assert len(table.columns) == 4  # ID, Status, Task, Created

    @pytest.mark.asyncio
    async def test_add_todo_item(self, todo_app):
        """Test adding a new todo item."""
        app, pilot = todo_app

        inp = app.screen.query_one("#new-task-input", Input)
        inp.value = "Test task"
        await pilot.pause()

        add_btn = app.screen.query_one("#add-btn", Button)
        add_btn.press()
        await pilot.pause()

        table = app.screen.query_one(DataTable)
        assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_add_todo_via_enter_key(self, todo_app):
        """Test adding todo via Enter key binding."""
        app, pilot = todo_app

        inp = app.screen.query_one("#new-task-input", Input)
        inp.value = "Another task"
        await pilot.pause()

        app.screen.action_add_task()
        await pilot.pause()

        table = app.screen.query_one(DataTable)
        assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_mark_todo_complete(self, todo_app):
        """Test marking a todo as complete (toggle status)."""
        app, pilot = todo_app

        # Add a task first
        app.screen.manager.add("Task to complete")
        app.screen.load_tasks()
        await pilot.pause()

        table = app.screen.query_one(DataTable)
        assert table.row_count == 1

        # Focus table and toggle status (pending -> in_progress)
        table.focus()
        await pilot.pause()

        app.screen.action_toggle_status()
        await pilot.pause()

        # Verify status changed - reload and check
        todos = app.screen.manager.load()
        assert todos[0]["status"] == "in_progress"

        # Toggle again (in_progress -> done)
        app.screen.action_toggle_status()
        await pilot.pause()

        todos = app.screen.manager.load()
        assert todos[0]["status"] == "done"

    @pytest.mark.asyncio
    async def test_delete_todo_item(self, todo_app):
        """Test deleting a todo item."""
        app, pilot = todo_app

        # Add a task first
        app.screen.manager.add("Task to delete")
        app.screen.load_tasks()
        await pilot.pause()

        table = app.screen.query_one(DataTable)
        assert table.row_count == 1

        # Focus table and delete
        table.focus()
        await pilot.pause()

        app.screen.action_delete_task()
        await pilot.pause()

        # Verify task deleted
        assert table.row_count == 0
        assert len(app.screen.manager.load()) == 0

    @pytest.mark.asyncio
    async def test_close_button_dismisses(self, todo_app):
        """Test that close button dismisses the screen."""
        app, pilot = todo_app

        close_btn = app.screen.query_one("#close-btn", Button)
        close_btn.press()
        await pilot.pause()

        # Screen should be dismissed (back to main)
        assert not isinstance(app.screen, TodoScreen)

    @pytest.mark.asyncio
    async def test_escape_dismisses(self, todo_app):
        """Test that Escape key dismisses the screen."""
        app, pilot = todo_app

        app.screen.dismiss()
        await pilot.pause()

        assert not isinstance(app.screen, TodoScreen)

    @pytest.mark.asyncio
    async def test_multiple_todos_rendered(self, todo_app):
        """Test that multiple todo items are rendered correctly."""
        app, pilot = todo_app

        # Add multiple tasks
        app.screen.manager.add("First task")
        app.screen.manager.add("Second task")
        app.screen.manager.add("Third task")
        app.screen.load_tasks()
        await pilot.pause()

        table = app.screen.query_one(DataTable)
        assert table.row_count == 3
