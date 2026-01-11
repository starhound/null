"""Prompt Editor Screen."""

from __future__ import annotations

from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TextArea,
)

from prompts import get_prompt_manager
from screens.base import ModalScreen


class PromptListItem(ListItem):
    """List item for a prompt."""

    def __init__(self, key: str, name: str, is_user: bool):
        super().__init__()
        self.key = key
        self.prompt_name = name
        self.is_user = is_user

    def compose(self) -> ComposeResult:
        icon = "👤" if self.is_user else "🔒"
        yield Label(f"{icon} {self.prompt_name} ({self.key})")


class PromptEditorScreen(ModalScreen):
    """Screen for managing system prompts."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("ctrl+s", "save_prompt", "Save"),
        Binding("ctrl+n", "new_prompt", "New"),
        Binding("ctrl+d", "delete_prompt", "Delete"),
    ]

    def __init__(self):
        super().__init__()
        self.pm = get_prompt_manager()
        self.current_key: str | None = None
        self.is_dirty = False

    def compose(self) -> ComposeResult:
        with Container(id="editor-container"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Label("System Prompts", id="sidebar-title")
                yield ListView(id="prompt-list")
                with Horizontal(id="sidebar-buttons"):
                    yield Button("New", id="new-btn", variant="success")

            # Main Content
            with Vertical(id="main-content"):
                yield Label("Name (Key)", classes="field-label")
                yield Input(id="prompt-name-input", placeholder="e.g. python-expert")

                yield Label("Description", classes="field-label")
                yield Input(id="prompt-desc-input", placeholder="Brief description...")

                yield Label("System Prompt", classes="field-label")
                yield TextArea.code_editor(
                    "", language="markdown", id="prompt-content-area"
                )

                with Horizontal(id="footer-buttons"):
                    yield Button(
                        "Delete", id="delete-btn", variant="error", disabled=True
                    )
                    yield Static("", classes="spacer")
                    yield Button("Close", id="close-btn")
                    yield Button("Save", id="save-btn", variant="success")

    def on_mount(self):
        self.load_prompts()

    def load_prompts(self):
        """Load prompts into the list view."""
        lv = self.query_one("#prompt-list", ListView)
        lv.clear()

        prompts = self.pm.list_prompts()
        # Sort: user prompts first, then alphabetical
        prompts.sort(key=lambda x: (not x[3], x[0]))

        for key, name, _, is_user in prompts:
            lv.append(PromptListItem(key, name, is_user))

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle prompt selection."""
        item = cast(PromptListItem, event.item)
        self.load_prompt_details(item.key)

    def load_prompt_details(self, key: str):
        """Load details into the form."""
        self.current_key = key
        data = self.pm.get_prompt(key)
        if not data:
            return

        name_input = self.query_one("#prompt-name-input", Input)
        desc_input = self.query_one("#prompt-desc-input", Input)
        content_area = self.query_one("#prompt-content-area", TextArea)
        delete_btn = self.query_one("#delete-btn", Button)

        name_input.value = key
        desc_input.value = data.get("description", "")
        content_area.text = data.get("content", "")

        # If it's built-in, disable delete and warn on save (or force name change)
        if key in self.pm._user_prompts:
            delete_btn.disabled = False
            name_input.disabled = False  # Can rename (creates new file)
        else:
            delete_btn.disabled = True
            # We allow editing built-ins but it must be saved as a new key
            # Actually, let's keep it simple: if built-in, lock the key input?
            # Or just let them save a copy.
            pass

    def action_new_prompt(self):
        """Clear form for new prompt."""
        self.query_one("#prompt-list", ListView).index = None
        self.current_key = None

        self.query_one("#prompt-name-input", Input).value = ""
        self.query_one("#prompt-desc-input", Input).value = ""
        self.query_one("#prompt-content-area", TextArea).text = ""
        self.query_one("#delete-btn", Button).disabled = True
        self.query_one("#prompt-name-input", Input).focus()

    def action_save_prompt(self):
        """Save the current prompt."""
        key = self.query_one("#prompt-name-input", Input).value.strip()
        desc = self.query_one("#prompt-desc-input", Input).value.strip()
        content = self.query_one("#prompt-content-area", TextArea).text

        if not key:
            self.notify("Prompt name (key) is required", severity="error")
            return

        # Check for key collision with built-ins if it's a new key
        from prompts.templates import BUILTIN_PROMPTS

        if key in BUILTIN_PROMPTS and self.current_key != key:
            self.notify(
                f"Cannot overwrite built-in prompt '{key}'. Choose a different name.",
                severity="error",
            )
            return

        try:
            # If renaming, delete old file (if it was a user prompt)
            if self.current_key and self.current_key != key:
                if self.current_key in self.pm._user_prompts:
                    self.pm.delete_prompt(self.current_key)

            self.pm.save_prompt(key, key, desc, content)
            self.notify(f"Prompt '{key}' saved.")
            self.load_prompts()

            # Reselect the saved item
            # (Finding the item index is a bit manual, skip for now or implement if needed)

        except Exception as e:
            self.notify(f"Error saving prompt: {e}", severity="error")

    def action_delete_prompt(self):
        """Delete current prompt."""
        if not self.current_key:
            return

        if self.pm.delete_prompt(self.current_key):
            self.notify(f"Deleted '{self.current_key}'")
            self.action_new_prompt()
            self.load_prompts()
        else:
            self.notify("Cannot delete built-in prompt", severity="error")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "new-btn":
            self.action_new_prompt()
        elif event.button.id == "save-btn":
            self.action_save_prompt()
        elif event.button.id == "delete-btn":
            self.action_delete_prompt()
        elif event.button.id == "close-btn":
            self.dismiss()
