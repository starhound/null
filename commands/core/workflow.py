from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class WorkflowCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_workflow(self, args: list[str]):
        """Workflow management. Usage: /workflow [list|run|save|import|export]"""
        if not args:
            await self._workflow_list()
            return

        subcommand = args[0].lower()
        if subcommand == "list":
            await self._workflow_list()
        elif subcommand == "run" and len(args) > 1:
            await self._workflow_run(args[1])
        elif subcommand == "save":
            name = args[1] if len(args) > 1 else None
            await self._workflow_save(name)
        elif subcommand == "import" and len(args) > 1:
            await self._workflow_import(args[1])
        elif subcommand == "export" and len(args) > 1:
            await self._workflow_export(args[1])
        else:
            self.notify(
                "Usage: /workflow [list|run|save|import|export]", severity="warning"
            )

    async def _workflow_list(self):
        from managers.workflow import WorkflowManager

        wm = WorkflowManager()
        wm.load_workflows()

        lines = ["Available Workflows:", "=" * 20, ""]
        for w in wm.workflows.values():
            lines.append(f"{w.name} ({w.id}) - {w.description}")

        await self.show_output("/workflow list", "\n".join(lines))

    async def _workflow_run(self, name: str):
        from managers.workflow import WorkflowManager

        wm = WorkflowManager()
        wm.load_workflows()

        workflow = wm.get_workflow_by_name(name)
        if not workflow:
            self.notify(f"Workflow not found: {name}", severity="error")
            return

        await self._execute_workflow(workflow)

    async def _execute_workflow(self, workflow):
        # Implementation of workflow execution
        self.notify(f"Running workflow: {workflow.name}")
        # Logic would go here
        pass

    async def _workflow_save(self, name: str | None):
        # Logic to save current session as workflow
        pass

    async def _workflow_import(self, path: str):
        # Logic to import from file
        pass

    async def _workflow_export(self, name: str):
        # Logic to export to file
        pass
