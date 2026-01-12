from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    DirectoryTree,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from commands.todo import TodoManager

if TYPE_CHECKING:
    from managers.agent import AgentState


class AgentStatusWidget(Static):
    def __init__(self):
        super().__init__(id="agent-status-widget")
        self._state_labels = {
            "idle": ("IDLE", "dim"),
            "thinking": ("THINKING", "yellow"),
            "executing": ("EXECUTING", "cyan"),
            "waiting_approval": ("WAITING", "magenta"),
            "paused": ("PAUSED", "yellow"),
            "cancelled": ("CANCELLED", "red"),
        }

    def compose(self) -> ComposeResult:
        yield Label("State: IDLE", id="agent-state-label")
        yield Label("Session: --", id="agent-session-label")
        yield Label("Iterations: 0", id="agent-iter-label")
        yield Label("Tools: 0", id="agent-tools-label")
        yield Label("Duration: 0.0s", id="agent-duration-label")
        yield Static("", id="agent-recent-tools")

    def update_status(self, status: dict):
        try:
            state = status.get("state", "idle")
            label, _ = self._state_labels.get(state, ("UNKNOWN", "white"))
            self.query_one("#agent-state-label", Label).update(f"State: {label}")

            session = status.get("current_session")
            if session:
                self.query_one("#agent-session-label", Label).update(
                    f"Session: {session['id']}"
                )
                self.query_one("#agent-iter-label", Label).update(
                    f"Iterations: {session['iterations']}"
                )
                self.query_one("#agent-tools-label", Label).update(
                    f"Tools: {session['tool_calls']}"
                )
                self.query_one("#agent-duration-label", Label).update(
                    f"Duration: {session['duration']:.1f}s"
                )
            else:
                self.query_one("#agent-session-label", Label).update("Session: --")
                self.query_one("#agent-iter-label", Label).update("Iterations: 0")
                self.query_one("#agent-tools-label", Label).update("Tools: 0")
                self.query_one("#agent-duration-label", Label).update("Duration: 0.0s")
        except Exception:
            pass

    def update_recent_tools(self, tool_history: list[dict]):
        try:
            recent = tool_history[-3:] if tool_history else []
            lines = []
            for t in reversed(recent):
                status = "ok" if t.get("success") else "err"
                lines.append(f"  {t['tool'][:15]} [{status}]")

            content = "\n".join(lines) if lines else "  No tool calls yet"
            self.query_one("#agent-recent-tools", Static).update(f"Recent:\n{content}")
        except Exception:
            pass


class Sidebar(Container):
    current_view = reactive("files")

    def __init__(self):
        super().__init__(id="sidebar")
        self.todo_manager = TodoManager()
        self._agent_callback_registered = False

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-content"):
            with TabbedContent(initial="files", id="sidebar-tabs"):
                with TabPane("Files", id="files"):
                    yield DirectoryTree(".", id="file-tree")

                with TabPane("Todo", id="todo"):
                    yield DataTable(id="todo-table", cursor_type="row")

                with TabPane("Agent", id="agent"):
                    yield AgentStatusWidget()

                with TabPane("Branch", id="branches"):
                    yield Static("Loading branches...", id="branch-placeholder")

    def on_mount(self):
        table = self.query_one("#todo-table", DataTable)
        table.add_columns("S", "Task")
        self._populate_todos(table)
        self._register_agent_callback()

    def _register_agent_callback(self):
        if self._agent_callback_registered:
            return

        try:
            manager = self.app.agent_manager
            manager.add_state_callback(self._on_agent_state_change)
            self._agent_callback_registered = True
        except Exception:
            pass

    def _on_agent_state_change(self, state: AgentState):
        self.call_later(self._refresh_agent_view)

    def watch_current_view(self, view: str):
        try:
            tabs = self.query_one("#sidebar-tabs", TabbedContent)
            tabs.active = view

            if view == "todo":
                self.load_todos()
            elif view == "agent":
                self._refresh_agent_view()
            elif view == "branches":
                self._refresh_branch_view()
        except Exception:
            pass

    def _refresh_branch_view(self):
        try:
            placeholder = self.query_one("#branch-placeholder", Static)
            branch_manager = getattr(self.app, "branch_manager", None)
            if branch_manager:
                branches = branch_manager.list_branches()
                current = branch_manager.current_branch
                lines = ["🔀 Branches", ""]
                for b in branches:
                    prefix = "● " if b == current else "○ "
                    lines.append(f"{prefix}{b}")
                if not branches:
                    lines.append("(no branches yet)")
                lines.append("")
                lines.append("Fork with 'f' on any block")
                placeholder.update("\n".join(lines))
            else:
                placeholder.update("Branch manager not available")
        except Exception:
            pass

    def _refresh_agent_view(self):
        try:
            manager = self.app.agent_manager
            widget = self.query_one(AgentStatusWidget)
            widget.update_status(manager.get_status())
            widget.update_recent_tools(manager.get_current_tool_history())
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
            elif self.current_view == "agent":
                self._refresh_agent_view()

    def set_view(self, view: str):
        if view not in ("files", "todo", "agent"):
            return

        self.current_view = view
        self.display = True

        try:
            tabs = self.query_one("#sidebar-tabs", TabbedContent)
            tabs.active = view

            if view == "todo":
                self.load_todos()
            elif view == "agent":
                self._refresh_agent_view()
        except Exception:
            pass

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        # Bubble up to app
        pass
