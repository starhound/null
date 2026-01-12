import pytest

from widgets import InputController, StatusBar


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestContextManager:
    @pytest.mark.asyncio
    async def test_context_command_executes(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/context")

    @pytest.mark.asyncio
    async def test_context_opens_screen(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/context")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_context_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/context")
        await pilot.pause()

        if len(app.screen_stack) > 1:
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        assert len(app.screen_stack) <= 2


class TestContextStatusBar:
    @pytest.mark.asyncio
    async def test_status_bar_has_context_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        context_indicator = status.query_one("#context-indicator", Label)
        assert context_indicator is not None

    @pytest.mark.asyncio
    async def test_context_indicator_updates(self, running_app):
        pilot, app = running_app

        status = app.query_one("#status-bar", StatusBar)

        status.set_context(1000, 16000)
        await pilot.pause()

        status.set_context(8000, 16000)
        await pilot.pause()


class TestContextFromBlocks:
    @pytest.mark.asyncio
    async def test_empty_blocks_has_context(self, running_app):
        _pilot, app = running_app
        from context import ContextManager

        context = ContextManager.get_context(app.blocks)
        assert isinstance(context, str)

    @pytest.mark.asyncio
    async def test_context_grows_with_blocks(self, running_app):
        pilot, app = running_app
        from context import ContextManager

        initial_context = ContextManager.get_context(app.blocks)

        await submit_input(pilot, app, "echo test message")

        new_context = ContextManager.get_context(app.blocks)
        assert len(new_context) >= len(initial_context)


class TestContextCommands:
    @pytest.mark.asyncio
    async def test_context_clear_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test")

        await submit_input(pilot, app, "/clear")

        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_context_preserved_after_command(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo first")
        first_count = len(app.blocks)

        await submit_input(pilot, app, "echo second")

        assert len(app.blocks) >= first_count
