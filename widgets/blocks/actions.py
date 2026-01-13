from textual.app import ComposeResult
from textual import on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, Static

from .copy_types import CopyType


class CopyMenuItem(Button):
    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    def __init__(
        self,
        label: str,
        copy_type: str,
        shortcut: str = "",
        id: str | None = None,
    ):
        display_label = f"{label} [{shortcut}]" if shortcut else label
        super().__init__(display_label, id=id, classes="copy-menu-item")
        self.copy_type = copy_type


class CopyMenu(Vertical):
    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("1", "select_full", "Full", show=False),
        Binding("2", "select_code", "Code", show=False),
        Binding("3", "select_markdown", "Markdown", show=False),
        Binding("4", "select_raw", "Raw", show=False),
    ]

    class CopySelected(Message, bubble=True):
        def __init__(self, copy_type: str, block_id: str):
            super().__init__()
            self.copy_type = copy_type
            self.block_id = block_id

    class Dismissed(Message, bubble=True):
        pass

    def __init__(self, block_id: str, id: str | None = None):
        super().__init__(id=id, classes="copy-menu")
        self.block_id = block_id

    def compose(self) -> ComposeResult:
        yield Label("Copy Options", classes="copy-menu-title")
        yield CopyMenuItem("Full Content", CopyType.FULL, "1", id="copy-full")
        yield CopyMenuItem("Code Only", CopyType.CODE, "2", id="copy-code")
        yield CopyMenuItem("As Markdown", CopyType.MARKDOWN, "3", id="copy-markdown")
        yield CopyMenuItem("Raw Text", CopyType.RAW, "4", id="copy-raw")

    def on_mount(self) -> None:
        self.focus()

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        if isinstance(button, CopyMenuItem):
            event.stop()
            self.post_message(self.CopySelected(button.copy_type, self.block_id))
            self.remove()

    def action_dismiss(self) -> None:
        self.post_message(self.Dismissed())
        self.remove()

    def action_select_full(self) -> None:
        self._select_type(CopyType.FULL)

    def action_select_code(self) -> None:
        self._select_type(CopyType.CODE)

    def action_select_markdown(self) -> None:
        self._select_type(CopyType.MARKDOWN)

    def action_select_raw(self) -> None:
        self._select_type(CopyType.RAW)

    def _select_type(self, copy_type: str) -> None:
        self.post_message(self.CopySelected(copy_type, self.block_id))
        self.remove()


class ActionButton(Button):
    class ActionPressed(Message, bubble=True):
        def __init__(self, action: str, block_id: str):
            super().__init__()
            self.action = action
            self.block_id = block_id

    def __init__(
        self,
        label: str,
        action: str,
        block_id: str,
        disabled: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(label, id=id, classes=classes, disabled=disabled)
        self.action_name = action
        self.block_id = block_id


class ActionBar(Horizontal):
    def __init__(
        self,
        block_id: str,
        show_fork: bool = True,
        show_edit: bool = True,
        meta_text: str = "",
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.block_id = block_id
        self.show_fork = show_fork
        self.show_edit = show_edit
        self.meta_text = meta_text
        self._copy_menu: CopyMenu | None = None

    def compose(self) -> ComposeResult:
        yield ActionButton("Copy ▾", "copy_menu", self.block_id, id="copy-btn")
        yield ActionButton("Retry", "retry", self.block_id, id="retry-btn")
        if self.show_edit:
            yield ActionButton("Edit", "edit", self.block_id, id="edit-btn")
        if self.show_fork:
            yield ActionButton("Fork", "fork", self.block_id, id="fork-btn")

        yield Static("", classes="action-spacer")

        if self.meta_text:
            yield Label(self.meta_text, classes="action-meta")

    def show_copy_menu(self) -> None:
        if self._copy_menu is not None:
            return
        self._copy_menu = CopyMenu(self.block_id, id="copy-menu-popup")
        self.mount(self._copy_menu)

    def hide_copy_menu(self) -> None:
        if self._copy_menu is not None:
            try:
                self._copy_menu.remove()
            except Exception:
                pass
            self._copy_menu = None

    @on(CopyMenu.Dismissed)
    def on_copy_menu_dismissed(self, event: CopyMenu.Dismissed) -> None:
        event.stop()
        self._copy_menu = None

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Catch Button.Pressed from child ActionButtons and emit ActionPressed."""
        button = event.button
        if isinstance(button, ActionButton):
            event.stop()
            self.post_message(
                ActionButton.ActionPressed(button.action_name, button.block_id)
            )

    def update_meta(self, meta_text: str) -> None:
        """Update the meta text."""
        self.meta_text = meta_text
        try:
            meta_label = self.query_one(".action-meta", Label)
            meta_label.update(meta_text)
        except Exception:
            pass

    def show_copy_feedback(self, label: str = "✓ Copied") -> None:
        try:
            copy_btn = self.query_one("#copy-btn", ActionButton)
            original_label = copy_btn.label
            copy_btn.label = f"✓ {label}"
            copy_btn.add_class("copied")
            self.set_timer(
                1.5, lambda: self._reset_copy_button(copy_btn, original_label)
            )
        except Exception:
            pass

    def _reset_copy_button(self, btn: ActionButton, original_label) -> None:
        try:
            btn.label = original_label
            btn.remove_class("copied")
        except Exception:
            pass
