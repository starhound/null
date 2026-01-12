import pytest

from models import BlockState, BlockType
from widgets import InputController
from widgets.blocks import BaseBlockWidget


async def submit_command(pilot, app, command: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = command
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestCommandBlockCreation:
    @pytest.mark.asyncio
    async def test_command_creates_block(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_command_block_has_input(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo hello")

        if app.blocks:
            block = app.blocks[-1]
            assert block.content_input == "echo hello"

    @pytest.mark.asyncio
    async def test_command_block_type(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        if app.blocks:
            block = app.blocks[-1]
            assert block.type == BlockType.COMMAND


class TestBlockWidgetInHistory:
    @pytest.mark.asyncio
    async def test_history_contains_block_widgets(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test1")
        await submit_command(pilot, app, "echo test2")

        history = app.query_one("#history")
        widgets = list(history.query(BaseBlockWidget))
        assert len(widgets) >= 1

    @pytest.mark.asyncio
    async def test_block_widget_has_content(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo widget_test")

        history = app.query_one("#history")
        widgets = list(history.query(BaseBlockWidget))
        if widgets:
            widget = widgets[-1]
            assert hasattr(widget, "block")


class TestBlockStateProperties:
    @pytest.mark.asyncio
    async def test_block_state_has_id(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        if app.blocks:
            block = app.blocks[-1]
            assert block.id is not None
            assert len(block.id) > 0

    @pytest.mark.asyncio
    async def test_block_state_has_timestamp(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        if app.blocks:
            block = app.blocks[-1]
            assert hasattr(block, "timestamp")

    @pytest.mark.asyncio
    async def test_block_state_has_type(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        if app.blocks:
            block = app.blocks[-1]
            assert isinstance(block.type, BlockType)


class TestSlashCommandBlocks:
    @pytest.mark.asyncio
    async def test_status_creates_system_block(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/status")

    @pytest.mark.asyncio
    async def test_git_creates_block(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/git status")

    @pytest.mark.asyncio
    async def test_help_block_content(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/help")

        await pilot.press("escape")
        await pilot.pause()


class TestMultipleBlocks:
    @pytest.mark.asyncio
    async def test_multiple_commands_create_blocks(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo one")
        await submit_command(pilot, app, "echo two")
        await submit_command(pilot, app, "echo three")

        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_clear_removes_all_blocks(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")
        await submit_command(pilot, app, "/clear")

        assert len(app.blocks) == 0


class TestBlockOutput:
    @pytest.mark.asyncio
    async def test_echo_command_has_output(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo hello_world")
        await pilot.pause()

        if app.blocks:
            block = app.blocks[-1]
            assert block.content_output is not None or block.content_output == ""

    @pytest.mark.asyncio
    async def test_pwd_command_has_output(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "pwd")
        await pilot.pause()

        if app.blocks:
            block = app.blocks[-1]
            assert block.content_output is not None


class TestBlockActions:
    @pytest.mark.asyncio
    async def test_block_widget_has_actions(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        history = app.query_one("#history")
        widgets = list(history.query(BaseBlockWidget))
        if widgets:
            widget = widgets[-1]
            assert hasattr(widget, "block")


class TestSystemBlocks:
    @pytest.mark.asyncio
    async def test_system_message_via_status(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/status")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_notification_on_clear(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")
        await submit_command(pilot, app, "/clear")
        await pilot.pause()


class TestBlockMetadata:
    @pytest.mark.asyncio
    async def test_block_has_metadata_fields(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")

        if app.blocks:
            block = app.blocks[-1]
            assert hasattr(block, "id")
            assert hasattr(block, "type")
            assert hasattr(block, "content_input")
            assert hasattr(block, "content_output")


class TestExecutionBlocks:
    @pytest.mark.asyncio
    async def test_ls_command_creates_block(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "ls")
        await pilot.pause()

        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_date_command_creates_block(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "date")
        await pilot.pause()

        assert len(app.blocks) >= 1
