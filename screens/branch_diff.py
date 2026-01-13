from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class BranchDiffScreen(ModalScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def action_dismiss(self) -> None:
        self.dismiss()

    def __init__(self, branch_a_id: str, branch_b_id: str, branch_manager):
        super().__init__()
        self.branch_a_id = branch_a_id
        self.branch_b_id = branch_b_id
        self.branch_manager = branch_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="diff-container"):
            with Horizontal():
                with Vertical(classes="column"):
                    yield Label(f"Branch: {self.branch_a_id}", classes="header")
                    with ScrollableContainer():
                        for block in self.branch_manager.branches.get(
                            self.branch_a_id, []
                        ):
                            yield self._create_block_widget(block)

                with Vertical(classes="column"):
                    yield Label(f"Branch: {self.branch_b_id}", classes="header")
                    with ScrollableContainer():
                        for block in self.branch_manager.branches.get(
                            self.branch_b_id, []
                        ):
                            yield self._create_block_widget(block)

            yield Button("Close", variant="primary", id="close")

    def _create_block_widget(self, block) -> Static:
        content = (
            block.content_input[:50] + "..."
            if len(block.content_input) > 50
            else block.content_input
        )
        return Static(f"[{block.type.name}]\n{content}", classes="block-item")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss()
