import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestAppActions:
    @pytest.mark.asyncio
    async def test_action_toggle_ai_mode(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial = input_widget.is_ai_mode

        app.action_toggle_ai_mode()
        await pilot.pause()

        assert input_widget.is_ai_mode != initial

    @pytest.mark.asyncio
    async def test_action_open_help(self, running_app):
        pilot, app = running_app
        from screens import HelpScreen

        app.action_open_help()
        await pilot.pause()

        assert isinstance(app.screen_stack[-1], HelpScreen)

    @pytest.mark.asyncio
    async def test_action_select_model(self, running_app):
        pilot, app = running_app

        app.action_select_model()
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_action_select_theme(self, running_app):
        pilot, app = running_app
        from screens.selection import ThemeSelectionScreen

        app.action_select_theme()
        await pilot.pause()

        assert isinstance(app.screen_stack[-1], ThemeSelectionScreen)

    @pytest.mark.asyncio
    async def test_action_select_provider(self, running_app):
        pilot, app = running_app
        from screens.selection import SelectionListScreen

        app.action_select_provider()
        await pilot.pause()

        assert isinstance(app.screen_stack[-1], SelectionListScreen)

    @pytest.mark.asyncio
    async def test_action_clear_history(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")
        assert len(app.blocks) >= 1

        app.action_clear_history()
        await pilot.pause()

        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_action_toggle_file_tree(self, running_app):
        pilot, app = running_app
        from widgets import Sidebar

        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        assert sidebar.display is True

    @pytest.mark.asyncio
    async def test_action_toggle_branches(self, running_app):
        pilot, app = running_app
        from widgets import Sidebar

        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_branches()
        await pilot.pause()

        assert sidebar.display is True

    @pytest.mark.asyncio
    async def test_action_search_history(self, running_app):
        pilot, app = running_app
        from widgets.history_search import HistorySearch

        app.action_search_history()
        await pilot.pause()

        search = app.query_one("#history-search", HistorySearch)
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_action_search_blocks(self, running_app):
        pilot, app = running_app
        from widgets.block_search import BlockSearch

        app.action_search_blocks()
        await pilot.pause()

        search = app.query_one("#block-search", BlockSearch)
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_action_open_command_palette(self, running_app):
        pilot, app = running_app
        from widgets import CommandPalette

        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        assert "visible" in palette.classes

    @pytest.mark.asyncio
    async def test_action_cancel_operation(self, running_app):
        pilot, app = running_app

        app.action_cancel_operation()
        await pilot.pause()


class TestAppState:
    @pytest.mark.asyncio
    async def test_is_busy_initially_false(self, running_app):
        _pilot, app = running_app
        assert app.is_busy() is False

    @pytest.mark.asyncio
    async def test_app_has_blocks_list(self, running_app):
        _pilot, app = running_app
        assert isinstance(app.blocks, list)

    @pytest.mark.asyncio
    async def test_app_has_config(self, running_app):
        _pilot, app = running_app
        assert app.config is not None

    @pytest.mark.asyncio
    async def test_app_has_theme(self, running_app):
        _pilot, app = running_app
        assert app.theme is not None


class TestAppManagers:
    @pytest.mark.asyncio
    async def test_app_has_process_manager(self, running_app):
        _pilot, app = running_app
        assert app.process_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_branch_manager(self, running_app):
        _pilot, app = running_app
        assert app.branch_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_agent_manager(self, running_app):
        _pilot, app = running_app
        assert app.agent_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_ai_manager(self, running_app):
        _pilot, app = running_app
        assert app.ai_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_mcp_manager(self, running_app):
        _pilot, app = running_app
        assert app.mcp_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_plan_manager(self, running_app):
        _pilot, app = running_app
        assert app.plan_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_error_detector(self, running_app):
        _pilot, app = running_app
        assert app.error_detector is not None

    @pytest.mark.asyncio
    async def test_app_has_review_manager(self, running_app):
        _pilot, app = running_app
        assert app.review_manager is not None

    @pytest.mark.asyncio
    async def test_app_has_suggestion_engine(self, running_app):
        _pilot, app = running_app
        assert app.suggestion_engine is not None


class TestAppHandlers:
    @pytest.mark.asyncio
    async def test_app_has_command_handler(self, running_app):
        _pilot, app = running_app
        assert app.command_handler is not None

    @pytest.mark.asyncio
    async def test_app_has_execution_handler(self, running_app):
        _pilot, app = running_app
        assert app.execution_handler is not None

    @pytest.mark.asyncio
    async def test_app_has_input_handler(self, running_app):
        _pilot, app = running_app
        assert app.input_handler is not None
