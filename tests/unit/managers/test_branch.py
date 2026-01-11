"""Unit tests for BranchManager."""

import pytest

from managers.branch import BranchManager
from models import BlockState, BlockType


@pytest.fixture
def branch_manager():
    """Create a fresh BranchManager instance."""
    return BranchManager()


@pytest.fixture
def sample_blocks():
    """Create a list of sample BlockState objects."""
    return [
        BlockState(id="block-1", type=BlockType.COMMAND, content_input="ls"),
        BlockState(id="block-2", type=BlockType.AI_RESPONSE, content_input="explain"),
        BlockState(id="block-3", type=BlockType.COMMAND, content_input="pwd"),
        BlockState(id="block-4", type=BlockType.AI_RESPONSE, content_input="help"),
    ]


class TestBranchManagerInit:
    """Tests for BranchManager initialization."""

    def test_default_state(self, branch_manager):
        """Test default initialization state."""
        assert branch_manager.branches == {}
        assert branch_manager.current_branch == "main"

    def test_branches_is_empty_dict(self, branch_manager):
        """Test that branches starts as an empty dictionary."""
        assert isinstance(branch_manager.branches, dict)
        assert len(branch_manager.branches) == 0

    def test_current_branch_is_main(self, branch_manager):
        """Test that current_branch defaults to 'main'."""
        assert branch_manager.current_branch == "main"


class TestFork:
    """Tests for BranchManager.fork() method."""

    def test_fork_at_first_block(self, branch_manager, sample_blocks):
        """Test forking at the first block."""
        result = branch_manager.fork("feature-1", sample_blocks, "block-1")

        assert result == "feature-1"
        assert branch_manager.current_branch == "feature-1"
        assert "feature-1" in branch_manager.branches
        assert len(branch_manager.branches["feature-1"]) == 1
        assert branch_manager.branches["feature-1"][0].id == "block-1"

    def test_fork_at_middle_block(self, branch_manager, sample_blocks):
        """Test forking at a middle block."""
        result = branch_manager.fork("feature-2", sample_blocks, "block-2")

        assert result == "feature-2"
        assert len(branch_manager.branches["feature-2"]) == 2
        assert branch_manager.branches["feature-2"][0].id == "block-1"
        assert branch_manager.branches["feature-2"][1].id == "block-2"

    def test_fork_at_last_block(self, branch_manager, sample_blocks):
        """Test forking at the last block."""
        result = branch_manager.fork("feature-3", sample_blocks, "block-4")

        assert result == "feature-3"
        assert len(branch_manager.branches["feature-3"]) == 4
        # All blocks should be included
        block_ids = [b.id for b in branch_manager.branches["feature-3"]]
        assert block_ids == ["block-1", "block-2", "block-3", "block-4"]

    def test_fork_updates_current_branch(self, branch_manager, sample_blocks):
        """Test that fork updates current_branch."""
        assert branch_manager.current_branch == "main"

        branch_manager.fork("new-branch", sample_blocks, "block-2")

        assert branch_manager.current_branch == "new-branch"

    def test_fork_returns_branch_name(self, branch_manager, sample_blocks):
        """Test that fork returns the new branch name."""
        result = branch_manager.fork("my-branch", sample_blocks, "block-1")

        assert result == "my-branch"

    def test_fork_invalid_fork_point_raises(self, branch_manager, sample_blocks):
        """Test that forking with invalid fork_point_id raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            branch_manager.fork("bad-branch", sample_blocks, "nonexistent-block")

        assert "Fork point nonexistent-block not found" in str(exc_info.value)

    def test_fork_empty_blocks_raises(self, branch_manager):
        """Test that forking with empty blocks raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            branch_manager.fork("empty-branch", [], "any-block")

        assert "Fork point any-block not found" in str(exc_info.value)

    def test_multiple_forks(self, branch_manager, sample_blocks):
        """Test creating multiple forks."""
        branch_manager.fork("branch-a", sample_blocks, "block-1")
        branch_manager.fork("branch-b", sample_blocks, "block-3")

        assert "branch-a" in branch_manager.branches
        assert "branch-b" in branch_manager.branches
        assert len(branch_manager.branches["branch-a"]) == 1
        assert len(branch_manager.branches["branch-b"]) == 3
        # Current branch should be the last forked
        assert branch_manager.current_branch == "branch-b"

    def test_fork_overwrites_existing_branch(self, branch_manager, sample_blocks):
        """Test that forking with same name overwrites existing branch."""
        branch_manager.fork("same-name", sample_blocks, "block-1")
        assert len(branch_manager.branches["same-name"]) == 1

        # Fork again with same name at different point
        branch_manager.fork("same-name", sample_blocks, "block-3")
        assert len(branch_manager.branches["same-name"]) == 3

    def test_fork_preserves_block_data(self, branch_manager, sample_blocks):
        """Test that forked blocks preserve their data."""
        branch_manager.fork("data-branch", sample_blocks, "block-2")

        forked_blocks = branch_manager.branches["data-branch"]
        assert forked_blocks[0].content_input == "ls"
        assert forked_blocks[1].content_input == "explain"
        assert forked_blocks[0].type == BlockType.COMMAND
        assert forked_blocks[1].type == BlockType.AI_RESPONSE


class TestSwitch:
    """Tests for BranchManager.switch() method."""

    def test_switch_to_existing_branch(self, branch_manager, sample_blocks):
        """Test switching to an existing branch."""
        branch_manager.fork("target-branch", sample_blocks, "block-2")
        branch_manager.current_branch = "main"  # Reset current branch

        result = branch_manager.switch("target-branch")

        assert branch_manager.current_branch == "target-branch"
        assert len(result) == 2

    def test_switch_returns_branch_blocks(self, branch_manager, sample_blocks):
        """Test that switch returns the branch's blocks."""
        branch_manager.fork("return-branch", sample_blocks, "block-3")

        result = branch_manager.switch("return-branch")

        assert len(result) == 3
        assert result[0].id == "block-1"
        assert result[1].id == "block-2"
        assert result[2].id == "block-3"

    def test_switch_nonexistent_branch_raises(self, branch_manager):
        """Test that switching to nonexistent branch raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            branch_manager.switch("nonexistent")

        assert "Branch nonexistent not found" in str(exc_info.value)

    def test_switch_updates_current_branch(self, branch_manager, sample_blocks):
        """Test that switch updates current_branch."""
        branch_manager.fork("branch-1", sample_blocks, "block-1")
        branch_manager.fork("branch-2", sample_blocks, "block-2")

        assert branch_manager.current_branch == "branch-2"

        branch_manager.switch("branch-1")
        assert branch_manager.current_branch == "branch-1"

    def test_switch_between_multiple_branches(self, branch_manager, sample_blocks):
        """Test switching between multiple branches."""
        branch_manager.fork("a", sample_blocks, "block-1")
        branch_manager.fork("b", sample_blocks, "block-2")
        branch_manager.fork("c", sample_blocks, "block-3")

        # Switch to each and verify
        result_a = branch_manager.switch("a")
        assert branch_manager.current_branch == "a"
        assert len(result_a) == 1

        result_c = branch_manager.switch("c")
        assert branch_manager.current_branch == "c"
        assert len(result_c) == 3

        result_b = branch_manager.switch("b")
        assert branch_manager.current_branch == "b"
        assert len(result_b) == 2


class TestListBranches:
    """Tests for BranchManager.list_branches() method."""

    def test_list_branches_empty(self, branch_manager):
        """Test list_branches returns empty list when no branches exist."""
        result = branch_manager.list_branches()

        assert result == []

    def test_list_branches_single(self, branch_manager, sample_blocks):
        """Test list_branches with a single branch."""
        branch_manager.fork("only-branch", sample_blocks, "block-1")

        result = branch_manager.list_branches()

        assert result == ["only-branch"]

    def test_list_branches_multiple(self, branch_manager, sample_blocks):
        """Test list_branches with multiple branches."""
        branch_manager.fork("alpha", sample_blocks, "block-1")
        branch_manager.fork("beta", sample_blocks, "block-2")
        branch_manager.fork("gamma", sample_blocks, "block-3")

        result = branch_manager.list_branches()

        assert len(result) == 3
        assert "alpha" in result
        assert "beta" in result
        assert "gamma" in result

    def test_list_branches_returns_list(self, branch_manager, sample_blocks):
        """Test that list_branches returns a list type."""
        branch_manager.fork("test", sample_blocks, "block-1")

        result = branch_manager.list_branches()

        assert isinstance(result, list)

    def test_list_branches_after_fork_and_switch(self, branch_manager, sample_blocks):
        """Test list_branches after forking and switching."""
        branch_manager.fork("first", sample_blocks, "block-1")
        branch_manager.fork("second", sample_blocks, "block-2")
        branch_manager.switch("first")

        result = branch_manager.list_branches()

        # Switching should not affect the list of branches
        assert len(result) == 2
        assert "first" in result
        assert "second" in result


class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_workflow_fork_switch_list(self, branch_manager, sample_blocks):
        """Test a typical workflow: fork, switch, list."""
        # Create initial fork
        branch_manager.fork("experiment", sample_blocks, "block-2")

        # Create another fork
        branch_manager.fork("feature", sample_blocks, "block-3")

        # List branches
        branches = branch_manager.list_branches()
        assert len(branches) == 2

        # Switch back to experiment
        blocks = branch_manager.switch("experiment")
        assert len(blocks) == 2
        assert branch_manager.current_branch == "experiment"

    def test_isolated_branches(self, branch_manager, sample_blocks):
        """Test that branches are isolated from each other."""
        branch_manager.fork("branch-a", sample_blocks, "block-1")
        branch_manager.fork("branch-b", sample_blocks, "block-4")

        # Verify isolation
        assert len(branch_manager.branches["branch-a"]) == 1
        assert len(branch_manager.branches["branch-b"]) == 4

        # Switching should give correct blocks
        a_blocks = branch_manager.switch("branch-a")
        b_blocks = branch_manager.switch("branch-b")

        assert len(a_blocks) == 1
        assert len(b_blocks) == 4

    def test_branch_with_special_characters(self, branch_manager, sample_blocks):
        """Test branch names with special characters."""
        special_names = ["feature/new-ui", "fix-123", "user@branch", "v1.0.0"]

        for name in special_names:
            branch_manager.fork(name, sample_blocks, "block-1")
            assert name in branch_manager.branches

        branches = branch_manager.list_branches()
        for name in special_names:
            assert name in branches
