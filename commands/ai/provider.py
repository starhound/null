from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp


class AIProvider:
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_provider(self, args: list[str]):
        """Select AI provider."""
        if not args:
            self.app.action_select_provider()
            return

        provider_name = args[0]
        # Logic from original ai.py...
        # Simplified for now as we are decomposing
        await self.app.ai_manager.set_provider(provider_name)
        self.app.notify(f"Provider set to {provider_name}")

    async def cmd_providers(self, args: list[str]):
        """Manage all AI providers."""
        self.app.push_screen("providers")
