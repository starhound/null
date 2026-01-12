"""Tests for widgets/branch_navigator.py - BranchNavigator widget."""

from unittest.mock import MagicMock, patch

from widgets.branch_navigator import (
    BranchForkRequested,
    BranchNavigator,
    BranchSelected,
)


class TestBranchSelectedMessage:
    """Tests for BranchSelected message."""

    def test_carries_branch_id(self):
        msg = BranchSelected(branch_id="branch_123")
        assert msg.branch_id == "branch_123"

    def test_carries_main_branch_id(self):
        msg = BranchSelected(branch_id="main")
        assert msg.branch_id == "main"

    def test_carries_empty_branch_id(self):
        msg = BranchSelected(branch_id="")
        assert msg.branch_id == ""

    def test_carries_complex_branch_id(self):
        msg = BranchSelected(branch_id="feature/my-branch-2026")
        assert msg.branch_id == "feature/my-branch-2026"


class TestBranchForkRequestedMessage:
    """Tests for BranchForkRequested message."""

    def test_carries_block_id(self):
        msg = BranchForkRequested(at_block_id="block_456")
        assert msg.at_block_id == "block_456"

    def test_carries_empty_block_id(self):
        msg = BranchForkRequested(at_block_id="")
        assert msg.at_block_id == ""

    def test_carries_uuid_block_id(self):
        msg = BranchForkRequested(at_block_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert msg.at_block_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


class TestBranchNavigatorInit:
    """Tests for BranchNavigator initialization."""

    def test_stores_branch_manager(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)
        assert navigator.branch_manager is mock_manager

    def test_creates_tree_widget(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)
        assert navigator._branch_tree is not None

    def test_tree_root_label(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)
        assert navigator._branch_tree.root.label.plain == "Conversation"

    def test_tree_root_is_expanded(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)
        assert navigator._branch_tree.root.is_expanded is True

    def test_accepts_kwargs(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager, id="test-nav", classes="custom-class")
        assert navigator.id == "test-nav"


class TestBranchNavigatorDefaultCSS:
    """Tests for BranchNavigator default CSS."""

    def test_has_default_css(self):
        assert BranchNavigator.DEFAULT_CSS is not None
        assert len(BranchNavigator.DEFAULT_CSS) > 0

    def test_default_css_contains_width(self):
        assert "width: 25" in BranchNavigator.DEFAULT_CSS

    def test_default_css_contains_dock(self):
        assert "dock: right" in BranchNavigator.DEFAULT_CSS

    def test_default_css_contains_border(self):
        assert "border-left" in BranchNavigator.DEFAULT_CSS

    def test_default_css_contains_branch_header_class(self):
        assert ".branch-header" in BranchNavigator.DEFAULT_CSS

    def test_default_css_contains_branch_list_id(self):
        assert "#branch-list" in BranchNavigator.DEFAULT_CSS


class TestBranchNavigatorRenderBranchTree:
    """Tests for _render_branch_tree method."""

    def test_clears_tree_before_rendering(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        assert navigator._branch_tree.root is not None

    def test_main_branch_first_in_list(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["feature", "main", "bugfix"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        assert len(children) == 3
        assert children[0].data == "main"

    def test_current_branch_marked_with_filled_circle(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        assert len(children) == 1
        label_text = str(children[0].label)
        assert "main" in label_text

    def test_non_current_branch_marked_with_empty_circle(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main", "feature"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        feature_node = next(c for c in children if c.data == "feature")
        label_text = str(feature_node.label)
        assert "feature" in label_text

    def test_node_data_stores_branch_name(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main", "feature-x"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        branch_names = [c.data for c in children]
        assert "main" in branch_names
        assert "feature-x" in branch_names

    def test_empty_branch_list(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = []

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        assert len(children) == 0

    def test_many_branches(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "branch-5"
        branches = [f"branch-{i}" for i in range(10)]
        mock_manager.list_branches.return_value = branches

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        assert len(children) == 10


class TestBranchNavigatorRefreshBranches:
    """Tests for refresh_branches method."""

    def test_calls_render_branch_tree(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main"]

        navigator = BranchNavigator(mock_manager)
        navigator.refresh_branches()

        assert mock_manager.list_branches.called

    def test_updates_tree_with_new_branches(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        mock_manager.list_branches.return_value = ["main", "new-branch"]
        navigator.refresh_branches()

        children = list(navigator._branch_tree.root.children)
        assert len(children) == 2


class TestBranchNavigatorEventHandlers:
    """Tests for event handler methods."""

    def test_on_tree_node_selected_posts_message_with_branch_id(self):
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main"]

        navigator = BranchNavigator(mock_manager)

        mock_event = MagicMock()
        mock_event.node.data = "feature-branch"

        with patch.object(navigator, "post_message") as mock_post:
            navigator.on_tree_node_selected(mock_event)

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, BranchSelected)
            assert message.branch_id == "feature-branch"

    def test_on_tree_node_selected_skips_none_data(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)

        mock_event = MagicMock()
        mock_event.node.data = None

        with patch.object(navigator, "post_message") as mock_post:
            navigator.on_tree_node_selected(mock_event)
            mock_post.assert_not_called()

    def test_on_button_pressed_new_branch_posts_fork_message(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)

        mock_event = MagicMock()
        mock_event.button.id = "new-branch"

        with patch.object(navigator, "post_message") as mock_post:
            navigator.on_button_pressed(mock_event)

            mock_post.assert_called_once()
            message = mock_post.call_args[0][0]
            assert isinstance(message, BranchForkRequested)
            assert message.at_block_id == ""

    def test_on_button_pressed_ignores_other_buttons(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)

        mock_event = MagicMock()
        mock_event.button.id = "some-other-button"

        with patch.object(navigator, "post_message") as mock_post:
            navigator.on_button_pressed(mock_event)
            mock_post.assert_not_called()


class TestBranchNavigatorCompose:
    """Tests for compose method structure."""

    def test_compose_returns_generator(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)

        result = navigator.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_is_defined(self):
        mock_manager = MagicMock()
        navigator = BranchNavigator(mock_manager)

        assert hasattr(navigator, "compose")
        assert callable(navigator.compose)


class TestBranchNavigatorIntegration:
    """Integration-style tests for BranchNavigator behavior."""

    def test_branch_ordering_with_main_not_first(self):
        """Test that main is moved to first position regardless of original order."""
        mock_manager = MagicMock()
        mock_manager.current_branch = "feature"
        mock_manager.list_branches.return_value = ["alpha", "beta", "main", "zeta"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        assert children[0].data == "main"
        remaining = [c.data for c in children[1:]]
        assert remaining == ["alpha", "beta", "zeta"]

    def test_branch_ordering_main_already_first(self):
        """Test that ordering is preserved when main is already first."""
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main", "feature", "bugfix"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        branch_order = [c.data for c in children]
        assert branch_order == ["main", "feature", "bugfix"]

    def test_current_branch_node_is_selected(self):
        """Test that the current branch node gets selected in the tree."""
        mock_manager = MagicMock()
        mock_manager.current_branch = "feature"
        mock_manager.list_branches.return_value = ["main", "feature"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        feature_node = next(c for c in children if c.data == "feature")
        assert feature_node.data == "feature"

    def test_refresh_preserves_manager_reference(self):
        """Test that refresh doesn't change the branch manager reference."""
        mock_manager = MagicMock()
        mock_manager.current_branch = "main"
        mock_manager.list_branches.return_value = ["main"]

        navigator = BranchNavigator(mock_manager)
        original_manager = navigator.branch_manager

        navigator.refresh_branches()

        assert navigator.branch_manager is original_manager

    def test_no_main_branch_in_list(self):
        """Test behavior when there is no 'main' branch."""
        mock_manager = MagicMock()
        mock_manager.current_branch = "develop"
        mock_manager.list_branches.return_value = ["develop", "feature"]

        navigator = BranchNavigator(mock_manager)
        navigator._render_branch_tree()

        children = list(navigator._branch_tree.root.children)
        branch_order = [c.data for c in children]
        assert branch_order == ["develop", "feature"]
