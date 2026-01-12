import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestInvalidCommands:
    @pytest.mark.asyncio
    async def test_invalid_slash_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/nonexistentcommand")

    @pytest.mark.asyncio
    async def test_empty_input_ignored(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)

        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) == initial_blocks

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        initial_blocks = len(app.blocks)

        input_widget.text = "   "
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert len(app.blocks) == initial_blocks


class TestCommandFailures:
    @pytest.mark.asyncio
    async def test_failed_command_creates_block(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "nonexistent_command_xyz")

        assert len(app.blocks) >= 1

    @pytest.mark.asyncio
    async def test_command_with_invalid_args(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "ls --invalid-option-xyz")


class TestGracefulFailures:
    @pytest.mark.asyncio
    async def test_app_stays_running_after_error(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/invalid")

        assert app.is_running

    @pytest.mark.asyncio
    async def test_input_focusable_after_error(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        await submit_input(pilot, app, "/invalid")

        input_widget.focus()
        await pilot.pause()

        assert input_widget.has_focus


class TestCancelOperations:
    @pytest.mark.asyncio
    async def test_escape_cancels_operation(self, running_app):
        pilot, app = running_app

        app.action_cancel_operation()
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_app_not_busy_after_cancel(self, running_app):
        pilot, app = running_app

        app.action_cancel_operation()
        await pilot.pause()

        assert not app.is_busy()


class TestErrorDetector:
    @pytest.mark.asyncio
    async def test_app_has_error_detector(self, running_app):
        _pilot, app = running_app

        assert app.error_detector is not None


class TestProcessManager:
    @pytest.mark.asyncio
    async def test_app_has_process_manager(self, running_app):
        _pilot, app = running_app

        assert app.process_manager is not None

    @pytest.mark.asyncio
    async def test_process_count_starts_at_zero(self, running_app):
        _pilot, app = running_app

        count = app.process_manager.get_count()
        assert count == 0


class TestBranchManager:
    @pytest.mark.asyncio
    async def test_app_has_branch_manager(self, running_app):
        _pilot, app = running_app

        assert app.branch_manager is not None
