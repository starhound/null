import pytest
from textual.widgets import DataTable, DirectoryTree, TabbedContent

from widgets import InputController, Sidebar


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestSidebarVisibility:
    @pytest.mark.asyncio
    async def test_sidebar_hidden_by_default(self, running_app):
        _pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)
        assert sidebar.display is False

    @pytest.mark.asyncio
    async def test_ctrl_backslash_toggles_sidebar(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        await pilot.press("ctrl+backslash")
        await pilot.pause()

        assert sidebar.display is True

    @pytest.mark.asyncio
    async def test_sidebar_toggle_twice_hides(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        await pilot.press("ctrl+backslash")
        await pilot.pause()
        await pilot.press("ctrl+backslash")
        await pilot.pause()

        assert sidebar.display is False

    @pytest.mark.asyncio
    async def test_action_toggle_file_tree_shows_files_tab(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        assert sidebar.display is True
        assert sidebar.current_view == "files"


class TestSidebarTabs:
    @pytest.mark.asyncio
    async def test_sidebar_has_tabbed_content(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        tabbed = sidebar.query_one("#sidebar-tabs", TabbedContent)
        assert tabbed is not None

    @pytest.mark.asyncio
    async def test_sidebar_has_files_tab(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        tree = sidebar.query_one("#file-tree", DirectoryTree)
        assert tree is not None

    @pytest.mark.asyncio
    async def test_sidebar_has_todo_tab(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        todo_table = sidebar.query_one("#todo-table", DataTable)
        assert todo_table is not None

    @pytest.mark.asyncio
    async def test_set_view_changes_active_tab(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        sidebar.set_view("todo")
        await pilot.pause()

        assert sidebar.current_view == "todo"

    @pytest.mark.asyncio
    async def test_set_view_to_agent(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        sidebar.set_view("agent")
        await pilot.pause()

        assert sidebar.current_view == "agent"


class TestSidebarFileTree:
    @pytest.mark.asyncio
    async def test_file_tree_shows_current_directory(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        tree = sidebar.query_one("#file-tree", DirectoryTree)
        assert tree.path is not None

    @pytest.mark.asyncio
    async def test_file_tree_is_focusable(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        tree = sidebar.query_one("#file-tree", DirectoryTree)
        tree.focus()
        await pilot.pause()

        assert tree.has_focus


class TestSidebarTodoPanel:
    @pytest.mark.asyncio
    async def test_todo_table_has_columns(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        todo_table = sidebar.query_one("#todo-table", DataTable)
        assert len(todo_table.columns) >= 2

    @pytest.mark.asyncio
    async def test_load_todos_refreshes_table(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        sidebar.load_todos()
        await pilot.pause()


class TestSidebarBranchPanel:
    @pytest.mark.asyncio
    async def test_action_toggle_branches_shows_sidebar(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_branches()
        await pilot.pause()

        assert sidebar.display is True

    @pytest.mark.asyncio
    async def test_branch_panel_has_placeholder(self, running_app):
        pilot, app = running_app
        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        from textual.widgets import Static

        placeholder = sidebar.query_one("#branch-placeholder", Static)
        assert placeholder is not None
