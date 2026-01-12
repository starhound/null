from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp


class AIAgent:
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_agent(self, args: list[str]):
        """Agent mode control."""
        if not args:
            self.app.action_toggle_agent_mode()
            return

        subcmd = args[0]
        if subcmd == "on":
            self.app.agent_mode = True
            self.app.notify("Agent mode enabled")
        elif subcmd == "off":
            self.app.agent_mode = False
            self.app.notify("Agent mode disabled")
        else:
            self.app.notify(f"Unknown agent command: {subcmd}")
