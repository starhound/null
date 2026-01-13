from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from commands.todo import TodoManager
from widgets.file_tree import FileBrowserWidget

if TYPE_CHECKING:
    from managers.agent import AgentState
    from managers.process import ProcessInfo


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
        yield Label("Step: 0/10", id="agent-step-label")
        yield Label("Tools: 0", id="agent-tools-label")
        yield Label("Tokens: 0", id="agent-tokens-label")
        yield Label("Cost: $0.0000", id="agent-cost-label")
        yield Label("Duration: 0.0s", id="agent-duration-label")
        yield Static("", id="agent-tool-usage")
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
                self.query_one("#agent-step-label", Label).update(
                    f"Step: {session['iterations']}/{session['max_iterations']}"
                )
                self.query_one("#agent-tools-label", Label).update(
                    f"Tools: {session['tool_calls']}"
                )
                self.query_one("#agent-tokens-label", Label).update(
                    f"Tokens: {session.get('tokens_used', 0):,}"
                )
                cost = session.get("estimated_cost", 0.0)
                cost_str = f"${cost:.4f}" if cost > 0 else "$0.0000"
                self.query_one("#agent-cost-label", Label).update(f"Cost: {cost_str}")
                self.query_one("#agent-duration-label", Label).update(
                    f"Duration: {session['duration']:.1f}s"
                )
                self._update_tool_usage(session.get("tool_usage_session", {}))
            else:
                self.query_one("#agent-session-label", Label).update("Session: --")
                self.query_one("#agent-step-label", Label).update("Step: 0/10")
                self.query_one("#agent-tools-label", Label).update("Tools: 0")
                self.query_one("#agent-tokens-label", Label).update("Tokens: 0")
                self.query_one("#agent-cost-label", Label).update("Cost: $0.0000")
                self.query_one("#agent-duration-label", Label).update("Duration: 0.0s")
                self.query_one("#agent-tool-usage", Static).update("")
        except Exception:
            pass

    def _update_tool_usage(self, tool_usage: dict[str, int]):
        try:
            if not tool_usage:
                self.query_one("#agent-tool-usage", Static).update("")
                return

            sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
            lines = ["Tool Usage:"]
            for tool_name, count in sorted_tools[:5]:
                short_name = tool_name[:18] + ".." if len(tool_name) > 20 else tool_name
                lines.append(f"  {short_name}: {count}")

            self.query_one("#agent-tool-usage", Static).update("\n".join(lines))
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


class ProcessItemWidget(Static):
    class KillRequested(Message):
        def __init__(self, block_id: str, force: bool = False):
            super().__init__()
            self.block_id = block_id
            self.force = force

    class KillChildrenRequested(Message):
        def __init__(self, block_id: str):
            super().__init__()
            self.block_id = block_id

    class TreeViewRequested(Message):
        def __init__(self, block_id: str):
            super().__init__()
            self.block_id = block_id

    def __init__(self, process_info: ProcessInfo):
        super().__init__(classes="process-item")
        self.process_info = process_info
        self._expanded = False

    def compose(self) -> ComposeResult:
        info = self.process_info
        cmd = info.command[:30] + "..." if len(info.command) > 30 else info.command
        duration = (datetime.now() - info.start_time).total_seconds()

        with Vertical(classes="process-item-content"):
            with Horizontal(classes="process-header"):
                yield Label(f"PID {info.pid}", classes="process-pid")
                yield Label(f"{duration:.0f}s", classes="process-duration")
                tui_indicator = " [TUI]" if info.is_tui else ""
                yield Label(tui_indicator, classes="process-tui-indicator")

            yield Label(cmd, classes="process-command")

            res = info.resources
            cpu_str = f"CPU: {res.cpu_percent:.1f}%"
            mem_str = f"MEM: {res.memory_mb:.1f}MB"
            yield Label(f"{cpu_str} | {mem_str}", classes="process-resources")

            with Horizontal(classes="process-actions"):
                yield Button("Stop", id=f"stop-{info.block_id}", classes="process-btn")
                yield Button(
                    "Kill", id=f"kill-{info.block_id}", classes="process-btn danger"
                )
                yield Button("Tree", id=f"tree-{info.block_id}", classes="process-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        block_id = self.process_info.block_id

        if button_id.startswith("stop-"):
            self.post_message(self.KillRequested(block_id, force=False))
        elif button_id.startswith("kill-"):
            self.post_message(self.KillRequested(block_id, force=True))
        elif button_id.startswith("tree-"):
            self.post_message(self.TreeViewRequested(block_id))

        event.stop()


class ProcessListWidget(Static):
    def __init__(self):
        super().__init__(id="process-list-widget")
        self._process_callback_registered = False
        self._update_timer: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Label("Running Processes", classes="process-list-header")
        yield Static("0 processes", id="process-count")
        with ScrollableContainer(id="process-items"):
            yield Static("No running processes", id="process-placeholder")
        with Horizontal(classes="process-list-actions"):
            yield Button("Stop All", id="stop-all-btn", classes="action-btn")
            yield Button("Kill All", id="kill-all-btn", classes="action-btn danger")

    def on_mount(self):
        self._register_process_callback()
        self._start_update_timer()

    def on_unmount(self):
        self._stop_update_timer()

    def _start_update_timer(self):
        if self._update_timer is not None:
            return

        async def periodic_update():
            while True:
                try:
                    self.refresh_processes()
                except Exception:
                    pass
                await asyncio.sleep(2.0)

        self._update_timer = asyncio.create_task(periodic_update())

    def _stop_update_timer(self):
        if self._update_timer:
            self._update_timer.cancel()
            self._update_timer = None

    def _register_process_callback(self):
        if self._process_callback_registered:
            return

        try:
            manager = self.app.process_manager
            manager.on_change(self._on_process_change)
            self._process_callback_registered = True
        except Exception:
            pass

    def _on_process_change(self):
        self.call_later(self.refresh_processes)

    def refresh_processes(self):
        try:
            manager = self.app.process_manager
            processes = manager.get_running()
            manager.update_all_resources()

            count_label = self.query_one("#process-count", Static)
            count_label.update(
                f"{len(processes)} process{'es' if len(processes) != 1 else ''}"
            )

            container = self.query_one("#process-items", ScrollableContainer)
            container.remove_children()

            if not processes:
                container.mount(
                    Static("No running processes", id="process-placeholder")
                )
            else:
                for proc in processes:
                    container.mount(ProcessItemWidget(proc))

        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""

        if button_id == "stop-all-btn":
            self._stop_all_processes(force=False)
        elif button_id == "kill-all-btn":
            self._stop_all_processes(force=True)

    def _stop_all_processes(self, force: bool):
        try:
            manager = self.app.process_manager
            count = manager.stop_all(force=force)
            action = "Killed" if force else "Stopped"
            self.app.notify(f"{action} {count} processes")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def on_process_item_widget_kill_requested(
        self, event: ProcessItemWidget.KillRequested
    ):
        try:
            manager = self.app.process_manager
            if event.force:
                manager.stop(event.block_id, force=True)
                self.app.notify(f"Killed process {event.block_id}")
            else:
                asyncio.create_task(self._graceful_kill(event.block_id))
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    async def _graceful_kill(self, block_id: str):
        try:
            manager = self.app.process_manager
            success = await manager.graceful_kill(block_id, timeout=5.0)
            if success:
                self.app.notify(f"Gracefully stopped {block_id}")
            else:
                self.app.notify(f"Failed to stop {block_id}", severity="warning")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def on_process_item_widget_tree_view_requested(
        self, event: ProcessItemWidget.TreeViewRequested
    ):
        try:
            manager = self.app.process_manager
            tree_str = manager.format_tree(event.block_id)
            self.app.notify(f"Process tree:\n{tree_str}", timeout=10)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")


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
                    yield FileBrowserWidget(".")

                with TabPane("Todo", id="todo"):
                    yield DataTable(id="todo-table", cursor_type="row")

                with TabPane("Procs", id="processes"):
                    yield ProcessListWidget()

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
            elif view == "processes":
                self._refresh_process_view()
        except Exception:
            pass

    def _refresh_branch_view(self):
        try:
            placeholder = self.query_one("#branch-placeholder", Static)
            branch_manager = getattr(self.app, "branch_manager", None)
            if branch_manager:
                branches = branch_manager.list_branches()
                current = branch_manager.current_branch
                lines = ["Branches", ""]
                for b in branches:
                    prefix = "> " if b == current else "  "
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

    def _refresh_process_view(self):
        try:
            widget = self.query_one(ProcessListWidget)
            widget.refresh_processes()
        except Exception:
            pass

    def _populate_todos(self, table: DataTable):
        todos = self.todo_manager.load()
        todos.sort(key=lambda x: (x["status"] == "done", x["created_at"]))

        for t in todos:
            status_icon = "[ ]"
            if t["status"] == "in_progress":
                status_icon = "[~]"
            elif t["status"] == "done":
                status_icon = "[x]"

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
                    browser = self.query_one(FileBrowserWidget)
                    browser.refresh()
                    browser.focus()
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
            elif self.current_view == "processes":
                self._refresh_process_view()

    def set_view(self, view: str):
        valid_views = ("files", "todo", "agent", "processes", "branches")
        if view not in valid_views:
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
            elif view == "processes":
                self._refresh_process_view()
        except Exception:
            pass

    def on_file_browser_widget_file_opened(
        self, event: FileBrowserWidget.FileOpened
    ) -> None:
        try:
            input_widget = self.app.query_one("InputController")
            path_str = str(event.path)
            if " " in path_str:
                path_str = f'"{path_str}"'
            input_widget.insert(path_str)
            input_widget.focus()
        except Exception:
            pass

    def add_to_recent_files(self, path) -> None:
        try:
            from pathlib import Path

            browser = self.query_one(FileBrowserWidget)
            browser.add_to_recent(Path(path))
        except Exception:
            pass
