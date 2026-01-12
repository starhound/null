from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class AIOrchestrator(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_orchestrate(self, args: list[str]):
        """Multi-agent orchestration. Usage: /orchestrate <goal> | /orchestrate status | /orchestrate stop"""
        from managers.orchestrator import AgentOrchestrator

        if not args:
            self.notify(
                "Usage: /orchestrate <goal> | /orchestrate status | /orchestrate stop",
                severity="error",
            )
            return

        subcommand = args[0].lower()

        if subcommand == "status":
            orch = getattr(self.app, "_orchestrator", None)
            if orch is None:
                self.notify("No active orchestration session")
                return

            if orch.is_running:
                self.notify("Orchestration in progress...")
            else:
                self.notify("Orchestration idle")
            return

        if subcommand == "stop":
            orch = getattr(self.app, "_orchestrator", None)
            if orch is None:
                self.notify("No active orchestration session")
                return

            orch.stop()
            self.notify("Orchestration stopped")
            return

        goal = " ".join(args)

        if not self.app.ai_provider:
            self.notify("No AI provider configured", severity="error")
            return

        orchestrator = AgentOrchestrator()
        object.__setattr__(self.app, "_orchestrator", orchestrator)

        self.notify(f"Starting orchestration for: {goal}")

        try:
            result = await orchestrator.execute(goal, self.app.ai_provider)

            output = "Orchestration Complete\n"
            output += f"Success: {result.success}\n"
            output += f"Duration: {result.duration:.2f}s\n"
            output += f"Subtasks: {len(result.subtasks)}\n\n"

            for subtask in result.subtasks:
                output += f"[{subtask.assigned_agent.value}] {subtask.id}: {subtask.description}\n"
                output += f"  Status: {subtask.status}\n"
                if subtask.result:
                    output += f"  Result: {subtask.result[:200]}...\n"
                output += "\n"

            output += f"Final Result:\n{result.final_result}\n"

            await self.show_output("/orchestrate", output)

        except Exception as e:
            self.notify(f"Orchestration error: {e}", severity="error")
