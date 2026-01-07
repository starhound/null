"""Todo Dashboard Screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Input, Label

from commands.todo import TodoManager
from screens.base import ModalScreen

if TYPE_CHECKING:
    from app import NullApp


class TodoScreen(ModalScreen):
    """Screen for managing todo list."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("delete", "delete_task", "Delete"),
        Binding("space", "toggle_status", "Toggle Status"),
        Binding("enter", "add_task", "Add Task"),
    ]

    CSS = """
    TodoScreen {
        align: center middle;
        background: $layer-void 80%;
    }

    TodoScreen #todo-container {
        width: 70%;
        height: 80%;
        background: $layer-base;
        border: double $primary $border-normal;
        layout: vertical;
        padding: 1 2;
    }

    TodoScreen #title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding-bottom: 1;
        border-bottom: solid $primary 20%;
    }

    TodoScreen DataTable {
        height: 1fr;
        background: $layer-raised 10%;
        margin-bottom: 1;
    }
    
    TodoScreen DataTable > .datatable--header {
        background: $layer-raised 30%;
        color: $primary;
        text-style: bold;
    }

    TodoScreen DataTable > .datatable--cursor {
        background: $primary 30%;
        color: $text-bright;
    }

    TodoScreen #input-area {
        height: auto;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }

    TodoScreen Input {
        width: 1fr;
        margin-right: 1;
    }

    TodoScreen Button {
        min-width: 8;
    }

    TodoScreen #add-btn {
        background: $success;
        color: $layer-void;
    }

    TodoScreen #close-btn {
        background: $layer-raised;
        margin-left: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.manager = TodoManager()

    def compose(self) -> ComposeResult:
        with Container(id="todo-container"):
            yield Label("Task Dashboard", id="title")
            yield DataTable(cursor_type="row")

            with Horizontal(id="input-area"):
                yield Input(placeholder="New task...", id="new-task-input")
                yield Button("Add", id="add-btn", variant="success")
                yield Button("Close", id="close-btn")

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("ID", "Status", "Task", "Created")
        self.load_tasks()

    def load_tasks(self):
        table = self.query_one(DataTable)
        table.clear()

        todos = self.manager.load()
        # Sort: pending/in_progress first, then done
        todos.sort(key=lambda x: (x["status"] == "done", x["created_at"]))

        for t in todos:
            status_icon = "☐"
            if t["status"] == "in_progress":
                status_icon = "🔄"
            elif t["status"] == "done":
                status_icon = "✅"

            created = t["created_at"][:16].replace("T", " ")
            table.add_row(t["id"], status_icon, t["content"], created, key=t["id"])

    def action_add_task(self):
        inp = self.query_one("#new-task-input", Input)
        content = inp.value.strip()
        if content:
            self.manager.add(content)
            inp.value = ""
            self.load_tasks()
            self.notify("Task added")

    def action_delete_task(self):
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            # key is the row key which we set to id
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            if row_key:
                self.manager.delete(row_key.value)
                self.load_tasks()

    def action_toggle_status(self):
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            if not row_key:
                return

            todo_id = row_key.value
            todos = self.manager.load()
            item = next((t for t in todos if t["id"] == todo_id), None)

            if item:
                new_status = "pending"
                if item["status"] == "pending":
                    new_status = "in_progress"
                elif item["status"] == "in_progress":
                    new_status = "done"

                self.manager.update_status(todo_id, new_status)
                self.load_tasks()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "add-btn":
            self.action_add_task()
        elif event.button.id == "close-btn":
            self.dismiss()
