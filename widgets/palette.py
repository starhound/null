"""Command palette widget for quick action access."""

from textual.app import ComposeResult
from textual.widgets import Static, Label, Input
from textual.containers import Vertical
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from dataclasses import dataclass
from typing import Callable, Optional
import re


@dataclass
class PaletteAction:
    """Represents an action in the command palette."""
    name: str
    description: str
    shortcut: str = ""
    category: str = "actions"
    action_id: str = ""

    def matches(self, query: str) -> tuple[bool, int]:
        """Check if action matches query using fuzzy matching.

        Returns (matches, score) where higher score is better match.
        """
        if not query:
            return True, 0

        query_lower = query.lower()
        name_lower = self.name.lower()
        desc_lower = self.description.lower()

        # Exact match in name gets highest score
        if query_lower in name_lower:
            # Boost score if match is at start
            if name_lower.startswith(query_lower):
                return True, 100
            return True, 80

        # Match in description
        if query_lower in desc_lower:
            return True, 60

        # Fuzzy match - all query chars appear in order in name
        query_idx = 0
        for char in name_lower:
            if query_idx < len(query_lower) and char == query_lower[query_idx]:
                query_idx += 1
        if query_idx == len(query_lower):
            return True, 40

        # Fuzzy match on description
        query_idx = 0
        for char in desc_lower:
            if query_idx < len(query_lower) and char == query_lower[query_idx]:
                query_idx += 1
        if query_idx == len(query_lower):
            return True, 20

        return False, 0


class PaletteItem(Static):
    """Single item in the command palette results."""

    def __init__(self, action: PaletteAction, **kwargs):
        super().__init__(**kwargs)
        self.action = action

    def compose(self) -> ComposeResult:
        # Format: name with shortcut on right
        shortcut_display = f"[{self.action.shortcut}]" if self.action.shortcut else ""
        yield Label(self.action.name, classes="palette-item-name")
        yield Label(self.action.description, classes="palette-item-desc")
        yield Label(shortcut_display, classes="palette-item-shortcut")


class CommandPalette(Static, can_focus=True):
    """Command palette overlay for quick action access (Ctrl+P)."""

    BINDINGS = [
        Binding("up", "select_prev", "Previous", show=False),
        Binding("down", "select_next", "Next", show=False),
        Binding("escape", "close", "Close", show=False),
        Binding("enter", "execute", "Execute", show=False),
    ]

    search_query = reactive("")
    filtered_actions = reactive([])
    selected_index = reactive(0)

    class ActionSelected(Message):
        """Sent when user selects an action."""
        def __init__(self, action: PaletteAction):
            self.action = action
            super().__init__()

    class Closed(Message):
        """Sent when palette is closed."""
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._all_actions: list[PaletteAction] = []

    def compose(self) -> ComposeResult:
        yield Label("Command Palette", id="palette-title")
        yield Input(placeholder="Type to search commands...", id="palette-input")
        yield Vertical(id="palette-results")
        yield Label("Up/Down to navigate, Enter to execute, Esc to close", id="palette-hint")

    def _build_actions(self) -> list[PaletteAction]:
        """Build the list of all available actions."""
        actions = []

        # Slash commands
        slash_commands = [
            ("/help", "Show help screen", "F1"),
            ("/config", "Open settings", ""),
            ("/settings", "Open settings", ""),
            ("/provider", "Select AI provider", "F4"),
            ("/model", "Select AI model", "F2"),
            ("/theme", "Change UI theme", "F3"),
            ("/prompts", "Manage system prompts", ""),
            ("/export md", "Export conversation to Markdown", "Ctrl+S"),
            ("/export json", "Export conversation to JSON", ""),
            ("/session save", "Save current session", ""),
            ("/session load", "Load a saved session", ""),
            ("/session list", "List saved sessions", ""),
            ("/session new", "Start new session", ""),
            ("/mcp list", "List MCP servers", ""),
            ("/mcp tools", "Show available MCP tools", ""),
            ("/status", "Show current status", ""),
            ("/clear", "Clear history", "Ctrl+L"),
            ("/compact", "Summarize context", ""),
            ("/quit", "Exit application", "Ctrl+C"),
            ("/ai", "Toggle AI mode", ""),
            ("/chat", "Toggle AI mode", ""),
        ]

        for cmd, desc, shortcut in slash_commands:
            actions.append(PaletteAction(
                name=cmd,
                description=desc,
                shortcut=shortcut,
                category="commands",
                action_id=f"slash:{cmd}"
            ))

        # Key binding actions
        keybindings = [
            ("Toggle AI Mode", "Switch between CLI and AI mode", "Ctrl+Space"),
            ("Clear History", "Clear all blocks from history", "Ctrl+L"),
            ("Quick Export", "Export conversation to Markdown", "Ctrl+S"),
            ("Search History", "Search command history", "Ctrl+R"),
            ("Open Help", "Show help screen", "F1"),
            ("Select Model", "Choose AI model", "F2"),
            ("Change Theme", "Select UI theme", "F3"),
            ("Select Provider", "Choose AI provider", "F4"),
            ("Cancel Operation", "Cancel running operation", "Escape"),
        ]

        for name, desc, shortcut in keybindings:
            action_id = name.lower().replace(" ", "_")
            actions.append(PaletteAction(
                name=name,
                description=desc,
                shortcut=shortcut,
                category="keybindings",
                action_id=f"action:{action_id}"
            ))

        # Recent commands from history
        try:
            from config import Config
            storage = Config._get_storage()
            recent = storage.get_last_history(limit=10)
            for cmd in recent:
                # Skip slash commands - they're already listed
                if not cmd.startswith("/"):
                    actions.append(PaletteAction(
                        name=cmd,
                        description="Recent command",
                        shortcut="",
                        category="history",
                        action_id=f"history:{cmd}"
                    ))
        except Exception:
            pass

        return actions

    def show(self):
        """Show the command palette and focus input."""
        self._all_actions = self._build_actions()
        self.filtered_actions = list(self._all_actions)
        self.search_query = ""
        self.selected_index = 0

        self.add_class("visible")
        self._render_results()

        try:
            input_widget = self.query_one("#palette-input", Input)
            input_widget.value = ""
            input_widget.focus()
        except Exception:
            pass

    def hide(self):
        """Hide the command palette."""
        self.remove_class("visible")
        self.post_message(self.Closed())

    def on_input_changed(self, event: Input.Changed):
        """Update results when search query changes."""
        self.search_query = event.value
        self._filter_actions()

    def on_input_submitted(self, event: Input.Submitted):
        """Execute current selection on Enter."""
        event.stop()
        self._execute_current()

    def action_select_prev(self):
        """Move selection up."""
        if self.filtered_actions and self.selected_index > 0:
            self.selected_index -= 1
            self._render_results()

    def action_select_next(self):
        """Move selection down."""
        if self.filtered_actions and self.selected_index < len(self.filtered_actions) - 1:
            self.selected_index += 1
            self._render_results()

    def action_close(self):
        """Close the palette."""
        self.hide()
        # Return focus to main input
        try:
            self.app.query_one("#input").focus()
        except Exception:
            pass

    def action_execute(self):
        """Execute the current selection."""
        self._execute_current()

    def _filter_actions(self):
        """Filter actions based on search query."""
        query = self.search_query.strip()

        if not query:
            self.filtered_actions = list(self._all_actions)
        else:
            # Score and filter actions
            scored = []
            for action in self._all_actions:
                matches, score = action.matches(query)
                if matches:
                    scored.append((score, action))

            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)
            self.filtered_actions = [action for _, action in scored]

        self.selected_index = 0
        self._render_results()

    def _render_results(self):
        """Render the filtered results list."""
        try:
            container = self.query_one("#palette-results", Vertical)
            container.remove_children()

            if not self.filtered_actions:
                container.mount(Label("No matching commands", classes="palette-no-results"))
                return

            # Show up to 15 results
            visible_actions = self.filtered_actions[:15]

            for i, action in enumerate(visible_actions):
                item = PaletteItem(action, classes="palette-item")
                if i == self.selected_index:
                    item.add_class("selected")
                container.mount(item)

        except Exception:
            pass

    def _execute_current(self):
        """Execute the currently selected action."""
        if not self.filtered_actions:
            self.hide()
            return

        if 0 <= self.selected_index < len(self.filtered_actions):
            action = self.filtered_actions[self.selected_index]
            self.remove_class("visible")
            self.post_message(self.ActionSelected(action))
        else:
            self.hide()
