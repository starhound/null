"""Tests for widgets/nl2shell_preview.py - NL2ShellPreview widget."""

from dataclasses import dataclass, field
from unittest.mock import MagicMock

from textual.widgets import Static

from widgets.nl2shell_preview import NL2ShellPreview


@dataclass
class MockCommandSuggestion:
    command: str
    explanation: str
    confidence: float = 0.8
    alternatives: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_sudo: bool = False


class MockedPreviewWidget:
    Accepted = NL2ShellPreview.Accepted
    Rejected = NL2ShellPreview.Rejected

    def __init__(self):
        self._alternatives = []
        self.current_alternative_index = -1
        self.suggestion = None
        self.is_loading = False
        self.post_message = MagicMock()
        self.query_one = MagicMock()
        self.set_class = MagicMock()
        self._update_display = MagicMock()

    def action_cycle(self):
        NL2ShellPreview.action_cycle(self)

    def action_accept(self):
        NL2ShellPreview.action_accept(self)

    def action_reject(self):
        NL2ShellPreview.action_reject(self)


# =============================================================================
# NL2ShellPreview CSS Tests
# =============================================================================


class TestNL2ShellPreviewCSS:
    """Test NL2ShellPreview DEFAULT_CSS configuration."""

    def test_default_css_sets_display_none(self):
        """NL2ShellPreview should be hidden by default."""
        assert "display: none" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_sets_vertical_layout(self):
        """NL2ShellPreview should use vertical layout."""
        assert "layout: vertical" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_sets_background(self):
        """NL2ShellPreview should have background: $surface."""
        assert "background: $surface" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_sets_border_top(self):
        """NL2ShellPreview should have a top border."""
        assert "border-top: solid $primary" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_visible_class(self):
        """NL2ShellPreview should have --visible class for showing."""
        assert "NL2ShellPreview.--visible" in NL2ShellPreview.DEFAULT_CSS
        assert "display: block" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_preview_container(self):
        """Preview container should have horizontal layout."""
        assert ".preview-container" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_command_text_styling(self):
        """Command text should have accent color and bold style."""
        assert ".command-text" in NL2ShellPreview.DEFAULT_CSS
        assert "color: $accent" in NL2ShellPreview.DEFAULT_CSS
        assert "text-style: bold" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_confidence_badge(self):
        """Confidence badge should have success styling."""
        assert ".confidence-badge" in NL2ShellPreview.DEFAULT_CSS
        assert "background: $success" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_low_confidence_styling(self):
        """Low confidence badge should have warning colors."""
        assert ".confidence-badge.low" in NL2ShellPreview.DEFAULT_CSS
        assert "color: $warning" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_explanation_styling(self):
        """Explanation should have muted text and italic style."""
        assert ".explanation" in NL2ShellPreview.DEFAULT_CSS
        assert "text-style: italic" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_controls_styling(self):
        """Controls should have disabled text and dim style."""
        assert ".controls" in NL2ShellPreview.DEFAULT_CSS
        assert "color: $text-disabled" in NL2ShellPreview.DEFAULT_CSS
        assert "text-style: dim" in NL2ShellPreview.DEFAULT_CSS

    def test_default_css_has_loading_container(self):
        """Loading container should have centered alignment."""
        assert ".loading-container" in NL2ShellPreview.DEFAULT_CSS
        assert "align: center middle" in NL2ShellPreview.DEFAULT_CSS


# =============================================================================
# NL2ShellPreview Reactive Properties Tests
# =============================================================================


class TestNL2ShellPreviewReactiveProperties:
    """Test NL2ShellPreview reactive properties."""

    def test_suggestion_is_reactive(self):
        """suggestion should be a reactive property."""
        assert hasattr(NL2ShellPreview, "suggestion")
        assert NL2ShellPreview.suggestion._default is None

    def test_is_loading_is_reactive(self):
        """is_loading should be a reactive property."""
        assert hasattr(NL2ShellPreview, "is_loading")
        assert NL2ShellPreview.is_loading._default is False

    def test_current_alternative_index_is_reactive(self):
        """current_alternative_index should be a reactive property."""
        assert hasattr(NL2ShellPreview, "current_alternative_index")
        assert NL2ShellPreview.current_alternative_index._default == -1


# =============================================================================
# NL2ShellPreview Messages Tests
# =============================================================================


class TestNL2ShellPreviewAcceptedMessage:
    """Test Accepted message class."""

    def test_accepted_message_stores_command(self):
        """Accepted message should store the command."""
        msg = NL2ShellPreview.Accepted("ls -la")
        assert msg.command == "ls -la"

    def test_accepted_message_empty_command(self):
        """Accepted message should handle empty command."""
        msg = NL2ShellPreview.Accepted("")
        assert msg.command == ""

    def test_accepted_message_complex_command(self):
        """Accepted message should handle complex commands."""
        msg = NL2ShellPreview.Accepted("find . -name '*.py' | xargs grep 'def'")
        assert msg.command == "find . -name '*.py' | xargs grep 'def'"


class TestNL2ShellPreviewRejectedMessage:
    """Test Rejected message class."""

    def test_rejected_message_instantiates(self):
        """Rejected message should instantiate without error."""
        msg = NL2ShellPreview.Rejected()
        assert msg is not None

    def test_rejected_message_is_message_subclass(self):
        """Rejected message should be a Message subclass."""
        from textual.message import Message

        msg = NL2ShellPreview.Rejected()
        assert isinstance(msg, Message)


# =============================================================================
# NL2ShellPreview Class Definition Tests
# =============================================================================


class TestNL2ShellPreviewClassDefinition:
    """Test NL2ShellPreview class definition."""

    def test_inherits_from_static(self):
        """NL2ShellPreview should inherit from Static."""
        assert issubclass(NL2ShellPreview, Static)

    def test_has_compose_method(self):
        """NL2ShellPreview should have compose method."""
        assert hasattr(NL2ShellPreview, "compose")
        assert callable(NL2ShellPreview.compose)

    def test_has_watch_is_loading_method(self):
        """NL2ShellPreview should have watch_is_loading method."""
        assert hasattr(NL2ShellPreview, "watch_is_loading")

    def test_has_watch_suggestion_method(self):
        """NL2ShellPreview should have watch_suggestion method."""
        assert hasattr(NL2ShellPreview, "watch_suggestion")

    def test_has_update_display_method(self):
        """NL2ShellPreview should have _update_display method."""
        assert hasattr(NL2ShellPreview, "_update_display")

    def test_has_action_cycle_method(self):
        """NL2ShellPreview should have action_cycle method."""
        assert hasattr(NL2ShellPreview, "action_cycle")

    def test_has_action_accept_method(self):
        """NL2ShellPreview should have action_accept method."""
        assert hasattr(NL2ShellPreview, "action_accept")

    def test_has_action_reject_method(self):
        """NL2ShellPreview should have action_reject method."""
        assert hasattr(NL2ShellPreview, "action_reject")


# =============================================================================
# NL2ShellPreview Action Methods Tests (using mocked instance)
# =============================================================================


class TestNL2ShellPreviewActionCycle:
    """Test action_cycle method."""

    def test_action_cycle_does_nothing_without_alternatives(self):
        """action_cycle should do nothing without alternatives."""
        widget = MockedPreviewWidget()
        widget._alternatives = []
        widget.current_alternative_index = 0

        widget.action_cycle()

        widget._update_display.assert_not_called()

    def test_action_cycle_increments_index(self):
        """action_cycle should increment current_alternative_index."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["cmd1", "cmd2", "cmd3"]
        widget.current_alternative_index = 0

        widget.action_cycle()

        assert widget.current_alternative_index == 1

    def test_action_cycle_wraps_around(self):
        """action_cycle should wrap around to 0 after last alternative."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["cmd1", "cmd2", "cmd3"]
        widget.current_alternative_index = 2

        widget.action_cycle()

        assert widget.current_alternative_index == 0

    def test_action_cycle_calls_update_display(self):
        """action_cycle should call _update_display after cycling."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["cmd1", "cmd2"]
        widget.current_alternative_index = 0

        widget.action_cycle()

        widget._update_display.assert_called_once()

    def test_action_cycle_handles_single_alternative(self):
        """action_cycle should handle single alternative (stay at 0)."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["cmd1"]
        widget.current_alternative_index = 0

        widget.action_cycle()

        assert widget.current_alternative_index == 0


class TestNL2ShellPreviewActionAccept:
    """Test action_accept method."""

    def test_action_accept_does_nothing_without_alternatives(self):
        """action_accept should do nothing without alternatives."""
        widget = MockedPreviewWidget()
        widget._alternatives = []

        widget.action_accept()

        widget.post_message.assert_not_called()

    def test_action_accept_posts_accepted_message(self):
        """action_accept should post Accepted message with current command."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["ls -la", "ls -l"]
        widget.current_alternative_index = 0

        widget.action_accept()

        widget.post_message.assert_called_once()
        msg = widget.post_message.call_args[0][0]
        assert isinstance(msg, NL2ShellPreview.Accepted)
        assert msg.command == "ls -la"

    def test_action_accept_sends_selected_alternative(self):
        """action_accept should send the currently selected alternative."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["ls -la", "ls -l", "ls -lah"]
        widget.current_alternative_index = 2

        widget.action_accept()

        msg = widget.post_message.call_args[0][0]
        assert msg.command == "ls -lah"


class TestNL2ShellPreviewActionReject:
    """Test action_reject method."""

    def test_action_reject_posts_rejected_message(self):
        """action_reject should post Rejected message."""
        widget = MockedPreviewWidget()

        widget.action_reject()

        widget.post_message.assert_called_once()
        msg = widget.post_message.call_args[0][0]
        assert isinstance(msg, NL2ShellPreview.Rejected)


# =============================================================================
# NL2ShellPreview Watch Methods Tests
# =============================================================================


class TestNL2ShellPreviewWatchIsLoading:
    """Test watch_is_loading method."""

    def test_watch_is_loading_hides_content_when_loading(self):
        """Content area should be hidden when loading."""
        widget = MockedPreviewWidget()
        mock_content = MagicMock()
        mock_loader = MagicMock()

        def query_side_effect(sel):
            if "content" in sel:
                return mock_content
            return mock_loader

        widget.query_one = MagicMock(side_effect=query_side_effect)

        NL2ShellPreview.watch_is_loading(widget, True)

        assert mock_content.display is False

    def test_watch_is_loading_shows_loader_when_loading(self):
        """Loader area should be shown when loading."""
        widget = MockedPreviewWidget()
        mock_content = MagicMock()
        mock_loader = MagicMock()

        def query_side_effect(sel):
            if "content" in sel:
                return mock_content
            return mock_loader

        widget.query_one = MagicMock(side_effect=query_side_effect)

        NL2ShellPreview.watch_is_loading(widget, True)

        assert mock_loader.display is True

    def test_watch_is_loading_shows_content_when_not_loading(self):
        """Content area should be shown when not loading."""
        widget = MockedPreviewWidget()
        mock_content = MagicMock()
        mock_loader = MagicMock()

        def query_side_effect(sel):
            if "content" in sel:
                return mock_content
            return mock_loader

        widget.query_one = MagicMock(side_effect=query_side_effect)

        NL2ShellPreview.watch_is_loading(widget, False)

        assert mock_content.display is True

    def test_watch_is_loading_hides_loader_when_not_loading(self):
        """Loader area should be hidden when not loading."""
        widget = MockedPreviewWidget()
        mock_content = MagicMock()
        mock_loader = MagicMock()

        def query_side_effect(sel):
            if "content" in sel:
                return mock_content
            return mock_loader

        widget.query_one = MagicMock(side_effect=query_side_effect)

        NL2ShellPreview.watch_is_loading(widget, False)

        assert mock_loader.display is False


class TestNL2ShellPreviewWatchSuggestion:
    """Test watch_suggestion method."""

    def test_watch_suggestion_populates_alternatives(self):
        """Setting suggestion should populate _alternatives list."""
        widget = MockedPreviewWidget()

        suggestion = MockCommandSuggestion(
            command="ls -la",
            explanation="List all files",
            confidence=0.9,
            alternatives=["ls -l", "ls -lah"],
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        assert widget._alternatives == ["ls -la", "ls -l", "ls -lah"]

    def test_watch_suggestion_resets_alternative_index(self):
        """Setting suggestion should reset current_alternative_index to 0."""
        widget = MockedPreviewWidget()
        widget.current_alternative_index = 5

        suggestion = MockCommandSuggestion(
            command="ls -la", explanation="List all files"
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        assert widget.current_alternative_index == 0

    def test_watch_suggestion_calls_update_display(self):
        """Setting suggestion should call _update_display."""
        widget = MockedPreviewWidget()

        suggestion = MockCommandSuggestion(
            command="ls -la", explanation="List all files"
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        widget._update_display.assert_called_once()

    def test_watch_suggestion_returns_early_for_none(self):
        """Setting suggestion to None should not call _update_display."""
        widget = MockedPreviewWidget()

        NL2ShellPreview.watch_suggestion(widget, None)

        widget._update_display.assert_not_called()

    def test_watch_suggestion_handles_empty_alternatives(self):
        """Setting suggestion with no alternatives should work."""
        widget = MockedPreviewWidget()

        suggestion = MockCommandSuggestion(
            command="pwd", explanation="Print working directory", alternatives=[]
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        assert widget._alternatives == ["pwd"]


# =============================================================================
# NL2ShellPreview Update Display Tests
# =============================================================================


class TestNL2ShellPreviewUpdateDisplay:
    """Test _update_display method."""

    def test_update_display_does_nothing_without_suggestion(self):
        """_update_display should return early without suggestion."""
        widget = MockedPreviewWidget()
        widget.suggestion = None

        NL2ShellPreview._update_display(widget)

        widget.query_one.assert_not_called()

    def test_update_display_does_nothing_without_alternatives(self):
        """_update_display should return early without alternatives."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files"
        )
        widget._alternatives = []

        NL2ShellPreview._update_display(widget)

        widget.query_one.assert_not_called()

    def test_update_display_updates_command_preview(self):
        """_update_display should update command preview label."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls -la", explanation="List all files", confidence=0.9
        )
        widget._alternatives = ["ls -la"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        calls = [
            c for c in widget.query_one.call_args_list if "command-preview" in str(c)
        ]
        assert len(calls) > 0

    def test_update_display_updates_confidence_badge(self):
        """_update_display should update confidence badge."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls -la", explanation="List all files", confidence=0.85
        )
        widget._alternatives = ["ls -la"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        confidence_updates = [c for c in update_calls if "85%" in str(c)]
        assert len(confidence_updates) > 0

    def test_update_display_sets_low_class_for_low_confidence(self):
        """_update_display should add 'low' class when confidence < 0.7."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="rm -rf /", explanation="Delete everything", confidence=0.5
        )
        widget._alternatives = ["rm -rf /"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        set_class_calls = mock_label.set_class.call_args_list
        low_class_calls = [c for c in set_class_calls if c[0] == (True, "low")]
        assert len(low_class_calls) > 0

    def test_update_display_removes_low_class_for_high_confidence(self):
        """_update_display should not add 'low' class when confidence >= 0.7."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.9
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        set_class_calls = mock_label.set_class.call_args_list
        low_class_calls = [c for c in set_class_calls if c[0] == (False, "low")]
        assert len(low_class_calls) > 0

    def test_update_display_shows_explanation_for_main_command(self):
        """_update_display should show explanation when on main command."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls -la", explanation="List all files with details", confidence=0.9
        )
        widget._alternatives = ["ls -la", "ls -l"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        explanation_updates = [
            c for c in update_calls if "List all files with details" in str(c)
        ]
        assert len(explanation_updates) > 0

    def test_update_display_shows_alternative_text_for_alternatives(self):
        """_update_display should show 'Alternative command' for non-main."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls -la",
            explanation="List all files",
            confidence=0.9,
            alternatives=["ls -l"],
        )
        widget._alternatives = ["ls -la", "ls -l"]
        widget.current_alternative_index = 1

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        alt_updates = [c for c in update_calls if "Alternative command" in str(c)]
        assert len(alt_updates) > 0

    def test_update_display_shows_cycle_info_with_multiple_alternatives(self):
        """_update_display should show cycle info when multiple alternatives."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls -la",
            explanation="List files",
            confidence=0.9,
            alternatives=["ls -l", "ls -lah"],
        )
        widget._alternatives = ["ls -la", "ls -l", "ls -lah"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        cycle_updates = [c for c in update_calls if "Cycle (1/3)" in str(c)]
        assert len(cycle_updates) > 0

    def test_update_display_hides_cycle_info_with_single_command(self):
        """_update_display should hide cycle info when single command."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="pwd", explanation="Print working directory", confidence=0.95
        )
        widget._alternatives = ["pwd"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        cycle_updates = [c for c in update_calls if "Cycle" in str(c)]
        assert len(cycle_updates) == 0


# =============================================================================
# NL2ShellPreview Confidence Threshold Tests
# =============================================================================


class TestNL2ShellPreviewConfidenceThreshold:
    """Test confidence threshold behavior."""

    def test_confidence_exactly_07_is_not_low(self):
        """Confidence of exactly 0.7 should not be marked as low."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.7
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        set_class_calls = mock_label.set_class.call_args_list
        low_class_calls = [c for c in set_class_calls if c[0] == (False, "low")]
        assert len(low_class_calls) > 0

    def test_confidence_just_below_07_is_low(self):
        """Confidence just below 0.7 should be marked as low."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.69
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        set_class_calls = mock_label.set_class.call_args_list
        low_class_calls = [c for c in set_class_calls if c[0] == (True, "low")]
        assert len(low_class_calls) > 0

    def test_confidence_zero_is_low(self):
        """Confidence of 0.0 should be marked as low."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.0
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        set_class_calls = mock_label.set_class.call_args_list
        low_class_calls = [c for c in set_class_calls if c[0] == (True, "low")]
        assert len(low_class_calls) > 0

    def test_confidence_one_is_not_low(self):
        """Confidence of 1.0 should not be marked as low."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=1.0
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        set_class_calls = mock_label.set_class.call_args_list
        low_class_calls = [c for c in set_class_calls if c[0] == (False, "low")]
        assert len(low_class_calls) > 0


# =============================================================================
# NL2ShellPreview Confidence Display Tests
# =============================================================================


class TestNL2ShellPreviewConfidenceDisplay:
    """Test confidence percentage display."""

    def test_confidence_display_rounds_to_integer(self):
        """Confidence should be displayed as integer percentage."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.856
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        confidence_updates = [c for c in update_calls if "85%" in str(c)]
        assert len(confidence_updates) > 0

    def test_confidence_display_100_percent(self):
        """Confidence of 1.0 should display as 100%."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=1.0
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        confidence_updates = [c for c in update_calls if "100%" in str(c)]
        assert len(confidence_updates) > 0

    def test_confidence_display_0_percent(self):
        """Confidence of 0.0 should display as 0%."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.0
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        confidence_updates = [c for c in update_calls if "0%" in str(c)]
        assert len(confidence_updates) > 0


# =============================================================================
# NL2ShellPreview Visibility Logic Tests
# =============================================================================


class TestNL2ShellPreviewVisibility:
    """Test visibility logic."""

    def test_visible_when_loading_true(self):
        """Widget should be visible when is_loading is True."""
        widget = MockedPreviewWidget()
        widget.suggestion = None
        mock_content = MagicMock()
        mock_loader = MagicMock()
        widget.query_one = MagicMock(
            side_effect=lambda sel: mock_content if "content" in sel else mock_loader
        )

        NL2ShellPreview.watch_is_loading(widget, True)

        widget.set_class.assert_called_with(True, "--visible")

    def test_visible_when_suggestion_present(self):
        """Widget should be visible when suggestion is present."""
        widget = MockedPreviewWidget()
        widget.is_loading = False

        suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.9
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        widget.set_class.assert_called_with(True, "--visible")

    def test_hidden_when_not_loading_and_no_suggestion(self):
        """Widget should be hidden when not loading and no suggestion."""
        widget = MockedPreviewWidget()
        widget.suggestion = None
        mock_content = MagicMock()
        mock_loader = MagicMock()
        widget.query_one = MagicMock(
            side_effect=lambda sel: mock_content if "content" in sel else mock_loader
        )

        NL2ShellPreview.watch_is_loading(widget, False)

        widget.set_class.assert_called_with(False, "--visible")


# =============================================================================
# NL2ShellPreview Integration-style Tests
# =============================================================================


class TestNL2ShellPreviewIntegration:
    """Integration-style tests for NL2ShellPreview behavior."""

    def test_full_workflow_accept(self):
        """Test full workflow: show suggestion, accept."""
        widget = MockedPreviewWidget()
        widget.is_loading = False

        suggestion = MockCommandSuggestion(
            command="git status",
            explanation="Show git repository status",
            confidence=0.95,
            alternatives=["git status -s"],
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        assert widget._alternatives == ["git status", "git status -s"]
        assert widget.current_alternative_index == 0

        widget.action_accept()

        msg = widget.post_message.call_args[0][0]
        assert msg.command == "git status"

    def test_full_workflow_cycle_then_accept(self):
        """Test full workflow: show suggestion, cycle, accept."""
        widget = MockedPreviewWidget()
        widget.is_loading = False

        suggestion = MockCommandSuggestion(
            command="git status",
            explanation="Show git status",
            confidence=0.9,
            alternatives=["git status -s", "git status --short"],
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        widget.action_cycle()
        assert widget.current_alternative_index == 1

        widget.action_accept()

        msg = widget.post_message.call_args[0][0]
        assert msg.command == "git status -s"

    def test_full_workflow_reject(self):
        """Test full workflow: show suggestion, reject."""
        widget = MockedPreviewWidget()
        widget.is_loading = False

        suggestion = MockCommandSuggestion(
            command="rm -rf /", explanation="Delete everything", confidence=0.3
        )

        NL2ShellPreview.watch_suggestion(widget, suggestion)

        widget.action_reject()

        msg = widget.post_message.call_args[0][0]
        assert isinstance(msg, NL2ShellPreview.Rejected)

    def test_cycle_through_all_alternatives(self):
        """Test cycling through all alternatives wraps around."""
        widget = MockedPreviewWidget()
        widget._alternatives = ["cmd1", "cmd2", "cmd3"]
        widget.current_alternative_index = 0

        widget.action_cycle()
        assert widget.current_alternative_index == 1

        widget.action_cycle()
        assert widget.current_alternative_index == 2

        widget.action_cycle()
        assert widget.current_alternative_index == 0

    def test_loading_to_suggestion_transition(self):
        """Test transition from loading to showing suggestion."""
        widget = MockedPreviewWidget()
        mock_content = MagicMock()
        mock_loader = MagicMock()
        widget.query_one = MagicMock(
            side_effect=lambda sel: mock_content if "content" in sel else mock_loader
        )

        NL2ShellPreview.watch_is_loading(widget, True)
        assert mock_loader.display is True
        assert mock_content.display is False

        NL2ShellPreview.watch_is_loading(widget, False)
        assert mock_loader.display is False
        assert mock_content.display is True


# =============================================================================
# NL2ShellPreview Init Tests
# =============================================================================


class TestNL2ShellPreviewInit:
    """Test NL2ShellPreview __init__ method."""

    def test_init_creates_empty_alternatives(self):
        """__init__ should initialize _alternatives as empty list."""
        widget = object.__new__(NL2ShellPreview)
        NL2ShellPreview.__init__(widget)
        assert widget._alternatives == []


# =============================================================================
# NL2ShellPreview Command Format Tests
# =============================================================================


class TestNL2ShellPreviewCommandFormat:
    """Test command display formatting."""

    def test_command_preview_has_prompt_prefix(self):
        """Command preview should start with '> '."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.9
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        cmd_updates = [c for c in update_calls if "> ls" in str(c)]
        assert len(cmd_updates) > 0

    def test_command_preserves_pipes_and_quotes(self):
        """Command with pipes and quotes should be preserved."""
        widget = MockedPreviewWidget()
        cmd = "cat file.txt | grep 'pattern' | wc -l"
        widget.suggestion = MockCommandSuggestion(
            command=cmd, explanation="Count lines", confidence=0.9
        )
        widget._alternatives = [cmd]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        cmd_updates = [c for c in update_calls if cmd in str(c)]
        assert len(cmd_updates) > 0


# =============================================================================
# NL2ShellPreview Controls Text Tests
# =============================================================================


class TestNL2ShellPreviewControlsText:
    """Test controls text display."""

    def test_controls_show_accept_and_reject(self):
        """Controls should always show Accept and Reject."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls", explanation="List files", confidence=0.9
        )
        widget._alternatives = ["ls"]
        widget.current_alternative_index = 0

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        accept_updates = [c for c in update_calls if "Accept" in str(c)]
        reject_updates = [c for c in update_calls if "Reject" in str(c)]
        assert len(accept_updates) > 0
        assert len(reject_updates) > 0

    def test_controls_show_current_position_when_cycling(self):
        """Controls should show current position when cycling through alternatives."""
        widget = MockedPreviewWidget()
        widget.suggestion = MockCommandSuggestion(
            command="ls",
            explanation="List files",
            confidence=0.9,
            alternatives=["ls -l", "ls -la"],
        )
        widget._alternatives = ["ls", "ls -l", "ls -la"]
        widget.current_alternative_index = 1

        mock_label = MagicMock()
        widget.query_one = MagicMock(return_value=mock_label)

        NL2ShellPreview._update_display(widget)

        update_calls = mock_label.update.call_args_list
        position_updates = [c for c in update_calls if "2/3" in str(c)]
        assert len(position_updates) > 0
