import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestConfigScreenOpening:
    @pytest.mark.asyncio
    async def test_settings_command_opens_screen(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        from screens.config import ConfigScreen

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen_stack[-1], ConfigScreen)

    @pytest.mark.asyncio
    async def test_settings_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1


class TestConfigScreenTabs:
    @pytest.mark.asyncio
    async def test_config_screen_has_tabbed_content(self, running_app):
        pilot, app = running_app
        from textual.widgets import TabbedContent

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        tabbed = screen.query_one(TabbedContent)
        assert tabbed is not None

    @pytest.mark.asyncio
    async def test_config_has_appearance_tab(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        tab = screen.query_one("#tab-appearance")
        assert tab is not None

    @pytest.mark.asyncio
    async def test_config_has_editor_tab(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        tab = screen.query_one("#tab-editor")
        assert tab is not None

    @pytest.mark.asyncio
    async def test_config_has_terminal_tab(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        tab = screen.query_one("#tab-terminal")
        assert tab is not None

    @pytest.mark.asyncio
    async def test_config_has_ai_tab(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        tab = screen.query_one("#tab-ai")
        assert tab is not None


class TestConfigScreenButtons:
    @pytest.mark.asyncio
    async def test_config_has_save_button(self, running_app):
        pilot, app = running_app
        from textual.widgets import Button

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        save_btn = screen.query_one("#save-btn", Button)
        assert save_btn is not None

    @pytest.mark.asyncio
    async def test_config_has_cancel_button(self, running_app):
        pilot, app = running_app
        from textual.widgets import Button

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        cancel_btn = screen.query_one("#cancel-btn", Button)
        assert cancel_btn is not None

    @pytest.mark.asyncio
    async def test_config_has_reset_button(self, running_app):
        pilot, app = running_app
        from textual.widgets import Button

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        reset_btn = screen.query_one("#reset-btn", Button)
        assert reset_btn is not None


class TestConfigScreenControls:
    @pytest.mark.asyncio
    async def test_config_has_theme_select(self, running_app):
        pilot, app = running_app
        from textual.widgets import Select

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        theme_select = screen.query_one("#theme", Select)
        assert theme_select is not None

    @pytest.mark.asyncio
    async def test_config_has_provider_select(self, running_app):
        pilot, app = running_app
        from textual.widgets import Select

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        provider_select = screen.query_one("#ai_provider", Select)
        assert provider_select is not None


class TestConfigScreenActions:
    @pytest.mark.asyncio
    async def test_cancel_button_closes_screen(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        from screens.config import ConfigScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, ConfigScreen)
        screen.action_cancel()
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_ctrl_s_saves_settings(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/settings")

        screen = app.screen_stack[-1]
        screen.action_save()
        await pilot.pause()
