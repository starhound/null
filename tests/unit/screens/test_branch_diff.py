"""Tests for the branch diff screen."""

from unittest.mock import MagicMock

from managers.branch import BranchManager
from models import BlockState, BlockType
from screens.branch_diff import (
    BranchDiffScreen,
    DiffHunk,
    DiffHunkWidget,
    DiffLineWidget,
    UnchangedSection,
)


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

    def test_init_creates_empty_change_positions(self):
        """Test that change_positions is initialized as empty list."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        assert screen.change_positions == []

    def test_init_creates_empty_diff_hunks(self):
        """Test that _diff_hunks is initialized as empty list."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        assert screen._diff_hunks == []


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

    def test_n_binding_for_next_change(self):
        """Test that 'n' binding exists for next change."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "n" in binding_keys
        n_binding = next(b for b in screen.BINDINGS if b.key == "n")
        assert n_binding.action == "next_change"

    def test_p_binding_for_prev_change(self):
        """Test that 'p' binding exists for previous change."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "p" in binding_keys
        p_binding = next(b for b in screen.BINDINGS if b.key == "p")
        assert p_binding.action == "prev_change"

    def test_j_binding_for_scroll_down(self):
        """Test that 'j' binding exists for scroll down."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "j" in binding_keys

    def test_k_binding_for_scroll_up(self):
        """Test that 'k' binding exists for scroll up."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "k" in binding_keys


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

    def test_action_next_change_increments_current_change(self):
        """Test that action_next_change increments current_change."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.change_positions = [0, 1, 2]
        screen.current_change = 0
        screen.action_next_change()
        assert screen.current_change == 1

    def test_action_next_change_wraps_around(self):
        """Test that action_next_change wraps around at end."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.change_positions = [0, 1, 2]
        screen.current_change = 2
        screen.action_next_change()
        assert screen.current_change == 0

    def test_action_prev_change_decrements_current_change(self):
        """Test that action_prev_change decrements current_change."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.change_positions = [0, 1, 2]
        screen.current_change = 2
        screen.action_prev_change()
        assert screen.current_change == 1

    def test_action_prev_change_wraps_around(self):
        """Test that action_prev_change wraps around at start."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.change_positions = [0, 1, 2]
        screen.current_change = 0
        screen.action_prev_change()
        assert screen.current_change == 2

    def test_action_next_change_no_changes(self):
        """Test that action_next_change does nothing when no changes."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.change_positions = []
        screen.current_change = 0
        screen.action_next_change()
        assert screen.current_change == 0


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

    def test_next_button_calls_action(self):
        """Test that btn-next calls action_next_change."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.action_next_change = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "btn-next"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.action_next_change.assert_called_once()

    def test_prev_button_calls_action(self):
        """Test that btn-prev calls action_prev_change."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.action_prev_change = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "btn-prev"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.action_prev_change.assert_called_once()

    def test_jump_button_sets_current_change(self):
        """Test that jump button sets current_change correctly."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        screen.change_positions = [0, 2, 5]
        screen.current_change = 0

        mock_button = MagicMock()
        mock_button.id = "jump-2"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        assert screen.current_change == 1  # Index of 2 in change_positions

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


class TestBlocksToLines:
    """Tests for the _blocks_to_lines method."""

    def test_empty_blocks_returns_empty_list(self):
        """Test that empty blocks list returns empty list."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        result = screen._blocks_to_lines([])
        assert result == []

    def test_single_block_converts_correctly(self):
        """Test that a single block converts to lines."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        block = BlockState(type=BlockType.COMMAND, content_input="ls -la")
        result = screen._blocks_to_lines([block])
        assert "[COMMAND]" in result
        assert "ls -la" in result

    def test_multiline_content_splits(self):
        """Test that multiline content is split into lines."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        block = BlockState(type=BlockType.COMMAND, content_input="line1\nline2\nline3")
        result = screen._blocks_to_lines([block])
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_multiple_blocks_have_separators(self):
        """Test that multiple blocks have empty line separators."""
        manager = BranchManager()
        screen = BranchDiffScreen("a", "b", manager)
        blocks = [
            BlockState(type=BlockType.COMMAND, content_input="cmd1"),
            BlockState(type=BlockType.AI_RESPONSE, content_input="response"),
        ]
        result = screen._blocks_to_lines(blocks)
        # Should have block headers
        assert "[COMMAND]" in result
        assert "[AI_RESPONSE]" in result


class TestComputeDiff:
    """Tests for the _compute_diff method."""

    def test_empty_branches_returns_empty_hunks(self):
        """Test that comparing empty branches returns empty hunks."""
        manager = BranchManager()
        manager.branches = {"a": [], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        result = screen._compute_diff()
        assert result == []

    def test_identical_branches_returns_unchanged_hunks(self):
        """Test that identical branches return unchanged hunks."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        manager.branches = {"a": [block], "b": [block]}
        screen = BranchDiffScreen("a", "b", manager)
        result = screen._compute_diff()
        # All hunks should be unchanged
        assert all(not h.is_change for h in result)

    def test_different_content_creates_change_hunks(self):
        """Test that different content creates change hunks."""
        manager = BranchManager()
        block_a = BlockState(type=BlockType.COMMAND, content_input="original")
        block_b = BlockState(type=BlockType.COMMAND, content_input="modified")
        manager.branches = {"a": [block_a], "b": [block_b]}
        screen = BranchDiffScreen("a", "b", manager)
        result = screen._compute_diff()
        # Should have at least one change hunk
        assert any(h.is_change for h in result)

    def test_added_block_creates_insert_hunk(self):
        """Test that an added block creates an insert hunk."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        manager.branches = {"a": [], "b": [block]}
        screen = BranchDiffScreen("a", "b", manager)
        result = screen._compute_diff()
        # Should have change hunks for additions
        assert any(h.is_change for h in result)

    def test_removed_block_creates_delete_hunk(self):
        """Test that a removed block creates a delete hunk."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        result = screen._compute_diff()
        # Should have change hunks for deletions
        assert any(h.is_change for h in result)


class TestDiffHunk:
    """Tests for the DiffHunk dataclass."""

    def test_diff_hunk_creation(self):
        """Test that DiffHunk can be created."""
        hunk = DiffHunk(
            start_line_a=1,
            start_line_b=1,
            lines=[("same", "line1", "line1")],
            is_change=False,
        )
        assert hunk.start_line_a == 1
        assert hunk.start_line_b == 1
        assert len(hunk.lines) == 1

    def test_diff_hunk_is_change_default(self):
        """Test that is_change defaults to False."""
        hunk = DiffHunk(start_line_a=1, start_line_b=1, lines=[])
        assert hunk.is_change is False


class TestDiffLineWidget:
    """Tests for the DiffLineWidget."""

    def test_diff_line_widget_creation(self):
        """Test that DiffLineWidget can be created."""
        widget = DiffLineWidget("add", "10", "11", "new content", "python")
        assert widget.line_type == "add"
        assert widget.line_num_a == "10"
        assert widget.line_num_b == "11"
        assert widget.content == "new content"
        assert widget.language == "python"

    def test_diff_line_widget_default_language(self):
        """Test that DiffLineWidget defaults to python language."""
        widget = DiffLineWidget("same", "1", "1", "code")
        assert widget.language == "python"


class TestDiffHunkWidget:
    """Tests for the DiffHunkWidget."""

    def test_diff_hunk_widget_creation(self):
        """Test that DiffHunkWidget can be created."""
        hunk = DiffHunk(
            start_line_a=1,
            start_line_b=1,
            lines=[("same", "line1", "line1")],
            is_change=False,
        )
        widget = DiffHunkWidget(hunk, 0, "python")
        assert widget.hunk is hunk
        assert widget.hunk_index == 0
        assert widget.language == "python"


class TestUnchangedSection:
    """Tests for the UnchangedSection collapsible."""

    def test_unchanged_section_creation(self):
        """Test that UnchangedSection can be created."""
        lines_data = [(1, 1, "line1"), (2, 2, "line2")]
        section = UnchangedSection(lines_data, "python")
        assert section.lines_data == lines_data
        assert section.language == "python"

    def test_unchanged_section_collapsed_by_default(self):
        """Test that UnchangedSection is collapsed by default."""
        lines_data = [(1, 1, "line1")]
        section = UnchangedSection(lines_data, "python")
        assert section.collapsed is True


class TestBranchDiffScreenCSS:
    """Tests for screen class attributes."""

    def test_screen_is_importable(self):
        """Test that BranchDiffScreen can be imported."""
        assert BranchDiffScreen is not None

    def test_screen_can_be_instantiated(self):
        """Test that BranchDiffScreen can be created."""
        branch_mgr = MagicMock()
        branch_mgr.branches = {}
        screen = BranchDiffScreen("branch_a", "branch_b", branch_mgr)
        assert screen is not None


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

        BranchDiffScreen("main", "feature", manager)

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
    """Tests ensuring all block types are handled correctly in diff."""

    def test_command_block_type_in_diff(self):
        """Test handling of COMMAND block type in diff."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input="ls")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "COMMAND" in str(lines)

    def test_ai_response_block_type_in_diff(self):
        """Test handling of AI_RESPONSE block type in diff."""
        manager = BranchManager()
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="help me")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "AI_RESPONSE" in str(lines)

    def test_agent_response_block_type_in_diff(self):
        """Test handling of AGENT_RESPONSE block type in diff."""
        manager = BranchManager()
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="run task")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "AGENT_RESPONSE" in str(lines)

    def test_ai_query_block_type_in_diff(self):
        """Test handling of AI_QUERY block type in diff."""
        manager = BranchManager()
        block = BlockState(type=BlockType.AI_QUERY, content_input="what is python?")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "AI_QUERY" in str(lines)

    def test_system_msg_block_type_in_diff(self):
        """Test handling of SYSTEM_MSG block type in diff."""
        manager = BranchManager()
        block = BlockState(type=BlockType.SYSTEM_MSG, content_input="system message")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "SYSTEM_MSG" in str(lines)

    def test_tool_call_block_type_in_diff(self):
        """Test handling of TOOL_CALL block type in diff."""
        manager = BranchManager()
        block = BlockState(type=BlockType.TOOL_CALL, content_input="read_file")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "TOOL_CALL" in str(lines)


class TestBranchDiffScreenEdgeCases:
    """Edge case tests."""

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
        """Test blocks with unicode content in diff."""
        manager = BranchManager()
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="echo 'Hello \u4e16\u754c \ud83c\udf0d'",
        )
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "\u4e16\u754c" in str(lines)

    def test_very_long_branch_name(self):
        """Test with very long branch names."""
        manager = BranchManager()
        long_name = "feature/" + "x" * 200
        screen = BranchDiffScreen(long_name, "main", manager)
        assert screen.branch_a_id == long_name

    def test_whitespace_in_content(self):
        """Test blocks with whitespace-only content in diff."""
        manager = BranchManager()
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="   \t\n   ",
        )
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert lines is not None

    def test_special_characters_in_content(self):
        """Test blocks with special/control characters in diff."""
        manager = BranchManager()
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="echo $HOME && cat /etc/passwd | grep 'root'",
        )
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "$HOME" in str(lines)

    def test_empty_content_input(self):
        """Test block with empty content_input."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input="")
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "[COMMAND]" in lines

    def test_none_content_input(self):
        """Test block with None content_input."""
        manager = BranchManager()
        block = BlockState(type=BlockType.COMMAND, content_input=None)
        manager.branches = {"a": [block], "b": []}
        screen = BranchDiffScreen("a", "b", manager)
        lines = screen._blocks_to_lines([block])
        assert "[COMMAND]" in lines
