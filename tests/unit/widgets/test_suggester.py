"""Tests for widgets/suggester.py - CommandSuggester and CommandItem widgets."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.events import Click
from textual.timer import Timer
from textual.widgets import Label, ListView

from managers.suggestions import Suggestion
from widgets.suggester import CommandItem, CommandSuggester


# =============================================================================
# CommandItem Tests
# =============================================================================


class TestCommandItemInit:
    """Tests for CommandItem initialization."""

    def test_basic_init(self):
        """CommandItem should initialize with label and value."""
        item = CommandItem("Test Label", "test-value")
        assert item.value == "test-value"

    def test_inherits_from_listitem(self):
        """CommandItem should inherit from ListItem."""
        from textual.widgets import ListItem

        item = CommandItem("Test Label", "test-value")
        assert isinstance(item, ListItem)

    def test_passes_label_to_parent(self):
        """CommandItem should pass Label to ListItem parent init."""
        item = CommandItem("My Command", "cmd")
        assert item._nodes is not None

    def test_value_different_from_label(self):
        """Value can be different from label text."""
        item = CommandItem("/help        Show help", "/help")
        assert item.value == "/help"

    def test_not_ai_by_default(self):
        """Items should not have ai-suggestion class by default."""
        item = CommandItem("test", "test")
        assert "ai-suggestion" not in item.classes

    def test_ai_suggestion_class_added(self):
        """AI suggestions should have ai-suggestion class."""
        item = CommandItem("AI cmd", "cmd", is_ai=True)
        assert "ai-suggestion" in item.classes

    def test_ai_false_no_class(self):
        """Explicit is_ai=False should not add class."""
        item = CommandItem("cmd", "cmd", is_ai=False)
        assert "ai-suggestion" not in item.classes

    def test_empty_label(self):
        """Empty label should be allowed."""
        item = CommandItem("", "value")
        assert item.value == "value"

    def test_empty_value(self):
        """Empty value should be allowed."""
        item = CommandItem("Label", "")
        assert item.value == ""

    def test_special_characters_in_label(self):
        """Special characters in label should work."""
        item = CommandItem("/help [option] --flag", "/help")
        assert item.value == "/help"

    def test_unicode_label(self):
        """Unicode characters in label should work."""
        item = CommandItem("📁 /files", "/files")
        assert item.value == "/files"


class TestCommandItemEdgeCases:
    """Edge case tests for CommandItem."""

    def test_multiline_label(self):
        """Multiline labels should be handled."""
        item = CommandItem("line1\nline2", "value")
        assert item.value == "value"

    def test_whitespace_value(self):
        """Whitespace-only value should be preserved."""
        item = CommandItem("label", "   ")
        assert item.value == "   "

    def test_very_long_label(self):
        """Very long labels should be handled."""
        long_label = "x" * 1000
        item = CommandItem(long_label, "value")
        assert item.value == "value"


# =============================================================================
# CommandSuggester Initialization Tests
# =============================================================================


class TestCommandSuggesterInit:
    """Tests for CommandSuggester initialization."""

    def test_can_focus_is_false(self):
        """CommandSuggester should not be focusable."""
        suggester = CommandSuggester()
        assert suggester.can_focus is False

    def test_selected_index_default(self):
        """Default selected index should be 0."""
        suggester = CommandSuggester()
        assert suggester._selected_index == 0

    def test_debounce_timer_default(self):
        """Debounce timer should be None initially."""
        suggester = CommandSuggester()
        assert suggester._debounce_timer is None

    def test_current_task_default(self):
        """Current task should be None initially."""
        suggester = CommandSuggester()
        assert suggester._current_task is None

    def test_last_input_default(self):
        """Last input should be empty string initially."""
        suggester = CommandSuggester()
        assert suggester.last_input == ""

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        suggester = CommandSuggester(id="my-suggester")
        assert suggester.id == "my-suggester"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        suggester = CommandSuggester(classes="custom-class")
        assert "custom-class" in suggester.classes


# =============================================================================
# SuggestionReady Message Tests
# =============================================================================


class TestSuggestionReadyMessage:
    """Tests for SuggestionReady message class."""

    def test_message_stores_suggestion(self):
        """Message should store the suggestion string."""
        msg = CommandSuggester.SuggestionReady("ls -la")
        assert msg.suggestion == "ls -la"

    def test_message_empty_suggestion(self):
        """Message should handle empty suggestion."""
        msg = CommandSuggester.SuggestionReady("")
        assert msg.suggestion == ""

    def test_message_complex_suggestion(self):
        """Message should handle complex command strings."""
        cmd = "git commit -m 'fix: update readme'"
        msg = CommandSuggester.SuggestionReady(cmd)
        assert msg.suggestion == cmd

    def test_message_unicode_suggestion(self):
        """Message should handle unicode in suggestions."""
        msg = CommandSuggester.SuggestionReady("echo 'Hello 世界'")
        assert msg.suggestion == "echo 'Hello 世界'"


# =============================================================================
# Compose Method Tests
# =============================================================================


class TestCommandSuggesterCompose:
    """Tests for compose method."""

    def test_compose_yields_listview(self):
        """Compose should yield a ListView."""
        suggester = CommandSuggester()
        children = list(suggester.compose())
        assert len(children) == 1
        assert isinstance(children[0], ListView)

    def test_listview_has_suggestions_id(self):
        """ListView should have 'suggestions' id."""
        suggester = CommandSuggester()
        children = list(suggester.compose())
        assert children[0].id == "suggestions"

    def test_listview_not_focusable(self):
        """ListView should not be focusable."""
        suggester = CommandSuggester()
        children = list(suggester.compose())
        assert children[0].can_focus is False


# =============================================================================
# commands_data Property Tests
# =============================================================================


class TestCommandsDataProperty:
    """Tests for commands_data property."""

    def test_no_app_returns_empty(self):
        """Without app context, should return empty dict."""
        suggester = CommandSuggester()
        # No app attached, should handle gracefully
        assert suggester.commands_data == {}

    def test_no_handler_returns_empty(self):
        """Without command_handler, should return empty dict."""
        suggester = CommandSuggester()
        suggester._app = MagicMock()
        suggester._app.command_handler = None
        assert suggester.commands_data == {}

    def test_handler_exception_returns_empty(self):
        """Exception in handler should return empty dict."""
        suggester = CommandSuggester()
        mock_app = MagicMock()
        mock_app.command_handler.get_all_commands.side_effect = Exception("Error")
        suggester._app = mock_app
        assert suggester.commands_data == {}

    def test_parses_commands_correctly(self):
        """Should parse commands into expected format."""
        suggester = CommandSuggester()

        mock_cmd = MagicMock()
        mock_cmd.name = "help"
        mock_cmd.description = "Show help"
        mock_cmd.subcommands = [("list", "List items"), ("add item", "Add item")]

        mock_handler = MagicMock()
        mock_handler.get_all_commands.return_value = [mock_cmd]

        with patch.object(
            type(suggester),
            "app",
            new_callable=lambda: property(
                lambda self: MagicMock(command_handler=mock_handler)
            ),
        ):
            data = suggester.commands_data
            assert "/help" in data
            assert data["/help"]["desc"] == "Show help"
            assert "list" in data["/help"]["args"]
            assert "add" in data["/help"]["args"]

    def test_empty_subcommand_handled(self):
        """Empty subcommands should be handled."""
        suggester = CommandSuggester()

        mock_cmd = MagicMock()
        mock_cmd.name = "test"
        mock_cmd.description = "Test cmd"
        mock_cmd.subcommands = [("", ""), (None, None)]

        mock_handler = MagicMock()
        mock_handler.get_all_commands.return_value = [mock_cmd]

        with patch.object(
            type(suggester),
            "app",
            new_callable=lambda: property(
                lambda self: MagicMock(command_handler=mock_handler)
            ),
        ):
            data = suggester.commands_data
            assert "/test" in data
            assert data["/test"]["args"] == []


# =============================================================================
# update_filter Method Tests
# =============================================================================


class TestUpdateFilter:
    """Tests for update_filter method."""

    def test_stores_last_input(self):
        """Should store the input text as last_input."""
        suggester = CommandSuggester()
        suggester._update_slash_commands = MagicMock()
        suggester.update_filter("/help")
        assert suggester.last_input == "/help"

    def test_slash_command_calls_update_slash_commands(self):
        """Slash commands should call _update_slash_commands."""
        suggester = CommandSuggester()
        suggester._update_slash_commands = MagicMock()
        suggester.update_filter("/test")
        suggester._update_slash_commands.assert_called_once_with("/test")

    def test_non_slash_with_ai_disabled_hides(self):
        """Non-slash input with AI disabled should hide suggester."""
        suggester = CommandSuggester()
        suggester.display = True

        with patch("widgets.suggester.Config") as mock_config:
            mock_config.get.return_value = "False"
            suggester.update_filter("ls")

        assert suggester.display is False

    def test_non_slash_with_ai_enabled_debounces(self):
        """Non-slash input with AI enabled should debounce."""
        suggester = CommandSuggester()
        suggester._debounce_ai_fetch = MagicMock()

        with patch("widgets.suggester.Config") as mock_config:
            mock_config.get.return_value = "True"
            suggester.update_filter("ls")

        suggester._debounce_ai_fetch.assert_called_once_with("ls")

    def test_ai_enabled_various_true_values(self):
        """Various truthy string values should enable AI."""
        suggester = CommandSuggester()
        suggester._debounce_ai_fetch = MagicMock()

        for val in ["true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"]:
            suggester._debounce_ai_fetch.reset_mock()
            with patch("widgets.suggester.Config") as mock_config:
                mock_config.get.return_value = val
                suggester.update_filter("test")
            suggester._debounce_ai_fetch.assert_called_once()

    def test_ai_disabled_various_false_values(self):
        """Various falsy string values should disable AI."""
        suggester = CommandSuggester()
        suggester.display = True

        for val in ["false", "False", "FALSE", "0", "no", "No", "off", "OFF"]:
            with patch("widgets.suggester.Config") as mock_config:
                mock_config.get.return_value = val
                suggester.update_filter("test")
            assert suggester.display is False


# =============================================================================
# _update_slash_commands Method Tests
# =============================================================================


class TestUpdateSlashCommands:
    """Tests for _update_slash_commands method."""

    def _mock_commands_data(self, suggester, data):
        """Helper to mock commands_data property via app.command_handler."""
        mock_handler = MagicMock()
        cmds = []
        for cmd_name, info in data.items():
            mock_cmd = MagicMock()
            mock_cmd.name = cmd_name.lstrip("/")
            mock_cmd.description = info["desc"]
            mock_cmd.subcommands = [(arg, "") for arg in info["args"]]
            cmds.append(mock_cmd)
        mock_handler.get_all_commands.return_value = cmds
        mock_app = MagicMock()
        mock_app.command_handler = mock_handler
        return patch.object(
            type(suggester), "app", new_callable=lambda: property(lambda self: mock_app)
        )

    def test_no_candidates_hides_suggester(self):
        """No matching candidates should hide suggester."""
        suggester = CommandSuggester()
        suggester.display = True

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        with self._mock_commands_data(suggester, {}):
            suggester._update_slash_commands("/nonexistent")

        assert suggester.display is False

    def test_matching_commands_shown(self):
        """Matching commands should be shown."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        with self._mock_commands_data(
            suggester,
            {
                "/help": {"desc": "Show help", "args": []},
                "/history": {"desc": "History", "args": []},
            },
        ):
            suggester._update_slash_commands("/h")

        assert suggester.display is True
        assert mock_lv.append.call_count == 2

    def test_args_mode_filters_args(self):
        """Args mode should filter subcommand args."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        with self._mock_commands_data(
            suggester,
            {"/mcp": {"desc": "MCP commands", "args": ["add", "remove", "list"]}},
        ):
            suggester._update_slash_commands("/mcp a")

        assert suggester.display is True
        assert mock_lv.append.call_count == 1

    def test_resets_selected_index(self):
        """Should reset selected index to 0."""
        suggester = CommandSuggester()
        suggester._selected_index = 5
        suggester._update_highlight = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        with self._mock_commands_data(
            suggester, {"/help": {"desc": "Help", "args": []}}
        ):
            suggester._update_slash_commands("/h")

        assert suggester._selected_index == 0

    def test_clears_listview_first(self):
        """Should clear ListView before adding new items."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        with self._mock_commands_data(
            suggester, {"/help": {"desc": "Help", "args": []}}
        ):
            suggester._update_slash_commands("/h")

        mock_lv.clear.assert_called_once()


# =============================================================================
# _debounce_ai_fetch Method Tests
# =============================================================================


class TestDebounceAiFetch:
    """Tests for _debounce_ai_fetch method."""

    def test_empty_text_hides_suggester(self):
        """Empty text should hide suggester."""
        suggester = CommandSuggester()
        suggester.display = True
        suggester._debounce_ai_fetch("")
        assert suggester.display is False

    def test_whitespace_only_hides_suggester(self):
        """Whitespace-only text should hide suggester."""
        suggester = CommandSuggester()
        suggester.display = True
        suggester._debounce_ai_fetch("   ")
        assert suggester.display is False

    def test_stops_existing_timer(self):
        """Should stop existing debounce timer."""
        suggester = CommandSuggester()
        mock_timer = MagicMock(spec=Timer)
        suggester._debounce_timer = mock_timer
        suggester.set_timer = MagicMock()

        suggester._debounce_ai_fetch("test")

        mock_timer.stop.assert_called_once()

    def test_cancels_existing_task(self):
        """Should cancel existing task."""
        suggester = CommandSuggester()
        mock_task = MagicMock()
        suggester._current_task = mock_task
        suggester.set_timer = MagicMock()

        suggester._debounce_ai_fetch("test")

        mock_task.cancel.assert_called_once()

    def test_sets_new_timer(self):
        """Should set a new timer for debouncing."""
        suggester = CommandSuggester()
        suggester.set_timer = MagicMock()

        suggester._debounce_ai_fetch("test")

        suggester.set_timer.assert_called_once()
        # Check first argument is 0.6 seconds
        assert suggester.set_timer.call_args[0][0] == 0.6


# =============================================================================
# _fetch_ai_suggestion Method Tests
# =============================================================================


class TestFetchAiSuggestion:
    """Tests for _fetch_ai_suggestion async method."""

    @pytest.mark.asyncio
    async def test_no_engine_returns_early(self):
        """Without suggestion_engine, should return early."""
        suggester = CommandSuggester()
        suggester._show_ai_suggestions = MagicMock()

        mock_app = MagicMock()
        mock_app.suggestion_engine = None
        suggester._app = mock_app

        await suggester._fetch_ai_suggestion("test")

        suggester._show_ai_suggestions.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_engine_suggest(self):
        """Should call engine.suggest with correct params."""
        suggester = CommandSuggester()
        suggester._show_ai_suggestions = MagicMock()

        mock_suggestion = Suggestion(
            command="ls -la", description="List files", source="ai"
        )
        mock_engine = MagicMock()
        mock_engine.suggest = AsyncMock(return_value=[mock_suggestion])
        mock_provider = MagicMock()

        with patch.object(
            type(suggester),
            "app",
            new_callable=lambda: property(
                lambda self: MagicMock(
                    suggestion_engine=mock_engine, ai_provider=mock_provider
                )
            ),
        ):
            await suggester._fetch_ai_suggestion("ls")

        mock_engine.suggest.assert_called_once_with(
            "ls", mock_provider, max_suggestions=3
        )

    @pytest.mark.asyncio
    async def test_shows_suggestions_when_different(self):
        """Should show suggestions when command differs from input."""
        suggester = CommandSuggester()
        suggester._show_ai_suggestions = MagicMock()

        mock_suggestion = Suggestion(
            command="ls -la", description="List files", source="ai"
        )
        mock_engine = MagicMock()
        mock_engine.suggest = AsyncMock(return_value=[mock_suggestion])

        with patch.object(
            type(suggester),
            "app",
            new_callable=lambda: property(
                lambda self: MagicMock(
                    suggestion_engine=mock_engine, ai_provider=MagicMock()
                )
            ),
        ):
            await suggester._fetch_ai_suggestion("ls")

        suggester._show_ai_suggestions.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_show_when_same_as_input(self):
        """Should not show when suggestion equals input."""
        suggester = CommandSuggester()
        suggester._show_ai_suggestions = MagicMock()

        mock_suggestion = Suggestion(command="ls", description="", source="ai")
        mock_engine = MagicMock()
        mock_engine.suggest = AsyncMock(return_value=[mock_suggestion])

        mock_app = MagicMock()
        mock_app.suggestion_engine = mock_engine
        mock_app.ai_provider = MagicMock()
        suggester._app = mock_app

        await suggester._fetch_ai_suggestion("ls")

        suggester._show_ai_suggestions.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_suggestions_no_show(self):
        """Empty suggestions should not call show."""
        suggester = CommandSuggester()
        suggester._show_ai_suggestions = MagicMock()

        mock_engine = MagicMock()
        mock_engine.suggest = AsyncMock(return_value=[])

        mock_app = MagicMock()
        mock_app.suggestion_engine = mock_engine
        mock_app.ai_provider = MagicMock()
        suggester._app = mock_app

        await suggester._fetch_ai_suggestion("test")

        suggester._show_ai_suggestions.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_handled_gracefully(self):
        """Exceptions should be handled gracefully."""
        suggester = CommandSuggester()
        suggester._show_ai_suggestions = MagicMock()

        mock_engine = MagicMock()
        mock_engine.suggest = AsyncMock(side_effect=Exception("Network error"))

        mock_app = MagicMock()
        mock_app.suggestion_engine = mock_engine
        mock_app.ai_provider = MagicMock()
        suggester._app = mock_app

        # Should not raise
        await suggester._fetch_ai_suggestion("test")
        suggester._show_ai_suggestions.assert_not_called()


# =============================================================================
# _show_ai_suggestions Method Tests
# =============================================================================


class TestShowAiSuggestions:
    """Tests for _show_ai_suggestions method."""

    def test_empty_suggestions_hides(self):
        """Empty suggestions should hide suggester."""
        suggester = CommandSuggester()
        suggester.display = True

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggester._show_ai_suggestions([])

        assert suggester.display is False

    def test_shows_suggester_with_suggestions(self):
        """Should show suggester when suggestions exist."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggestions = [
            Suggestion(command="ls", description="List", source="history"),
        ]
        suggester._show_ai_suggestions(suggestions)

        assert suggester.display is True

    def test_resets_selected_index(self):
        """Should reset selected index to 0."""
        suggester = CommandSuggester()
        suggester._selected_index = 3
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggestions = [Suggestion(command="ls", description="", source="ai")]
        suggester._show_ai_suggestions(suggestions)

        assert suggester._selected_index == 0

    def test_adds_correct_icons(self):
        """Should add correct source icons."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggestions = [
            Suggestion(command="cmd1", description="", source="history"),
            Suggestion(command="cmd2", description="", source="context"),
            Suggestion(command="cmd3", description="", source="ai"),
        ]
        suggester._show_ai_suggestions(suggestions)

        # Check all 3 items were added
        assert mock_lv.append.call_count == 3

    def test_posts_suggestion_ready_message(self):
        """Should post SuggestionReady message with first suggestion."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggestions = [
            Suggestion(command="ls -la", description="", source="ai"),
        ]
        suggester._show_ai_suggestions(suggestions)

        suggester.post_message.assert_called_once()
        msg = suggester.post_message.call_args[0][0]
        assert isinstance(msg, CommandSuggester.SuggestionReady)
        assert msg.suggestion == "ls -la"


# =============================================================================
# _show_ai_suggestion Method Tests (Single Suggestion)
# =============================================================================


class TestShowAiSuggestion:
    """Tests for _show_ai_suggestion method (single suggestion)."""

    def test_clears_listview(self):
        """Should clear ListView first."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggester._show_ai_suggestion("test")

        mock_lv.clear.assert_called_once()

    def test_adds_item_with_sparkle(self):
        """Should add item with sparkle emoji."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggester._show_ai_suggestion("ls -la")

        mock_lv.append.assert_called_once()

    def test_sets_display_true(self):
        """Should set display to True."""
        suggester = CommandSuggester()
        suggester.display = False
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggester._show_ai_suggestion("test")

        assert suggester.display is True

    def test_posts_message(self):
        """Should post SuggestionReady message."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()
        suggester.post_message = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggester._show_ai_suggestion("my-command")

        msg = suggester.post_message.call_args[0][0]
        assert msg.suggestion == "my-command"


# =============================================================================
# Selection Navigation Tests
# =============================================================================


class TestSelectNext:
    """Tests for select_next method."""

    def test_increments_index(self):
        """Should increment selected index."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()

        mock_items = [MagicMock(), MagicMock(), MagicMock()]
        suggester.query = MagicMock(return_value=mock_items)

        suggester.select_next()

        assert suggester._selected_index == 1

    def test_does_not_exceed_max(self):
        """Should not exceed max index."""
        suggester = CommandSuggester()
        suggester._selected_index = 2
        suggester._update_highlight = MagicMock()

        mock_items = [MagicMock(), MagicMock(), MagicMock()]
        suggester.query = MagicMock(return_value=mock_items)

        suggester.select_next()

        assert suggester._selected_index == 2

    def test_no_items_no_change(self):
        """No items should not change index."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()

        suggester.query = MagicMock(return_value=[])

        suggester.select_next()

        assert suggester._selected_index == 0

    def test_calls_update_highlight(self):
        """Should call _update_highlight when index changes."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()

        mock_items = [MagicMock(), MagicMock()]
        suggester.query = MagicMock(return_value=mock_items)

        suggester.select_next()

        suggester._update_highlight.assert_called_once()


class TestSelectPrev:
    """Tests for select_prev method."""

    def test_decrements_index(self):
        """Should decrement selected index."""
        suggester = CommandSuggester()
        suggester._selected_index = 2
        suggester._update_highlight = MagicMock()

        suggester.select_prev()

        assert suggester._selected_index == 1

    def test_does_not_go_below_zero(self):
        """Should not go below 0."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()

        suggester.select_prev()

        assert suggester._selected_index == 0

    def test_calls_update_highlight(self):
        """Should call _update_highlight when index changes."""
        suggester = CommandSuggester()
        suggester._selected_index = 2
        suggester._update_highlight = MagicMock()

        suggester.select_prev()

        suggester._update_highlight.assert_called_once()

    def test_no_highlight_at_zero(self):
        """At zero, should not call update_highlight."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()

        suggester.select_prev()

        suggester._update_highlight.assert_not_called()


# =============================================================================
# get_selected Method Tests
# =============================================================================


class TestGetSelected:
    """Tests for get_selected method."""

    def test_returns_selected_value(self):
        """Should return value of selected item."""
        suggester = CommandSuggester()
        suggester._selected_index = 1

        mock_item1 = MagicMock(spec=CommandItem)
        mock_item1.value = "cmd1"
        mock_item2 = MagicMock(spec=CommandItem)
        mock_item2.value = "cmd2"

        suggester.query = MagicMock(return_value=[mock_item1, mock_item2])

        assert suggester.get_selected() == "cmd2"

    def test_returns_empty_when_no_items(self):
        """Should return empty string when no items."""
        suggester = CommandSuggester()
        suggester._selected_index = 0

        suggester.query = MagicMock(return_value=[])

        assert suggester.get_selected() == ""

    def test_returns_empty_when_index_out_of_bounds(self):
        """Should return empty string when index out of bounds."""
        suggester = CommandSuggester()
        suggester._selected_index = 10

        mock_item = MagicMock(spec=CommandItem)
        mock_item.value = "cmd"

        suggester.query = MagicMock(return_value=[mock_item])

        assert suggester.get_selected() == ""

    def test_returns_empty_for_negative_index(self):
        """Should return empty string for negative index."""
        suggester = CommandSuggester()
        suggester._selected_index = -1

        mock_item = MagicMock(spec=CommandItem)
        mock_item.value = "cmd"

        suggester.query = MagicMock(return_value=[mock_item])

        assert suggester.get_selected() == ""


# =============================================================================
# _update_highlight Method Tests
# =============================================================================


class TestUpdateHighlight:
    """Tests for _update_highlight method."""

    def test_adds_highlight_to_selected(self):
        """Should add --highlight class to selected item."""
        suggester = CommandSuggester()
        suggester._selected_index = 1

        mock_item0 = MagicMock(spec=CommandItem)
        mock_item1 = MagicMock(spec=CommandItem)

        suggester.query = MagicMock(return_value=[mock_item0, mock_item1])
        suggester.query_one = MagicMock(side_effect=Exception("No ListView"))

        suggester._update_highlight()

        mock_item0.remove_class.assert_called_with("--highlight")
        mock_item1.add_class.assert_called_with("--highlight")

    def test_removes_highlight_from_others(self):
        """Should remove --highlight from non-selected items."""
        suggester = CommandSuggester()
        suggester._selected_index = 0

        mock_item0 = MagicMock(spec=CommandItem)
        mock_item1 = MagicMock(spec=CommandItem)
        mock_item2 = MagicMock(spec=CommandItem)

        suggester.query = MagicMock(return_value=[mock_item0, mock_item1, mock_item2])
        suggester.query_one = MagicMock(side_effect=Exception("No ListView"))

        suggester._update_highlight()

        mock_item0.add_class.assert_called_with("--highlight")
        mock_item1.remove_class.assert_called_with("--highlight")
        mock_item2.remove_class.assert_called_with("--highlight")

    def test_scrolls_to_selected_item(self):
        """Should scroll ListView to selected item."""
        suggester = CommandSuggester()
        suggester._selected_index = 1

        mock_item0 = MagicMock(spec=CommandItem)
        mock_item1 = MagicMock(spec=CommandItem)

        mock_lv = MagicMock(spec=ListView)

        suggester.query = MagicMock(return_value=[mock_item0, mock_item1])
        suggester.query_one = MagicMock(return_value=mock_lv)

        suggester._update_highlight()

        mock_lv.scroll_to_widget.assert_called_once_with(mock_item1)

    def test_handles_scroll_exception(self):
        """Should handle scroll exceptions gracefully."""
        suggester = CommandSuggester()
        suggester._selected_index = 0

        mock_item = MagicMock(spec=CommandItem)

        mock_lv = MagicMock(spec=ListView)
        mock_lv.scroll_to_widget.side_effect = Exception("Scroll error")

        suggester.query = MagicMock(return_value=[mock_item])
        suggester.query_one = MagicMock(return_value=mock_lv)

        # Should not raise
        suggester._update_highlight()


# =============================================================================
# on_click Handler Tests
# =============================================================================


class TestOnClick:
    """Tests for on_click event handler."""

    def test_click_on_item_selects_it(self):
        """Clicking an item should select it."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()
        suggester._apply_selection = MagicMock()

        mock_item = MagicMock(spec=CommandItem)
        mock_item.region.contains.return_value = True

        suggester.query = MagicMock(return_value=[mock_item])

        mock_event = MagicMock(spec=Click)
        mock_event.x = 10
        mock_event.y = 10

        suggester.on_click(mock_event)

        assert suggester._selected_index == 0
        suggester._update_highlight.assert_called_once()
        suggester._apply_selection.assert_called_once()
        mock_event.stop.assert_called_once()

    def test_click_on_second_item(self):
        """Clicking second item should set index to 1."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()
        suggester._apply_selection = MagicMock()

        mock_item0 = MagicMock(spec=CommandItem)
        mock_item0.region.contains.return_value = False
        mock_item1 = MagicMock(spec=CommandItem)
        mock_item1.region.contains.return_value = True

        suggester.query = MagicMock(return_value=[mock_item0, mock_item1])

        mock_event = MagicMock(spec=Click)
        mock_event.x = 10
        mock_event.y = 50

        suggester.on_click(mock_event)

        assert suggester._selected_index == 1

    def test_click_outside_items_no_action(self):
        """Clicking outside items should do nothing."""
        suggester = CommandSuggester()
        suggester._selected_index = 0
        suggester._update_highlight = MagicMock()
        suggester._apply_selection = MagicMock()

        mock_item = MagicMock(spec=CommandItem)
        mock_item.region.contains.return_value = False

        suggester.query = MagicMock(return_value=[mock_item])

        mock_event = MagicMock(spec=Click)
        mock_event.x = 100
        mock_event.y = 100

        suggester.on_click(mock_event)

        suggester._update_highlight.assert_not_called()
        suggester._apply_selection.assert_not_called()


# =============================================================================
# _apply_selection Method Tests
# =============================================================================


class TestApplySelection:
    """Tests for _apply_selection method."""

    def test_single_word_completion(self):
        """Single word input should be replaced entirely."""
        suggester = CommandSuggester()
        suggester.get_selected = MagicMock(return_value="/help")

        class MockInput:
            def __init__(self):
                self.text = "/hel"

            def move_cursor(self, pos):
                pass

        mock_input = MockInput()
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_input

        with patch.object(
            type(suggester), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("widgets.suggester.cast", side_effect=lambda t, x: x):
                suggester._apply_selection()

        assert mock_input.text == "/help "
        assert suggester.display is False

    def test_multi_word_completion(self):
        """Multi-word input should complete the last part."""
        suggester = CommandSuggester()
        suggester.get_selected = MagicMock(return_value="add")

        class MockInput:
            def __init__(self):
                self.text = "/mcp a"

            def move_cursor(self, pos):
                pass

        mock_input = MockInput()
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_input

        with patch.object(
            type(suggester), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("widgets.suggester.cast", side_effect=lambda t, x: x):
                suggester._apply_selection()

        assert mock_input.text == "/mcp add "
        assert suggester.display is False

    def test_no_selection_no_change(self):
        """No selection should not modify input."""
        suggester = CommandSuggester()
        suggester.get_selected = MagicMock(return_value="")

        mock_input = MagicMock()
        mock_input.text = "/test"

        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_input

        with patch.object(
            type(suggester), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("widgets.suggester.cast", side_effect=lambda t, x: x):
                suggester._apply_selection()

        mock_input.move_cursor.assert_not_called()

    def test_moves_cursor_to_end(self):
        """Should move cursor to end of text."""
        suggester = CommandSuggester()
        suggester.get_selected = MagicMock(return_value="/help")

        class MockInput:
            def __init__(self):
                self.text = "/h"
                self.cursor_moved = False
                self.cursor_pos = None

            def move_cursor(self, pos):
                self.cursor_moved = True
                self.cursor_pos = pos

        mock_input = MockInput()
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_input

        with patch.object(
            type(suggester), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("widgets.suggester.cast", side_effect=lambda t, x: x):
                suggester._apply_selection()

        assert mock_input.cursor_moved is True
        assert mock_input.cursor_pos == (6, 0)

    def test_exception_handled_gracefully(self):
        """Exceptions should be handled gracefully."""
        suggester = CommandSuggester()
        suggester.get_selected = MagicMock(return_value="/help")

        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No input")

        with patch.object(
            type(suggester), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            suggester._apply_selection()


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestSuggesterWorkflow:
    """Integration-style tests for typical workflows."""

    def test_slash_command_workflow(self):
        """Test typical slash command suggestion workflow."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()

        mock_lv = MagicMock(spec=ListView)
        suggester.query_one = MagicMock(return_value=mock_lv)

        mock_help = MagicMock()
        mock_help.name = "help"
        mock_help.description = "Show help"
        mock_help.subcommands = [("all", ""), ("commands", "")]

        mock_history = MagicMock()
        mock_history.name = "history"
        mock_history.description = "Show history"
        mock_history.subcommands = []

        mock_handler = MagicMock()
        mock_handler.get_all_commands.return_value = [mock_help, mock_history]

        with patch.object(
            type(suggester),
            "app",
            new_callable=lambda: property(
                lambda self: MagicMock(command_handler=mock_handler)
            ),
        ):
            suggester.update_filter("/h")

            assert suggester.display is True
            assert mock_lv.append.call_count == 2

    def test_ai_workflow_disabled(self):
        """Test AI suggestions when disabled."""
        suggester = CommandSuggester()
        suggester.display = True

        with patch("widgets.suggester.Config") as mock_config:
            mock_config.get.return_value = "false"
            suggester.update_filter("list files")

        assert suggester.display is False

    def test_navigation_workflow(self):
        """Test navigating through suggestions."""
        suggester = CommandSuggester()
        suggester._update_highlight = MagicMock()

        mock_items = [MagicMock(spec=CommandItem) for _ in range(3)]
        for i, item in enumerate(mock_items):
            item.value = f"cmd{i}"

        suggester.query = MagicMock(return_value=mock_items)

        # Initial state
        assert suggester._selected_index == 0
        assert suggester.get_selected() == "cmd0"

        # Navigate down
        suggester.select_next()
        assert suggester._selected_index == 1
        assert suggester.get_selected() == "cmd1"

        # Navigate down again
        suggester.select_next()
        assert suggester._selected_index == 2
        assert suggester.get_selected() == "cmd2"

        # Try to go past end
        suggester.select_next()
        assert suggester._selected_index == 2

        # Navigate up
        suggester.select_prev()
        assert suggester._selected_index == 1

        # Navigate to start
        suggester.select_prev()
        suggester.select_prev()
        assert suggester._selected_index == 0
