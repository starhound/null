from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp


class AICore:
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_ai(self, args: list[str]):
        """Toggle AI mode."""
        self.app.action_toggle_ai_mode()

    async def cmd_chat(self, args: list[str]):
        """Alias for toggling AI mode."""
        self.app.action_toggle_ai_mode()
