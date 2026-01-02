"""AI-related commands: model, provider, prompts, chat, compact."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from .base import CommandMixin
from config import Config
from models import BlockState, BlockType
from widgets import BlockWidget, HistoryViewport
from ai.factory import AIFactory


class AICommands(CommandMixin):
    """AI-related commands."""

    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_provider(self, args: list[str]):
        """Switch AI provider. Usage: /provider [provider_name]"""
        if args:
            # Direct provider configuration
            provider_name = args[0].lower()
            valid_providers = AIFactory.list_providers()

            if provider_name not in valid_providers:
                self.notify(f"Unknown provider: {provider_name}", severity="error")
                self.notify(f"Available: {', '.join(valid_providers)}")
                return

            # Go directly to config screen for this provider
            self._open_provider_config(provider_name)
        else:
            # Show provider selection
            self.app.action_select_provider()

    async def cmd_providers(self, args: list[str]):
        """Open providers management screen."""
        from screens import ProvidersScreen, ProviderConfigScreen

        def on_providers_result(result):
            if result is None:
                return

            action, provider_name = result

            if action == "configure":
                # Open config screen for this provider
                self._open_provider_config(provider_name)

            elif action == "activated":
                # Provider was set as active
                self.notify(f"Switched to {provider_name}")
                try:
                    self.app.config = Config.load_all()
                    self.app.ai_manager.get_provider(provider_name)
                    self.app.ai_provider = self.app.ai_manager.get_provider(provider_name)
                    self.app._update_status_bar()
                except Exception as e:
                    self.notify(f"Error initializing provider: {e}", severity="error")

            elif action == "unconfigured":
                # Provider config was removed
                self.notify(f"Removed {provider_name} configuration")
                # Reload config and update status bar
                self.app.config = Config.load_all()
                self.app._update_status_bar()

        self.app.push_screen(ProvidersScreen(), on_providers_result)

    def _open_provider_config(self, provider_name: str):
        """Open the config screen for a specific provider."""
        from screens import ProviderConfigScreen

        sm = Config._get_storage()
        current_conf = {
            "api_key": sm.get_config(f"ai.{provider_name}.api_key", ""),
            "endpoint": sm.get_config(f"ai.{provider_name}.endpoint", ""),
            "region": sm.get_config(f"ai.{provider_name}.region", ""),
            "model": sm.get_config(f"ai.{provider_name}.model", ""),
            "project_id": sm.get_config(f"ai.{provider_name}.project_id", ""),
            "account_id": sm.get_config(f"ai.{provider_name}.account_id", ""),
            "api_version": sm.get_config(f"ai.{provider_name}.api_version", ""),
        }

        def on_config_saved(result):
            if result is not None:
                for k, v in result.items():
                    Config.set(f"ai.{provider_name}.{k}", v)

                Config.set("ai.provider", provider_name)
                self.notify(f"Provider switched to {provider_name}")

                try:
                    self.app.config = Config.load_all()
                    self.app.ai_manager.get_provider(provider_name)
                    self.app.ai_provider = self.app.ai_manager.get_provider(provider_name)
                    self.app._update_status_bar()
                except Exception as e:
                    self.notify(f"Error initializing provider: {e}", severity="error")

        self.app.push_screen(ProviderConfigScreen(provider_name, current_conf), on_config_saved)

    async def cmd_ai(self, args: list[str]):
        """Toggle AI mode."""
        self.app.action_toggle_ai_mode()

    async def cmd_chat(self, args: list[str]):
        """Toggle AI mode (alias)."""
        await self.cmd_ai(args)

    async def cmd_model(self, args: list[str]):
        """Select or set AI model."""
        if not args:
            if not self.app.ai_provider:
                self.notify("AI Provider not initialized.", severity="error")
                return

            self.notify("Fetching models...")
            models = await self.app.ai_provider.list_models()

            def on_model_select(selected_model):
                if selected_model:
                    Config.update_key(["ai", "model"], str(selected_model))
                    self.app.ai_provider.model = str(selected_model)
                    self.notify(f"Model set to {selected_model}")

            from screens import ModelListScreen
            self.app.push_screen(ModelListScreen(models), on_model_select)

        elif len(args) == 2:
            Config.update_key(["ai", "provider"], args[0])
            Config.update_key(["ai", "model"], args[1])
            self.notify(f"AI Model set to {args[0]}/{args[1]}")
            self.app.config = Config.load_all()
            self.app.ai_provider = AIFactory.get_provider(self.app.config["ai"])
        else:
            self.notify("Usage: /model OR /model <provider> <model_name>", severity="error")

    async def cmd_prompts(self, args: list[str]):
        """Select or manage system prompts."""
        if not args:
            self.app.action_select_prompt()
            return

        subcommand = args[0]

        if subcommand == "list":
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
        for key, name, desc, is_user in prompts:
            source = "[user]" if is_user else "[built-in]"
            lines.append(f"  {key:15} {source:10} {desc[:40]}")

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

    async def cmd_agent(self, args: list[str]):
        """Toggle agent mode for autonomous tool execution."""
        current_mode = self.app.config.get("ai", {}).get("agent_mode", False)
        new_mode = not current_mode

        Config.update_key(["ai", "agent_mode"], str(new_mode).lower())
        self.app.config = Config.load_all()

        status = "enabled" if new_mode else "disabled"
        self.notify(f"Agent mode {status}")

        if new_mode:
            # Show helpful info about agent mode
            info = """Agent mode enabled. The AI will now:
- Automatically execute tool calls without confirmation
- Loop until task completion (max 10 iterations)
- Show each tool execution as a separate block
- Continue reasoning after receiving tool results

Use /agent again to disable."""
            await self.show_output("Agent Mode", info)

    async def cmd_compact(self, args: list[str]):
        """Summarize context to reduce token usage."""
        if not self.app.blocks:
            self.notify("Nothing to compact", severity="warning")
            return

        if not self.app.ai_provider:
            self.notify("AI provider not configured", severity="error")
            return

        from context import ContextManager
        context_info = ContextManager.build_messages(self.app.blocks)

        if context_info.estimated_tokens < 500:
            self.notify("Context too small to compact", severity="warning")
            return

        self.notify("Compacting context...")

        summary_prompt = """Summarize this conversation concisely. Include:
- Key topics discussed
- Important decisions or conclusions
- Any code/commands that were significant
- Current state/context needed for continuity

Be brief but preserve essential context. Output only the summary."""

        content_parts = []
        for block in self.app.blocks:
            if block.type == BlockType.AI_QUERY:
                content_parts.append(f"User: {block.content_input}")
            elif block.type == BlockType.AI_RESPONSE:
                content_parts.append(f"Assistant: {block.content_output[:1000]}")
            elif block.type == BlockType.COMMAND:
                content_parts.append(f"Command: {block.content_input}")
                if block.content_output:
                    content_parts.append(f"Output: {block.content_output[:500]}")

        context_text = "\n".join(content_parts)

        try:
            summary = ""
            async for chunk in self.app.ai_provider.generate(
                summary_prompt,
                [{"role": "user", "content": context_text}],
                system_prompt="You are a helpful assistant that creates concise conversation summaries."
            ):
                summary += chunk

            old_token_count = context_info.estimated_tokens
            self.app.blocks = []
            self.app.current_cli_block = None
            self.app.current_cli_widget = None
            history = self.app.query_one("#history", HistoryViewport)
            await history.remove_children()

            summary_block = BlockState(
                type=BlockType.SYSTEM_MSG,
                content_input="Context Summary",
                content_output=summary,
                is_running=False
            )
            self.app.blocks.append(summary_block)

            block_widget = BlockWidget(summary_block)
            await history.mount(block_widget)

            new_token_count = len(summary) // 4
            reduction = ((old_token_count - new_token_count) / old_token_count) * 100

            self.app._update_status_bar()
            self.notify(f"Compacted: ~{old_token_count} → ~{new_token_count} tokens ({reduction:.0f}% reduction)")

        except Exception as e:
            self.notify(f"Compact failed: {e}", severity="error")
