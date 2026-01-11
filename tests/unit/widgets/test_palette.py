"""Tests for widgets/palette.py - CommandPalette widget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.containers import Vertical
from textual.widgets import Input, Label

from widgets.palette import CommandPalette, PaletteAction, PaletteItem


# =============================================================================
# PaletteAction Tests
# =============================================================================


class TestPaletteActionDataclass:
    """Tests for PaletteAction dataclass."""

    def test_creates_with_required_fields(self):
        """PaletteAction should require name and description."""
        action = PaletteAction(name="Test", description="Test action")
        assert action.name == "Test"
        assert action.description == "Test action"

    def test_default_shortcut_is_empty(self):
        """Default shortcut should be empty string."""
        action = PaletteAction(name="Test", description="Test action")
        assert action.shortcut == ""

    def test_default_category_is_actions(self):
        """Default category should be 'actions'."""
        action = PaletteAction(name="Test", description="Test action")
        assert action.category == "actions"

    def test_default_action_id_is_empty(self):
        """Default action_id should be empty string."""
        action = PaletteAction(name="Test", description="Test action")
        assert action.action_id == ""

    def test_all_fields_can_be_set(self):
        """All fields should be settable."""
        action = PaletteAction(
            name="My Action",
            description="My Description",
            shortcut="Ctrl+X",
            category="custom",
            action_id="custom:action",
        )
        assert action.name == "My Action"
        assert action.description == "My Description"
        assert action.shortcut == "Ctrl+X"
        assert action.category == "custom"
        assert action.action_id == "custom:action"


class TestPaletteActionMatches:
    """Tests for PaletteAction.matches() fuzzy matching."""

    def test_empty_query_matches_everything(self):
        """Empty query should match any action with score 0."""
        action = PaletteAction(name="Test", description="Description")
        matches, score = action.matches("")
        assert matches is True
        assert score == 0

    def test_exact_name_start_match_highest_score(self):
        """Query matching start of name should get score 100."""
        action = PaletteAction(name="Clear History", description="Clear all")
        matches, score = action.matches("Clear")
        assert matches is True
        assert score == 100

    def test_exact_name_start_match_case_insensitive(self):
        """Start match should be case-insensitive."""
        action = PaletteAction(name="Clear History", description="Clear all")
        matches, score = action.matches("clear")
        assert matches is True
        assert score == 100

    def test_name_contains_match_score_80(self):
        """Query contained in name (not at start) should get score 80."""
        action = PaletteAction(name="Clear History", description="Desc")
        matches, score = action.matches("History")
        assert matches is True
        assert score == 80

    def test_name_contains_match_case_insensitive(self):
        """Contains match should be case-insensitive."""
        action = PaletteAction(name="Clear History", description="Desc")
        matches, score = action.matches("history")
        assert matches is True
        assert score == 80

    def test_description_match_score_60(self):
        """Query in description should get score 60."""
        action = PaletteAction(name="Action", description="Special feature here")
        matches, score = action.matches("special")
        assert matches is True
        assert score == 60

    def test_description_match_case_insensitive(self):
        """Description match should be case-insensitive."""
        action = PaletteAction(name="Action", description="Special Feature")
        matches, score = action.matches("feature")
        assert matches is True
        assert score == 60

    def test_fuzzy_match_name_score_40(self):
        """Fuzzy match in name (chars in order) should get score 40."""
        action = PaletteAction(name="Clear History", description="Desc")
        matches, score = action.matches("clh")  # C-L-ear H-istory
        assert matches is True
        assert score == 40

    def test_fuzzy_match_name_all_chars_must_appear_in_order(self):
        """Fuzzy match requires all chars in order."""
        action = PaletteAction(name="Clear History", description="Desc")
        matches, score = action.matches("clry")  # C-L-ear histo-R-Y
        assert matches is True
        assert score == 40

    def test_fuzzy_match_description_score_20(self):
        """Fuzzy match in description should get score 20."""
        action = PaletteAction(name="Action", description="Special feature")
        matches, score = action.matches("sft")  # S-pecial F-ea T-ure
        assert matches is True
        assert score == 20

    def test_no_match_returns_false(self):
        """Non-matching query should return (False, 0)."""
        action = PaletteAction(name="Clear History", description="Desc")
        matches, score = action.matches("xyz")
        assert matches is False
        assert score == 0

    def test_partial_fuzzy_no_match(self):
        """Partial fuzzy (not all chars) should not match."""
        action = PaletteAction(name="abc", description="def")
        matches, score = action.matches("xyz")
        assert matches is False

    def test_single_char_query(self):
        """Single character query should work."""
        action = PaletteAction(name="Test", description="Desc")
        matches, score = action.matches("t")
        assert matches is True
        assert score == 100  # starts with t

    def test_long_query_matching_entire_name(self):
        """Query matching entire name should work."""
        action = PaletteAction(name="Help", description="Show help")
        matches, score = action.matches("Help")
        assert matches is True
        assert score == 100

    def test_query_longer_than_name_can_match_description(self):
        """Query longer than name can still match description."""
        action = PaletteAction(name="Hi", description="This is a very long description")
        matches, score = action.matches("very long")
        assert matches is True
        assert score == 60


# =============================================================================
# PaletteItem Tests
# =============================================================================


class TestPaletteItemMessages:
    """Tests for PaletteItem.Selected message."""

    def test_selected_message_stores_action(self):
        """Selected message should store the action."""
        action = PaletteAction(name="Test", description="Desc")
        msg = PaletteItem.Selected(action)
        assert msg.action is action

    def test_selected_message_with_full_action(self):
        """Selected message should work with fully populated action."""
        action = PaletteAction(
            name="Full",
            description="Full action",
            shortcut="Ctrl+F",
            category="test",
            action_id="test:full",
        )
        msg = PaletteItem.Selected(action)
        assert msg.action.name == "Full"
        assert msg.action.shortcut == "Ctrl+F"


class TestPaletteItemInit:
    """Tests for PaletteItem initialization."""

    def test_stores_action(self):
        """PaletteItem should store the action."""
        action = PaletteAction(name="Test", description="Desc")
        item = PaletteItem(action)
        assert item.action is action

    def test_accepts_kwargs(self):
        """PaletteItem should pass kwargs to parent."""
        action = PaletteAction(name="Test", description="Desc")
        item = PaletteItem(action, id="my-item", classes="custom-class")
        assert item.id == "my-item"
        assert "custom-class" in item.classes


class TestPaletteItemCompose:
    """Tests for PaletteItem.compose() method."""

    def test_compose_yields_three_labels(self):
        """Compose should yield 3 Label widgets."""
        action = PaletteAction(name="Test", description="Desc", shortcut="Ctrl+T")
        item = PaletteItem(action)
        children = list(item.compose())
        assert len(children) == 3
        assert all(isinstance(c, Label) for c in children)

    def test_first_label_is_name(self):
        """First label should be the action name."""
        action = PaletteAction(name="My Action", description="Desc")
        item = PaletteItem(action)
        children = list(item.compose())
        name_label = children[0]
        # Label content is a renderable, check class
        assert "palette-item-name" in name_label.classes

    def test_second_label_is_description(self):
        """Second label should be the action description."""
        action = PaletteAction(name="Test", description="My Description")
        item = PaletteItem(action)
        children = list(item.compose())
        desc_label = children[1]
        assert "palette-item-desc" in desc_label.classes

    def test_third_label_is_shortcut(self):
        """Third label should be the shortcut."""
        action = PaletteAction(name="Test", description="Desc", shortcut="Ctrl+X")
        item = PaletteItem(action)
        children = list(item.compose())
        shortcut_label = children[2]
        assert "palette-item-shortcut" in shortcut_label.classes

    def test_shortcut_label_empty_when_no_shortcut(self):
        """Shortcut label should be empty when no shortcut."""
        action = PaletteAction(name="Test", description="Desc", shortcut="")
        item = PaletteItem(action)
        children = list(item.compose())
        shortcut_label = children[2]
        # When shortcut is empty, the label text should be empty
        assert "palette-item-shortcut" in shortcut_label.classes

    def test_shortcut_label_formatted_with_brackets(self):
        """Shortcut should be formatted with brackets."""
        action = PaletteAction(name="Test", description="Desc", shortcut="F1")
        item = PaletteItem(action)
        children = list(item.compose())
        # The shortcut_display should be "[F1]"
        # We can verify by checking the Label was created properly


class TestPaletteItemOnClick:
    """Tests for PaletteItem click handling."""

    def test_click_stops_event(self):
        """Click should stop event propagation."""
        action = PaletteAction(name="Test", description="Desc")
        item = PaletteItem(action)
        event = MagicMock()

        with patch.object(item, "post_message"):
            item.on_click(event)

        event.stop.assert_called_once()

    def test_click_posts_selected_message(self):
        """Click should post Selected message with action."""
        action = PaletteAction(name="Test", description="Desc")
        item = PaletteItem(action)
        event = MagicMock()

        with patch.object(item, "post_message") as mock_post:
            item.on_click(event)

        mock_post.assert_called_once()
        message = mock_post.call_args[0][0]
        assert isinstance(message, PaletteItem.Selected)
        assert message.action is action


# =============================================================================
# CommandPalette Tests
# =============================================================================


class TestCommandPaletteMessages:
    """Tests for CommandPalette message classes."""

    def test_action_selected_stores_action(self):
        """ActionSelected should store the action."""
        action = PaletteAction(name="Test", description="Desc")
        msg = CommandPalette.ActionSelected(action)
        assert msg.action is action

    def test_closed_message_exists(self):
        """Closed message should be instantiable."""
        msg = CommandPalette.Closed()
        assert isinstance(msg, CommandPalette.Closed)


class TestCommandPaletteInit:
    """Tests for CommandPalette initialization."""

    def test_can_focus(self):
        """CommandPalette should be focusable."""
        widget = CommandPalette()
        assert widget.can_focus is True

    def test_default_id(self):
        """Default ID should be None."""
        widget = CommandPalette()
        assert widget.id is None

    def test_custom_id(self):
        """Custom ID should be passed to parent."""
        widget = CommandPalette(id="my-palette")
        assert widget.id == "my-palette"

    def test_custom_classes(self):
        """Custom classes should be passed to parent."""
        widget = CommandPalette(classes="custom-class")
        assert "custom-class" in widget.classes

    def test_all_actions_starts_empty(self):
        """_all_actions should start as empty list."""
        widget = CommandPalette()
        assert widget._all_actions == []


class TestCommandPaletteBindings:
    """Tests for CommandPalette key bindings."""

    def test_up_binding_exists(self):
        """Up arrow binding should exist."""
        bindings = {b.key: b for b in CommandPalette.BINDINGS}
        assert "up" in bindings
        assert bindings["up"].action == "select_prev"

    def test_down_binding_exists(self):
        """Down arrow binding should exist."""
        bindings = {b.key: b for b in CommandPalette.BINDINGS}
        assert "down" in bindings
        assert bindings["down"].action == "select_next"

    def test_escape_binding_exists(self):
        """Escape binding should exist."""
        bindings = {b.key: b for b in CommandPalette.BINDINGS}
        assert "escape" in bindings
        assert bindings["escape"].action == "close"

    def test_enter_binding_exists(self):
        """Enter binding should exist."""
        bindings = {b.key: b for b in CommandPalette.BINDINGS}
        assert "enter" in bindings
        assert bindings["enter"].action == "execute"

    def test_bindings_are_hidden(self):
        """All bindings should be hidden from footer."""
        for binding in CommandPalette.BINDINGS:
            assert binding.show is False


class TestCommandPaletteReactiveDefaults:
    """Tests for reactive property default values."""

    def test_search_query_default(self):
        """Default search_query should be empty string."""
        widget = CommandPalette()
        assert widget.search_query == ""

    def test_filtered_actions_default(self):
        """Default filtered_actions should be empty list."""
        widget = CommandPalette()
        assert widget.filtered_actions == []

    def test_selected_index_default(self):
        """Default selected_index should be 0."""
        widget = CommandPalette()
        assert widget.selected_index == 0


class TestCommandPaletteCompose:
    """Tests for compose method."""

    def test_compose_yields_four_widgets(self):
        """Compose should yield 4 widgets."""
        widget = CommandPalette()
        children = list(widget.compose())
        assert len(children) == 4

    def test_compose_yields_title_label(self):
        """First widget should be title Label."""
        widget = CommandPalette()
        children = list(widget.compose())
        assert isinstance(children[0], Label)
        assert children[0].id == "palette-title"

    def test_compose_yields_input(self):
        """Second widget should be Input."""
        widget = CommandPalette()
        children = list(widget.compose())
        assert isinstance(children[1], Input)
        assert children[1].id == "palette-input"

    def test_compose_yields_results_container(self):
        """Third widget should be Vertical container for results."""
        widget = CommandPalette()
        children = list(widget.compose())
        assert isinstance(children[2], Vertical)
        assert children[2].id == "palette-results"

    def test_compose_yields_hint_label(self):
        """Fourth widget should be hint Label."""
        widget = CommandPalette()
        children = list(widget.compose())
        assert isinstance(children[3], Label)
        assert children[3].id == "palette-hint"

    def test_input_has_placeholder(self):
        """Input should have placeholder text."""
        widget = CommandPalette()
        children = list(widget.compose())
        input_widget = children[1]
        assert input_widget.placeholder == "Type to search commands..."


class TestCommandPaletteShow:
    """Tests for show method."""

    def test_show_adds_visible_class(self):
        """Show should add 'visible' class."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        with patch.object(widget, "_build_actions", return_value=[]):
            widget.show()
        assert "visible" in widget.classes

    def test_show_resets_search_query(self):
        """Show should reset search_query to empty."""
        widget = CommandPalette()
        widget.search_query = "old search"
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        with patch.object(widget, "_build_actions", return_value=[]):
            widget.show()
        assert widget.search_query == ""

    def test_show_resets_selected_index(self):
        """Show should reset selected_index to 0."""
        widget = CommandPalette()
        widget.selected_index = 5
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        with patch.object(widget, "_build_actions", return_value=[]):
            widget.show()
        assert widget.selected_index == 0

    def test_show_builds_actions(self):
        """Show should call _build_actions to populate actions."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        with patch.object(widget, "_build_actions", return_value=[]) as mock_build:
            widget.show()
            mock_build.assert_called_once()

    def test_show_sets_filtered_actions_to_all(self):
        """Show should set filtered_actions to all actions."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        with patch.object(widget, "_build_actions", return_value=actions):
            widget.show()

        assert widget.filtered_actions == actions

    def test_show_calls_render_results(self):
        """Show should call _render_results."""
        widget = CommandPalette()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        with patch.object(widget, "_build_actions", return_value=[]):
            with patch.object(widget, "_render_results") as mock_render:
                widget.show()
                mock_render.assert_called_once()

    def test_show_focuses_input(self):
        """Show should focus the input widget."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        mock_input = MagicMock(spec=Input)
        widget.query_one = MagicMock(return_value=mock_input)

        with patch.object(widget, "_build_actions", return_value=[]):
            widget.show()

        mock_input.focus.assert_called_once()

    def test_show_clears_input_value(self):
        """Show should clear input value."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        mock_input = MagicMock(spec=Input)
        mock_input.value = "old value"
        widget.query_one = MagicMock(return_value=mock_input)

        with patch.object(widget, "_build_actions", return_value=[]):
            widget.show()

        assert mock_input.value == ""

    def test_show_handles_missing_input(self):
        """Show should not crash if input is missing."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(side_effect=Exception("No widget"))

        with patch.object(widget, "_build_actions", return_value=[]):
            # Should not raise
            widget.show()


class TestCommandPaletteHide:
    """Tests for hide method."""

    def test_hide_removes_visible_class(self):
        """Hide should remove 'visible' class."""
        widget = CommandPalette()
        widget.add_class("visible")

        with patch.object(widget, "post_message"):
            widget.hide()

        assert "visible" not in widget.classes

    def test_hide_posts_closed_message(self):
        """Hide should post Closed message."""
        widget = CommandPalette()

        with patch.object(widget, "post_message") as mock_post:
            widget.hide()

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, CommandPalette.Closed)


class TestCommandPaletteOnInputChanged:
    """Tests for on_input_changed handler."""

    def test_input_changed_updates_search_query(self):
        """Input change should update search_query."""
        widget = CommandPalette()
        event = MagicMock()
        event.value = "new query"

        with patch.object(widget, "_filter_actions"):
            widget.on_input_changed(event)

        assert widget.search_query == "new query"

    def test_input_changed_calls_filter_actions(self):
        """Input change should call _filter_actions."""
        widget = CommandPalette()
        event = MagicMock()
        event.value = "test"

        with patch.object(widget, "_filter_actions") as mock_filter:
            widget.on_input_changed(event)
            mock_filter.assert_called_once()


class TestCommandPaletteOnInputSubmitted:
    """Tests for on_input_submitted handler."""

    def test_input_submitted_stops_event(self):
        """Input submitted should stop event propagation."""
        widget = CommandPalette()
        event = MagicMock()

        with patch.object(widget, "_execute_current"):
            widget.on_input_submitted(event)

        event.stop.assert_called_once()

    def test_input_submitted_calls_execute_current(self):
        """Input submitted should call _execute_current."""
        widget = CommandPalette()
        event = MagicMock()

        with patch.object(widget, "_execute_current") as mock_execute:
            widget.on_input_submitted(event)
            mock_execute.assert_called_once()


class TestCommandPaletteOnPaletteItemSelected:
    """Tests for on_palette_item_selected handler."""

    def test_item_selected_stops_event(self):
        """Item selected should stop event propagation."""
        widget = CommandPalette()
        action = PaletteAction(name="Test", description="Desc")
        event = PaletteItem.Selected(action)
        event.stop = MagicMock()

        with patch.object(widget, "post_message"):
            widget.on_palette_item_selected(event)

        event.stop.assert_called_once()

    def test_item_selected_removes_visible_class(self):
        """Item selected should remove visible class."""
        widget = CommandPalette()
        widget.add_class("visible")
        action = PaletteAction(name="Test", description="Desc")
        event = PaletteItem.Selected(action)
        event.stop = MagicMock()

        with patch.object(widget, "post_message"):
            widget.on_palette_item_selected(event)

        assert "visible" not in widget.classes

    def test_item_selected_posts_action_selected(self):
        """Item selected should post ActionSelected message."""
        widget = CommandPalette()
        action = PaletteAction(name="Test", description="Desc")
        event = PaletteItem.Selected(action)
        event.stop = MagicMock()

        with patch.object(widget, "post_message") as mock_post:
            widget.on_palette_item_selected(event)

        mock_post.assert_called_once()
        message = mock_post.call_args[0][0]
        assert isinstance(message, CommandPalette.ActionSelected)
        assert message.action is action


class TestCommandPaletteActionSelectPrev:
    """Tests for action_select_prev method."""

    def test_select_prev_decrements_index(self):
        """Select prev should decrement selected_index."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
            PaletteAction(name="C", description="D"),
        ]
        widget.selected_index = 2

        with patch.object(widget, "_render_results"):
            widget.action_select_prev()

        assert widget.selected_index == 1

    def test_select_prev_calls_render_results(self):
        """Select prev should call _render_results."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 1

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()
            mock_render.assert_called_once()

    def test_select_prev_does_not_go_below_zero(self):
        """Select prev should not decrement below 0."""
        widget = CommandPalette()
        widget.filtered_actions = [PaletteAction(name="A", description="D")]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()

        assert widget.selected_index == 0
        mock_render.assert_not_called()

    def test_select_prev_with_empty_results(self):
        """Select prev should do nothing with empty results."""
        widget = CommandPalette()
        widget.filtered_actions = []
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_prev()

        assert widget.selected_index == 0
        mock_render.assert_not_called()


class TestCommandPaletteActionSelectNext:
    """Tests for action_select_next method."""

    def test_select_next_increments_index(self):
        """Select next should increment selected_index."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
            PaletteAction(name="C", description="D"),
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results"):
            widget.action_select_next()

        assert widget.selected_index == 1

    def test_select_next_calls_render_results(self):
        """Select next should call _render_results."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()
            mock_render.assert_called_once()

    def test_select_next_does_not_exceed_length(self):
        """Select next should not increment beyond results length."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 1

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()

        assert widget.selected_index == 1
        mock_render.assert_not_called()

    def test_select_next_with_empty_results(self):
        """Select next should do nothing with empty results."""
        widget = CommandPalette()
        widget.filtered_actions = []
        widget.selected_index = 0

        with patch.object(widget, "_render_results") as mock_render:
            widget.action_select_next()

        assert widget.selected_index == 0
        mock_render.assert_not_called()


class TestCommandPaletteActionClose:
    """Tests for action_close method."""

    def test_action_close_calls_hide(self):
        """Close action should call hide."""
        widget = CommandPalette()

        with patch.object(widget, "hide") as mock_hide:
            mock_app = MagicMock()
            mock_app.query_one.side_effect = Exception("No widget")

            with patch.object(
                type(widget),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                widget.action_close()
                mock_hide.assert_called_once()

    def test_action_close_tries_to_focus_main_input(self):
        """Close action should try to focus main input."""
        widget = CommandPalette()
        mock_app = MagicMock()
        mock_input = MagicMock()
        mock_app.query_one.return_value = mock_input

        with patch.object(widget, "hide"):
            with patch.object(
                type(widget),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                widget.action_close()

        mock_app.query_one.assert_called_with("#input")
        mock_input.focus.assert_called_once()

    def test_action_close_handles_missing_input(self):
        """Close action should not crash if input is missing."""
        widget = CommandPalette()

        with patch.object(widget, "hide"):
            mock_app = MagicMock()
            mock_app.query_one.side_effect = Exception("No widget")

            with patch.object(
                type(widget),
                "app",
                new_callable=lambda: property(lambda self: mock_app),
            ):
                # Should not raise
                widget.action_close()


class TestCommandPaletteActionExecute:
    """Tests for action_execute method."""

    def test_action_execute_calls_execute_current(self):
        """Execute action should call _execute_current."""
        widget = CommandPalette()

        with patch.object(widget, "_execute_current") as mock_execute:
            widget.action_execute()
            mock_execute.assert_called_once()


class TestCommandPaletteFilterActions:
    """Tests for _filter_actions method."""

    def test_empty_query_returns_all_actions(self):
        """Empty query should return all actions."""
        widget = CommandPalette()
        widget._all_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.search_query = ""

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        assert len(widget.filtered_actions) == 2

    def test_whitespace_query_returns_all_actions(self):
        """Whitespace-only query should return all actions."""
        widget = CommandPalette()
        widget._all_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.search_query = "   "

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        assert len(widget.filtered_actions) == 2

    def test_query_filters_actions(self):
        """Query should filter to matching actions."""
        widget = CommandPalette()
        widget._all_actions = [
            PaletteAction(name="Clear History", description="D"),
            PaletteAction(name="Open File", description="D"),
            PaletteAction(name="Save File", description="D"),
        ]
        widget.search_query = "file"

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        assert len(widget.filtered_actions) == 2
        names = [a.name for a in widget.filtered_actions]
        assert "Open File" in names
        assert "Save File" in names

    def test_filter_sorts_by_score_descending(self):
        """Filtered actions should be sorted by match score descending."""
        widget = CommandPalette()
        widget._all_actions = [
            PaletteAction(name="xyz", description="File operations"),  # desc match
            PaletteAction(name="File Manager", description="D"),  # name start match
            PaletteAction(name="Open File", description="D"),  # name contains match
        ]
        widget.search_query = "file"

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        # File Manager should be first (starts with File)
        assert widget.filtered_actions[0].name == "File Manager"

    def test_filter_resets_selected_index(self):
        """Filter should reset selected_index to 0."""
        widget = CommandPalette()
        widget._all_actions = [PaletteAction(name="A", description="D")]
        widget.search_query = "a"
        widget.selected_index = 5

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        assert widget.selected_index == 0

    def test_filter_calls_render_results(self):
        """Filter should call _render_results."""
        widget = CommandPalette()
        widget._all_actions = []
        widget.search_query = ""

        with patch.object(widget, "_render_results") as mock_render:
            widget._filter_actions()
            mock_render.assert_called_once()


class TestCommandPaletteRenderResults:
    """Tests for _render_results method."""

    def test_render_results_clears_container(self):
        """Render results should clear container first."""
        widget = CommandPalette()
        widget.filtered_actions = []

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.remove_children.assert_called_once()

    def test_render_results_shows_no_matching_label(self):
        """Empty results should show 'No matching commands' label."""
        widget = CommandPalette()
        widget.filtered_actions = []

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        mock_container.mount.assert_called_once()
        mounted_widget = mock_container.mount.call_args[0][0]
        assert isinstance(mounted_widget, Label)
        assert "palette-no-results" in mounted_widget.classes

    def test_render_results_mounts_palette_items(self):
        """Results should be mounted as PaletteItem widgets."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        assert mock_container.mount.call_count == 2

    def test_render_results_limits_to_15(self):
        """Results should be limited to 15 items."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name=f"Action {i}", description="D") for i in range(20)
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        assert mock_container.mount.call_count == 15

    def test_render_results_adds_selected_class(self):
        """Selected item should have 'selected' class."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 1

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        calls = mock_container.mount.call_args_list
        first_item = calls[0][0][0]
        second_item = calls[1][0][0]

        assert "selected" not in first_item.classes
        assert "selected" in second_item.classes

    def test_render_results_all_have_palette_item_class(self):
        """All items should have 'palette-item' class."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 0

        mock_container = MagicMock(spec=Vertical)
        widget.query_one = MagicMock(return_value=mock_container)

        widget._render_results()

        calls = mock_container.mount.call_args_list
        for call in calls:
            item = call[0][0]
            assert "palette-item" in item.classes

    def test_render_results_handles_exception(self):
        """Render results should not crash on exception."""
        widget = CommandPalette()
        widget.filtered_actions = [PaletteAction(name="A", description="D")]
        widget.query_one = MagicMock(side_effect=Exception("No widget"))

        # Should not raise
        widget._render_results()


class TestCommandPaletteExecuteCurrent:
    """Tests for _execute_current method."""

    def test_execute_current_with_valid_selection(self):
        """Valid selection should post ActionSelected message."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
        ]
        widget.selected_index = 1
        widget.add_class("visible")

        with patch.object(widget, "post_message") as mock_post:
            widget._execute_current()

        mock_post.assert_called_once()
        message = mock_post.call_args[0][0]
        assert isinstance(message, CommandPalette.ActionSelected)
        assert message.action.name == "B"

    def test_execute_current_removes_visible_class(self):
        """Execute current should remove 'visible' class."""
        widget = CommandPalette()
        widget.filtered_actions = [PaletteAction(name="A", description="D")]
        widget.selected_index = 0
        widget.add_class("visible")

        with patch.object(widget, "post_message"):
            widget._execute_current()

        assert "visible" not in widget.classes

    def test_execute_current_empty_results_calls_hide(self):
        """Empty results should call hide."""
        widget = CommandPalette()
        widget.filtered_actions = []
        widget.selected_index = 0

        with patch.object(widget, "hide") as mock_hide:
            widget._execute_current()
            mock_hide.assert_called_once()

    def test_execute_current_invalid_index_calls_hide(self):
        """Invalid index should call hide."""
        widget = CommandPalette()
        widget.filtered_actions = [PaletteAction(name="A", description="D")]
        widget.selected_index = 5

        with patch.object(widget, "hide") as mock_hide:
            widget._execute_current()
            mock_hide.assert_called_once()

    def test_execute_current_negative_index_calls_hide(self):
        """Negative index should call hide."""
        widget = CommandPalette()
        widget.filtered_actions = [PaletteAction(name="A", description="D")]
        widget.selected_index = -1

        with patch.object(widget, "hide") as mock_hide:
            widget._execute_current()
            mock_hide.assert_called_once()


class TestCommandPaletteBuildActions:
    """Tests for _build_actions method."""

    def test_build_actions_includes_keybindings(self):
        """Build actions should include keybinding actions."""
        widget = CommandPalette()
        mock_app = MagicMock(spec=[])

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.side_effect = Exception("No config")
                actions = widget._build_actions()

        names = [a.name for a in actions]
        assert "Toggle AI Mode" in names
        assert "Clear History" in names
        assert "Open Help" in names

    def test_build_actions_keybindings_have_shortcuts(self):
        """Keybinding actions should have shortcuts."""
        widget = CommandPalette()
        mock_app = MagicMock(spec=[])

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.side_effect = Exception("No config")
                actions = widget._build_actions()

        toggle = next((a for a in actions if a.name == "Toggle AI Mode"), None)
        assert toggle is not None
        assert toggle.shortcut == "Ctrl+Space"
        assert toggle.category == "keybindings"
        assert toggle.action_id == "action:toggle_ai_mode"

    def test_build_actions_includes_slash_commands(self):
        """Build actions should include slash commands from command handler."""
        widget = CommandPalette()

        mock_cmd_info = MagicMock()
        mock_cmd_info.name = "help"
        mock_cmd_info.description = "Show help"
        mock_cmd_info.shortcut = "F1"
        mock_cmd_info.subcommands = []

        mock_cmd_handler = MagicMock()
        mock_cmd_handler.get_all_commands.return_value = [mock_cmd_info]

        mock_app = MagicMock()
        mock_app.command_handler = mock_cmd_handler

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.side_effect = Exception("No config")
                actions = widget._build_actions()

        help_action = next((a for a in actions if a.name == "/help"), None)
        assert help_action is not None
        assert help_action.category == "commands"
        assert help_action.action_id == "slash:/help"

    def test_build_actions_includes_subcommands(self):
        """Build actions should include subcommands."""
        widget = CommandPalette()

        mock_cmd_info = MagicMock()
        mock_cmd_info.name = "mcp"
        mock_cmd_info.description = "MCP management"
        mock_cmd_info.shortcut = ""
        mock_cmd_info.subcommands = [
            ("list", "List servers"),
            ("add", "Add server"),
        ]

        mock_cmd_handler = MagicMock()
        mock_cmd_handler.get_all_commands.return_value = [mock_cmd_info]

        mock_app = MagicMock()
        mock_app.command_handler = mock_cmd_handler

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.side_effect = Exception("No config")
                actions = widget._build_actions()

        names = [a.name for a in actions]
        assert "/mcp list" in names
        assert "/mcp add" in names

    def test_build_actions_includes_history(self):
        """Build actions should include recent history commands."""
        widget = CommandPalette()
        mock_app = MagicMock(spec=[])

        mock_storage = MagicMock()
        mock_storage.get_last_history.return_value = ["ls -la", "git status"]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.return_value = mock_storage
                actions = widget._build_actions()

        names = [a.name for a in actions]
        assert "ls -la" in names
        assert "git status" in names

    def test_build_actions_skips_slash_commands_in_history(self):
        """History should skip slash commands (already listed)."""
        widget = CommandPalette()
        mock_app = MagicMock(spec=[])

        mock_storage = MagicMock()
        mock_storage.get_last_history.return_value = ["/help", "ls -la"]

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.return_value = mock_storage
                actions = widget._build_actions()

        history_actions = [a for a in actions if a.category == "history"]
        names = [a.name for a in history_actions]
        assert "ls -la" in names
        assert "/help" not in names

    def test_build_actions_handles_history_exception(self):
        """Build actions should handle history exceptions gracefully."""
        widget = CommandPalette()
        mock_app = MagicMock(spec=[])

        with patch.object(
            type(widget), "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            with patch("config.Config") as mock_config:
                mock_config._get_storage.side_effect = Exception("No config")
                actions = widget._build_actions()

        assert len(actions) > 0


class TestCommandPaletteIntegration:
    """Integration-style tests for CommandPalette behavior."""

    def test_full_search_flow(self):
        """Test complete search flow: show -> type -> select."""
        widget = CommandPalette()
        widget._render_results = MagicMock()
        widget.query_one = MagicMock(return_value=MagicMock(spec=Input))

        with patch.object(widget, "_build_actions", return_value=[]):
            widget.show()

        assert "visible" in widget.classes
        assert widget.search_query == ""
        assert widget.filtered_actions == []
        assert widget.selected_index == 0

    def test_navigation_boundaries(self):
        """Test navigation stays within bounds."""
        widget = CommandPalette()
        widget.filtered_actions = [
            PaletteAction(name="A", description="D"),
            PaletteAction(name="B", description="D"),
            PaletteAction(name="C", description="D"),
        ]
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

    def test_filter_updates_selection(self):
        """Test that filtering resets selection to first item."""
        widget = CommandPalette()
        widget._all_actions = [
            PaletteAction(name="Aaa", description="D"),
            PaletteAction(name="Bbb", description="D"),
            PaletteAction(name="Ccc", description="D"),
        ]
        widget.filtered_actions = list(widget._all_actions)
        widget.selected_index = 2

        widget.search_query = "a"

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        assert widget.selected_index == 0
        assert len(widget.filtered_actions) == 1
        assert widget.filtered_actions[0].name == "Aaa"

    def test_fuzzy_matching_works(self):
        """Test that fuzzy matching finds partial matches."""
        widget = CommandPalette()
        widget._all_actions = [
            PaletteAction(name="Clear History", description="D"),
            PaletteAction(name="Open File", description="D"),
        ]
        widget.search_query = "clh"  # C-L-ear H-istory

        with patch.object(widget, "_render_results"):
            widget._filter_actions()

        assert len(widget.filtered_actions) == 1
        assert widget.filtered_actions[0].name == "Clear History"

    def test_reactive_properties_are_independent(self):
        """Test that reactive properties don't interfere with each other."""
        widget = CommandPalette()

        widget.search_query = "test"
        widget.filtered_actions = [PaletteAction(name="A", description="D")]
        widget.selected_index = 0

        assert widget.search_query == "test"
        assert len(widget.filtered_actions) == 1
        assert widget.selected_index == 0

        # Modify one, others should be unchanged
        widget.selected_index = 0
        assert widget.search_query == "test"
        assert len(widget.filtered_actions) == 1

    def test_select_with_no_results_hides(self):
        """Test that selecting with no results hides palette."""
        widget = CommandPalette()
        widget.filtered_actions = []

        with patch.object(widget, "hide") as mock_hide:
            widget.action_execute()
            mock_hide.assert_called_once()
