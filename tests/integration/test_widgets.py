import pytest

from widgets import AppHeader, HistoryViewport, InputController, StatusBar


class TestInputControllerModes:
    @pytest.mark.asyncio
    async def test_input_starts_in_cli_mode(self, running_app):
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)
        assert input_widget.mode == "CLI"

    @pytest.mark.asyncio
    async def test_input_mode_property(self, running_app):
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)
        assert input_widget.is_ai_mode is False

    @pytest.mark.asyncio
    async def test_toggle_mode_changes_to_ai(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        assert input_widget.mode == "AI"
        assert input_widget.is_ai_mode is True

    @pytest.mark.asyncio
    async def test_toggle_mode_adds_css_class(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        await pilot.pause()

        assert "ai-mode" in input_widget.classes

    @pytest.mark.asyncio
    async def test_toggle_back_removes_css_class(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.toggle_mode()
        input_widget.toggle_mode()
        await pilot.pause()

        assert "ai-mode" not in input_widget.classes


class TestInputControllerText:
    @pytest.mark.asyncio
    async def test_input_accepts_text(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "hello world"
        await pilot.pause()

        assert input_widget.text == "hello world"

    @pytest.mark.asyncio
    async def test_input_clears_after_submit(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "echo test"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert input_widget.text == ""

    @pytest.mark.asyncio
    async def test_input_value_property(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.value = "test value"
        await pilot.pause()

        assert input_widget.value == "test value"


class TestInputControllerHistory:
    @pytest.mark.asyncio
    async def test_input_has_history(self, running_app):
        _pilot, app = running_app
        input_widget = app.query_one("#input", InputController)
        assert hasattr(input_widget, "cmd_history")

    @pytest.mark.asyncio
    async def test_history_stores_commands(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.text = "command1"
        await pilot.press("enter")
        await pilot.pause()

        assert "command1" in input_widget.cmd_history

    @pytest.mark.asyncio
    async def test_history_navigation_up(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = ["first", "second", "third"]

        input_widget.action_history_up()
        await pilot.pause()

        assert input_widget.text == "third"

    @pytest.mark.asyncio
    async def test_history_navigation_down(self, running_app):
        pilot, app = running_app
        input_widget = app.query_one("#input", InputController)

        input_widget.cmd_history = ["first", "second"]

        input_widget.action_history_up()
        input_widget.action_history_up()
        await pilot.pause()

        input_widget.action_history_down()
        await pilot.pause()

        assert input_widget.text == "second"


class TestStatusBarIndicators:
    @pytest.mark.asyncio
    async def test_status_bar_has_mode_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        mode = status.query_one("#mode-indicator", Label)
        assert mode is not None

    @pytest.mark.asyncio
    async def test_status_bar_mode_updates(self, running_app):
        pilot, app = running_app

        status = app.query_one("#status-bar", StatusBar)

        status.set_mode("CLI")
        await pilot.pause()
        assert status.mode == "CLI"

        status.set_mode("AI")
        await pilot.pause()
        assert status.mode == "AI"

    @pytest.mark.asyncio
    async def test_status_bar_has_provider_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        provider = status.query_one("#provider-indicator", Label)
        assert provider is not None

    @pytest.mark.asyncio
    async def test_status_bar_provider_updates(self, running_app):
        pilot, app = running_app

        status = app.query_one("#status-bar", StatusBar)

        status.set_provider("ollama", "connected")
        await pilot.pause()

        status.set_provider("openai", "disconnected")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_status_bar_has_context_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        context = status.query_one("#context-indicator", Label)
        assert context is not None

    @pytest.mark.asyncio
    async def test_status_bar_context_updates(self, running_app):
        pilot, app = running_app

        status = app.query_one("#status-bar", StatusBar)

        status.set_context(500, 4000)
        await pilot.pause()

        status.set_context(3500, 4000)
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_status_bar_has_git_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        git = status.query_one("#git-indicator", Label)
        assert git is not None

    @pytest.mark.asyncio
    async def test_status_bar_has_mcp_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        mcp = status.query_one("#mcp-indicator", Label)
        assert mcp is not None

    @pytest.mark.asyncio
    async def test_status_bar_has_process_indicator(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        status = app.query_one("#status-bar", StatusBar)
        process = status.query_one("#process-indicator", Label)
        assert process is not None


class TestAppHeaderContent:
    @pytest.mark.asyncio
    async def test_header_has_title(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        header = app.query_one("#app-header", AppHeader)
        title = header.query_one(".header-title", Label)
        assert title is not None

    @pytest.mark.asyncio
    async def test_header_has_left_section(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        header = app.query_one("#app-header", AppHeader)
        left = header.query_one(".header-left", Label)
        assert left is not None

    @pytest.mark.asyncio
    async def test_header_has_clock(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        header = app.query_one("#app-header", AppHeader)
        clock = header.query_one("#header-clock", Label)
        assert clock is not None

    @pytest.mark.asyncio
    async def test_header_set_provider_updates_text(self, running_app):
        pilot, app = running_app

        header = app.query_one("#app-header", AppHeader)

        header.set_provider("test_provider", "test_model", connected=True)
        await pilot.pause()

        assert "test_provider" in header.provider_text

    @pytest.mark.asyncio
    async def test_header_connected_state(self, running_app):
        pilot, app = running_app

        header = app.query_one("#app-header", AppHeader)

        header.set_provider("test", "model", connected=True)
        await pilot.pause()
        assert header.connected is True

        header.set_provider("test", "model", connected=False)
        await pilot.pause()
        assert header.connected is False


class TestHistoryViewportContent:
    @pytest.mark.asyncio
    async def test_history_viewport_exists(self, running_app):
        _pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)
        assert history is not None

    @pytest.mark.asyncio
    async def test_history_initially_empty(self, running_app):
        _pilot, app = running_app
        history = app.query_one("#history", HistoryViewport)
        assert len(list(history.children)) == 0

    @pytest.mark.asyncio
    async def test_history_add_block(self, running_app):
        pilot, app = running_app
        from models import BlockState, BlockType
        from widgets.blocks import create_block

        history = app.query_one("#history", HistoryViewport)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="test",
            content_output="output",
            is_running=False,
        )
        widget = create_block(block)
        await history.add_block(widget)
        await pilot.pause()

        assert len(list(history.children)) >= 1


class TestPromptLine:
    @pytest.mark.asyncio
    async def test_prompt_line_exists(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        prompt = app.query_one("#prompt-line", Label)
        assert prompt is not None

    @pytest.mark.asyncio
    async def test_prompt_has_content(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Label

        prompt = app.query_one("#prompt-line", Label)
        assert prompt is not None


class TestFooter:
    @pytest.mark.asyncio
    async def test_footer_exists(self, running_app):
        _pilot, app = running_app
        from textual.widgets import Footer

        footer = app.query_one(Footer)
        assert footer is not None
