from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, Static

from managers.agent import AgentState


class AgentScreen(ModalScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "dismiss", "Close"),
        ("c", "clear_history", "Clear History"),
        ("s", "stop_agent", "Stop Agent"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="agent-dialog"):
            yield Label("Agent Inspector", id="agent-header")
            with VerticalScroll(id="agent-content"):
                yield Label("Current Status", classes="section-title")
                yield Static(id="status-display")

                yield Label("Cumulative Statistics", classes="section-title")
                yield Static(id="stats-display")

                yield Label("Session History", classes="section-title")
                yield DataTable(id="session-table", cursor_type="row")

                yield Label("Tool Usage", classes="section-title")
                yield DataTable(id="tool-table", cursor_type="row")

            with Horizontal(id="agent-footer"):
                yield Button("Close", id="close-btn", variant="primary")
                yield Button("Stop Agent", id="stop-btn", variant="warning")
                yield Button("Clear History", id="clear-btn", variant="error")

    def on_mount(self):
        self._setup_tables()
        self._refresh_data()

    def _setup_tables(self):
        session_table = self.query_one("#session-table", DataTable)
        session_table.add_columns(
            "ID", "Status", "Iters", "Tools", "Duration", "Errors"
        )

        tool_table = self.query_one("#tool-table", DataTable)
        tool_table.add_columns("Tool", "Calls", "Success Rate")

    def _refresh_data(self):
        manager = self.app.agent_manager
        status = manager.get_status()
        stats = manager.stats.to_dict()

        self._update_status(status)
        self._update_stats(stats)
        self._update_session_table(manager.get_history(limit=20))
        self._update_tool_table(stats.get("tool_usage", {}))

    def _update_status(self, status: dict):
        display = self.query_one("#status-display", Static)

        state = status.get("state", "idle")
        state_colors = {
            "idle": "dim",
            "thinking": "yellow",
            "executing": "cyan",
            "waiting_approval": "magenta",
            "paused": "yellow",
            "cancelled": "red",
        }

        lines = [f"State: [{state_colors.get(state, 'white')}]{state.upper()}[/]"]

        session = status.get("current_session")
        if session:
            lines.extend(
                [
                    f"Session ID: {session['id']}",
                    f"Task: {session['task'][:60]}{'...' if len(session['task']) > 60 else ''}",
                    f"Iterations: {session['iterations']}",
                    f"Tool Calls: {session['tool_calls']}",
                    f"Duration: {session['duration']:.1f}s",
                ]
            )
            if session.get("errors"):
                lines.append(f"Errors: {session['errors']}")
        else:
            lines.append("No active session")

        display.update("\n".join(lines))

    def _update_stats(self, stats: dict):
        display = self.query_one("#stats-display", Static)

        if stats.get("total_sessions", 0) == 0:
            display.update("No sessions recorded yet.")
            return

        lines = [
            f"Total Sessions: {stats['total_sessions']}",
            f"Total Iterations: {stats['total_iterations']}",
            f"Total Tool Calls: {stats['total_tool_calls']}",
            f"Total Tokens: {stats['total_tokens']:,}",
            f"Total Duration: {stats['total_duration']:.1f}s",
            f"Error Count: {stats['error_count']}",
            f"Avg Iterations/Session: {stats['avg_iterations_per_session']:.1f}",
            f"Avg Tools/Session: {stats['avg_tools_per_session']:.1f}",
        ]

        display.update("\n".join(lines))

    def _update_session_table(self, sessions: list):
        table = self.query_one("#session-table", DataTable)
        table.clear()

        for s in reversed(sessions):
            status = "cancelled" if s.state == AgentState.CANCELLED else "completed"
            table.add_row(
                s.id,
                status,
                str(s.iterations),
                str(s.tool_calls),
                f"{s.duration:.1f}s",
                str(len(s.errors)),
            )

    def _update_tool_table(self, tool_usage: dict):
        table = self.query_one("#tool-table", DataTable)
        table.clear()

        if not tool_usage:
            return

        total_calls = sum(tool_usage.values())
        for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_calls * 100) if total_calls > 0 else 0
            table.add_row(tool, str(count), f"{pct:.0f}%")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.dismiss()
        elif event.button.id == "stop-btn":
            self.action_stop_agent()
        elif event.button.id == "clear-btn":
            self.action_clear_history()

    def action_stop_agent(self):
        manager = self.app.agent_manager
        if manager.is_active:
            manager.request_cancel()
            self.app.notify("Agent session cancelled")
            self._refresh_data()
        else:
            self.app.notify("No active agent session", severity="warning")

    def action_clear_history(self):
        manager = self.app.agent_manager
        manager.clear_history()
        manager.reset_stats()
        self.app.notify("Agent history and stats cleared")
        self._refresh_data()

    def action_dismiss(self):
        self.dismiss()
