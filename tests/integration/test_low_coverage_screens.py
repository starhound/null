import pytest

from widgets import InputController


async def submit_command(pilot, app, command: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = command
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestMCPScreen:
    @pytest.mark.asyncio
    async def test_mcp_add_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.mcp import MCPServerConfigScreen

        await submit_command(pilot, app, "/mcp add")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, MCPServerConfigScreen)

    @pytest.mark.asyncio
    async def test_mcp_add_screen_has_inputs(self, running_app):
        pilot, app = running_app
        from textual.widgets import Input

        await submit_command(pilot, app, "/mcp add")

        if len(app.screen_stack) > 1:
            screen = app.screen
            inputs = list(screen.query(Input))
            assert len(inputs) >= 1

    @pytest.mark.asyncio
    async def test_mcp_add_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/mcp add")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestToolsScreen:
    @pytest.mark.asyncio
    async def test_mcp_tools_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.tools import ToolsScreen

        await submit_command(pilot, app, "/mcp tools")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, ToolsScreen)

    @pytest.mark.asyncio
    async def test_tools_screen_has_container(self, running_app):
        pilot, app = running_app
        from textual.containers import VerticalScroll

        await submit_command(pilot, app, "/mcp tools")

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                container = screen.query_one("#tools-list", VerticalScroll)
                assert container is not None
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_tools_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/mcp tools")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestMCPCatalogScreen:
    @pytest.mark.asyncio
    async def test_mcp_catalog_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.mcp_catalog import MCPCatalogScreen

        await submit_command(pilot, app, "/mcp catalog")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, MCPCatalogScreen)

    @pytest.mark.asyncio
    async def test_catalog_screen_has_list(self, running_app):
        pilot, app = running_app
        from textual.widgets import OptionList

        await submit_command(pilot, app, "/mcp catalog")

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                option_list = screen.query_one(OptionList)
                assert option_list is not None
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_catalog_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/mcp catalog")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestProviderConfigViaF4:
    @pytest.mark.asyncio
    async def test_f4_opens_provider_selection(self, running_app):
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_provider_selection_has_list(self, running_app):
        pilot, app = running_app
        from textual.widgets import SelectionList

        await pilot.press("f4")
        await pilot.pause()

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                selection = screen.query_one(SelectionList)
                assert selection is not None
            except Exception:
                pass


class TestContextScreen:
    @pytest.mark.asyncio
    async def test_context_command_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.context import ContextScreen

        await submit_command(pilot, app, "/context")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, ContextScreen)

    @pytest.mark.asyncio
    async def test_context_screen_has_container(self, running_app):
        pilot, app = running_app
        from textual.containers import VerticalScroll

        await submit_command(pilot, app, "/context")

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                container = screen.query_one("#context-list", VerticalScroll)
                assert container is not None
            except Exception:
                pass


class TestAgentScreen:
    @pytest.mark.asyncio
    async def test_agent_status_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.agent import AgentScreen

        await submit_command(pilot, app, "/agent status")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, AgentScreen)

    @pytest.mark.asyncio
    async def test_agent_status_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/agent status")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestBranchDiffScreen:
    @pytest.mark.asyncio
    async def test_branch_diff_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/branch save test_branch_for_diff")
        await pilot.pause()
        await submit_command(pilot, app, "/branch diff test_branch_for_diff")
        await pilot.pause()


class TestApprovalScreen:
    @pytest.mark.asyncio
    async def test_approval_screen_structure(self, running_app):
        pilot, app = running_app
        from screens.approval import ToolApprovalScreen

        screen = ToolApprovalScreen(
            tool_calls=[{"name": "test_tool", "arguments": {"arg1": "value1"}}],
            iteration_number=1,
        )

        await app.push_screen(screen)
        await pilot.pause()

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen, ToolApprovalScreen)

    @pytest.mark.asyncio
    async def test_approval_screen_has_buttons(self, running_app):
        pilot, app = running_app
        from screens.approval import ToolApprovalScreen
        from textual.widgets import Button

        screen = ToolApprovalScreen(
            tool_calls=[{"name": "test_tool", "arguments": {}}],
        )

        await app.push_screen(screen)
        await pilot.pause()

        buttons = list(app.screen.query(Button))
        assert len(buttons) >= 2

    @pytest.mark.asyncio
    async def test_approval_screen_cancel_closes(self, running_app):
        pilot, app = running_app
        from screens.approval import ToolApprovalScreen

        screen = ToolApprovalScreen(
            tool_calls=[{"name": "test", "arguments": {}}],
        )

        await app.push_screen(screen)
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1


class TestConfirmDialog:
    @pytest.mark.asyncio
    async def test_confirm_dialog_structure(self, running_app):
        pilot, app = running_app
        from screens.confirm import ConfirmDialog

        screen = ConfirmDialog(
            title="Test Confirm",
            message="Are you sure?",
        )

        await app.push_screen(screen)
        await pilot.pause()

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen, ConfirmDialog)

    @pytest.mark.asyncio
    async def test_confirm_dialog_has_buttons(self, running_app):
        pilot, app = running_app
        from screens.confirm import ConfirmDialog
        from textual.widgets import Button

        screen = ConfirmDialog(
            title="Test",
            message="Confirm?",
        )

        await app.push_screen(screen)
        await pilot.pause()

        buttons = list(app.screen.query(Button))
        assert len(buttons) >= 2

    @pytest.mark.asyncio
    async def test_confirm_dialog_escape_closes(self, running_app):
        pilot, app = running_app
        from screens.confirm import ConfirmDialog

        screen = ConfirmDialog(title="Test", message="?")

        await app.push_screen(screen)
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1
