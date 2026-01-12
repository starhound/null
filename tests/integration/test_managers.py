import pytest

from widgets import InputController


async def submit_command(pilot, app, command: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = command
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestAgentManager:
    @pytest.mark.asyncio
    async def test_agent_manager_exists(self, running_app):
        _pilot, app = running_app

        assert hasattr(app, "agent_manager")
        assert app.agent_manager is not None

    @pytest.mark.asyncio
    async def test_agent_manager_initial_state(self, running_app):
        _pilot, app = running_app

        from managers.agent import AgentState

        assert app.agent_manager.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_agent_toggle_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/agent")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_agent_on_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/agent on")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_agent_off_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/agent off")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_agent_status_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/agent status")

    @pytest.mark.asyncio
    async def test_agent_manager_get_status(self, running_app):
        _pilot, app = running_app

        status = app.agent_manager.get_status()
        assert isinstance(status, dict)


class TestBranchManager:
    @pytest.mark.asyncio
    async def test_branch_manager_exists(self, running_app):
        _pilot, app = running_app

        assert hasattr(app, "branch_manager")
        assert app.branch_manager is not None

    @pytest.mark.asyncio
    async def test_branch_manager_current_branch(self, running_app):
        _pilot, app = running_app

        current = app.branch_manager.current_branch
        assert current is None or isinstance(current, str)

    @pytest.mark.asyncio
    async def test_branch_save_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/branch save test_branch_save")

    @pytest.mark.asyncio
    async def test_branch_list_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/branch list")

    @pytest.mark.asyncio
    async def test_branch_list_returns_data(self, running_app):
        _pilot, app = running_app

        branches = app.branch_manager.list_branches()
        assert isinstance(branches, list)


class TestProcessManager:
    @pytest.mark.asyncio
    async def test_process_manager_exists(self, running_app):
        _pilot, app = running_app

        assert hasattr(app, "process_manager")
        assert app.process_manager is not None

    @pytest.mark.asyncio
    async def test_process_manager_count(self, running_app):
        _pilot, app = running_app

        count = app.process_manager.get_count()
        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_process_manager_has_methods(self, running_app):
        _pilot, app = running_app

        assert hasattr(app.process_manager, "get_count")
        assert hasattr(app.process_manager, "stop")


class TestMCPManager:
    @pytest.mark.asyncio
    async def test_mcp_manager_exists(self, running_app):
        _pilot, app = running_app

        assert hasattr(app, "mcp_manager")

    @pytest.mark.asyncio
    async def test_mcp_list_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/mcp list")

    @pytest.mark.asyncio
    async def test_mcp_status_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/mcp status")


class TestAIManager:
    @pytest.mark.asyncio
    async def test_ai_manager_exists(self, running_app):
        _pilot, app = running_app

        assert hasattr(app, "ai_manager")

    @pytest.mark.asyncio
    async def test_ai_manager_get_usable_providers(self, running_app):
        _pilot, app = running_app

        providers = app.ai_manager.get_usable_providers()
        assert isinstance(providers, list)


class TestGitManager:
    @pytest.mark.asyncio
    async def test_git_status_via_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/git status")

    @pytest.mark.asyncio
    async def test_git_log_via_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/git log")

    @pytest.mark.asyncio
    async def test_git_diff_via_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/git diff")


class TestErrorDetector:
    @pytest.mark.asyncio
    async def test_watch_mode_toggle(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/watch")
        assert getattr(app, "_watch_mode", False) is True

        await submit_command(pilot, app, "/watch stop")
        assert getattr(app, "_watch_mode", False) is False


class TestPlanningManager:
    @pytest.mark.asyncio
    async def test_todo_list_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/todo list")

    @pytest.mark.asyncio
    async def test_todo_add_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/todo add Test task")

    @pytest.mark.asyncio
    async def test_todo_clear_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/todo clear")
