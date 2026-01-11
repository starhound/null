"""Tests for the branch diff screen."""

import pytest
from unittest.mock import MagicMock, patch

from screens.branch_diff import BranchDiffScreen
from models import BlockState, BlockType
from managers.branch import BranchManager


class TestBranchDiffScreenInit:
    """Tests for BranchDiffScreen initialization."""

    def test_init_stores_branch_ids(self):
        """Test that branch IDs are stored correctly."""
        manager = BranchManager()
        screen = BranchDiffScreen("branch-a", "branch-b", manager)
        assert screen.branch_a_id == "branch-a"
        assert screen.branch_b_id == "branch-b"

    def test_init_stores_branch_manager(self):
        """Test that branch manager reference is stored."""
        manager = BranchManager()
        screen = BranchDiffScreen("main", "feature", manager)
        assert screen.branch_manager is manager

    def test_init_with_mock_manager(self):
        """Test initialization with a mock manager."""
        mock_manager = MagicMock()
        mock_manager.branches = {}
        screen = BranchDiffScreen("a", "b", mock_manager)
        assert screen.branch_manager is mock_manager

    def test_init_with_empty_branch_ids(self):
        """Test initialization with empty string branch IDs."""
        manager = BranchManager()
        screen = BranchDiffScreen("", "", manager)
        assert screen.branch_a_id == ""
        assert screen.branch_b_id == ""

    def test_init_with_special_characters_in_branch_id(self):
        """Test initialization with special characters in branch IDs."""
        manager = BranchManager()
        screen = BranchDiffScreen("feature/test-123", "bugfix_456", manager)
        assert screen.branch_a_id == "feature/test-123"
        assert screen.branch_b_id == "bugfix_456"


class TestBranchDiffScreenBindings:
    """Tests for screen key bindings."""

    def test_bindings_defined(self):
        """Test that BINDINGS are defined on the class."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        assert hasattr(screen, "BINDINGS")
        assert len(screen.BINDINGS) >= 2

    def test_escape_binding_exists(self):
        """Test that escape key binding exists."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    def test_q_binding_exists(self):
        """Test that 'q' key binding exists for closing."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "q" in binding_keys

    def test_escape_action_is_dismiss(self):
        """Test that escape binding calls dismiss action."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        escape_binding = next(b for b in screen.BINDINGS if b.key == "escape")
        assert escape_binding.action == "dismiss"

    def test_q_binding_is_hidden(self):
        """Test that 'q' binding has show=False."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        q_binding = next(b for b in screen.BINDINGS if b.key == "q")
        assert q_binding.show is False


class TestBranchDiffScreenActions:
    """Tests for screen action methods."""

    def test_action_dismiss_calls_dismiss(self):
        """Test that action_dismiss calls the dismiss method."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.dismiss = MagicMock()
        screen.action_dismiss()
        screen.dismiss.assert_called_once()

    def test_action_dismiss_no_arguments(self):
        """Test that action_dismiss calls dismiss without arguments."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.dismiss = MagicMock()
        screen.action_dismiss()
        screen.dismiss.assert_called_once_with()


class TestBranchDiffScreenButtonHandling:
    """Tests for button press handling."""

    def test_close_button_dismisses(self):
        """Test that pressing close button dismisses the screen."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "close"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once()

    def test_other_button_does_not_dismiss(self):
        """Test that other button IDs don't dismiss the screen."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "other-button"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_not_called()

    def test_none_button_id_does_not_dismiss(self):
        """Test that None button ID doesn't dismiss the screen."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = None
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_not_called()


class TestBranchDiffScreenCreateBlockWidget:
    """Tests for the _create_block_widget method."""

    def _get_widget_text(self, widget):
        return str(widget._Static__content)

    def test_create_block_widget_short_content(self):
        """Test widget creation with short content."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="ls -la",
        )

        widget = screen._create_block_widget(block)
        text = self._get_widget_text(widget)
        assert BlockType.COMMAND.name in text
        assert "ls -la" in text

    def test_create_block_widget_long_content_truncated(self):
        """Test widget creation truncates content over 50 chars."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        long_content = "x" * 100
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input=long_content,
        )

        widget = screen._create_block_widget(block)
        text = self._get_widget_text(widget)
        assert "..." in text
        assert "x" * 50 in text

    def test_create_block_widget_exactly_50_chars(self):
        """Test widget creation with exactly 50 characters."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        content_50 = "y" * 50
        block = BlockState(
            type=BlockType.COMMAND,
            content_input=content_50,
        )

        widget = screen._create_block_widget(block)
        text = self._get_widget_text(widget)
        assert "..." not in text
        assert content_50 in text

    def test_create_block_widget_51_chars_truncated(self):
        """Test widget creation with 51 characters gets truncated."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        content_51 = "z" * 51
        block = BlockState(
            type=BlockType.COMMAND,
            content_input=content_51,
        )

        widget = screen._create_block_widget(block)
        text = self._get_widget_text(widget)
        assert "..." in text

    def test_create_block_widget_has_block_item_class(self):
        """Test widget has the correct CSS class."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="test",
        )

        widget = screen._create_block_widget(block)
        assert "block-item" in widget.classes

    def test_create_block_widget_shows_block_type_name(self):
        """Test widget displays the block type name."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        for block_type in [
            BlockType.COMMAND,
            BlockType.AI_RESPONSE,
            BlockType.AGENT_RESPONSE,
        ]:
            block = BlockState(
                type=block_type,
                content_input="test content",
            )
            widget = screen._create_block_widget(block)
            text = self._get_widget_text(widget)
            assert block_type.name in text

    def test_create_block_widget_empty_content(self):
        """Test widget creation with empty content."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="",
        )

        widget = screen._create_block_widget(block)
        text = self._get_widget_text(widget)
        assert BlockType.COMMAND.name in text


class TestBranchDiffScreenCSS:
    """Tests for CSS definition."""

    def test_default_css_defined(self):
        """Test that DEFAULT_CSS is defined."""
        assert hasattr(BranchDiffScreen, "DEFAULT_CSS")
        assert len(BranchDiffScreen.DEFAULT_CSS) > 0

    def test_css_contains_diff_container(self):
        """Test that CSS includes diff-container styles."""
        assert "#diff-container" in BranchDiffScreen.DEFAULT_CSS

    def test_css_contains_column_styles(self):
        """Test that CSS includes column styles."""
        assert ".column" in BranchDiffScreen.DEFAULT_CSS

    def test_css_contains_header_styles(self):
        """Test that CSS includes header styles."""
        assert ".header" in BranchDiffScreen.DEFAULT_CSS

    def test_css_contains_block_item_styles(self):
        """Test that CSS includes block-item styles."""
        assert ".block-item" in BranchDiffScreen.DEFAULT_CSS

    def test_css_contains_close_button_styles(self):
        """Test that CSS includes close button styles."""
        assert "#close" in BranchDiffScreen.DEFAULT_CSS


class TestBranchDiffScreenBranchData:
    """Tests for branch data handling."""

    def test_empty_branches_dict_handled(self):
        """Test screen handles empty branches dictionary."""
        manager = BranchManager()
        manager.branches = {}
        screen = BranchDiffScreen("branch-a", "branch-b", manager)
        assert screen.branch_manager.branches == {}

    def test_nonexistent_branch_ids_stored(self):
        """Test screen stores branch IDs that don't exist in manager."""
        manager = BranchManager()
        manager.branches = {"other": []}
        screen = BranchDiffScreen("missing-a", "missing-b", manager)
        assert screen.branch_a_id == "missing-a"
        assert screen.branch_b_id == "missing-b"
        assert "missing-a" not in manager.branches

    def test_one_empty_branch_handled(self):
        """Test screen handles one populated and one empty branch."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        manager.branches = {
            "branch-a": [block],
            "branch-b": [],
        }
        screen = BranchDiffScreen("branch-a", "branch-b", manager)
        assert len(screen.branch_manager.branches["branch-a"]) == 1
        assert len(screen.branch_manager.branches["branch-b"]) == 0

    def test_populated_branches_accessible(self):
        """Test screen can access blocks in both branches."""
        manager = BranchManager()
        block_a = BlockState(type=BlockType.COMMAND, content_input="cmd a")
        block_b = BlockState(type=BlockType.AI_RESPONSE, content_input="response b")
        manager.branches = {
            "branch-a": [block_a],
            "branch-b": [block_b],
        }
        screen = BranchDiffScreen("branch-a", "branch-b", manager)
        assert screen.branch_manager.branches.get("branch-a") == [block_a]
        assert screen.branch_manager.branches.get("branch-b") == [block_b]

    def test_multiple_blocks_per_branch_accessible(self):
        """Test screen can access multiple blocks in each branch."""
        manager = BranchManager()
        blocks_a = [
            BlockState(type=BlockType.COMMAND, content_input="cmd 1"),
            BlockState(type=BlockType.COMMAND, content_input="cmd 2"),
            BlockState(type=BlockType.AI_RESPONSE, content_input="response 1"),
        ]
        blocks_b = [
            BlockState(type=BlockType.COMMAND, content_input="cmd 3"),
            BlockState(type=BlockType.AGENT_RESPONSE, content_input="agent response"),
        ]
        manager.branches = {
            "branch-a": blocks_a,
            "branch-b": blocks_b,
        }
        screen = BranchDiffScreen("branch-a", "branch-b", manager)
        assert len(screen.branch_manager.branches["branch-a"]) == 3
        assert len(screen.branch_manager.branches["branch-b"]) == 2


class TestBranchDiffScreenIntegration:
    """Integration tests for BranchDiffScreen with BranchManager."""

    def test_with_real_branch_manager_forked_branches(self):
        """Test with a real branch manager that has forked branches."""
        manager = BranchManager()
        blocks = [
            BlockState(type=BlockType.COMMAND, content_input="first", id="block-1"),
            BlockState(type=BlockType.COMMAND, content_input="second", id="block-2"),
            BlockState(type=BlockType.AI_RESPONSE, content_input="third", id="block-3"),
        ]
        # Simulate having a main branch
        manager.branches["main"] = blocks

        # Fork at block-2
        manager.fork("feature", blocks, "block-2")

        screen = BranchDiffScreen("main", "feature", manager)

        assert screen.branch_a_id == "main"
        assert screen.branch_b_id == "feature"
        # Verify the branches exist in manager
        assert "main" in manager.branches
        assert "feature" in manager.branches
        # Feature branch should have 2 blocks (up to and including fork point)
        assert len(manager.branches["feature"]) == 2

    def test_screen_preserves_branch_manager_state(self):
        """Test that creating a screen doesn't modify branch manager."""
        manager = BranchManager()
        blocks = [BlockState(type=BlockType.COMMAND, content_input="test")]
        manager.branches = {"main": blocks, "feature": []}
        manager.current_branch = "main"

        screen = BranchDiffScreen("main", "feature", manager)

        assert manager.current_branch == "main"
        assert len(manager.branches) == 2

    def test_screen_does_not_copy_branch_manager(self):
        """Test that screen uses reference to original manager."""
        manager = BranchManager()
        manager.branches = {"main": []}
        screen = BranchDiffScreen("main", "feature", manager)

        manager.branches["new_branch"] = []
        assert "new_branch" in screen.branch_manager.branches


class TestBranchDiffScreenBlockTypes:
    """Tests ensuring all block types are handled correctly."""

    def _get_widget_text(self, widget):
        return str(widget._Static__content)

    def test_command_block_type(self):
        """Test handling of COMMAND block type."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        widget = screen._create_block_widget(block)
        assert "COMMAND" in self._get_widget_text(widget)

    def test_ai_response_block_type(self):
        """Test handling of AI_RESPONSE block type."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(type=BlockType.AI_RESPONSE, content_input="help me")
        widget = screen._create_block_widget(block)
        assert "AI_RESPONSE" in self._get_widget_text(widget)

    def test_agent_response_block_type(self):
        """Test handling of AGENT_RESPONSE block type."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="run task")
        widget = screen._create_block_widget(block)
        assert "AGENT_RESPONSE" in self._get_widget_text(widget)

    def test_ai_query_block_type(self):
        """Test handling of AI_QUERY block type."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(type=BlockType.AI_QUERY, content_input="what is python?")
        widget = screen._create_block_widget(block)
        assert "AI_QUERY" in self._get_widget_text(widget)

    def test_system_msg_block_type(self):
        """Test handling of SYSTEM_MSG block type."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="system message")
        widget = screen._create_block_widget(block)
        assert "SYSTEM_MSG" in self._get_widget_text(widget)

    def test_tool_call_block_type(self):
        """Test handling of TOOL_CALL block type."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(type=BlockType.TOOL_CALL, content_input="read_file")
        widget = screen._create_block_widget(block)
        assert "TOOL_CALL" in self._get_widget_text(widget)


class TestBranchDiffScreenEdgeCases:
    """Edge case tests."""

    def _get_widget_text(self, widget):
        return str(widget._Static__content)

    def test_same_branch_comparison(self):
        """Test comparing a branch with itself."""
        manager = BranchManager()
        blocks = [BlockState(type=BlockType.COMMAND, content_input="test")]
        manager.branches = {"main": blocks}

        screen = BranchDiffScreen("main", "main", manager)
        assert screen.branch_a_id == screen.branch_b_id

    def test_unicode_in_branch_names(self):
        """Test with unicode characters in branch names."""
        manager = BranchManager()
        screen = BranchDiffScreen("feature/emoji-\u2764", "fix/bug-\u26a0", manager)
        assert "\u2764" in screen.branch_a_id
        assert "\u26a0" in screen.branch_b_id

    def test_unicode_in_block_content(self):
        """Test blocks with unicode content."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="echo 'Hello \u4e16\u754c \ud83c\udf0d'",
        )
        widget = screen._create_block_widget(block)
        assert "\u4e16\u754c" in self._get_widget_text(widget)

    def test_very_long_branch_name(self):
        """Test with very long branch names."""
        manager = BranchManager()
        long_name = "feature/" + "x" * 200
        screen = BranchDiffScreen(long_name, "main", manager)
        assert screen.branch_a_id == long_name

    def test_whitespace_in_content(self):
        """Test blocks with whitespace-only content."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="   \t\n   ",
        )
        widget = screen._create_block_widget(block)
        assert widget is not None

    def test_special_characters_in_content(self):
        """Test blocks with special/control characters."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)

        block = BlockState(
            type=BlockType.COMMAND,
            content_input="echo $HOME && cat /etc/passwd | grep 'root'",
        )
        widget = screen._create_block_widget(block)
        assert "$HOME" in self._get_widget_text(widget)
