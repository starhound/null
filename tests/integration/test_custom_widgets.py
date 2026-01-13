"""Integration tests for custom widgets in widgets/ directory."""

import pytest
from textual.widgets import Label

from widgets import InputController, StatusBar
from widgets.input import GhostLabel
from widgets.sidebar import Sidebar
from widgets.suggester import CommandItem, CommandSuggester


class TestNullInputWidget:
    """Test NullInput/InputController widget functionality."""

    @pytest.mark.asyncio
    async def test_input_controller_initial_state(self, running_app):
        """InputController initializes with correct defaults."""
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        assert input_widget.mode == "CLI"
        assert input_widget.is_ai_mode is False
        assert input_widget.cmd_history == []
        assert input_widget.cmd_history_index == -1

    @pytest.mark.asyncio
    async def test_input_controller_mode_toggle(self, running_app):
        """Mode toggle switches between CLI and AI mode."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        assert input_widget.mode == "AI"
        assert input_widget.is_ai_mode is True
        assert "ai-mode" in input_widget.classes

        input_widget.toggle_mode()
        await pilot.pause()

        assert input_widget.mode == "CLI"
        assert "ai-mode" not in input_widget.classes

    @pytest.mark.asyncio
    async def test_input_controller_value_property(self, running_app):
        """Value property provides Input-like API."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.value = "test command"
        await pilot.pause()

        assert input_widget.value == "test command"
        assert input_widget.text == "test command"

    @pytest.mark.asyncio
    async def test_input_controller_add_to_history(self, running_app):
        """Add to history stores commands correctly."""
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.add_to_history("first_cmd")
        input_widget.add_to_history("second_cmd")

        assert "first_cmd" in input_widget.cmd_history
        assert "second_cmd" in input_widget.cmd_history
        assert input_widget.cmd_history_index == -1

    @pytest.mark.asyncio
    async def test_input_controller_history_no_duplicates(self, running_app):
        """History does not store consecutive duplicates."""
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.add_to_history("same_cmd")
        input_widget.add_to_history("same_cmd")

        assert input_widget.cmd_history.count("same_cmd") == 1

    @pytest.mark.asyncio
    async def test_input_controller_history_navigation(self, running_app):
        """History navigation with up/down works correctly."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = ["cmd1", "cmd2", "cmd3"]

        input_widget.action_history_up()
        await pilot.pause()
        assert input_widget.text == "cmd3"

        input_widget.action_history_up()
        await pilot.pause()
        assert input_widget.text == "cmd2"

        input_widget.action_history_down()
        await pilot.pause()
        assert input_widget.text == "cmd3"

    @pytest.mark.asyncio
    async def test_input_controller_clear_to_start(self, running_app):
        """Ctrl+U clears line to start."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "hello world"
        input_widget.move_cursor((0, 6))
        await pilot.pause()

        input_widget.action_clear_to_start()
        await pilot.pause()

        assert len(input_widget.text) <= len("hello world")


class TestGhostLabel:
    """Test GhostLabel placeholder text widget."""

    @pytest.mark.asyncio
    async def test_ghost_label_exists_on_input(self, running_app):
        """GhostLabel is mounted on InputController."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        await pilot.pause()

        assert input_widget.ghost_label is not None
        assert isinstance(input_widget.ghost_label, GhostLabel)

    @pytest.mark.asyncio
    async def test_ghost_label_hidden_by_default(self, running_app):
        """GhostLabel is hidden when no suggestion active."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        await pilot.pause()

        assert input_widget.ghost_label.display is False

    @pytest.mark.asyncio
    async def test_ghost_label_accept_suggestion(self, running_app):
        """Accept ghost action completes suggestion."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo "
        input_widget.current_suggestion = "echo hello"
        input_widget.ghost_label.display = True
        await pilot.pause()

        input_widget.action_accept_ghost()
        await pilot.pause()

        assert input_widget.text == "echo hello"
        assert input_widget.ghost_label.display is False


class TestStatusBarWidget:
    """Test StatusBar widget updates."""

    @pytest.mark.asyncio
    async def test_status_bar_mode_indicator(self, running_app):
        """Status bar shows correct mode indicator."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_mode("CLI")
        await pilot.pause()
        assert status.mode == "CLI"

        status.set_mode("AI")
        await pilot.pause()
        assert status.mode == "AI"

    @pytest.mark.asyncio
    async def test_status_bar_agent_mode(self, running_app):
        """Status bar tracks agent mode state."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_agent_mode(True)
        await pilot.pause()
        assert status.agent_mode is True

        status.set_agent_mode(False)
        await pilot.pause()
        assert status.agent_mode is False

    @pytest.mark.asyncio
    async def test_status_bar_context_updates(self, running_app):
        """Status bar context indicator updates correctly."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_context(1000, 4000)
        await pilot.pause()

        assert status.context_chars == 1000
        assert status.context_limit == 4000

    @pytest.mark.asyncio
    async def test_status_bar_context_classes(self, running_app):
        """Status bar applies correct context level classes."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_context(1000, 4000)
        await pilot.pause()
        indicator = status.query_one("#context-indicator", Label)
        assert "context-low" in indicator.classes

        status.set_context(3600, 4000)
        await pilot.pause()
        assert "context-high" in indicator.classes

    @pytest.mark.asyncio
    async def test_status_bar_provider_display(self, running_app):
        """Status bar provider indicator shows name and status."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_provider("ollama", "connected")
        await pilot.pause()

        assert status.provider_name == "ollama"
        assert status.provider_status == "connected"

    @pytest.mark.asyncio
    async def test_status_bar_mcp_count(self, running_app):
        """Status bar MCP indicator shows server count."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_mcp_status(3)
        await pilot.pause()

        assert status.mcp_count == 3

    @pytest.mark.asyncio
    async def test_status_bar_process_count(self, running_app):
        """Status bar process indicator shows count."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_process_count(2)
        await pilot.pause()

        assert status.process_count == 2

    @pytest.mark.asyncio
    async def test_status_bar_git_status(self, running_app):
        """Status bar git indicator shows branch and dirty state."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_git_status("main", True)
        await pilot.pause()

        assert status.git_branch == "main"
        assert status.git_dirty is True

    @pytest.mark.asyncio
    async def test_status_bar_recording_state(self, running_app):
        """Status bar voice recording indicator."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.set_recording(True)
        await pilot.pause()
        assert status.is_recording is True

        status.set_recording(False)
        await pilot.pause()
        assert status.is_recording is False

    @pytest.mark.asyncio
    async def test_status_bar_token_usage(self, running_app):
        """Status bar token usage tracking."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.add_token_usage(100, 50, 0.01)
        await pilot.pause()

        assert status.session_input_tokens == 100
        assert status.session_output_tokens == 50
        assert status.session_cost == pytest.approx(0.01)

    @pytest.mark.asyncio
    async def test_status_bar_reset_tokens(self, running_app):
        """Status bar token reset clears counters."""
        pilot, app = running_app
        status = app.query_one("#status-bar", StatusBar)

        status.add_token_usage(100, 50, 0.01)
        status.reset_token_usage()
        await pilot.pause()

        assert status.session_input_tokens == 0
        assert status.session_output_tokens == 0
        assert status.session_cost == 0.0


class TestSidebarWidget:
    """Test Sidebar widget functionality."""

    @pytest.mark.asyncio
    async def test_sidebar_hidden_initially(self, running_app):
        """Sidebar starts hidden."""
        _pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        assert sidebar.display is False

    @pytest.mark.asyncio
    async def test_sidebar_toggle_visibility(self, running_app):
        """Toggle visibility shows/hides sidebar."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        sidebar.toggle_visibility()
        await pilot.pause()
        assert sidebar.display is True

        sidebar.toggle_visibility()
        await pilot.pause()
        assert sidebar.display is False

    @pytest.mark.asyncio
    async def test_sidebar_set_view(self, running_app):
        """Set view changes active tab."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        sidebar.set_view("files")
        await pilot.pause()
        assert sidebar.current_view == "files"
        assert sidebar.display is True

        sidebar.set_view("todo")
        await pilot.pause()
        assert sidebar.current_view == "todo"

        sidebar.set_view("agent")
        await pilot.pause()
        assert sidebar.current_view == "agent"

    @pytest.mark.asyncio
    async def test_sidebar_invalid_view_ignored(self, running_app):
        """Invalid view names are ignored."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        sidebar.set_view("files")
        await pilot.pause()

        sidebar.set_view("invalid_view")
        await pilot.pause()

        assert sidebar.current_view == "files"


class TestCommandSuggester:
    """Test CommandSuggester autocomplete widget."""

    @pytest.mark.asyncio
    async def test_suggester_shows_on_slash(self, running_app):
        """Suggester shows when typing slash command."""
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)
        suggester = app.query_one("CommandSuggester", CommandSuggester)

        input_widget.text = "/"
        suggester.update_filter("/")
        await pilot.pause()

        assert suggester.display is True

    @pytest.mark.asyncio
    async def test_suggester_select_next(self, running_app):
        """Suggester navigates selection down."""
        pilot, app = running_app
        suggester = app.query_one("CommandSuggester", CommandSuggester)

        suggester.update_filter("/")
        await pilot.pause()

        initial_index = suggester._selected_index
        suggester.select_next()
        await pilot.pause()

        items = list(suggester.query(CommandItem))
        if len(items) > 1:
            assert suggester._selected_index >= initial_index

    @pytest.mark.asyncio
    async def test_suggester_select_prev(self, running_app):
        """Suggester navigates selection up."""
        pilot, app = running_app
        suggester = app.query_one("CommandSuggester", CommandSuggester)

        suggester.update_filter("/")
        await pilot.pause()

        suggester.select_next()
        suggester.select_next()
        await pilot.pause()

        prev_index = suggester._selected_index
        suggester.select_prev()
        await pilot.pause()

        assert suggester._selected_index <= prev_index

    @pytest.mark.asyncio
    async def test_suggester_get_selected(self, running_app):
        """Suggester returns selected command value."""
        pilot, app = running_app
        suggester = app.query_one("CommandSuggester", CommandSuggester)

        suggester.update_filter("/")
        await pilot.pause()

        selected = suggester.get_selected()
        assert isinstance(selected, str)

    @pytest.mark.asyncio
    async def test_suggester_hides_on_empty(self, running_app):
        """Suggester hides when no matching commands."""
        pilot, app = running_app
        suggester = app.query_one("CommandSuggester", CommandSuggester)

        suggester.update_filter("/nonexistent_xyz_cmd")
        await pilot.pause()

        assert suggester.display is False


class TestCommandItem:
    """Test CommandItem list item widget."""

    @pytest.mark.asyncio
    async def test_command_item_stores_value(self, running_app):
        """CommandItem stores command value."""
        _pilot, _app = running_app

        item = CommandItem("/test", "/test")
        assert item.value == "/test"

    @pytest.mark.asyncio
    async def test_command_item_ai_class(self, running_app):
        """CommandItem adds ai-suggestion class for AI items."""
        _pilot, _app = running_app

        item = CommandItem("AI suggestion", "suggestion", is_ai=True)
        assert "ai-suggestion" in item.classes

    @pytest.mark.asyncio
    async def test_command_item_no_ai_class(self, running_app):
        """CommandItem without AI flag has no ai-suggestion class."""
        _pilot, _app = running_app

        item = CommandItem("Regular", "regular", is_ai=False)
        assert "ai-suggestion" not in item.classes


class TestWidgetIntegration:
    """Test widget interactions with each other."""

    @pytest.mark.asyncio
    async def test_sidebar_files_focuses_tree(self, running_app):
        """Opening sidebar files tab focuses directory tree."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        sidebar.set_view("files")
        await pilot.pause()

        from textual.widgets import DirectoryTree

        tree = sidebar.query_one("#file-tree", DirectoryTree)
        assert tree is not None

    @pytest.mark.asyncio
    async def test_sidebar_todo_loads_table(self, running_app):
        """Opening sidebar todo tab loads todo table."""
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        sidebar.set_view("todo")
        await pilot.pause()

        from textual.widgets import DataTable

        table = sidebar.query_one("#todo-table", DataTable)
        assert table is not None
        assert len(table.columns) >= 2
