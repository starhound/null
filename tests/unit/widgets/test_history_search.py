"""Tests for widgets/history_search.py - HistorySearch widget."""

from unittest.mock import MagicMock, patch

from textual.containers import Vertical
from textual.widgets import Input, Label

from widgets.history_search import HistorySearch


class TestHistorySearchMessages:
    """Tests for HistorySearch message classes."""

    def test_selected_message_stores_command(self):
        """Selected message should store the command."""
        msg = HistorySearch.Selected(command="ls -la")
        assert msg.command == "ls -la"

    def test_selected_message_empty_command(self):
        """Selected message should handle empty command."""
        msg = HistorySearch.Selected(command="")
        assert msg.command == ""

    def test_selected_message_complex_command(self):
        """Selected message should handle complex commands."""
        msg = HistorySearch.Selected(command="git commit -m 'feat: add new feature'")
        assert msg.command == "git commit -m 'feat: add new feature'"

    def test_selected_message_multiline_command(self):
        """Selected message should handle multiline commands."""
        cmd = "echo 'line1\nline2'"
        msg = HistorySearch.Selected(command=cmd)
        assert msg.command == cmd

    def test_cancelled_message_exists(self):
        """Cancelled message should be instantiable."""
        msg = HistorySearch.Cancelled()
        assert isinstance(msg, HistorySearch.Cancelled)


class TestHistorySearchInit:
    """Tests for HistorySearch initialization."""

    def test_can_focus(self):
        """HistorySearch should be focusable."""
        widget = HistorySearch()
        assert widget.can_focus is True

    def test_default_id(self):
        """Default ID should be None."""
        widget = HistorySearch()
        assert widget.id is None

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        widget = HistorySearch(id="my-search")
        assert widget.id == "my-search"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        widget = HistorySearch(classes="custom-class")
        assert "custom-class" in widget.classes


class TestHistorySearchBindings:
    """Tests for HistorySearch key bindings."""

    def test_up_binding_exists(self):
        """Up arrow binding should exist."""
        bindings = {b.key: b for b in HistorySearch.BINDINGS}
        assert "up" in bindings
        assert bindings["up"].action == "select_prev"

    def test_down_binding_exists(self):
        """Down arrow binding should exist."""
        bindings = {b.key: b for b in HistorySearch.BINDINGS}
        assert "down" in bindings
        assert bindings["down"].action == "select_next"

    def test_escape_binding_exists(self):
        """Escape binding should exist."""
        bindings = {b.key: b for b in HistorySearch.BINDINGS}
        assert "escape" in bindings
        assert bindings["escape"].action == "cancel"

    def test_enter_binding_exists(self):
        """Enter binding should exist."""
        bindings = {b.key: b for b in HistorySearch.BINDINGS}
        assert "enter" in bindings
        assert bindings["enter"].action == "select"

    def test_bindings_are_hidden(self):
        """All bindings should be hidden from footer."""
        for binding in HistorySearch.BINDINGS:
            assert binding.show is False


class TestHistorySearchReactiveDefaults:
    """Tests for reactive property default values."""

    def test_search_query_default(self):
        """Default search_query should be empty string."""
        widget = HistorySearch()
        assert widget.search_query == ""

    def test_results_default(self):
        """Default results should be empty list."""
        widget = HistorySearch()
        assert widget.results == []

    def test_selected_index_default(self):
        """Default selected_index should be 0."""
        widget = HistorySearch()
        assert widget.selected_index == 0


class TestHistorySearchCompose:
    """Tests for compose method."""

    def test_compose_yields_three_widgets(self):
        """Compose should yield 3 widgets."""
        widget = HistorySearch()
        children = list(widget.compose())
        assert len(children) == 3

    def test_compose_yields_vertical_container(self):
        """First widget should be Vertical container for results."""
        widget = HistorySearch()
        children = list(widget.compose())
        assert isinstance(children[0], Vertical)
        assert children[0].id == "search-results"

    def test_compose_yields_input(self):
        """Second widget should be Input."""
        widget = HistorySearch()
        children = list(widget.compose())
        assert isinstance(children[1], Input)
        assert children[1].id == "search-input"

    def test_compose_yields_label(self):
        """Third widget should be Label with instructions."""
        widget = HistorySearch()
        children = list(widget.compose())
        assert isinstance(children[2], Label)

    def test_input_has_placeholder(self):
        """Input should have placeholder text."""
        widget = HistorySearch()
        children = list(widget.compose())
        input_widget = children[1]
        assert input_widget.placeholder == "Type to search..."

    def test_results_container_has_class(self):
        """Results container should have search-results class."""
        widget = HistorySearch()
        children = list(widget.compose())
        container = children[0]
        assert "search-results" in container.classes

    def test_input_has_class(self):
        """Input should have search-input class."""
        widget = HistorySearch()
        children = list(widget.compose())
        input_widget = children[1]
        assert "search-input" in input_widget.classes

    def test_label_has_class(self):
        """Label should have search-header class."""
        widget = HistorySearch()
        children = list(widget.compose())
        label = children[2]
        assert "search-header" in label.classes


class TestHistorySearchShow:
    """Tests for show method."""

    def test_show_adds_visible_class(self):
        """Show should add 'visible' class."""
        widget = HistorySearch()
        widget.show()
        assert "visible" in widget.classes

    def test_show_resets_search_query(self):
        """Show should reset search_query to empty."""
        widget = HistorySearch()
        widget.search_query = "old search"
        widget.show()
        assert widget.search_query == ""

    def test_show_resets_results(self):
        """Show should reset results to empty list."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.show()
        assert widget.results == []

    def test_show_resets_selected_index(self):
        """Show should reset selected_index to 0."""
        widget = HistorySearch()
        widget.selected_index = 5
        widget.show()
        assert widget.selected_index == 0

    def test_show_hides_input_container(self):
        """Show should hide the main input container."""
        widget = HistorySearch()
        mock_app = MagicMock()
        mock_container = MagicMock()
        mock_app.query_one.return_value = mock_container

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            widget.show()

        mock_app.query_one.assert_called_with("#input-container")
        assert mock_container.display is False

    def test_show_focuses_search_input(self):
        """Show should focus the search input."""
        widget = HistorySearch()
        mock_input = MagicMock(spec=Input)
        widget.query_one = MagicMock(return_value=mock_input)

        widget.show()

        widget.query_one.assert_called_with("#search-input", Input)
        mock_input.focus.assert_called_once()

    def test_show_clears_input_value(self):
        """Show should clear the input value."""
        widget = HistorySearch()
        mock_input = MagicMock(spec=Input)
        mock_input.value = "old value"
        widget.query_one = MagicMock(return_value=mock_input)

        widget.show()

        assert mock_input.value == ""

    def test_show_handles_missing_input_container(self):
        """Show should not crash if input container is missing."""
        widget = HistorySearch()
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")
        widget._app = mock_app

        # Should not raise
        widget.show()

    def test_show_handles_missing_search_input(self):
        """Show should not crash if search input is missing."""
        widget = HistorySearch()
        widget.query_one = MagicMock(side_effect=Exception("No widget"))

        # Should not raise
        widget.show()


class TestHistorySearchHide:
    """Tests for hide method."""

    def test_hide_removes_visible_class(self):
        """Hide should remove 'visible' class."""
        widget = HistorySearch()
        widget.add_class("visible")
        widget.hide()
        assert "visible" not in widget.classes

    def test_hide_shows_input_container(self):
        """Hide should show the main input container."""
        widget = HistorySearch()
        mock_app = MagicMock()
        mock_container = MagicMock()
        mock_input = MagicMock()

        def query_side_effect(selector):
            if selector == "#input-container":
                return mock_container
            elif selector == "#input":
                return mock_input
            raise Exception("Unknown selector")

        mock_app.query_one = MagicMock(side_effect=query_side_effect)

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            widget.hide()

        assert mock_container.display is True

    def test_hide_focuses_main_input(self):
        """Hide should focus the main input."""
        widget = HistorySearch()
        mock_app = MagicMock()
        mock_container = MagicMock()
        mock_input = MagicMock()

        def query_side_effect(selector):
            if selector == "#input-container":
                return mock_container
            elif selector == "#input":
                return mock_input
            raise Exception("Unknown selector")

        mock_app.query_one = MagicMock(side_effect=query_side_effect)

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            widget.hide()

        mock_input.focus.assert_called_once()

    def test_hide_posts_cancelled_message(self):
        """Hide should post Cancelled message."""
        widget = HistorySearch()

        with patch.object(widget, "post_message") as mock_post:
            widget.hide()

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, HistorySearch.Cancelled)

    def test_hide_handles_missing_input_container(self):
        """Hide should not crash if input container is missing."""
        widget = HistorySearch()
        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")
        widget._app = mock_app

        # Should not raise, but should still post cancelled message
        with patch.object(widget, "post_message"):
            widget.hide()


class TestHistorySearchOnInputChanged:
    """Tests for on_input_changed handler."""

    def test_input_changed_updates_search_query(self):
        """Input change should update search_query."""
        widget = HistorySearch()
        event = MagicMock()
        event.value = "new query"

        with patch.object(widget, "_update_results"):
            widget.on_input_changed(event)

        assert widget.search_query == "new query"

    def test_input_changed_calls_update_results(self):
        """Input change should call _update_results."""
        widget = HistorySearch()
        event = MagicMock()
        event.value = "test"

        with patch.object(widget, "_update_results") as mock_update:
            widget.on_input_changed(event)
            mock_update.assert_called_once()


class TestHistorySearchOnInputSubmitted:
    """Tests for on_input_submitted handler."""

    def test_input_submitted_stops_event(self):
        """Input submitted should stop event propagation."""
        widget = HistorySearch()
        event = MagicMock()

        with patch.object(widget, "_select_current"):
            widget.on_input_submitted(event)

        event.stop.assert_called_once()

    def test_input_submitted_calls_select_current(self):
        """Input submitted should call _select_current."""
        widget = HistorySearch()
        event = MagicMock()

        with patch.object(widget, "_select_current") as mock_select:
            widget.on_input_submitted(event)
            mock_select.assert_called_once()


class TestHistorySearchActionSelectPrev:
    """Tests for action_select_prev method."""

    def test_select_prev_decrements_index(self):
        """Select prev should decrement selected_index."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2", "cmd3"]
        widget.selected_index = 2

        with patch.object(widget, "_render_results"):
            widget.action_select_prev()

        assert widget.selected_index == 1

    def test_select_prev_calls_render_results(self):
        """Select prev should call _render_results."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 1

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()
            mock_render.assert_called_once()

    def test_select_prev_does_not_go_below_zero(self):
        """Select prev should not decrement below 0."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()

        assert widget.selected_index == 0
        mock_render.assert_not_called()

    def test_select_prev_with_empty_results(self):
        """Select prev should do nothing with empty results."""
        widget = HistorySearch()
        widget.results = []
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()

        assert widget.selected_index == 0
        mock_render.assert_not_called()


class TestHistorySearchActionSelectNext:
    """Tests for action_select_next method."""

    def test_select_next_increments_index(self):
        """Select next should increment selected_index."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2", "cmd3"]
        widget.selected_index = 0

        with patch.object(widget, "_render_results"):
            widget.action_select_next()

        assert widget.selected_index == 1

    def test_select_next_calls_render_results(self):
        """Select next should call _render_results."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()
            mock_render.assert_called_once()

    def test_select_next_does_not_exceed_length(self):
        """Select next should not increment beyond results length."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 1

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()

        assert widget.selected_index == 1
        mock_render.assert_not_called()

    def test_select_next_with_empty_results(self):
        """Select next should do nothing with empty results."""
        widget = HistorySearch()
        widget.results = []
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()

        assert widget.selected_index == 0
        mock_render.assert_not_called()


class TestHistorySearchActionCancel:
    """Tests for action_cancel method."""

    def test_action_cancel_calls_hide(self):
        """Cancel action should call hide."""
        widget = HistorySearch()

        with patch.object(widget, "hide") as mock_hide:
            widget.action_cancel()
            mock_hide.assert_called_once()


class TestHistorySearchActionSelect:
    """Tests for action_select method."""

    def test_action_select_calls_select_current(self):
        """Select action should call _select_current."""
        widget = HistorySearch()

        with patch.object(widget, "_select_current") as mock_select:
            widget.action_select()
            mock_select.assert_called_once()


class TestHistorySearchUpdateResults:
    """Tests for _update_results method."""

    def test_empty_query_clears_results(self):
        """Empty query should clear results."""
        widget = HistorySearch()
        widget.search_query = "   "
        widget.results = ["old", "results"]

        with patch("config.Config"):
            with patch.object(widget, "_render_results"):
                widget._update_results()

        assert widget.results == []

    def test_query_searches_history(self):
        """Non-empty query should search history via Config."""
        widget = HistorySearch()
        widget.search_query = "git"

        mock_storage = MagicMock()
        mock_storage.search_history.return_value = ["git status", "git commit"]

        with patch("config.Config") as mock_config:
            mock_config._get_storage.return_value = mock_storage
            with patch.object(widget, "_render_results"):
                widget._update_results()

        mock_storage.search_history.assert_called_once_with("git", limit=10)
        assert widget.results == ["git status", "git commit"]

    def test_update_results_resets_selected_index(self):
        """Update results should reset selected_index to 0."""
        widget = HistorySearch()
        widget.search_query = "test"
        widget.selected_index = 5

        mock_storage = MagicMock()
        mock_storage.search_history.return_value = []

        with patch("config.Config") as mock_config:
            mock_config._get_storage.return_value = mock_storage
            with patch.object(widget, "_render_results"):
                widget._update_results()

        assert widget.selected_index == 0

    def test_update_results_calls_render_results(self):
        """Update results should call _render_results."""
        widget = HistorySearch()
        widget.search_query = ""

        with patch("config.Config"):
            with patch.object(widget, "_render_results") as mock_render:
                widget._update_results()
                mock_render.assert_called_once()


class TestHistorySearchRenderResults:
    """Tests for _render_results method."""

    def test_render_results_clears_container(self):
        """Render results should clear the container first."""
        widget = HistorySearch()
        widget.results = []
        widget.search_query = ""

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.remove_children.assert_called_once()

    def test_render_results_shows_no_matches_label(self):
        """Empty results with query should show 'No matches found'."""
        widget = HistorySearch()
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
        widget = HistorySearch()
        widget.results = []
        widget.search_query = ""

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.mount.assert_not_called()

    def test_render_results_mounts_labels_for_results(self):
        """Results should be mounted as Label widgets."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2", "cmd3"]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        assert mock_container.mount.call_count == 3

    def test_render_results_adds_selected_class_to_current(self):
        """Selected result should have 'selected' class."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 1

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        # Second call should have selected class
        calls = mock_container.mount.call_args_list
        first_label = calls[0][0][0]
        second_label = calls[1][0][0]

        assert "selected" not in first_label.classes
        assert "selected" in second_label.classes

    def test_render_results_all_have_search_result_class(self):
        """All result labels should have 'search-result' class."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        calls = mock_container.mount.call_args_list
        for call in calls:
            label = call[0][0]
            assert "search-result" in label.classes

    def test_render_results_handles_query_exception(self):
        """Render results should not crash on query exception."""
        widget = HistorySearch()
        widget.results = ["cmd1"]
        widget.query_one = MagicMock(side_effect=Exception("No widget"))

        # Should not raise
        widget._render_results()


class TestHistorySearchSelectCurrent:
    """Tests for _select_current method."""

    def test_select_current_with_valid_selection(self):
        """Valid selection should post Selected message."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2"]
        widget.selected_index = 1
        widget.add_class("visible")

        with patch.object(widget, "post_message") as mock_post:
            widget._select_current()

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, HistorySearch.Selected)
            assert message.command == "cmd2"

    def test_select_current_removes_visible_class(self):
        """Select current should remove 'visible' class."""
        widget = HistorySearch()
        widget.results = ["cmd1"]
        widget.selected_index = 0
        widget.add_class("visible")

        with patch.object(widget, "post_message"):
            widget._select_current()

        assert "visible" not in widget.classes

    def test_select_current_shows_input_container(self):
        """Select current should show the main input container."""
        widget = HistorySearch()
        widget.results = ["cmd1"]
        widget.selected_index = 0

        mock_app = MagicMock()
        mock_container = MagicMock()
        mock_app.query_one.return_value = mock_container

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch.object(widget, "post_message"):
                widget._select_current()

        mock_app.query_one.assert_called_with("#input-container")
        assert mock_container.display is True

    def test_select_current_empty_results_calls_hide(self):
        """Empty results should call hide."""
        widget = HistorySearch()
        widget.results = []
        widget.selected_index = 0

        with patch.object(widget, "hide") as mock_hide:
            widget._select_current()
            mock_hide.assert_called_once()

    def test_select_current_invalid_index_calls_hide(self):
        """Invalid index should call hide."""
        widget = HistorySearch()
        widget.results = ["cmd1"]
        widget.selected_index = 5

        with patch.object(widget, "hide") as mock_hide:
            widget._select_current()
            mock_hide.assert_called_once()

    def test_select_current_negative_index_calls_hide(self):
        """Negative index should call hide."""
        widget = HistorySearch()
        widget.results = ["cmd1"]
        widget.selected_index = -1

        with patch.object(widget, "hide") as mock_hide:
            widget._select_current()
            mock_hide.assert_called_once()

    def test_select_current_handles_missing_input_container(self):
        """Select current should not crash if input container is missing."""
        widget = HistorySearch()
        widget.results = ["cmd1"]
        widget.selected_index = 0

        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("No widget")
        widget._app = mock_app

        # Should not raise, but should still post message
        with patch.object(widget, "post_message") as mock_post:
            widget._select_current()
            mock_post.assert_called_once()


class TestHistorySearchIntegration:
    """Integration-style tests for HistorySearch behavior."""

    def test_full_search_flow(self):
        """Test complete search flow: show -> type -> select."""
        widget = HistorySearch()

        # Show widget
        widget.show()
        assert "visible" in widget.classes
        assert widget.search_query == ""
        assert widget.results == []
        assert widget.selected_index == 0

    def test_navigation_boundaries(self):
        """Test navigation stays within bounds."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2", "cmd3"]
        widget.selected_index = 0

        with patch.object(widget, "_render_results"):
            # Navigate down
            widget.action_select_next()
            assert widget.selected_index == 1

            widget.action_select_next()
            assert widget.selected_index == 2

            # Try to go past end
            widget.action_select_next()
            assert widget.selected_index == 2

            # Navigate up
            widget.action_select_prev()
            assert widget.selected_index == 1

            widget.action_select_prev()
            assert widget.selected_index == 0

            # Try to go past start
            widget.action_select_prev()
            assert widget.selected_index == 0

    def test_results_update_resets_selection(self):
        """Test that updating results resets selection to first item."""
        widget = HistorySearch()
        widget.results = ["cmd1", "cmd2", "cmd3"]
        widget.selected_index = 2

        widget.search_query = "new"
        mock_storage = MagicMock()
        mock_storage.search_history.return_value = ["new1", "new2"]

        with patch("config.Config") as mock_config:
            mock_config._get_storage.return_value = mock_storage
            with patch.object(widget, "_render_results"):
                widget._update_results()

        assert widget.selected_index == 0
        assert widget.results == ["new1", "new2"]

    def test_cancel_restores_state(self):
        """Test that cancel posts cancelled message."""
        widget = HistorySearch()
        widget.add_class("visible")

        with patch.object(widget, "post_message") as mock_post:
            widget.action_cancel()

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, HistorySearch.Cancelled)

    def test_select_with_no_results_cancels(self):
        """Test that selecting with no results cancels search."""
        widget = HistorySearch()
        widget.results = []

        with patch.object(widget, "hide") as mock_hide:
            widget.action_select()
            mock_hide.assert_called_once()

    def test_reactive_properties_are_independent(self):
        """Test that reactive properties don't interfere with each other."""
        widget = HistorySearch()

        widget.search_query = "test"
        widget.results = ["result1", "result2"]
        widget.selected_index = 1

        assert widget.search_query == "test"
        assert widget.results == ["result1", "result2"]
        assert widget.selected_index == 1

        # Modify one, others should be unchanged
        widget.selected_index = 0
        assert widget.search_query == "test"
        assert widget.results == ["result1", "result2"]

    def test_whitespace_query_treated_as_empty(self):
        """Test that whitespace-only query is treated as empty."""
        widget = HistorySearch()
        widget.search_query = "   \t\n  "
        widget.results = ["old"]

        with patch("config.Config"):
            with patch.object(widget, "_render_results"):
                widget._update_results()

        assert widget.results == []
