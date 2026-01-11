from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static, Button, Tree
from textual.containers import ScrollableContainer


class BranchSelected(Message):
    def __init__(self, branch_id: str):
        self.branch_id = branch_id
        super().__init__()


class BranchForkRequested(Message):
    def __init__(self, at_block_id: str):
        self.at_block_id = at_block_id
        super().__init__()


class BranchNavigator(Static):
    DEFAULT_CSS = """
    BranchNavigator {
        width: 25;
        dock: right;
        border-left: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    .branch-header {
        text-style: bold;
        margin-bottom: 1;
    }
    
    #branch-list {
        height: 1fr;
    }
    
    Tree {
        background: $surface;
        padding: 0;
    }
    
    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, branch_manager, **kwargs):
        super().__init__(**kwargs)
        self.branch_manager = branch_manager
        self.tree = Tree("Conversation")
        self.tree.root.expand()

    def compose(self) -> ComposeResult:
        yield Static("🔀 Branches", classes="branch-header")

        with ScrollableContainer(id="branch-list"):
            yield self.tree

        yield Button("+ New Branch", id="new-branch")

    def on_mount(self) -> None:
        self._render_branch_tree()

    def _render_branch_tree(self) -> None:
        self.tree.clear()
        self.tree.root.expand()

        current = self.branch_manager.current_branch

        branches = self.branch_manager.list_branches()
        if "main" in branches:
            branches.remove("main")
            branches.insert(0, "main")

        for branch in branches:
            label = branch
            if branch == current:
                label = f"● {branch}"
            else:
                label = f"○ {branch}"

            node = self.tree.root.add(label, data=branch)
            if branch == current:
                self.tree.select_node(node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        branch_id = event.node.data
        if branch_id:
            self.post_message(BranchSelected(branch_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-branch":
            self.post_message(BranchForkRequested(""))

    def refresh_branches(self) -> None:
        self._render_branch_tree()
