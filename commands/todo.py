"""Todo management commands."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from textual.widgets import DataTable

from .base import CommandMixin


class TodoItem(TypedDict):
    id: str
    content: str
    status: str  # pending, in_progress, done
    created_at: str


class TodoManager:
    def __init__(self):
        self.file_path = Path.home() / ".null" / "todos.json"
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text("[]")

    def load(self) -> list[TodoItem]:
        try:
            return json.loads(self.file_path.read_text())
        except Exception:
            return []

    def save(self, todos: list[TodoItem]):
        self.file_path.write_text(json.dumps(todos, indent=2))

    def add(self, content: str) -> TodoItem:
        todos = self.load()
        item: TodoItem = {
            "id": str(uuid.uuid4())[:8],
            "content": content,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        todos.append(item)
        self.save(todos)
        return item

    def update_status(self, todo_id: str, status: str) -> bool:
        todos = self.load()
        for item in todos:
            if item["id"] == todo_id:
                item["status"] = status
                self.save(todos)
                return True
        return False

    def delete(self, todo_id: str) -> bool:
        todos = self.load()
        new_todos = [t for t in todos if t["id"] != todo_id]
        if len(new_todos) != len(todos):
            self.save(new_todos)
            return True
        return False

    def clear_completed(self):
        todos = self.load()
        new_todos = [t for t in todos if t["status"] != "done"]
        self.save(new_todos)


class TodoCommands(CommandMixin):
    """Todo list management."""

    def __init__(self, app):
        self.app = app
        self.manager = TodoManager()

    async def cmd_todo(self, args: list[str]):
        """Manage todos. Usage: /todo [add|list|done|del]"""
        if not args:
            from screens.todo import TodoScreen

            self.app.push_screen(TodoScreen())
            return

        subcmd = args[0]

        if subcmd == "add":
            content = " ".join(args[1:])
            if not content:
                self.notify("Usage: /todo add <content>", severity="error")
                return
            item = self.manager.add(content)
            self.notify(f"Added task: {item['content']}")

        elif subcmd == "list":
            todos = self.manager.load()
            if not todos:
                self.notify("No tasks.")
                return

            lines = []
            for t in todos:
                icon = (
                    "☐"
                    if t["status"] == "pending"
                    else ("🔄" if t["status"] == "in_progress" else "✅")
                )
                lines.append(f"{t['id']} {icon} {t['content']}")

            await self.show_output("/todo list", "\n".join(lines))

        elif subcmd in ("done", "finish", "complete"):
            if len(args) < 2:
                self.notify("Usage: /todo done <id>", severity="error")
                return
            if self.manager.update_status(args[1], "done"):
                self.notify(f"Task {args[1]} marked done")
            else:
                self.notify("Task not found", severity="error")

        elif subcmd == "del":
            if len(args) < 2:
                self.notify("Usage: /todo del <id>", severity="error")
                return
            if self.manager.delete(args[1]):
                self.notify(f"Task {args[1]} deleted")
            else:
                self.notify("Task not found", severity="error")
        else:
            self.notify(
                "Unknown subcommand. Try add, list, done, del.", severity="error"
            )
