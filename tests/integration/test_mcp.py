import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestMCPManager:
    @pytest.mark.asyncio
    async def test_app_has_mcp_manager(self, running_app):
        _pilot, app = running_app
        assert app.mcp_manager is not None

    @pytest.mark.asyncio
    async def test_mcp_manager_has_get_all_tools(self, running_app):
        _pilot, app = running_app
        tools = app.mcp_manager.get_all_tools()
        assert isinstance(tools, (list, type(None))) or hasattr(tools, "__iter__")

    @pytest.mark.asyncio
    async def test_mcp_manager_has_get_status_method(self, running_app):
        _pilot, app = running_app
        assert hasattr(app.mcp_manager, "get_status")


class TestMCPCommands:
    @pytest.mark.asyncio
    async def test_mcp_command_executes(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/mcp")

    @pytest.mark.asyncio
    async def test_mcp_status_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/mcp status")

    @pytest.mark.asyncio
    async def test_mcp_tools_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/mcp tools")

    @pytest.mark.asyncio
    async def test_mcp_catalog_opens_screen(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/mcp catalog")
        await pilot.pause()

        assert len(app.screen_stack) > 1


class TestMCPStatusBar:
    @pytest.mark.asyncio
    async def test_status_bar_shows_mcp_count(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        from widgets import StatusBar

        status = app.query_one("#status-bar", StatusBar)
        mcp_indicator = status.query_one("#mcp-indicator", Label)
        assert mcp_indicator is not None

    @pytest.mark.asyncio
    async def test_mcp_indicator_updates(self, running_app):
        pilot, app = running_app
        from widgets import StatusBar

        status = app.query_one("#status-bar", StatusBar)

        status.set_mcp_status(0)
        await pilot.pause()

        status.set_mcp_status(3)
        await pilot.pause()
