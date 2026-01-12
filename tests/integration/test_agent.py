import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestAgentManager:
    @pytest.mark.asyncio
    async def test_app_has_agent_manager(self, running_app):
        _pilot, app = running_app
        assert app.agent_manager is not None

    @pytest.mark.asyncio
    async def test_agent_manager_initial_state(self, running_app):
        _pilot, app = running_app
        status = app.agent_manager.get_status()
        assert status.get("state") == "idle"

    @pytest.mark.asyncio
    async def test_agent_manager_has_get_status(self, running_app):
        _pilot, app = running_app
        status = app.agent_manager.get_status()
        assert isinstance(status, dict)
        assert "state" in status


class TestAgentModeToggle:
    @pytest.mark.asyncio
    async def test_agent_command_toggles_mode(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/agent")

    @pytest.mark.asyncio
    async def test_agent_on_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/agent on")

    @pytest.mark.asyncio
    async def test_agent_off_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/agent off")

    @pytest.mark.asyncio
    async def test_agent_status_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/agent status")


class TestAgentStatusBar:
    @pytest.mark.asyncio
    async def test_status_bar_shows_agent_mode(self, running_app):
        _pilot, app = running_app
        from widgets import StatusBar

        status = app.query_one("#status-bar", StatusBar)
        assert hasattr(status, "set_agent_mode")

    @pytest.mark.asyncio
    async def test_status_bar_agent_mode_updates(self, running_app):
        pilot, app = running_app
        from widgets import StatusBar

        status = app.query_one("#status-bar", StatusBar)

        status.set_agent_mode(False)
        await pilot.pause()

        status.set_agent_mode(True)
        await pilot.pause()


class TestAgentSidebarPanel:
    @pytest.mark.asyncio
    async def test_sidebar_has_agent_tab(self, running_app):
        pilot, app = running_app
        from widgets import Sidebar

        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        sidebar.set_view("agent")
        await pilot.pause()

        assert sidebar.current_view == "agent"

    @pytest.mark.asyncio
    async def test_agent_panel_has_status_widget(self, running_app):
        pilot, app = running_app
        from widgets import Sidebar
        from widgets.sidebar import AgentStatusWidget

        sidebar = app.query_one("#sidebar", Sidebar)

        app.action_toggle_file_tree()
        await pilot.pause()

        sidebar.set_view("agent")
        await pilot.pause()

        agent_widget = sidebar.query_one(AgentStatusWidget)
        assert agent_widget is not None


class TestAgentToolHistory:
    @pytest.mark.asyncio
    async def test_agent_manager_has_tool_history(self, running_app):
        _pilot, app = running_app
        history = app.agent_manager.get_current_tool_history()
        assert isinstance(history, list)
