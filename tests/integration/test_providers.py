import pytest

from widgets import InputController


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestAIManager:
    @pytest.mark.asyncio
    async def test_app_has_ai_manager(self, running_app):
        _pilot, app = running_app
        assert app.ai_manager is not None

    @pytest.mark.asyncio
    async def test_ai_manager_has_get_usable_providers(self, running_app):
        _pilot, app = running_app
        providers = app.ai_manager.get_usable_providers()
        assert isinstance(providers, list)

    @pytest.mark.asyncio
    async def test_ai_manager_has_get_active_provider(self, running_app):
        _pilot, app = running_app
        provider = app.ai_manager.get_active_provider()
        assert provider is None or hasattr(provider, "generate_stream")


class TestProviderCommands:
    @pytest.mark.asyncio
    async def test_provider_command_executes(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/provider")

    @pytest.mark.asyncio
    async def test_providers_command_lists(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/providers")


class TestProviderSelection:
    @pytest.mark.asyncio
    async def test_f4_opens_provider_selection(self, running_app):
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_provider_selection_closes_with_escape(self, running_app):
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_provider_selection_has_items(self, running_app):
        pilot, app = running_app

        await pilot.press("f4")
        await pilot.pause()

        from screens.selection import SelectionListScreen

        screen = app.screen_stack[-1]
        assert isinstance(screen, SelectionListScreen)
        assert len(screen.items) > 0


class TestModelSelection:
    @pytest.mark.asyncio
    async def test_f2_opens_model_selection(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        assert len(app.screen_stack) > 1

    @pytest.mark.asyncio
    async def test_model_selection_closes_with_escape(self, running_app):
        pilot, app = running_app

        await pilot.press("f2")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_model_command_executes(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "/model")


class TestProviderStatusBar:
    @pytest.mark.asyncio
    async def test_status_bar_has_provider_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        from widgets import StatusBar

        status = app.query_one("#status-bar", StatusBar)
        provider_indicator = status.query_one("#provider-indicator", Label)
        assert provider_indicator is not None

    @pytest.mark.asyncio
    async def test_provider_indicator_updates(self, running_app):
        pilot, app = running_app
        from widgets import StatusBar

        status = app.query_one("#status-bar", StatusBar)

        status.set_provider("ollama", "connected")
        await pilot.pause()

        status.set_provider("openai", "disconnected")
        await pilot.pause()


class TestProviderFactory:
    def test_list_providers_returns_list(self):
        from ai.factory import AIFactory

        providers = AIFactory.list_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_get_provider_info_returns_dict(self):
        from ai.factory import AIFactory

        providers = AIFactory.list_providers()
        if providers:
            info = AIFactory.get_provider_info(providers[0])
            assert isinstance(info, dict)


class TestAppHeader:
    @pytest.mark.asyncio
    async def test_header_updates_with_provider(self, running_app):
        pilot, app = running_app
        from widgets import AppHeader

        header = app.query_one("#app-header", AppHeader)

        header.set_provider("test_provider", "test_model", connected=True)
        await pilot.pause()

        assert header.provider_text == "test_provider · test_model"

    @pytest.mark.asyncio
    async def test_header_shows_disconnected_state(self, running_app):
        pilot, app = running_app
        from widgets import AppHeader

        header = app.query_one("#app-header", AppHeader)

        header.set_provider("test", "", connected=False)
        await pilot.pause()

        assert header.connected is False
