"""Tests for widgets/block_search.py - BlockSearch widget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.containers import Vertical
from textual.widgets import Input, Label

from widgets.block_search import BlockSearch


class TestBlockSearchMessages:
    """Tests for BlockSearch message classes."""

    def test_selected_message_stores_block_id(self):
        """Selected message should store the block_id."""
        msg = BlockSearch.Selected(block_id="block-123", match_text="test match")
        assert msg.block_id == "block-123"

    def test_selected_message_stores_match_text(self):
        """Selected message should store the match_text."""
        msg = BlockSearch.Selected(block_id="block-123", match_text="test match")
        assert msg.match_text == "test match"

    def test_selected_message_empty_values(self):
        """Selected message should handle empty values."""
        msg = BlockSearch.Selected(block_id="", match_text="")
        assert msg.block_id == ""
        assert msg.match_text == ""

    def test_selected_message_complex_block_id(self):
        """Selected message should handle complex block IDs."""
        msg = BlockSearch.Selected(
            block_id="block-uuid-1234-5678", match_text="some text"
        )
        assert msg.block_id == "block-uuid-1234-5678"

    def test_selected_message_multiline_match_text(self):
        """Selected message should handle multiline match text."""
        text = "line1\nline2\nline3"
        msg = BlockSearch.Selected(block_id="block-1", match_text=text)
        assert msg.match_text == text

    def test_cancelled_message_exists(self):
        """Cancelled message should be instantiable."""
        msg = BlockSearch.Cancelled()
        assert isinstance(msg, BlockSearch.Cancelled)


class TestBlockSearchInit:
    """Tests for BlockSearch initialization."""

    def test_can_focus(self):
        """BlockSearch should be focusable."""
        widget = BlockSearch()
        assert widget.can_focus is True

    def test_default_id(self):
        """Default ID should be None."""
        widget = BlockSearch()
        assert widget.id is None

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        widget = BlockSearch(id="my-search")
        assert widget.id == "my-search"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        widget = BlockSearch(classes="custom-class")
        assert "custom-class" in widget.classes


class TestBlockSearchBindings:
    """Tests for BlockSearch key bindings."""

    def test_up_binding_exists(self):
        """Up arrow binding should exist."""
        bindings = {b.key: b for b in BlockSearch.BINDINGS}
        assert "up" in bindings
        assert bindings["up"].action == "select_prev"

    def test_down_binding_exists(self):
        """Down arrow binding should exist."""
        bindings = {b.key: b for b in BlockSearch.BINDINGS}
        assert "down" in bindings
        assert bindings["down"].action == "select_next"

    def test_escape_binding_exists(self):
        """Escape binding should exist."""
        bindings = {b.key: b for b in BlockSearch.BINDINGS}
        assert "escape" in bindings
        assert bindings["escape"].action == "cancel"

    def test_enter_binding_exists(self):
        """Enter binding should exist."""
        bindings = {b.key: b for b in BlockSearch.BINDINGS}
        assert "enter" in bindings
        assert bindings["enter"].action == "select"

    def test_f3_binding_exists(self):
        """F3 binding should exist for next match."""
        bindings = {b.key: b for b in BlockSearch.BINDINGS}
        assert "f3" in bindings
        assert bindings["f3"].action == "select_next"

    def test_shift_f3_binding_exists(self):
        """Shift+F3 binding should exist for previous match."""
        bindings = {b.key: b for b in BlockSearch.BINDINGS}
        assert "shift+f3" in bindings
        assert bindings["shift+f3"].action == "select_prev"

    def test_bindings_are_hidden(self):
        """All bindings should be hidden from footer."""
        for binding in BlockSearch.BINDINGS:
            assert binding.show is False


class TestBlockSearchReactiveDefaults:
    """Tests for reactive property default values."""

    def test_search_query_default(self):
        """Default search_query should be empty string."""
        widget = BlockSearch()
        assert widget.search_query == ""

    def test_results_default(self):
        """Default results should be empty list."""
        widget = BlockSearch()
        assert widget.results == []

    def test_selected_index_default(self):
        """Default selected_index should be 0."""
        widget = BlockSearch()
        assert widget.selected_index == 0


class TestBlockSearchCompose:
    """Tests for compose method."""

    def test_compose_yields_three_widgets(self):
        """Compose should yield 3 widgets."""
        widget = BlockSearch()
        children = list(widget.compose())
        assert len(children) == 3

    def test_compose_yields_vertical_container(self):
        """First widget should be Vertical container for results."""
        widget = BlockSearch()
        children = list(widget.compose())
        assert isinstance(children[0], Vertical)
        assert children[0].id == "block-search-results"

    def test_compose_yields_input(self):
        """Second widget should be Input."""
        widget = BlockSearch()
        children = list(widget.compose())
        assert isinstance(children[1], Input)
        assert children[1].id == "block-search-input"

    def test_compose_yields_label(self):
        """Third widget should be Label with instructions."""
        widget = BlockSearch()
        children = list(widget.compose())
        assert isinstance(children[2], Label)

    def test_input_has_placeholder(self):
        """Input should have placeholder text."""
        widget = BlockSearch()
        children = list(widget.compose())
        input_widget = children[1]
        assert input_widget.placeholder == "Search blocks..."

    def test_results_container_has_class(self):
        """Results container should have search-results class."""
        widget = BlockSearch()
        children = list(widget.compose())
        container = children[0]
        assert "search-results" in container.classes

    def test_input_has_class(self):
        """Input should have search-input class."""
        widget = BlockSearch()
        children = list(widget.compose())
        input_widget = children[1]
        assert "search-input" in input_widget.classes

    def test_label_has_class(self):
        """Label should have search-header class."""
        widget = BlockSearch()
        children = list(widget.compose())
        label = children[2]
        assert "search-header" in label.classes

    def test_label_contains_navigation_instructions(self):
        """Label should contain navigation instructions."""
        widget = BlockSearch()
        children = list(widget.compose())
        label = children[2]
        assert isinstance(label, Label)


class TestBlockSearchShow:
    """Tests for show method."""

    def test_show_adds_visible_class(self):
        """Show should add 'visible' class."""
        widget = BlockSearch()
        widget.show()
        assert "visible" in widget.classes

    def test_show_resets_search_query(self):
        """Show should reset search_query to empty."""
        widget = BlockSearch()
        widget.search_query = "old search"
        widget.show()
        assert widget.search_query == ""

    def test_show_resets_results(self):
        """Show should reset results to empty list."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "test"}]
        widget.show()
        assert widget.results == []

    def test_show_resets_selected_index(self):
        """Show should reset selected_index to 0."""
        widget = BlockSearch()
        widget.selected_index = 5
        widget.show()
        assert widget.selected_index == 0

    def test_show_focuses_search_input(self):
        """Show should focus the search input."""
        widget = BlockSearch()
        mock_input = MagicMock(spec=Input)
        widget.query_one = MagicMock(return_value=mock_input)

        widget.show()

        widget.query_one.assert_called_with("#block-search-input", Input)
        mock_input.focus.assert_called_once()

    def test_show_clears_input_value(self):
        """Show should clear the input value."""
        widget = BlockSearch()
        mock_input = MagicMock(spec=Input)
        mock_input.value = "old value"
        widget.query_one = MagicMock(return_value=mock_input)

        widget.show()

        assert mock_input.value == ""

    def test_show_handles_missing_search_input(self):
        """Show should not crash if search input is missing."""
        widget = BlockSearch()
        widget.query_one = MagicMock(side_effect=Exception("No widget"))
        widget.show()


class TestBlockSearchHide:
    """Tests for hide method."""

    def test_hide_removes_visible_class(self):
        """Hide should remove 'visible' class."""
        widget = BlockSearch()
        widget.add_class("visible")
        widget.hide()
        assert "visible" not in widget.classes

    def test_hide_calls_clear_highlights(self):
        """Hide should call _clear_highlights."""
        widget = BlockSearch()

        with patch.object(widget, "_clear_highlights") as mock_clear:
            with patch.object(widget, "post_message"):
                widget.hide()
                mock_clear.assert_called_once()

    def test_hide_focuses_main_input(self):
        """Hide should focus the main input."""
        widget = BlockSearch()
        mock_app = MagicMock()
        mock_input = MagicMock()
        mock_app.query_one.return_value = mock_input

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch.object(widget, "post_message"):
                widget.hide()

        mock_app.query_one.assert_called_with("#input")
        mock_input.focus.assert_called_once()

    def test_hide_posts_cancelled_message(self):
        """Hide should post Cancelled message."""
        widget = BlockSearch()

        with patch.object(widget, "post_message") as mock_post:
            widget.hide()

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, BlockSearch.Cancelled)

    def test_hide_handles_missing_main_input(self):
        """Hide should not crash if main input is missing."""
        widget = BlockSearch()
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")
        widget._app = mock_app
        with patch.object(widget, "post_message"):
            widget.hide()


class TestBlockSearchOnInputChanged:
    """Tests for on_input_changed handler."""

    def test_input_changed_updates_search_query(self):
        """Input change should update search_query."""
        widget = BlockSearch()
        event = MagicMock()
        event.value = "new query"

        with patch.object(widget, "_update_results"):
            widget.on_input_changed(event)

        assert widget.search_query == "new query"

    def test_input_changed_calls_update_results(self):
        """Input change should call _update_results."""
        widget = BlockSearch()
        event = MagicMock()
        event.value = "test"

        with patch.object(widget, "_update_results") as mock_update:
            widget.on_input_changed(event)
            mock_update.assert_called_once()


class TestBlockSearchOnInputSubmitted:
    """Tests for on_input_submitted handler."""

    def test_input_submitted_stops_event(self):
        """Input submitted should stop event propagation."""
        widget = BlockSearch()
        event = MagicMock()

        with patch.object(widget, "_select_current"):
            widget.on_input_submitted(event)

        event.stop.assert_called_once()

    def test_input_submitted_calls_select_current(self):
        """Input submitted should call _select_current."""
        widget = BlockSearch()
        event = MagicMock()

        with patch.object(widget, "_select_current") as mock_select:
            widget.on_input_submitted(event)
            mock_select.assert_called_once()


class TestBlockSearchActionSelectPrev:
    """Tests for action_select_prev method."""

    def test_select_prev_decrements_index(self):
        """Select prev should decrement selected_index."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
            {"block_id": "3", "type": "input", "text": "cmd3"},
        ]
        widget.selected_index = 2

        with patch.object(widget, "_render_results"):
            with patch.object(widget, "_scroll_to_current"):
                widget.action_select_prev()

        assert widget.selected_index == 1

    def test_select_prev_calls_render_results(self):
        """Select prev should call _render_results."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
        ]
        widget.selected_index = 1

        with patch.object(widget, "_render_results") as mock_render:
            with patch.object(widget, "_scroll_to_current"):
                widget.action_select_prev()
                mock_render.assert_called_once()

    def test_select_prev_calls_scroll_to_current(self):
        """Select prev should call _scroll_to_current."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
        ]
        widget.selected_index = 1

        with patch.object(widget, "_render_results"):
            with patch.object(widget, "_scroll_to_current") as mock_scroll:
                widget.action_select_prev()
                mock_scroll.assert_called_once()

    def test_select_prev_does_not_go_below_zero(self):
        """Select prev should not decrement below 0."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()

        assert widget.selected_index == 0
        mock_render.assert_not_called()

    def test_select_prev_with_empty_results(self):
        """Select prev should do nothing with empty results."""
        widget = BlockSearch()
        widget.results = []
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()

        assert widget.selected_index == 0
        mock_render.assert_not_called()


class TestBlockSearchActionSelectNext:
    """Tests for action_select_next method."""

    def test_select_next_increments_index(self):
        """Select next should increment selected_index."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
            {"block_id": "3", "type": "input", "text": "cmd3"},
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results"):
            with patch.object(widget, "_scroll_to_current"):
                widget.action_select_next()

        assert widget.selected_index == 1

    def test_select_next_calls_render_results(self):
        """Select next should call _render_results."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            with patch.object(widget, "_scroll_to_current"):
                widget.action_select_next()
                mock_render.assert_called_once()

    def test_select_next_calls_scroll_to_current(self):
        """Select next should call _scroll_to_current."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results"):
            with patch.object(widget, "_scroll_to_current") as mock_scroll:
                widget.action_select_next()
                mock_scroll.assert_called_once()

    def test_select_next_does_not_exceed_length(self):
        """Select next should not increment beyond results length."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
        ]
        widget.selected_index = 1

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()

        assert widget.selected_index == 1
        mock_render.assert_not_called()

    def test_select_next_with_empty_results(self):
        """Select next should do nothing with empty results."""
        widget = BlockSearch()
        widget.results = []
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()

        assert widget.selected_index == 0
        mock_render.assert_not_called()


class TestBlockSearchActionCancel:
    """Tests for action_cancel method."""

    def test_action_cancel_calls_hide(self):
        """Cancel action should call hide."""
        widget = BlockSearch()

        with patch.object(widget, "hide") as mock_hide:
            widget.action_cancel()
            mock_hide.assert_called_once()


class TestBlockSearchActionSelect:
    """Tests for action_select method."""

    def test_action_select_calls_select_current(self):
        """Select action should call _select_current."""
        widget = BlockSearch()

        with patch.object(widget, "_select_current") as mock_select:
            widget.action_select()
            mock_select.assert_called_once()


class TestBlockSearchUpdateResults:
    """Tests for _update_results method."""

    def test_empty_query_clears_results(self):
        """Empty query should clear results."""
        widget = BlockSearch()
        widget.search_query = "   "
        widget.results = [{"block_id": "1", "type": "input", "text": "old"}]

        with patch.object(widget, "_clear_highlights"):
            with patch.object(widget, "_render_results"):
                widget._update_results()

        assert widget.results == []

    def test_empty_query_calls_clear_highlights(self):
        """Empty query should call _clear_highlights."""
        widget = BlockSearch()
        widget.search_query = "   "

        with patch.object(widget, "_clear_highlights") as mock_clear:
            with patch.object(widget, "_render_results"):
                widget._update_results()
                mock_clear.assert_called_once()

    def test_query_searches_blocks(self):
        """Non-empty query should search blocks."""
        widget = BlockSearch()
        widget.search_query = "test"

        mock_results = [{"block_id": "1", "type": "input", "text": "test match"}]

        with patch.object(widget, "_search_blocks", return_value=mock_results):
            with patch.object(widget, "_highlight_matches"):
                with patch.object(widget, "_render_results"):
                    with patch.object(widget, "_scroll_to_current"):
                        widget._update_results()

        assert widget.results == mock_results

    def test_query_calls_highlight_matches(self):
        """Non-empty query should call _highlight_matches."""
        widget = BlockSearch()
        widget.search_query = "test"

        with patch.object(widget, "_search_blocks", return_value=[]):
            with patch.object(widget, "_highlight_matches") as mock_highlight:
                with patch.object(widget, "_render_results"):
                    widget._update_results()
                    mock_highlight.assert_called_once_with("test")

    def test_update_results_resets_selected_index(self):
        """Update results should reset selected_index to 0."""
        widget = BlockSearch()
        widget.search_query = "test"
        widget.selected_index = 5

        with patch.object(widget, "_search_blocks", return_value=[]):
            with patch.object(widget, "_highlight_matches"):
                with patch.object(widget, "_render_results"):
                    widget._update_results()

        assert widget.selected_index == 0

    def test_update_results_calls_render_results(self):
        """Update results should call _render_results."""
        widget = BlockSearch()
        widget.search_query = ""

        with patch.object(widget, "_clear_highlights"):
            with patch.object(widget, "_render_results") as mock_render:
                widget._update_results()
                mock_render.assert_called_once()

    def test_update_results_scrolls_when_results_exist(self):
        """Update results should scroll when results exist."""
        widget = BlockSearch()
        widget.search_query = "test"

        mock_results = [{"block_id": "1", "type": "input", "text": "test"}]

        with patch.object(widget, "_search_blocks", return_value=mock_results):
            with patch.object(widget, "_highlight_matches"):
                with patch.object(widget, "_render_results"):
                    with patch.object(widget, "_scroll_to_current") as mock_scroll:
                        widget._update_results()
                        mock_scroll.assert_called_once()


class TestBlockSearchSearchBlocks:
    """Tests for _search_blocks method."""

    def test_search_blocks_no_app_blocks(self):
        """Should return empty list when app has no blocks attribute."""
        widget = BlockSearch()
        mock_app = MagicMock(spec=[])

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results == []

    def test_search_blocks_empty_blocks(self):
        """Should return empty list when blocks list is empty."""
        widget = BlockSearch()
        mock_app = MagicMock()
        mock_app.blocks = []

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results == []

    def test_search_blocks_matches_input(self):
        """Should find matches in block input."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "test command"
        mock_block.content_output = ""
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results) == 1
        assert results[0]["block_id"] == "block-1"
        assert results[0]["type"] == "input"
        assert results[0]["text"] == "test command"

    def test_search_blocks_matches_output(self):
        """Should find matches in block output."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = ""
        mock_block.content_output = "test output line"
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results) == 1
        assert results[0]["block_id"] == "block-1"
        assert results[0]["type"] == "output"

    def test_search_blocks_matches_multiline_output(self):
        """Should find matches in each line of multiline output."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = ""
        mock_block.content_output = "line1\ntest line2\ntest line3"
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results) == 2

    def test_search_blocks_case_insensitive(self):
        """Search should be case insensitive."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "TEST COMMAND"
        mock_block.content_output = ""
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results) == 1

    def test_search_blocks_limits_results(self):
        """Search should limit results to 50."""
        widget = BlockSearch()

        mock_blocks = []
        for i in range(60):
            mock_block = MagicMock()
            mock_block.id = f"block-{i}"
            mock_block.content_input = f"test command {i}"
            mock_block.content_output = ""
            mock_block.type.value = "command"
            mock_blocks.append(mock_block)

        mock_app = MagicMock()
        mock_app.blocks = mock_blocks

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results) == 50

    def test_search_blocks_truncates_long_lines(self):
        """Long output lines should be truncated to 100 chars."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = ""
        mock_block.content_output = "test " + "x" * 200
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results[0]["text"]) <= 100

    def test_search_blocks_handles_none_content(self):
        """Should handle None content gracefully."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = None
        mock_block.content_output = None
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results == []

    def test_search_blocks_handles_exception(self):
        """Should return empty list on exception."""
        widget = BlockSearch()
        mock_app = MagicMock()
        mock_app.blocks = MagicMock(side_effect=Exception("Error"))

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results == []

    def test_search_blocks_includes_block_type(self):
        """Results should include block type."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "test"
        mock_block.content_output = ""
        mock_block.type.value = "ai_response"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results[0]["block_type"] == "ai_response"

    def test_search_blocks_handles_type_without_value(self):
        """Should handle type without value attribute."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "test"
        mock_block.content_output = ""
        mock_block.type = "string_type"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results[0]["block_type"] == "string_type"


class TestBlockSearchRenderResults:
    """Tests for _render_results method."""

    def test_render_results_clears_container(self):
        """Render results should clear the container first."""
        widget = BlockSearch()
        widget.results = []
        widget.search_query = ""

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.remove_children.assert_called_once()

    def test_render_results_shows_no_matches_label(self):
        """Empty results with query should show 'No matches found'."""
        widget = BlockSearch()
        widget.results = []
        widget.search_query = "nonexistent"

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.mount.assert_called_once()
        mounted_widget = mock_container.mount.call_args[0][0]
        assert isinstance(mounted_widget, Label)
        assert "no-results" in mounted_widget.classes

    def test_render_results_no_label_without_query(self):
        """Empty results without query should not show label."""
        widget = BlockSearch()
        widget.results = []
        widget.search_query = ""

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.mount.assert_not_called()

    def test_render_results_mounts_labels_for_results(self):
        """Results should be mounted as Label widgets."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "output", "text": "cmd2"},
            {"block_id": "3", "type": "input", "text": "cmd3"},
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        assert mock_container.mount.call_count == 3

    def test_render_results_adds_selected_class_to_current(self):
        """Selected result should have 'selected' class."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "output", "text": "cmd2"},
        ]
        widget.selected_index = 1

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        calls = mock_container.mount.call_args_list
        first_label = calls[0][0][0]
        second_label = calls[1][0][0]

        assert "selected" not in first_label.classes
        assert "selected" in second_label.classes

    def test_render_results_all_have_search_result_class(self):
        """All result labels should have 'search-result' class."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "output", "text": "cmd2"},
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        calls = mock_container.mount.call_args_list
        for call in calls:
            label = call[0][0]
            assert "search-result" in label.classes

    def test_render_results_limits_to_10(self):
        """Should only render top 10 results."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": str(i), "type": "input", "text": f"cmd{i}"} for i in range(15)
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        assert mock_container.mount.call_count == 11

    def test_render_results_shows_more_indicator(self):
        """Should show '... and X more' when more than 10 results."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": str(i), "type": "input", "text": f"cmd{i}"} for i in range(15)
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        last_call = mock_container.mount.call_args_list[-1]
        last_label = last_call[0][0]
        assert "no-results" in last_label.classes

    def test_render_results_input_prefix(self):
        """Input type should use '>' prefix."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "test command"},
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        label = mock_container.mount.call_args_list[0][0][0]
        assert isinstance(label, Label)
        assert "search-result" in label.classes

    def test_render_results_output_prefix(self):
        """Output type should use '<' prefix."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "output", "text": "test output"},
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        label = mock_container.mount.call_args_list[0][0][0]
        assert isinstance(label, Label)
        assert "search-result" in label.classes

    def test_render_results_truncates_long_text(self):
        """Long text should be truncated with ellipsis."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "x" * 100},
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        label = mock_container.mount.call_args_list[0][0][0]
        assert isinstance(label, Label)
        assert "search-result" in label.classes

    def test_render_results_handles_query_exception(self):
        """Render results should not crash on query exception."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "cmd1"}]
        widget.query_one = MagicMock(side_effect=Exception("No widget"))
        widget._render_results()


class TestBlockSearchScrollToCurrent:
    """Tests for _scroll_to_current method."""

    def test_scroll_to_current_empty_results(self):
        """Should return early with empty results."""
        widget = BlockSearch()
        widget.results = []
        widget._scroll_to_current()

    def test_scroll_to_current_invalid_index(self):
        """Should return early with invalid index."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "test"}]
        widget.selected_index = 5
        widget._scroll_to_current()

    def test_scroll_to_current_scrolls_to_block(self):
        """Should scroll to the matching block widget."""
        widget = BlockSearch()
        widget.results = [{"block_id": "test-block", "type": "input", "text": "test"}]
        widget.selected_index = 0

        mock_block_widget = MagicMock()
        mock_block_widget.block.id = "test-block"

        mock_history = MagicMock()
        mock_history.query.return_value = [mock_block_widget]

        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_history

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch.dict(
                "sys.modules", {"widgets.block": MagicMock(BaseBlockWidget=MagicMock)}
            ):
                widget._scroll_to_current()

        mock_block_widget.scroll_visible.assert_called_once()

    def test_scroll_to_current_adds_highlight_class(self):
        """Should add search-highlight class to block."""
        widget = BlockSearch()
        widget.results = [{"block_id": "test-block", "type": "input", "text": "test"}]
        widget.selected_index = 0

        mock_block_widget = MagicMock()
        mock_block_widget.block.id = "test-block"

        mock_history = MagicMock()
        mock_history.query.return_value = [mock_block_widget]

        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_history

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch.dict(
                "sys.modules", {"widgets.block": MagicMock(BaseBlockWidget=MagicMock)}
            ):
                widget._scroll_to_current()

        mock_block_widget.add_class.assert_called_with("search-highlight")

    def test_scroll_to_current_handles_exception(self):
        """Should handle exceptions gracefully."""
        widget = BlockSearch()
        widget.results = [{"block_id": "test-block", "type": "input", "text": "test"}]
        widget.selected_index = 0

        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            widget._scroll_to_current()


class TestBlockSearchHighlightMatches:
    """Tests for _highlight_matches method."""

    def test_highlight_matches_empty_results(self):
        """Should return early with empty results."""
        widget = BlockSearch()
        widget.results = []
        widget._highlight_matches("test")

    def test_highlight_matches_adds_class_to_matching_blocks(self):
        """Should add search-match class to matching blocks."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "block-1", "type": "input", "text": "test1"},
            {"block_id": "block-2", "type": "output", "text": "test2"},
        ]

        mock_block1 = MagicMock()
        mock_block1.block.id = "block-1"
        mock_block2 = MagicMock()
        mock_block2.block.id = "block-2"
        mock_block3 = MagicMock()
        mock_block3.block.id = "block-3"

        mock_history = MagicMock()
        mock_history.query.return_value = [mock_block1, mock_block2, mock_block3]

        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_history

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch.dict(
                "sys.modules", {"widgets.block": MagicMock(BaseBlockWidget=MagicMock)}
            ):
                widget._highlight_matches("test")

        mock_block1.add_class.assert_called_with("search-match")
        mock_block2.add_class.assert_called_with("search-match")
        mock_block3.remove_class.assert_called_with("search-match")

    def test_highlight_matches_handles_exception(self):
        """Should handle exceptions gracefully."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "test"}]

        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            widget._highlight_matches("test")


class TestBlockSearchClearHighlights:
    """Tests for _clear_highlights method."""

    def test_clear_highlights_removes_classes(self):
        """Should remove search-match and search-highlight from all blocks."""
        widget = BlockSearch()

        mock_block = MagicMock()

        mock_history = MagicMock()
        mock_history.query.return_value = [mock_block]

        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_history

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch.dict(
                "sys.modules", {"widgets.block": MagicMock(BaseBlockWidget=MagicMock)}
            ):
                widget._clear_highlights()

        mock_block.remove_class.assert_any_call("search-match")
        mock_block.remove_class.assert_any_call("search-highlight")

    def test_clear_highlights_handles_exception(self):
        """Should handle exceptions gracefully."""
        widget = BlockSearch()

        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            widget._clear_highlights()


class TestBlockSearchSelectCurrent:
    """Tests for _select_current method."""

    def test_select_current_with_valid_selection(self):
        """Valid selection should scroll to current."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "block-1", "type": "input", "text": "cmd1"},
            {"block_id": "block-2", "type": "output", "text": "cmd2"},
        ]
        widget.selected_index = 1

        with patch.object(widget, "_scroll_to_current") as mock_scroll:
            widget._select_current()
            mock_scroll.assert_called_once()

    def test_select_current_empty_results_calls_hide(self):
        """Empty results should call hide."""
        widget = BlockSearch()
        widget.results = []
        widget.selected_index = 0

        with patch.object(widget, "hide") as mock_hide:
            widget._select_current()
            mock_hide.assert_called_once()

    def test_select_current_invalid_index_calls_hide(self):
        """Invalid index should call hide."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "cmd1"}]
        widget.selected_index = 5

        with patch.object(widget, "hide") as mock_hide:
            widget._select_current()
            mock_hide.assert_called_once()

    def test_select_current_negative_index_calls_hide(self):
        """Negative index should call hide."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "cmd1"}]
        widget.selected_index = -1

        with patch.object(widget, "hide") as mock_hide:
            widget._select_current()
            mock_hide.assert_called_once()

    def test_select_current_keeps_search_open(self):
        """Search should stay open to allow F3 navigation."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "cmd1"}]
        widget.selected_index = 0
        widget.add_class("visible")

        with patch.object(widget, "_scroll_to_current"):
            widget._select_current()

        assert "visible" in widget.classes


class TestBlockSearchIntegration:
    """Integration-style tests for BlockSearch behavior."""

    def test_full_search_flow(self):
        """Test complete search flow: show -> type -> select."""
        widget = BlockSearch()
        widget.show()
        assert "visible" in widget.classes
        assert widget.search_query == ""
        assert widget.results == []
        assert widget.selected_index == 0

    def test_navigation_boundaries(self):
        """Test navigation stays within bounds."""
        widget = BlockSearch()
        widget.results = [
            {"block_id": "1", "type": "input", "text": "cmd1"},
            {"block_id": "2", "type": "input", "text": "cmd2"},
            {"block_id": "3", "type": "input", "text": "cmd3"},
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results"):
            with patch.object(widget, "_scroll_to_current"):
                widget.action_select_next()
                assert widget.selected_index == 1

                widget.action_select_next()
                assert widget.selected_index == 2

                widget.action_select_next()
                assert widget.selected_index == 2

                widget.action_select_prev()
                assert widget.selected_index == 1

                widget.action_select_prev()
                assert widget.selected_index == 0

                widget.action_select_prev()
                assert widget.selected_index == 0

    def test_cancel_posts_cancelled_message(self):
        """Test that cancel posts cancelled message."""
        widget = BlockSearch()
        widget.add_class("visible")

        with patch.object(widget, "post_message") as mock_post:
            with patch.object(widget, "_clear_highlights"):
                widget.action_cancel()

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, BlockSearch.Cancelled)

    def test_select_with_no_results_hides(self):
        """Test that selecting with no results hides search."""
        widget = BlockSearch()
        widget.results = []

        with patch.object(widget, "hide") as mock_hide:
            widget.action_select()
            mock_hide.assert_called_once()

    def test_reactive_properties_are_independent(self):
        """Test that reactive properties don't interfere with each other."""
        widget = BlockSearch()

        widget.search_query = "test"
        widget.results = [
            {"block_id": "1", "type": "input", "text": "result1"},
            {"block_id": "2", "type": "output", "text": "result2"},
        ]
        widget.selected_index = 1

        assert widget.search_query == "test"
        assert len(widget.results) == 2
        assert widget.selected_index == 1

        widget.selected_index = 0
        assert widget.search_query == "test"
        assert len(widget.results) == 2

    def test_whitespace_query_treated_as_empty(self):
        """Test that whitespace-only query is treated as empty."""
        widget = BlockSearch()
        widget.search_query = "   \t\n  "
        widget.results = [{"block_id": "1", "type": "input", "text": "old"}]

        with patch.object(widget, "_clear_highlights"):
            with patch.object(widget, "_render_results"):
                widget._update_results()

        assert widget.results == []


class TestBlockSearchEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_result_navigation(self):
        """Navigation with single result should work correctly."""
        widget = BlockSearch()
        widget.results = [{"block_id": "1", "type": "input", "text": "only"}]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()
            assert widget.selected_index == 0
            mock_render.assert_not_called()

            widget.action_select_next()
            assert widget.selected_index == 0
            mock_render.assert_not_called()

    def test_special_characters_in_query(self):
        """Search should handle special characters."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "test [regex] (special) *chars*"
        mock_block.content_output = ""
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("[regex]")

        assert len(results) == 1

    def test_unicode_in_search(self):
        """Search should handle unicode characters."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "test unicode char"
        mock_block.content_output = ""
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("unicode")

        assert len(results) == 1

    def test_empty_block_content(self):
        """Should handle blocks with empty content."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = ""
        mock_block.content_output = ""
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert results == []

    def test_results_dict_structure(self):
        """Verify result dict has all required keys."""
        widget = BlockSearch()
        mock_block = MagicMock()
        mock_block.id = "block-1"
        mock_block.content_input = "test"
        mock_block.content_output = ""
        mock_block.type.value = "command"

        mock_app = MagicMock()
        mock_app.blocks = [mock_block]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            results = widget._search_blocks("test")

        assert len(results) == 1
        result = results[0]
        assert "block_id" in result
        assert "type" in result
        assert "text" in result
        assert "block_type" in result
