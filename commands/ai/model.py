from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp


class AIModel:
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_model(self, args: list[str]):
        """Select AI model."""
        if not args:
            self.app.action_select_model()
            return

        # Simplified logic
        self.app.notify(f"Model command not fully ported yet: {' '.join(args)}")
