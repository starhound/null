from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, DirectoryTree, TabbedContent, TabPane

from commands.todo import TodoManager


class Sidebar(Container):
    """Sidebar widget with multiple views (Files, Todo, Git)."""

    current_view = reactive("files")  # files, todo, git

    def __init__(self):
        super().__init__(id="sidebar")
        self.todo_manager = TodoManager()

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-content"):
            # Header with view switching tabs
            with TabbedContent(initial="files", id="sidebar-tabs"):
                with TabPane("Files", id="files"):
                    yield DirectoryTree(".", id="file-tree")

                with TabPane("Todo", id="todo"):
                    yield DataTable(id="todo-table", cursor_type="row")

                # Placeholder for git view
                # with TabPane("Git", id="git"):
                #     yield Label("Git status...", id="git-status")

    def on_mount(self):
        table = self.query_one("#todo-table", DataTable)
        table.add_columns("S", "Task")
        self._populate_todos(table)

    def watch_current_view(self, view: str):
        try:
            tabs = self.query_one("#sidebar-tabs", TabbedContent)
            tabs.active = view

            if view == "todo":
                self.load_todos()
        except Exception:
            pass

    def _populate_todos(self, table: DataTable):
        todos = self.todo_manager.load()
        todos.sort(key=lambda x: (x["status"] == "done", x["created_at"]))

        for t in todos:
            status_icon = "☐"
            if t["status"] == "in_progress":
                status_icon = "🔄"
            elif t["status"] == "done":
                status_icon = "✅"

            content = t["content"]
            if len(content) > 25:
                content = content[:22] + "..."

            table.add_row(status_icon, content, key=t["id"])

    def load_todos(self):
        try:
            table = self.query_one("#todo-table", DataTable)
            table.clear()
            self._populate_todos(table)
            table.refresh()
        except Exception as e:
            self.app.notify(f"Error loading todos: {e}", severity="error")

    def toggle_visibility(self):
        """Toggle sidebar visibility."""
        self.display = not self.display
        if self.display:
            if self.current_view == "files":
                try:
                    tree = self.query_one("#file-tree", DirectoryTree)
                    tree.path = "."
                    tree.focus()
                except Exception:
                    pass
            elif self.current_view == "todo":
                self.load_todos()
                try:
                    self.query_one("#todo-table", DataTable).focus()
                except Exception:
                    pass

    def set_view(self, view: str):
        """Switch to a specific view and ensure sidebar is visible."""
        if view not in ("files", "todo", "git"):
            return

        self.current_view = view
        self.display = True

        try:
            tabs = self.query_one("#sidebar-tabs", TabbedContent)
            tabs.active = view

            if view == "todo":
                self.load_todos()
        except Exception:
            pass

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        # Bubble up to app
        pass
