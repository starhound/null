import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from textual.binding import Binding, BindingType
from textual.events import Click
from textual.message import Message
from textual.widgets import Label, TextArea

if TYPE_CHECKING:
    pass

try:
    import pyperclip
except ImportError:
    pyperclip = None


class GhostLabel(Label):
    """Overlay label for ghost text suggestions."""

    DEFAULT_CSS = """
    GhostLabel {
        layer: overlay;
        color: #666666;
        background: transparent;
        display: none;
        width: auto;
        height: 1;
        padding: 0;
    }
    """


class InputController(TextArea):
    """
    Multi-line input widget with history and mode toggling.
    Supports Shift+Enter for newlines, Enter to submit.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "submit", "Submit", priority=True),
        Binding("shift+enter", "newline", "New Line", priority=True),
        Binding("ctrl+shift+c", "copy_selection", "Copy", priority=True),
        Binding("ctrl+u", "clear_to_start", "Clear Line", priority=True),
        Binding("right", "accept_ghost", "Accept Suggestion", priority=False),
    ]

    class Submitted(Message):
        """Sent when user submits input."""

        def __init__(self, value: str):
            self.value = value
            super().__init__()

    class Toggled(Message):
        """Sent when input mode is toggled."""

        def __init__(self, mode: str):
            self.mode = mode
            super().__init__()

    def __init__(self, placeholder: str = "", **kwargs):
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self.cmd_history: list[str] = []
        self.cmd_history_index: int = -1
        self.current_input: str = ""
        self.mode: str = "CLI"
        self.show_line_numbers = False
        self.tab_behavior = "indent"
        self.theme = "vscode_dark"

        self.ghost_label = GhostLabel("")
        self.current_suggestion = ""

        self._apply_cursor_settings()

    def on_mount(self):
        self.mount(self.ghost_label)

    def on_command_suggester_suggestion_ready(self, event):
        """Handle ghost text suggestion."""
        suggestion = event.suggestion
        if (
            suggestion
            and suggestion.startswith(self.text)
            and len(suggestion) > len(self.text)
        ):
            self.current_suggestion = suggestion
            remainder = suggestion[len(self.text) :]
            self.ghost_label.update(remainder)
            self.ghost_label.display = True
            self._update_ghost_position()
        else:
            self.ghost_label.display = False
            self.current_suggestion = ""

    def watch_text(self, new_text: str):
        """Update ghost text when input changes."""
        if self.current_suggestion and self.current_suggestion.startswith(new_text):
            remainder = self.current_suggestion[len(new_text) :]
            self.ghost_label.update(remainder)
            self._update_ghost_position()
        else:
            self.ghost_label.display = False
            self.current_suggestion = ""

    def _update_ghost_position(self):
        try:
            row, col = self.cursor_location
            self.ghost_label.styles.offset = (col + 1, row)
        except Exception:
            pass

    def action_accept_ghost(self):
        """Accept the ghost suggestion."""
        if self.ghost_label.display and self.current_suggestion:
            self.text = self.current_suggestion
            self.move_cursor((len(self.text), 0))
            self.ghost_label.display = False
            return

        cursor_row, cursor_col = self.cursor_location
        if cursor_col < len(self.document.get_line(cursor_row)):
            self.move_cursor_relative(0, 1)

    def _apply_cursor_settings(self) -> None:
        """Apply cursor settings from config."""
        try:
            from config import get_settings

            settings = get_settings()
            self.cursor_blink = settings.terminal.cursor_blink

            cursor_style = settings.terminal.cursor_style
            self.remove_class("cursor-block", "cursor-beam", "cursor-underline")
            self.add_class(f"cursor-{cursor_style}")
        except Exception:
            pass

    @property
    def value(self) -> str:
        """Compatibility property for Input-like API."""
        return self.text

    @value.setter
    def value(self, new_value: str):
        """Compatibility setter for Input-like API."""
        self.text = new_value

    @property
    def is_ai_mode(self) -> bool:
        return self.mode == "AI"

    def action_submit(self):
        """Handle Enter key - submit input or select from suggester."""
        try:
            from widgets.suggester import CommandSuggester

            suggester = cast(CommandSuggester, self.app.query_one("CommandSuggester"))
            if suggester.display and self.text.startswith("/"):
                complete = suggester.get_selected()
                if complete:
                    parts = self.text.split(" ")
                    if len(parts) == 1:
                        self.text = complete
                    else:
                        self.text = parts[0] + " " + complete
                    suggester.display = False
        except Exception:
            pass

        text = self.text.strip()
        if text:
            self.post_message(self.Submitted(text))

    def action_newline(self):
        """Handle Shift+Enter - insert newline."""
        self.insert("\n")

    def action_clear_to_start(self):
        cursor_row, cursor_col = self.cursor_location
        if cursor_col > 0:
            self.delete(start=(cursor_row, 0), end=(cursor_row, cursor_col))

    def add_to_history(self, command: str):
        if command and (not self.cmd_history or self.cmd_history[-1] != command):
            self.cmd_history.append(command)
        self.cmd_history_index = -1

    def action_history_up(self):
        if not self.cmd_history:
            return

        if self.cmd_history_index == -1:
            self.current_input = self.text
            self.cmd_history_index = len(self.cmd_history) - 1
        elif self.cmd_history_index > 0:
            self.cmd_history_index -= 1

        self.text = self.cmd_history[self.cmd_history_index]
        self.move_cursor((len(self.text), 0))

    def action_history_down(self):
        if self.cmd_history_index == -1:
            return

        if self.cmd_history_index < len(self.cmd_history) - 1:
            self.cmd_history_index += 1
            self.text = self.cmd_history[self.cmd_history_index]
        else:
            self.cmd_history_index = -1
            self.text = self.current_input

        self.move_cursor((len(self.text), 0))

    def toggle_mode(self):
        if self.mode == "CLI":
            self.mode = "AI"
            self.add_class("ai-mode")
            self.placeholder = "Ask AI..."
        else:
            self.mode = "CLI"
            self.remove_class("ai-mode")
            self.placeholder = "Type a command..."
        self.post_message(self.Toggled(self.mode))

    def _get_current_word(self) -> str:
        """Get the word at the current cursor position."""
        text = self.text
        words = text.split()
        if not words:
            return ""
        return words[-1]

    def _is_path_context(self) -> bool:
        """Check if current word looks like a path."""
        last_word = self._get_current_word()
        if not last_word:
            return False
        return bool(re.match(r"^[~./]|^\.\./", last_word))

    def _get_path_completions(self, partial: str) -> list[str]:
        """Get filesystem completions for partial path."""
        try:
            if partial.startswith("~"):
                base = Path.home()
                if len(partial) > 1 and partial[1] == "/":
                    partial = partial[2:]
                else:
                    partial = partial[1:]
                full_path = base / partial if partial else base
            elif partial.startswith("/"):
                base = Path("/")
                partial = partial[1:]
                full_path = base / partial if partial else base
            else:
                base = Path.cwd()
                full_path = base / partial if partial else base

            if full_path.exists() and full_path.is_dir():
                parent = full_path
                pattern = "*"
            else:
                parent = full_path.parent
                pattern = full_path.name + "*"

            if not parent.exists():
                return []

            matches = []
            for p in parent.glob(pattern):
                try:
                    if partial.startswith("~"):
                        rel = "~/" + str(p.relative_to(Path.home()))
                    elif partial.startswith("/"):
                        rel = str(p)
                    else:
                        rel = str(p.relative_to(Path.cwd()))
                except ValueError:
                    rel = str(p)

                if p.is_dir():
                    rel += "/"
                matches.append(rel)

            return sorted(matches)[:10]
        except Exception:
            return []

    def _complete_path(self, completions: list[str]):
        """Complete the current path with the given completion."""
        if not completions:
            return

        text = self.text
        words = text.split()

        if len(words) == 0:
            return

        if len(completions) == 1:
            words[-1] = completions[0]
            self.text = " ".join(words)
            self.move_cursor((len(self.text), 0))
        else:
            common = completions[0]
            for c in completions[1:]:
                while not c.startswith(common) and common:
                    common = common[:-1]
            if common and len(common) > len(words[-1]):
                words[-1] = common
                self.text = " ".join(words)
                self.move_cursor((len(self.text), 0))

    def _on_cursor_first_line(self) -> bool:
        """Check if cursor is on first line."""
        row, _ = self.cursor_location
        return row == 0

    def _on_cursor_last_line(self) -> bool:
        """Check if cursor is on last line."""
        row, _ = self.cursor_location
        return row >= self.document.line_count - 1

    async def on_key(self, event):
        from widgets.suggester import CommandSuggester

        if event.key == "up":
            if self.text.startswith("/"):
                suggester = cast(
                    CommandSuggester, self.app.query_one("CommandSuggester")
                )
                if suggester.display:
                    suggester.select_prev()
                    event.stop()
                    return
            if self._on_cursor_first_line():
                self.action_history_up()
                event.stop()

        elif event.key == "down":
            if self.text.startswith("/"):
                suggester = cast(
                    CommandSuggester, self.app.query_one("CommandSuggester")
                )
                if suggester.display:
                    suggester.select_next()
                    event.stop()
                    return
            if self._on_cursor_last_line():
                self.action_history_down()
                event.stop()

        elif event.key == "tab":
            if self.text.startswith("/"):
                suggester = cast(
                    CommandSuggester, self.app.query_one("CommandSuggester")
                )
                if suggester.display:
                    complete = suggester.get_selected()
                    if complete:
                        parts = self.text.split(" ")
                        if len(parts) == 1:
                            self.text = complete + " "
                        else:
                            self.text = " ".join(parts[:-1]) + " " + complete
                        suggester.display = False
                        self.move_cursor((len(self.text), 0))
                        event.stop()
                        return
            elif not self.is_ai_mode and self._is_path_context():
                partial = self._get_current_word()
                completions = self._get_path_completions(partial)
                if completions:
                    self._complete_path(completions)
                    event.stop()
                    return

        elif event.key == "escape":
            suggester = cast(CommandSuggester, self.app.query_one("CommandSuggester"))
            if suggester.display:
                suggester.display = False
                event.stop()

    async def on_click(self, event: Click) -> None:
        """Handle mouse clicks - right-click to paste."""
        if event.button == 3:
            event.stop()
            await self._paste_from_clipboard()
            return

    async def _paste_from_clipboard(self) -> None:
        """Paste content from clipboard at cursor position."""
        try:
            if pyperclip:
                content = pyperclip.paste()
                if content:
                    self.insert(content)
            else:
                import asyncio

                try:
                    process = await asyncio.create_subprocess_exec(
                        "xclip",
                        "-selection",
                        "clipboard",
                        "-o",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await process.communicate()
                    if process.returncode == 0 and stdout:
                        self.insert(stdout.decode("utf-8", errors="replace"))
                except FileNotFoundError:
                    self.notify(
                        "Install pyperclip for clipboard support", severity="warning"
                    )
        except Exception:
            pass

    def action_copy_selection(self) -> None:
        """Copy selected text to clipboard (Ctrl+Shift+C)."""
        selected = self.selected_text
        if selected:
            self.app.run_worker(self._copy_to_clipboard(selected))

    async def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        try:
            self.app.copy_to_clipboard(text)
        except Exception:
            pass

        try:
            if pyperclip:
                pyperclip.copy(text)
            else:
                import asyncio

                try:
                    process = await asyncio.create_subprocess_exec(
                        "xclip",
                        "-selection",
                        "clipboard",
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await process.communicate(text.encode("utf-8"))
                except FileNotFoundError:
                    pass
        except Exception:
            pass

    async def on_text_area_selection_changed(
        self, event: TextArea.SelectionChanged
    ) -> None:
        """Auto-copy text when selection is made (copy-on-highlight)."""
        if event.selection.start != event.selection.end:
            selected = self.selected_text
            if selected:
                await self._copy_to_clipboard(selected)
