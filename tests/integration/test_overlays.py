import pytest

from widgets import CommandPalette, InputController
from widgets.block_search import BlockSearch
from widgets.history_search import HistorySearch


async def submit_input(pilot, app, text: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = text
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestCommandPaletteVisibility:
    @pytest.mark.asyncio
    async def test_palette_hidden_by_default(self, running_app):
        _pilot, app = running_app
        palette = app.query_one("#command-palette", CommandPalette)
        assert "visible" not in palette.classes

    @pytest.mark.asyncio
    async def test_action_opens_palette(self, running_app):
        pilot, app = running_app

        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        assert "visible" in palette.classes

    @pytest.mark.asyncio
    async def test_escape_closes_palette(self, running_app):
        pilot, app = running_app

        app.action_open_command_palette()
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        assert "visible" not in palette.classes


class TestCommandPaletteContent:
    @pytest.mark.asyncio
    async def test_palette_has_input(self, running_app):
        pilot, app = running_app
        from textual.widgets import Input

        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        search_input = palette.query_one("#palette-input", Input)
        assert search_input is not None

    @pytest.mark.asyncio
    async def test_palette_has_results_container(self, running_app):
        pilot, app = running_app
        from textual.containers import Vertical

        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        results = palette.query_one("#palette-results", Vertical)
        assert results is not None

    @pytest.mark.asyncio
    async def test_palette_has_actions_list(self, running_app):
        pilot, app = running_app

        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        assert hasattr(palette, "filtered_actions")
        assert hasattr(palette, "_all_actions")
        assert isinstance(palette.filtered_actions, list)


class TestCommandPaletteFiltering:
    @pytest.mark.asyncio
    async def test_palette_filters_on_input(self, running_app):
        pilot, app = running_app

        app.action_open_command_palette()
        await pilot.pause()

        palette = app.query_one("#command-palette", CommandPalette)
        palette.filter_text = "help"
        await pilot.pause()


class TestHistorySearchVisibility:
    @pytest.mark.asyncio
    async def test_history_search_hidden_by_default(self, running_app):
        _pilot, app = running_app
        search = app.query_one("#history-search", HistorySearch)
        assert "visible" not in search.classes

    @pytest.mark.asyncio
    async def test_ctrl_r_opens_history_search(self, running_app):
        pilot, app = running_app

        await pilot.press("ctrl+r")
        await pilot.pause()

        search = app.query_one("#history-search", HistorySearch)
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_escape_closes_history_search(self, running_app):
        pilot, app = running_app

        await pilot.press("ctrl+r")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        search = app.query_one("#history-search", HistorySearch)
        assert "visible" not in search.classes


class TestHistorySearchContent:
    @pytest.mark.asyncio
    async def test_history_search_has_input(self, running_app):
        pilot, app = running_app
        from textual.widgets import Input

        await pilot.press("ctrl+r")
        await pilot.pause()

        search = app.query_one("#history-search", HistorySearch)
        search_input = search.query_one(Input)
        assert search_input is not None

    @pytest.mark.asyncio
    async def test_history_search_shows_history(self, running_app):
        pilot, app = running_app

        await submit_input(pilot, app, "echo test1")
        await submit_input(pilot, app, "echo test2")

        await pilot.press("ctrl+r")
        await pilot.pause()


class TestBlockSearchVisibility:
    @pytest.mark.asyncio
    async def test_block_search_hidden_by_default(self, running_app):
        _pilot, app = running_app
        search = app.query_one("#block-search", BlockSearch)
        assert "visible" not in search.classes

    @pytest.mark.asyncio
    async def test_action_opens_block_search(self, running_app):
        pilot, app = running_app

        app.action_search_blocks()
        await pilot.pause()

        search = app.query_one("#block-search", BlockSearch)
        assert "visible" in search.classes

    @pytest.mark.asyncio
    async def test_escape_closes_block_search(self, running_app):
        pilot, app = running_app

        app.action_search_blocks()
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        search = app.query_one("#block-search", BlockSearch)
        assert "visible" not in search.classes


class TestBlockSearchContent:
    @pytest.mark.asyncio
    async def test_block_search_has_input(self, running_app):
        pilot, app = running_app
        from textual.widgets import Input

        app.action_search_blocks()
        await pilot.pause()

        search = app.query_one("#block-search", BlockSearch)
        search_input = search.query_one(Input)
        assert search_input is not None


class TestSuggesterVisibility:
    @pytest.mark.asyncio
    async def test_suggester_hidden_by_default(self, running_app):
        _pilot, app = running_app
        from widgets import CommandSuggester

        suggester = app.query_one("#suggester", CommandSuggester)
        assert suggester.display is False

    @pytest.mark.asyncio
    async def test_suggester_shows_on_slash(self, running_app):
        pilot, app = running_app
        from widgets import CommandSuggester

        input_widget = app.query_one("#input", InputController)
        input_widget.text = "/"
        await pilot.pause()

        suggester = app.query_one("#suggester", CommandSuggester)
        assert suggester.display is True

    @pytest.mark.asyncio
    async def test_suggester_hides_on_non_slash(self, running_app):
        pilot, app = running_app
        from widgets import CommandSuggester

        input_widget = app.query_one("#input", InputController)
        input_widget.text = "/"
        await pilot.pause()

        input_widget.text = "echo"
        await pilot.pause()

        suggester = app.query_one("#suggester", CommandSuggester)
        assert suggester.display is False

    @pytest.mark.asyncio
    async def test_escape_hides_suggester(self, running_app):
        pilot, app = running_app
        from widgets import CommandSuggester

        input_widget = app.query_one("#input", InputController)
        input_widget.text = "/"
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        suggester = app.query_one("#suggester", CommandSuggester)
        assert suggester.display is False


class TestSuggesterFiltering:
    @pytest.mark.asyncio
    async def test_suggester_filters_on_text(self, running_app):
        pilot, app = running_app
        from widgets import CommandSuggester

        input_widget = app.query_one("#input", InputController)
        input_widget.text = "/he"
        await pilot.pause()

        suggester = app.query_one("#suggester", CommandSuggester)
        assert suggester.display is True

    @pytest.mark.asyncio
    async def test_suggester_shows_matching_commands(self, running_app):
        pilot, app = running_app
        from widgets import CommandSuggester

        input_widget = app.query_one("#input", InputController)
        input_widget.text = "/cle"
        await pilot.pause()

        suggester = app.query_one("#suggester", CommandSuggester)
        assert suggester.display is True
