from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.events import Click
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Label, ListItem, ListView, Static

from config import Config

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

    class SuggestionReady(Message):
        def __init__(self, suggestion: str):
            self.suggestion = suggestion
            super().__init__()

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
        try:
            handler = getattr(self.app, "command_handler", None)
            if handler:
                data = {}
                for cmd in handler.get_all_commands():
                    args = []
                    for sub in cmd.subcommands:
                        if sub and sub[0]:
                            parts = sub[0].split()
                            if parts:
                                args.append(parts[0])
                    data[f"/{cmd.name}"] = {"desc": cmd.description, "args": args}
                return data
        except Exception:
            pass
        return {}

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
        try:
            engine = getattr(self.app, "suggestion_engine", None)
            if not engine:
                return

            ai_provider = getattr(self.app, "ai_provider", None)
            suggestions = await engine.suggest(text, ai_provider, max_suggestions=3)

            if suggestions:
                best = suggestions[0]
                if best.command and best.command != text:
                    self._show_ai_suggestions(suggestions)
                    return

        except Exception:
            pass

    def _show_ai_suggestions(self, suggestions):
        lv = self.query_one(ListView)
        lv.clear()

        if not suggestions:
            self.display = False
            return

        self.display = True
        self._selected_index = 0

        for s in suggestions:
            source_icon = {"history": "📜", "context": "📁", "ai": "🤖"}.get(
                s.source, ""
            )
            label = f"{source_icon} {s.command}"
            lv.append(CommandItem(label, s.command, is_ai=(s.source == "ai")))

        self._update_highlight()

        if suggestions:
            self.post_message(self.SuggestionReady(suggestions[0].command))

    def _show_ai_suggestion(self, suggestion: str):
        """Display the AI suggestion."""
        lv = self.query_one(ListView)
        lv.clear()

        lv.append(CommandItem(f"✨ {suggestion}", suggestion, is_ai=True))

        self.display = True
        self._selected_index = 0
        self._update_highlight()

        self.post_message(self.SuggestionReady(suggestion))

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
