from textual.widgets import Input
from textual.message import Message


class InputController(Input):
    """
    Detached input widget with history and mode toggling.
    """

    class Toggled(Message):
        """Sent when input mode is toggled."""
        def __init__(self, mode: str):
            self.mode = mode
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history: list[str] = []
        self.history_index: int = -1
        self.current_input: str = ""
        self.mode: str = "CLI"  # "CLI" or "AI"

    @property
    def is_ai_mode(self) -> bool:
        return self.mode == "AI"

    def add_to_history(self, command: str):
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
        self.history_index = -1

    def action_history_up(self):
        if not self.history:
            return

        if self.history_index == -1:
            self.current_input = self.value
            self.history_index = len(self.history) - 1
        elif self.history_index > 0:
            self.history_index -= 1

        self.value = self.history[self.history_index]
        self.cursor_position = len(self.value)

    def action_history_down(self):
        if self.history_index == -1:
            return

        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
            self.cursor_position = len(self.value)
        else:
            self.history_index = -1
            self.value = self.current_input
            self.cursor_position = len(self.value)

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

    async def on_key(self, event):
        # Handle navigation keys manually to support both Suggester and History
        if event.key == "up":
            if self.value.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    suggester.select_prev()
                    event.stop()
                    return
            self.action_history_up()
            event.stop()

        elif event.key == "down":
            if self.value.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    suggester.select_next()
                    event.stop()
                    return
            self.action_history_down()
            event.stop()

        elif event.key == "tab" or event.key == "enter":
            if self.value.startswith("/"):
                suggester = self.app.query_one("CommandSuggester")
                if suggester.display:
                    complete = suggester.get_selected()
                    if complete:
                        parts = self.value.split(" ")
                        if len(parts) == 1:
                            self.value = complete + " "
                            event.stop()
                        else:
                            new_val = " ".join(parts[:-1]) + " " + complete
                            self.value = new_val
                            suggester.display = False
                            if event.key == "enter":
                                suggester.display = False
                                event.stop()
                            else:
                                event.stop()

                        self.cursor_position = len(self.value)
                        return

        elif event.key == "escape":
            suggester = self.app.query_one("CommandSuggester")
            if suggester.display:
                suggester.display = False
                event.stop()
