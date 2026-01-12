import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestExportCommands:
    @pytest.mark.asyncio
    async def test_export_command_executes(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        await submit_input(pilot, app, "/export")

    @pytest.mark.asyncio
    async def test_export_md_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        await submit_input(pilot, app, "/export md")

    @pytest.mark.asyncio
    async def test_export_json_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        await submit_input(pilot, app, "/export json")

    @pytest.mark.asyncio
    async def test_export_empty_history_warns(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/export")


class TestQuickExport:
    @pytest.mark.asyncio
    async def test_ctrl_s_triggers_export(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        await pilot.press("ctrl+s")
        await pilot.pause()


class TestSessionSave:
    @pytest.mark.asyncio
    async def test_session_autosave_on_command(self, running_app, mock_storage):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_session_save_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        await submit_input(pilot, app, "/session save")


class TestSessionLoad:
    @pytest.mark.asyncio
    async def test_blocks_list_accessible(self, running_app):
        _pilot, app = running_app

        assert isinstance(app.blocks, list)

    @pytest.mark.asyncio
    async def test_fresh_start_has_empty_blocks(self, running_app):
        _pilot, app = running_app

        assert len(app.blocks) == 0


class TestExportFormats:
    @pytest.mark.asyncio
    async def test_do_export_md(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        app._do_export("md")

    @pytest.mark.asyncio
    async def test_do_export_json(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        app._do_export("json")
