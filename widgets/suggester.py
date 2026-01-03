from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.events import Click
from textual.timer import Timer
from textual.widgets import Label, ListItem, ListView, Static

from config import Config
from models import BlockType

if TYPE_CHECKING:
    pass


class CommandItem(ListItem):
    """List item for command suggestions."""

    def __init__(self, label_text: str, value: str, is_ai: bool = False):
        super().__init__(Label(label_text))
        self.value = value
        if is_ai:
            self.add_class("ai-suggestion")


class CommandSuggester(Static):
    """Popup for command suggestions."""

    can_focus = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected_index = 0
        self._debounce_timer: Timer | None = None
        self._current_task = None
        self.last_input = ""

    def on_click(self, event: Click) -> None:
        """Handle clicks on suggester items."""
        # Find if we clicked on a CommandItem
        for i, widget in enumerate(self.query(CommandItem)):
            if widget.region.contains(event.x, event.y):
                self._selected_index = i
                self._update_highlight()
                self._apply_selection()
                event.stop()
                return

    def _update_highlight(self):
        """Update visual highlight on selected item."""
        items = list(self.query(CommandItem))
        for i, item in enumerate(items):
            if i == self._selected_index:
                item.add_class("--highlight")
            else:
                item.remove_class("--highlight")

        # Scroll the ListView to keep selected item visible
        if items and 0 <= self._selected_index < len(items):
            try:
                lv = self.query_one(ListView)
                selected_item = items[self._selected_index]
                lv.scroll_to_widget(selected_item)
            except Exception:
                pass

    def _apply_selection(self):
        """Apply the current selection to the input."""
        try:
            from widgets.input import InputController
            input_ctrl = cast(InputController, self.app.query_one("#input"))
            complete = self.get_selected()
            if complete:
                parts = input_ctrl.text.split(" ")
                if len(parts) == 1:
                    input_ctrl.text = complete + " "
                else:
                    input_ctrl.text = parts[0] + " " + complete + " "
                self.display = False
                input_ctrl.move_cursor((len(input_ctrl.text), 0))
        except Exception:
            pass

    @property
    def commands_data(self):
        """Command definitions with dynamic provider list."""
        from ai.factory import AIFactory

        providers = AIFactory.list_providers()

        return {
            "/help": {"desc": "Show help screen", "args": []},
            "/config": {"desc": "Open settings", "args": []},
            "/settings": {"desc": "Open settings", "args": []},
            "/provider": {"desc": "Select AI provider", "args": providers},
            "/providers": {"desc": "Manage all AI providers", "args": []},
            "/model": {"desc": "Select AI model", "args": []},
            "/theme": {
                "desc": "Change UI theme",
                "args": [
                    "null-dark",
                    "null-warm",
                    "null-mono",
                    "null-light",
                    "dracula",
                    "nord",
                    "monokai",
                ],
            },
            "/ai": {"desc": "Toggle AI Mode", "args": []},
            "/chat": {"desc": "Toggle AI Mode", "args": []},
            "/agent": {"desc": "Toggle agent mode", "args": []},
            "/prompts": {
                "desc": "Manage system prompts",
                "args": ["list", "reload", "show", "dir"],
            },
            "/export": {"desc": "Export conversation", "args": ["md", "json"]},
            "/session": {
                "desc": "Manage sessions",
                "args": ["save", "load", "list", "new"],
            },
            "/mcp": {
                "desc": "Manage MCP servers",
                "args": [
                    "list",
                    "tools",
                    "add",
                    "edit",
                    "remove",
                    "enable",
                    "disable",
                    "reconnect",
                ],
            },
            "/tools": {"desc": "Browse available MCP tools", "args": []},
            "/status": {"desc": "Show current status", "args": []},
            "/clear": {"desc": "Clear history", "args": []},
            "/compact": {"desc": "Summarize context", "args": []},
            "/ssh": {"desc": "Connect to SSH host", "args": []},
            "/ssh-add": {"desc": "Add new SSH host", "args": []},
            "/ssh-list": {"desc": "List SSH hosts", "args": []},
            "/ssh-del": {"desc": "Delete SSH host", "args": []},
            "/quit": {"desc": "Exit application", "args": []},
        }

    def compose(self) -> ComposeResult:
        lv = ListView(id="suggestions")
        lv.can_focus = False
        yield lv

    def update_filter(self, text: str):
        self.last_input = text

        # Handle slash commands (synchronous, instant)
        if text.startswith("/"):
            self._update_slash_commands(text)
            return

        # Handle AI Autocomplete
        # SQLite stores "True"/"False" strings sometimes, handle permissive parsing
        enabled_val = Config.get("ai.autocomplete.enabled", "False")
        is_enabled = str(enabled_val).lower() in ("true", "1", "yes", "on")

        if is_enabled:
            self._debounce_ai_fetch(text)
        else:
            self.display = False

    def _update_slash_commands(self, text: str):
        lv = self.query_one(ListView)
        lv.clear()

        parts = text.split(" ")
        base_cmd = parts[0]

        candidates = []

        if len(parts) > 1 and base_cmd in self.commands_data:
            # Args mode
            prefix = " ".join(parts[1:])
            args = self.commands_data[base_cmd]["args"]
            for arg in args:
                if arg.startswith(prefix):
                    candidates.append((arg, ""))
        else:
            # Command mode
            for cmd, data in self.commands_data.items():
                if cmd.startswith(base_cmd):
                    candidates.append((cmd, data["desc"]))

        if not candidates:
            self.display = False
            return

        self.display = True
        self._selected_index = 0

        for text_val, desc in candidates:
            label_str = f"{text_val:<15} {desc}" if desc else text_val
            lv.append(CommandItem(label_str, text_val))

        self._update_highlight()

    def _debounce_ai_fetch(self, text: str):
        """Debounce AI fetch requests."""
        if not text.strip():
            self.display = False
            return

        if self._debounce_timer:
            self._debounce_timer.stop()

        if self._current_task:
            self._current_task.cancel()

        # 600ms debounce
        self._debounce_timer = self.set_timer(
            0.6, lambda: self.run_worker(self._fetch_ai_suggestion(text))
        )

    async def _fetch_ai_suggestion(self, text: str):
        """Fetch suggestion from AI provider."""
        try:
            # Access app attributes with getattr to avoid type errors
            ai_manager = getattr(self.app, "ai_manager", None)
            if not ai_manager:
                return

            provider = ai_manager.get_autocomplete_provider()
            if not provider:
                return

            # Build minimal context from last few blocks
            blocks = getattr(self.app, "blocks", [])
            history_blocks = blocks[-5:]
            context_str = ""
            for b in history_blocks:
                if b.type == BlockType.COMMAND:
                    context_str += f"$ {b.content_input}\n{b.content_output[:200]}\n"
                elif b.type == BlockType.AI_RESPONSE:
                    context_str += f"AI: {b.content_output[:200]}\n"

            prompt = f"""Given the terminal history and current partial input '{text}', suggest the complete single line command the user intends to type.
            History:
            {context_str}

            Current Input: {text}

            Reply ONLY with the suggested command itself, no reasoning.
            """

            # Use generation (we want a single completion)
            # Some providers might not support streaming well for single line,
            # or we just take the first line.
            suggestion = ""
            async for chunk in provider.generate(prompt, []):
                suggestion += chunk

            suggestion = suggestion.strip().strip("`")
            if suggestion.startswith("$ "):
                suggestion = suggestion[2:]

            # If suggestion is valid and different from input
            if suggestion and suggestion != text:
                self._show_ai_suggestion(suggestion)

        except Exception:
            pass

    def _show_ai_suggestion(self, suggestion: str):
        """Display the AI suggestion."""
        # Only show if the input hasn't changed significantly (simple check)
        # Ideally we check self.last_input but debounce handles mostly.

        lv = self.query_one(ListView)
        lv.clear()

        lv.append(CommandItem(f"✨ {suggestion}", suggestion, is_ai=True))

        self.display = True
        self._selected_index = 0
        self._update_highlight()

    def select_next(self):
        """Move selection down."""
        items = list(self.query(CommandItem))
        if items and self._selected_index < len(items) - 1:
            self._selected_index += 1
            self._update_highlight()

    def select_prev(self):
        """Move selection up."""
        if self._selected_index > 0:
            self._selected_index -= 1
            self._update_highlight()

    def get_selected(self) -> str:
        """Get the currently selected command value."""
        items = list(self.query(CommandItem))
        if items and 0 <= self._selected_index < len(items):
            return items[self._selected_index].value
        return ""
