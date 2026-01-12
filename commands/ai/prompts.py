from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class AIPrompts(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_prompts(self, args: list[str]):
        """Select or manage system prompts."""
        if not args:
            from screens.prompts import PromptEditorScreen

            self.app.push_screen(PromptEditorScreen())
            return

        subcommand = args[0]

        if subcommand == "select":
            self.app.action_select_prompt()
        elif subcommand == "list":
            await self._prompts_list()
        elif subcommand == "reload":
            from prompts import get_prompt_manager

            get_prompt_manager().reload()
            self.notify("Prompts reloaded from ~/.null/prompts/")
        elif subcommand == "show" and len(args) >= 2:
            await self._prompts_show(args[1])
        elif subcommand == "dir":
            from prompts import get_prompt_manager

            pm = get_prompt_manager()
            self.notify(f"Prompts directory: {pm.prompts_dir}")
        else:
            self.app.action_select_prompt()

    async def _prompts_list(self):
        """List all available prompts."""
        from prompts import get_prompt_manager

        pm = get_prompt_manager()
        prompts = pm.list_prompts()

        lines = []
        for prompt_key, _name, desc, is_user in prompts:
            source = "[user]" if is_user else "[built-in]"
            lines.append(f"  {prompt_key:15} {source:10} {desc[:40]}")

        await self.show_output("/prompts list", "\n".join(lines))

    async def _prompts_show(self, key: str):
        """Show a prompt's content."""
        from prompts import get_prompt_manager

        pm = get_prompt_manager()
        prompt = pm.get_prompt(key)

        if not prompt:
            self.notify(f"Prompt not found: {key}", severity="error")
            return

        content = prompt.get("content", "")[:500]
        if len(prompt.get("content", "")) > 500:
            content += "\n... (truncated)"

        await self.show_output(f"/prompts show {key}", content)
