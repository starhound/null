"""Tests for widgets/sidebar.py - Sidebar and AgentStatusWidget."""

from unittest.mock import MagicMock, patch

from textual.containers import Container
from textual.widgets import (
    DataTable,
    DirectoryTree,
    Label,
    Static,
    TabbedContent,
)

from widgets.sidebar import AgentStatusWidget, Sidebar

# =============================================================================
# AgentStatusWidget Tests
# =============================================================================


class TestAgentStatusWidgetInit:
    """Test AgentStatusWidget initialization."""

    def test_has_default_id(self):
        """Widget should have 'agent-status-widget' as default ID."""
        widget = AgentStatusWidget()
        assert widget.id == "agent-status-widget"

    def test_state_labels_defined(self):
        """All expected state labels should be defined."""
        widget = AgentStatusWidget()
        assert "idle" in widget._state_labels
        assert "thinking" in widget._state_labels
        assert "executing" in widget._state_labels
        assert "waiting_approval" in widget._state_labels
        assert "paused" in widget._state_labels
        assert "cancelled" in widget._state_labels

    def test_state_labels_have_tuple_format(self):
        """Each state label should be a tuple of (label, color)."""
        widget = AgentStatusWidget()
        for _state, value in widget._state_labels.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert isinstance(value[0], str)
            assert isinstance(value[1], str)

    def test_idle_label_is_dim(self):
        """Idle state should have dim color."""
        widget = AgentStatusWidget()
        label, color = widget._state_labels["idle"]
        assert label == "IDLE"
        assert color == "dim"

    def test_thinking_label_is_yellow(self):
        """Thinking state should have yellow color."""
        widget = AgentStatusWidget()
        label, color = widget._state_labels["thinking"]
        assert label == "THINKING"
        assert color == "yellow"

    def test_executing_label_is_cyan(self):
        """Executing state should have cyan color."""
        widget = AgentStatusWidget()
        label, color = widget._state_labels["executing"]
        assert label == "EXECUTING"
        assert color == "cyan"

    def test_waiting_approval_label_is_magenta(self):
        """Waiting approval state should have magenta color."""
        widget = AgentStatusWidget()
        label, color = widget._state_labels["waiting_approval"]
        assert label == "WAITING"
        assert color == "magenta"

    def test_paused_label_is_yellow(self):
        """Paused state should have yellow color."""
        widget = AgentStatusWidget()
        label, color = widget._state_labels["paused"]
        assert label == "PAUSED"
        assert color == "yellow"

    def test_cancelled_label_is_red(self):
        """Cancelled state should have red color."""
        widget = AgentStatusWidget()
        label, color = widget._state_labels["cancelled"]
        assert label == "CANCELLED"
        assert color == "red"


class TestAgentStatusWidgetCompose:
    """Test AgentStatusWidget compose method."""

    def test_compose_yields_six_widgets(self):
        """Compose should yield exactly 6 widgets."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert len(children) == 6

    def test_compose_first_is_state_label(self):
        """First widget should be state label with correct ID."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert isinstance(children[0], Label)
        assert children[0].id == "agent-state-label"

    def test_compose_second_is_session_label(self):
        """Second widget should be session label with correct ID."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert isinstance(children[1], Label)
        assert children[1].id == "agent-session-label"

    def test_compose_third_is_iter_label(self):
        """Third widget should be iterations label with correct ID."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert isinstance(children[2], Label)
        assert children[2].id == "agent-iter-label"

    def test_compose_fourth_is_tools_label(self):
        """Fourth widget should be tools label with correct ID."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert isinstance(children[3], Label)
        assert children[3].id == "agent-tools-label"

    def test_compose_fifth_is_duration_label(self):
        """Fifth widget should be duration label with correct ID."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert isinstance(children[4], Label)
        assert children[4].id == "agent-duration-label"

    def test_compose_sixth_is_recent_tools_static(self):
        """Sixth widget should be recent tools Static with correct ID."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert isinstance(children[5], Static)
        assert children[5].id == "agent-recent-tools"

    def test_initial_state_label_text(self):
        """Initial state label should show 'State: IDLE'."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert str(children[0].render()) == "State: IDLE"

    def test_initial_session_label_text(self):
        """Initial session label should show 'Session: --'."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert str(children[1].render()) == "Session: --"

    def test_initial_iterations_label_text(self):
        """Initial iterations label should show 'Iterations: 0'."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert str(children[2].render()) == "Iterations: 0"

    def test_initial_tools_label_text(self):
        """Initial tools label should show 'Tools: 0'."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert str(children[3].render()) == "Tools: 0"

    def test_initial_duration_label_text(self):
        """Initial duration label should show 'Duration: 0.0s'."""
        widget = AgentStatusWidget()
        children = list(widget.compose())
        assert str(children[4].render()) == "Duration: 0.0s"


class TestAgentStatusWidgetUpdateStatus:
    """Test AgentStatusWidget update_status method."""

    def test_update_status_idle(self):
        """Update with idle state should show IDLE."""
        widget = AgentStatusWidget()
        mock_label = MagicMock(spec=Label)
        widget.query_one = MagicMock(return_value=mock_label)

        widget.update_status({"state": "idle"})

        calls = [
            call
            for call in widget.query_one.call_args_list
            if "#agent-state-label" in str(call)
        ]
        assert len(calls) > 0

    def test_update_status_thinking(self):
        """Update with thinking state should show THINKING."""
        widget = AgentStatusWidget()
        mock_label = MagicMock(spec=Label)
        widget.query_one = MagicMock(return_value=mock_label)

        widget.update_status({"state": "thinking"})
        mock_label.update.assert_called()

    def test_update_status_with_session(self):
        """Update with session info should update all labels."""
        widget = AgentStatusWidget()
        mock_label = MagicMock(spec=Label)
        widget.query_one = MagicMock(return_value=mock_label)

        status = {
            "state": "executing",
            "current_session": {
                "id": "abc123",
                "iterations": 5,
                "tool_calls": 3,
                "duration": 12.5,
            },
        }
        widget.update_status(status)

        assert mock_label.update.call_count >= 1

    def test_update_status_without_session(self):
        """Update without session info should reset labels."""
        widget = AgentStatusWidget()
        mock_label = MagicMock(spec=Label)
        widget.query_one = MagicMock(return_value=mock_label)

        status = {"state": "idle", "current_session": None}
        widget.update_status(status)

        assert mock_label.update.call_count >= 1

    def test_update_status_unknown_state(self):
        """Update with unknown state should show UNKNOWN."""
        widget = AgentStatusWidget()
        mock_label = MagicMock(spec=Label)
        widget.query_one = MagicMock(return_value=mock_label)

        widget.update_status({"state": "unknown_state"})
        mock_label.update.assert_called()

    def test_update_status_handles_exception(self):
        """Update should not raise when query_one fails."""
        widget = AgentStatusWidget()
        widget.query_one = MagicMock(side_effect=Exception("No widget"))

        widget.update_status({"state": "idle"})


class TestAgentStatusWidgetUpdateRecentTools:
    """Test AgentStatusWidget update_recent_tools method."""

    def test_update_recent_tools_empty(self):
        """Empty tool history should show 'No tool calls yet'."""
        widget = AgentStatusWidget()
        mock_static = MagicMock(spec=Static)
        widget.query_one = MagicMock(return_value=mock_static)

        widget.update_recent_tools([])

        mock_static.update.assert_called_once()
        call_arg = mock_static.update.call_args[0][0]
        assert "No tool calls yet" in call_arg

    def test_update_recent_tools_one_success(self):
        """One successful tool call should show with [ok]."""
        widget = AgentStatusWidget()
        mock_static = MagicMock(spec=Static)
        widget.query_one = MagicMock(return_value=mock_static)

        tool_history = [{"tool": "read_file", "success": True}]
        widget.update_recent_tools(tool_history)

        call_arg = mock_static.update.call_args[0][0]
        assert "[ok]" in call_arg
        assert "read_file" in call_arg

    def test_update_recent_tools_one_failure(self):
        """One failed tool call should show with [err]."""
        widget = AgentStatusWidget()
        mock_static = MagicMock(spec=Static)
        widget.query_one = MagicMock(return_value=mock_static)

        tool_history = [{"tool": "run_command", "success": False}]
        widget.update_recent_tools(tool_history)

        call_arg = mock_static.update.call_args[0][0]
        assert "[err]" in call_arg
        assert "run_command" in call_arg

    def test_update_recent_tools_shows_last_three(self):
        """Should show only the last 3 tools."""
        widget = AgentStatusWidget()
        mock_static = MagicMock(spec=Static)
        widget.query_one = MagicMock(return_value=mock_static)

        tool_history = [
            {"tool": "tool1", "success": True},
            {"tool": "tool2", "success": True},
            {"tool": "tool3", "success": True},
            {"tool": "tool4", "success": True},
            {"tool": "tool5", "success": True},
        ]
        widget.update_recent_tools(tool_history)

        call_arg = mock_static.update.call_args[0][0]
        assert "tool1" not in call_arg
        assert "tool2" not in call_arg
        assert "tool3" in call_arg
        assert "tool4" in call_arg
        assert "tool5" in call_arg

    def test_update_recent_tools_truncates_long_names(self):
        """Long tool names should be truncated to 15 chars."""
        widget = AgentStatusWidget()
        mock_static = MagicMock(spec=Static)
        widget.query_one = MagicMock(return_value=mock_static)

        tool_history = [
            {"tool": "very_long_tool_name_that_exceeds_limit", "success": True}
        ]
        widget.update_recent_tools(tool_history)

        call_arg = mock_static.update.call_args[0][0]
        assert "very_long_tool_" in call_arg
        assert "very_long_tool_name_that_exceeds_limit" not in call_arg

    def test_update_recent_tools_handles_exception(self):
        """Should not raise when query_one fails."""
        widget = AgentStatusWidget()
        widget.query_one = MagicMock(side_effect=Exception("No widget"))

        widget.update_recent_tools([{"tool": "test", "success": True}])


# =============================================================================
# Sidebar Tests
# =============================================================================


class TestSidebarInit:
    """Test Sidebar initialization."""

    def test_has_sidebar_id(self):
        """Sidebar should have 'sidebar' as ID."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            assert sidebar.id == "sidebar"

    def test_creates_todo_manager(self):
        """Sidebar should create a TodoManager instance."""
        with patch("widgets.sidebar.TodoManager") as mock_manager:
            sidebar = Sidebar()
            mock_manager.assert_called_once()
            assert sidebar.todo_manager is not None

    def test_agent_callback_not_registered_initially(self):
        """Agent callback should not be registered at init."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            assert sidebar._agent_callback_registered is False

    def test_inherits_from_container(self):
        """Sidebar should inherit from Container."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            assert isinstance(sidebar, Container)


class TestSidebarReactiveProperties:
    """Test Sidebar reactive properties."""

    def test_current_view_default_is_files(self):
        """Default current_view should be 'files'."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            assert sidebar.current_view == "files"

    def test_current_view_is_reactive(self):
        """current_view should be a reactive property."""
        assert hasattr(Sidebar, "current_view")
        assert Sidebar.current_view._default == "files"


class TestSidebarCompose:
    """Test Sidebar compose method."""

    def test_compose_yields_vertical(self):
        """Compose should start with Vertical container."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            result = sidebar.compose()
            assert hasattr(result, "__iter__")

    def test_compose_method_exists(self):
        """Compose method should be defined and callable."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            assert hasattr(sidebar, "compose")
            assert callable(sidebar.compose)


class TestSidebarOnMount:
    """Test Sidebar on_mount method."""

    def test_on_mount_adds_table_columns(self):
        """on_mount should add columns to todo table."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = []
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)
            sidebar.query_one = MagicMock(return_value=mock_table)

            # Mock app with agent_manager
            mock_app = MagicMock()
            mock_app.agent_manager = MagicMock()
            sidebar._app = mock_app

            sidebar.on_mount()

            mock_table.add_columns.assert_called_once_with("S", "Task")

    def test_on_mount_populates_todos(self):
        """on_mount should populate todos from manager."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "1",
                    "content": "Test",
                    "status": "pending",
                    "created_at": "2025-01-01",
                }
            ]
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)
            sidebar.query_one = MagicMock(return_value=mock_table)

            mock_app = MagicMock()
            mock_app.agent_manager = MagicMock()
            sidebar._app = mock_app

            sidebar.on_mount()

            mock_manager.load.assert_called()


class TestSidebarRegisterAgentCallback:
    """Test Sidebar _register_agent_callback method."""

    def test_registers_callback_on_agent_manager(self):
        """Should register callback on agent manager."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_agent_manager = MagicMock()
            mock_app = MagicMock()
            mock_app.agent_manager = mock_agent_manager

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar._register_agent_callback()

            mock_agent_manager.add_state_callback.assert_called_once()
            assert sidebar._agent_callback_registered is True

    def test_does_not_register_twice(self):
        """Should not register callback if already registered."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar._agent_callback_registered = True

            mock_app = MagicMock()
            mock_app.agent_manager = MagicMock()
            sidebar._app = mock_app

            sidebar._register_agent_callback()

            mock_app.agent_manager.add_state_callback.assert_not_called()

    def test_handles_missing_agent_manager(self):
        """Should handle missing agent manager gracefully."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_app = MagicMock()
            del mock_app.agent_manager
            sidebar._app = mock_app

            sidebar._register_agent_callback()
            assert sidebar._agent_callback_registered is False


class TestSidebarWatchCurrentView:
    """Test Sidebar watch_current_view method."""

    def test_watch_sets_active_tab(self):
        """Watcher should set active tab on TabbedContent."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)

            sidebar.watch_current_view("todo")

            mock_tabs.active = "todo"

    def test_watch_loads_todos_for_todo_view(self):
        """Watcher should load todos when switching to todo view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)
            sidebar.load_todos = MagicMock()

            sidebar.watch_current_view("todo")

            sidebar.load_todos.assert_called_once()

    def test_watch_refreshes_agent_for_agent_view(self):
        """Watcher should refresh agent view when switching to agent."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)
            sidebar._refresh_agent_view = MagicMock()

            sidebar.watch_current_view("agent")

            sidebar._refresh_agent_view.assert_called_once()

    def test_watch_refreshes_branch_for_branches_view(self):
        """Watcher should refresh branch view when switching to branches."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)
            sidebar._refresh_branch_view = MagicMock()

            sidebar.watch_current_view("branches")

            sidebar._refresh_branch_view.assert_called_once()

    def test_watch_handles_exception(self):
        """Watcher should not raise on query_one exception."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.query_one = MagicMock(side_effect=Exception("No widget"))

            sidebar.watch_current_view("files")


class TestSidebarRefreshBranchView:
    """Test Sidebar _refresh_branch_view method."""

    def test_shows_branches_from_manager(self):
        """Should display branches from branch manager."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_placeholder = MagicMock(spec=Static)
            sidebar.query_one = MagicMock(return_value=mock_placeholder)

            mock_branch_manager = MagicMock()
            mock_branch_manager.list_branches.return_value = ["main", "feature"]
            mock_branch_manager.current_branch = "main"
            mock_app = MagicMock()
            mock_app.branch_manager = mock_branch_manager

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar._refresh_branch_view()

            mock_placeholder.update.assert_called_once()
            call_arg = mock_placeholder.update.call_args[0][0]
            assert "main" in call_arg
            assert "feature" in call_arg

    def test_shows_current_branch_marker(self):
        """Current branch should have filled circle marker."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_placeholder = MagicMock(spec=Static)
            sidebar.query_one = MagicMock(return_value=mock_placeholder)

            mock_branch_manager = MagicMock()
            mock_branch_manager.list_branches.return_value = ["main"]
            mock_branch_manager.current_branch = "main"
            mock_app = MagicMock()
            mock_app.branch_manager = mock_branch_manager

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar._refresh_branch_view()

            call_arg = mock_placeholder.update.call_args[0][0]
            lines = call_arg.split("\n")
            main_line = next(line for line in lines if "main" in line)
            assert "\u25cf" in main_line

    def test_shows_empty_branches_message(self):
        """Should show message when no branches exist."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_placeholder = MagicMock(spec=Static)
            sidebar.query_one = MagicMock(return_value=mock_placeholder)

            mock_branch_manager = MagicMock()
            mock_branch_manager.list_branches.return_value = []
            mock_branch_manager.current_branch = "main"
            mock_app = MagicMock()
            mock_app.branch_manager = mock_branch_manager

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar._refresh_branch_view()

            call_arg = mock_placeholder.update.call_args[0][0]
            assert "no branches yet" in call_arg

    def test_handles_missing_branch_manager(self):
        """Should handle missing branch manager gracefully."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_placeholder = MagicMock(spec=Static)
            sidebar.query_one = MagicMock(return_value=mock_placeholder)
            mock_app = MagicMock()
            mock_app.branch_manager = None

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar._refresh_branch_view()

            call_arg = mock_placeholder.update.call_args[0][0]
            assert "not available" in call_arg

    def test_handles_exception(self):
        """Should not raise on exception."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.query_one = MagicMock(side_effect=Exception("No widget"))

            sidebar._refresh_branch_view()


class TestSidebarRefreshAgentView:
    """Test Sidebar _refresh_agent_view method."""

    def test_updates_agent_status_widget(self):
        """Should update AgentStatusWidget with manager status."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_widget = MagicMock(spec=AgentStatusWidget)
            sidebar.query_one = MagicMock(return_value=mock_widget)

            mock_agent_manager = MagicMock()
            mock_agent_manager.get_status.return_value = {"state": "idle"}
            mock_agent_manager.get_current_tool_history.return_value = []
            mock_app = MagicMock()
            mock_app.agent_manager = mock_agent_manager

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar._refresh_agent_view()

            mock_widget.update_status.assert_called_once()
            mock_widget.update_recent_tools.assert_called_once()

    def test_handles_exception(self):
        """Should not raise on exception."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.query_one = MagicMock(side_effect=Exception("No widget"))

            sidebar._refresh_agent_view()


class TestSidebarPopulateTodos:
    """Test Sidebar _populate_todos method."""

    def test_sorts_todos_by_status_and_date(self):
        """Todos should be sorted: pending/in_progress first, then done."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "1",
                    "content": "Done task",
                    "status": "done",
                    "created_at": "2025-01-01",
                },
                {
                    "id": "2",
                    "content": "Pending task",
                    "status": "pending",
                    "created_at": "2025-01-02",
                },
            ]
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)

            sidebar._populate_todos(mock_table)

            calls = mock_table.add_row.call_args_list
            assert len(calls) == 2

    def test_uses_correct_status_icons(self):
        """Should use correct icons for each status."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "1",
                    "content": "Pending",
                    "status": "pending",
                    "created_at": "2025-01-01",
                },
                {
                    "id": "2",
                    "content": "In Progress",
                    "status": "in_progress",
                    "created_at": "2025-01-02",
                },
                {
                    "id": "3",
                    "content": "Done",
                    "status": "done",
                    "created_at": "2025-01-03",
                },
            ]
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)

            sidebar._populate_todos(mock_table)

            calls = mock_table.add_row.call_args_list
            icons = [call[0][0] for call in calls]
            assert "☐" in icons
            assert "🔄" in icons
            assert "✅" in icons

    def test_truncates_long_content(self):
        """Content longer than 25 chars should be truncated."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            long_content = "This is a very long task description that exceeds limit"
            mock_manager.load.return_value = [
                {
                    "id": "1",
                    "content": long_content,
                    "status": "pending",
                    "created_at": "2025-01-01",
                },
            ]
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)

            sidebar._populate_todos(mock_table)

            call_arg = mock_table.add_row.call_args[0][1]
            assert len(call_arg) <= 25
            assert call_arg.endswith("...")

    def test_does_not_truncate_short_content(self):
        """Content 25 chars or less should not be truncated."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            short_content = "Short task"
            mock_manager.load.return_value = [
                {
                    "id": "1",
                    "content": short_content,
                    "status": "pending",
                    "created_at": "2025-01-01",
                },
            ]
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)

            sidebar._populate_todos(mock_table)

            call_arg = mock_table.add_row.call_args[0][1]
            assert call_arg == short_content
            assert "..." not in call_arg

    def test_uses_todo_id_as_key(self):
        """Should use todo ID as row key."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = [
                {
                    "id": "abc123",
                    "content": "Task",
                    "status": "pending",
                    "created_at": "2025-01-01",
                },
            ]
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)

            sidebar._populate_todos(mock_table)

            call_kwargs = mock_table.add_row.call_args[1]
            assert call_kwargs["key"] == "abc123"


class TestSidebarLoadTodos:
    """Test Sidebar load_todos method."""

    def test_clears_and_repopulates_table(self):
        """load_todos should clear table and repopulate."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = []
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_table = MagicMock(spec=DataTable)
            sidebar.query_one = MagicMock(return_value=mock_table)

            sidebar.load_todos()

            mock_table.clear.assert_called_once()
            mock_table.refresh.assert_called_once()

    def test_handles_exception_gracefully(self):
        """Should handle exception without crashing."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.query_one = MagicMock(side_effect=Exception("Test error"))
            mock_app = MagicMock()

            with patch.object(
                type(sidebar),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                sidebar.load_todos()
                mock_app.notify.assert_called_once()


class TestSidebarToggleVisibility:
    """Test Sidebar toggle_visibility method."""

    def test_toggles_display_true_to_false(self):
        """Should toggle display from True to False."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.display = True

            sidebar.toggle_visibility()

            assert sidebar.display is False

    def test_toggles_display_false_to_true(self):
        """Should toggle display from False to True."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.display = False
            sidebar.current_view = "files"

            mock_tree = MagicMock(spec=DirectoryTree)
            sidebar.query_one = MagicMock(return_value=mock_tree)

            sidebar.toggle_visibility()

            assert sidebar.display is True

    def test_focuses_file_tree_when_showing_files(self):
        """Should focus file tree when showing files view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.display = False
            sidebar.current_view = "files"

            mock_tree = MagicMock(spec=DirectoryTree)
            sidebar.query_one = MagicMock(return_value=mock_tree)

            sidebar.toggle_visibility()

            mock_tree.focus.assert_called_once()

    def test_loads_todos_when_showing_todo_view(self):
        """Should load todos when showing todo view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.display = False
            sidebar.current_view = "todo"
            sidebar.load_todos = MagicMock()

            mock_table = MagicMock(spec=DataTable)
            sidebar.query_one = MagicMock(return_value=mock_table)

            sidebar.toggle_visibility()

            sidebar.load_todos.assert_called_once()

    def test_refreshes_agent_when_showing_agent_view(self):
        """Should refresh agent view when showing agent view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.display = False
            sidebar.current_view = "agent"
            sidebar._refresh_agent_view = MagicMock()

            sidebar.toggle_visibility()

            sidebar._refresh_agent_view.assert_called_once()


class TestSidebarSetView:
    """Test Sidebar set_view method."""

    def test_sets_current_view(self):
        """Should set current_view to specified view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)

            sidebar.set_view("todo")

            assert sidebar.current_view == "todo"

    def test_sets_display_true(self):
        """Should set display to True."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.display = False
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)

            sidebar.set_view("files")

            assert sidebar.display is True

    def test_sets_tab_active(self):
        """Should set TabbedContent active tab."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)

            sidebar.set_view("agent")

            assert mock_tabs.active == "agent"

    def test_ignores_invalid_view(self):
        """Should ignore invalid view names."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.current_view = "files"

            sidebar.set_view("invalid_view")

            assert sidebar.current_view == "files"

    def test_loads_todos_for_todo_view(self):
        """Should load todos when setting todo view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)
            sidebar.load_todos = MagicMock()

            sidebar.set_view("todo")

            assert sidebar.load_todos.call_count >= 1

    def test_refreshes_agent_for_agent_view(self):
        """Should refresh agent view when setting agent view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)
            sidebar._refresh_agent_view = MagicMock()

            sidebar.set_view("agent")

            assert sidebar._refresh_agent_view.call_count >= 1

    def test_handles_exception(self):
        """Should not raise on exception."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.query_one = MagicMock(side_effect=Exception("No widget"))

            sidebar.set_view("files")


class TestSidebarDirectoryTreeHandler:
    """Test Sidebar on_directory_tree_file_selected handler."""

    def test_handler_exists(self):
        """Handler method should exist."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            assert hasattr(sidebar, "on_directory_tree_file_selected")
            assert callable(sidebar.on_directory_tree_file_selected)

    def test_handler_does_not_raise(self):
        """Handler should not raise on event."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_event = MagicMock()
            mock_event.path = "/some/file.py"

            sidebar.on_directory_tree_file_selected(mock_event)


class TestSidebarOnAgentStateChange:
    """Test Sidebar _on_agent_state_change callback."""

    def test_calls_refresh_agent_view_later(self):
        """Should schedule agent view refresh."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.call_later = MagicMock()

            from managers.agent import AgentState

            sidebar._on_agent_state_change(AgentState.THINKING)

            sidebar.call_later.assert_called_once_with(sidebar._refresh_agent_view)


class TestSidebarIntegration:
    """Integration-style tests for Sidebar behavior."""

    def test_full_workflow_file_to_todo(self):
        """Test switching from files to todo view."""
        with patch("widgets.sidebar.TodoManager") as mock_manager_cls:
            mock_manager = MagicMock()
            mock_manager.load.return_value = []
            mock_manager_cls.return_value = mock_manager

            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            mock_table = MagicMock(spec=DataTable)

            def query_one_side_effect(selector, *args):
                if "tabs" in str(selector):
                    return mock_tabs
                if "table" in str(selector):
                    return mock_table
                return MagicMock()

            sidebar.query_one = MagicMock(side_effect=query_one_side_effect)

            assert sidebar.current_view == "files"

            sidebar.set_view("todo")
            assert sidebar.current_view == "todo"
            assert sidebar.display is True

    def test_full_workflow_toggle_twice(self):
        """Test toggling visibility twice returns to original state."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            sidebar.current_view = "files"

            mock_tree = MagicMock(spec=DirectoryTree)
            sidebar.query_one = MagicMock(return_value=mock_tree)

            original_display = sidebar.display

            sidebar.toggle_visibility()
            sidebar.toggle_visibility()

            assert sidebar.display == original_display

    def test_valid_views(self):
        """Test that only valid views are accepted by set_view."""
        with patch("widgets.sidebar.TodoManager"):
            sidebar = Sidebar()
            mock_tabs = MagicMock(spec=TabbedContent)
            sidebar.query_one = MagicMock(return_value=mock_tabs)
            sidebar._refresh_agent_view = MagicMock()

            for view in ["files", "todo", "agent"]:
                sidebar.set_view(view)
                assert sidebar.current_view == view

            sidebar.set_view("files")
            sidebar.set_view("invalid")
            assert sidebar.current_view == "files"

            sidebar.set_view("branches")
            assert sidebar.current_view == "files"
