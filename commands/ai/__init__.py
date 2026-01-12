from typing import TYPE_CHECKING

from .agent import AIAgent
from .bg import AIBackground
from .context import AIContext
from .core import AICore
from .model import AIModel
from .orchestrate import AIOrchestrator
from .plan import AIPlan
from .profile import AIProfile
from .prompts import AIPrompts
from .provider import AIProvider

if TYPE_CHECKING:
    from app import NullApp


class AICommands:
    """Facade for decomposed AI commands."""

    def __init__(self, app: "NullApp"):
        self.core = AICore(app)
        self.provider = AIProvider(app)
        self.model = AIModel(app)
        self.agent = AIAgent(app)
        self.prompts = AIPrompts(app)
        self.context = AIContext(app)
        self.plan = AIPlan(app)
        self.bg = AIBackground(app)
        self.profile = AIProfile(app)
        self.orchestrate = AIOrchestrator(app)

    # Forwarding methods
    async def cmd_ai(self, args):
        await self.core.cmd_ai(args)

    async def cmd_chat(self, args):
        await self.core.cmd_chat(args)

    async def cmd_provider(self, args):
        await self.provider.cmd_provider(args)

    async def cmd_providers(self, args):
        await self.provider.cmd_providers(args)

    async def cmd_model(self, args):
        await self.model.cmd_model(args)

    async def cmd_agent(self, args):
        await self.agent.cmd_agent(args)

    async def cmd_prompts(self, args):
        await self.prompts.cmd_prompts(args)

    async def cmd_orchestrate(self, args):
        await self.orchestrate.cmd_orchestrate(args)

    async def cmd_compact(self, args):
        await self.context.cmd_compact(args)

    async def cmd_context(self, args):
        await self.context.cmd_context(args)

    async def cmd_plan(self, args):
        await self.plan.cmd_plan(args)

    async def cmd_bg(self, args):
        await self.bg.cmd_bg(args)

    async def cmd_profile(self, args):
        await self.profile.cmd_profile(args)
