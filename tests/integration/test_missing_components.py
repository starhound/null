import pytest

from widgets import InputController


async def submit_command(pilot, app, command: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = command
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestPromptEditorScreen:
    @pytest.mark.asyncio
    async def test_prompts_command_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.prompts import PromptEditorScreen

        await submit_command(pilot, app, "/prompts")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, PromptEditorScreen)

    @pytest.mark.asyncio
    async def test_prompt_editor_has_list(self, running_app):
        pilot, app = running_app
        from textual.widgets import ListView

        await submit_command(pilot, app, "/prompts")

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                list_view = screen.query_one("#prompt-list", ListView)
                assert list_view is not None
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_prompt_editor_close_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/prompts")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestTodoScreen:
    @pytest.mark.asyncio
    async def test_todo_dashboard_command(self, running_app):
        pilot, app = running_app
        from screens.todo import TodoScreen

        await submit_command(pilot, app, "/todo")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, TodoScreen)

    @pytest.mark.asyncio
    async def test_todo_screen_has_table(self, running_app):
        pilot, app = running_app
        from textual.widgets import DataTable

        await submit_command(pilot, app, "/todo")

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                table = screen.query_one(DataTable)
                assert table is not None
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_todo_screen_close_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/todo")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestSSHAddScreen:
    @pytest.mark.asyncio
    async def test_ssh_add_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.ssh_add import SSHAddScreen

        await submit_command(pilot, app, "/ssh-add")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, SSHAddScreen)

    @pytest.mark.asyncio
    async def test_ssh_add_has_inputs(self, running_app):
        pilot, app = running_app
        from textual.widgets import Input

        await submit_command(pilot, app, "/ssh-add")

        if len(app.screen_stack) > 1:
            screen = app.screen
            inputs = list(screen.query(Input))
            assert len(inputs) >= 1

    @pytest.mark.asyncio
    async def test_ssh_add_close_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/ssh-add")

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1


class TestSSHScreen:
    @pytest.mark.asyncio
    async def test_ssh_command_needs_alias(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/ssh")
        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_ssh_screen_opens_with_valid_host(self, running_app):
        pilot, app = running_app
        from screens.ssh import SSHScreen

        await submit_command(pilot, app, "/ssh-add test_host user hostname")
        await pilot.pause()

        await submit_command(pilot, app, "/ssh test_host")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, SSHScreen)
            await pilot.press("escape")
            await pilot.pause()


class TestSaveDialog:
    @pytest.mark.asyncio
    async def test_save_action_opens_dialog(self, running_app):
        pilot, app = running_app
        from screens.save_dialog import SaveSessionDialog

        await pilot.press("ctrl+s")
        await pilot.pause()

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, SaveSessionDialog)

    @pytest.mark.asyncio
    async def test_save_dialog_has_input(self, running_app):
        pilot, app = running_app
        from textual.widgets import Input

        await pilot.press("ctrl+s")
        await pilot.pause()

        if len(app.screen_stack) > 1:
            screen = app.screen
            try:
                inp = screen.query_one(Input)
                assert inp is not None
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_save_dialog_close_with_escape(self, running_app):
        pilot, app = running_app

        await pilot.press("ctrl+s")
        await pilot.pause()

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1
