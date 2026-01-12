from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class AIPlan(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_plan(self, args: list[str]):
        """Planning mode. Usage: /plan <goal> | /plan status | /plan approve [step_id|all] | /plan skip <step_id> | /plan cancel | /plan execute"""
        from managers.planning import PlanManager

        pm: PlanManager = getattr(self.app, "_plan_manager", None) or PlanManager()
        if not hasattr(self.app, "_plan_manager"):
            object.__setattr__(self.app, "_plan_manager", pm)

        if not args:
            if pm.active_plan:
                await self._plan_status(pm)
            else:
                self.notify(
                    "Usage: /plan <goal> - Create a plan for a task",
                    severity="warning",
                )
            return

        subcommand = args[0].lower()

        if subcommand == "status":
            await self._plan_status(pm)
        elif subcommand == "approve":
            await self._plan_approve(pm, args[1:])
        elif subcommand == "skip":
            if len(args) > 1:
                await self._plan_skip(pm, args[1])
            else:
                self.notify("Usage: /plan skip <step_id>", severity="warning")
        elif subcommand == "cancel":
            await self._plan_cancel(pm)
        elif subcommand == "execute":
            await self._plan_execute(pm)
        elif subcommand == "list":
            await self._plan_list(pm)
        else:
            goal = " ".join(args)
            await self._plan_create(pm, goal)

    async def _plan_create(self, pm, goal: str):
        if not self.app.ai_provider:
            self.notify("No AI provider configured", severity="error")
            return

        self.notify(f"Generating plan for: {goal}")

        context = ""
        if self.app.blocks:
            context_parts = []
            for block in self.app.blocks[-5:]:
                if block.content_output:
                    context_parts.append(block.content_output[:500])
            context = "\n".join(context_parts)

        plan = await pm.generate_plan(goal, self.app.ai_provider, context)

        from widgets.blocks.plan_block import PlanBlockWidget
        from widgets.history import HistoryViewport

        plan_widget = PlanBlockWidget(plan)
        history_vp = self.app.query_one("#history", HistoryViewport)
        await history_vp.mount(plan_widget)
        plan_widget.scroll_visible()

        object.__setattr__(self.app, "_active_plan_widget", plan_widget)

    def _update_plan_widget(self, plan):
        widget = getattr(self.app, "_active_plan_widget", None)
        if widget:
            widget.update_plan(plan)

    async def _plan_status(self, pm):
        plan = pm.active_plan
        if not plan:
            self.notify("No active plan. Use /plan <goal> to create one.")
            return

        self._update_plan_widget(plan)
        self.notify(f"Plan '{plan.goal}': {plan.progress * 100:.0f}% complete")

    async def _plan_approve(self, pm, args: list[str]):
        plan = pm.active_plan
        if not plan:
            self.notify("No active plan", severity="warning")
            return

        if not args or args[0].lower() == "all":
            count = pm.approve_all(plan.id)
            self.notify(f"Approved {count} steps")
        else:
            step_id = args[0]
            if pm.approve_step(plan.id, step_id):
                self.notify(f"Approved step {step_id}")
            else:
                self.notify(f"Could not approve step {step_id}", severity="error")

        self._update_plan_widget(plan)

    async def _plan_skip(self, pm, step_id: str):
        plan = pm.active_plan
        if not plan:
            self.notify("No active plan", severity="warning")
            return

        if pm.skip_step(plan.id, step_id):
            self.notify(f"Skipped step {step_id}")
            self._update_plan_widget(plan)
        else:
            self.notify(f"Could not skip step {step_id}", severity="error")

    async def _plan_cancel(self, pm):
        plan = pm.active_plan
        if not plan:
            self.notify("No active plan", severity="warning")
            return

        if pm.cancel_plan(plan.id):
            self.notify("Plan cancelled")
            widget = getattr(self.app, "_active_plan_widget", None)
            if widget:
                widget.remove()
                object.__setattr__(self.app, "_active_plan_widget", None)
        else:
            self.notify("Could not cancel plan", severity="error")

    async def _plan_execute(self, pm):
        import time

        from managers.planning import StepType

        plan = pm.active_plan
        if not plan:
            self.notify("No active plan", severity="warning")
            return

        next_step = plan.get_next_step()
        if not next_step:
            self.notify("No approved steps to execute. Use /plan approve first.")
            return

        pm.start_execution(plan.id)
        self.notify(f"Executing step {next_step.order}: {next_step.description}")

        start_time = time.time()

        try:
            if next_step.step_type == StepType.TOOL and next_step.tool_name:
                from tools.builtin import get_builtin_tool

                tool = get_builtin_tool(next_step.tool_name)
                if tool:
                    result = await tool.handler(**(next_step.tool_args or {}))
                    pm.complete_step(
                        plan.id,
                        next_step.id,
                        result=str(result),
                        duration=time.time() - start_time,
                    )
                    self.notify(f"Step {next_step.order} completed")
                else:
                    pm.complete_step(
                        plan.id,
                        next_step.id,
                        error=f"Tool not found: {next_step.tool_name}",
                        duration=time.time() - start_time,
                    )
                    self.notify(
                        f"Tool not found: {next_step.tool_name}", severity="error"
                    )
            elif next_step.step_type == StepType.CHECKPOINT:
                pm.complete_step(
                    plan.id,
                    next_step.id,
                    result="Checkpoint reached",
                    duration=time.time() - start_time,
                )
                self.notify("Checkpoint reached. Review before continuing.")
            else:
                if self.app.ai_provider:
                    response = ""
                    gen = self.app.ai_provider.generate(  # type: ignore[union-attr]
                        next_step.description,
                        [],
                    )
                    async for chunk in gen:
                        response += chunk
                    pm.complete_step(
                        plan.id,
                        next_step.id,
                        result=response[:500],
                        duration=time.time() - start_time,
                    )
                    await self.show_output(f"Step {next_step.order}", response)
                else:
                    pm.complete_step(
                        plan.id,
                        next_step.id,
                        error="No AI provider",
                        duration=time.time() - start_time,
                    )

            if plan.get_next_step():
                self.notify("Use /plan execute to continue to next step")
            elif plan.is_complete:
                self.notify("Plan completed!")

        except Exception as e:
            pm.complete_step(
                plan.id,
                next_step.id,
                error=str(e),
                duration=time.time() - start_time,
            )
            self.notify(f"Step failed: {e}", severity="error")

    async def _plan_list(self, pm):
        if not pm.plans:
            self.notify("No plans created yet")
            return

        lines = ["Plans:", ""]
        for plan_id, plan in pm.plans.items():
            active = " (active)" if plan_id == pm.active_plan_id else ""
            lines.append(f"  {plan_id}{active}: {plan.goal[:50]} [{plan.status.value}]")

        await self.show_output("/plan list", "\n".join(lines))
