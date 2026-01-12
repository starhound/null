"""AI-related commands: model, provider, prompts, chat, compact."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ai.factory import AIFactory
from config import Config
from models import BlockState, BlockType

from .base import CommandMixin


class AICommands(CommandMixin):
    """AI-related commands."""

    def __init__(self, app: NullApp):
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
        from screens import ProvidersScreen

        def on_providers_result(result):
            if result is None:
                return

            action, provider_name = result

            if action == "configure":
                # Open config screen for this provider
                self._open_provider_config(provider_name)

            elif action == "activated":
                self.notify(f"Switched to {provider_name}")
                try:
                    self.app.config = Config.load_all()
                    self.app.ai_manager.get_provider(provider_name)
                    self.app.ai_provider = self.app.ai_manager.get_provider(
                        provider_name
                    )
                    self.app._update_status_bar()
                    self.app.action_select_model()
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
                from config import SettingsManager

                SettingsManager().set("ai", "provider", provider_name)
                self.notify(f"Provider switched to {provider_name}")

                try:
                    self.app.config = Config.load_all()
                    self.app.ai_manager.get_provider(provider_name)
                    self.app.ai_provider = self.app.ai_manager.get_provider(
                        provider_name
                    )
                    self.app._update_status_bar()
                    self.app.action_select_model()
                except Exception as e:
                    self.notify(f"Error initializing provider: {e}", severity="error")

        self.app.push_screen(
            ProviderConfigScreen(provider_name, current_conf), on_config_saved
        )

    async def cmd_ai(self, args: list[str]):
        """Toggle AI mode."""
        self.app.action_toggle_ai_mode()

    async def cmd_chat(self, args: list[str]):
        """Toggle AI mode (alias)."""
        await self.cmd_ai(args)

    async def cmd_model(self, args: list[str]):
        """Select or set AI model. Supports: /model, /model embedding, /model autocomplete, /model status."""
        if not args:
            self.app.action_select_model()
            return

        subcommand = args[0].lower()

        if subcommand == "embedding":
            await self._model_embedding(args[1:])
        elif subcommand == "autocomplete":
            await self._model_autocomplete(args[1:])
        elif subcommand == "status":
            await self._model_status()
        elif len(args) == 2:
            await self._set_main_model(args[0], args[1])
        else:
            self.notify(
                "Usage: /model [embedding|autocomplete|status] OR /model <provider> <model>",
                severity="error",
            )

    async def _set_main_model(self, provider: str, model: str):
        valid_providers = AIFactory.list_providers()
        if provider not in valid_providers:
            self.notify(f"Unknown provider: {provider}", severity="error")
            self.notify(f"Available: {', '.join(valid_providers[:5])}...")
            return

        Config.update_key(["ai", "provider"], provider)
        Config.update_key(["ai", "model"], model)
        Config.set(f"ai.{provider}.model", model)
        self.notify(f"Main model set to {provider}/{model}")
        self.app.config = Config.load_all()
        self.app.ai_provider = AIFactory.get_provider(self.app.config["ai"])
        self.app._update_status_bar()

    async def _model_embedding(self, args: list[str]):
        if not args:
            provider = Config.get("ai.embedding_provider")
            if not provider:
                self.notify("No embedding provider configured")
                return
            model = Config.get(f"ai.embedding.{provider}.model", "")
            endpoint = Config.get(f"ai.embedding.{provider}.endpoint", "")
            self.notify(f"Embedding: {provider}/{model or 'default'}")
            if endpoint:
                self.notify(f"Endpoint: {endpoint}")
            return

        if len(args) == 1:
            provider = args[0].lower()
            valid_providers = AIFactory.list_providers()
            if provider not in valid_providers:
                self.notify(f"Unknown provider: {provider}", severity="error")
                return
            Config.set("ai.embedding_provider", provider)
            self.notify(f"Embedding provider set to {provider}")

        elif len(args) >= 2:
            provider = args[0].lower()
            model = args[1]
            valid_providers = AIFactory.list_providers()
            if provider not in valid_providers:
                self.notify(f"Unknown provider: {provider}", severity="error")
                return

            Config.set("ai.embedding_provider", provider)
            Config.set(f"ai.embedding.{provider}.model", model)

            if len(args) >= 3:
                Config.set(f"ai.embedding.{provider}.endpoint", args[2])

            self.notify(f"Embedding model set to {provider}/{model}")

    async def _model_autocomplete(self, args: list[str]):
        if not args:
            enabled = Config.get("ai.autocomplete.enabled", "false")
            provider = Config.get("ai.autocomplete.provider", "")
            model = Config.get("ai.autocomplete.model", "")

            if enabled.lower() == "true" and provider:
                self.notify(f"Autocomplete: {provider}/{model or 'default'} (enabled)")
            elif provider:
                self.notify(f"Autocomplete: {provider}/{model or 'default'} (disabled)")
            else:
                self.notify("Autocomplete: not configured")
            return

        subarg = args[0].lower()

        if subarg in ("on", "enable", "enabled"):
            Config.set("ai.autocomplete.enabled", "true")
            self.notify("Autocomplete enabled")
            return
        elif subarg in ("off", "disable", "disabled"):
            Config.set("ai.autocomplete.enabled", "false")
            self.notify("Autocomplete disabled")
            return

        provider = subarg
        valid_providers = AIFactory.list_providers()
        if provider not in valid_providers:
            self.notify(f"Unknown provider: {provider}", severity="error")
            return

        Config.set("ai.autocomplete.provider", provider)
        Config.set("ai.autocomplete.enabled", "true")

        if len(args) >= 2:
            model = args[1]
            Config.set("ai.autocomplete.model", model)
            self.notify(f"Autocomplete set to {provider}/{model} (enabled)")
        else:
            self.notify(f"Autocomplete provider set to {provider} (enabled)")

    async def _model_status(self):
        lines = ["Model Configuration:", ""]

        provider = Config.get("ai.provider") or "not configured"
        model = Config.get(f"ai.{provider}.model", Config.get("ai.model", ""))
        lines.append(f"  Main LLM:      {provider}/{model or 'default'}")

        emb_provider = Config.get("ai.embedding_provider") or "not configured"
        emb_model = Config.get(f"ai.embedding.{emb_provider}.model", "nomic-embed-text")
        lines.append(f"  Embedding:     {emb_provider}/{emb_model}")

        ac_enabled = Config.get("ai.autocomplete.enabled", "false")
        ac_provider = Config.get("ai.autocomplete.provider", "")
        ac_model = Config.get("ai.autocomplete.model", "")

        if ac_provider:
            status = "enabled" if ac_enabled.lower() == "true" else "disabled"
            lines.append(
                f"  Autocomplete:  {ac_provider}/{ac_model or 'default'} ({status})"
            )
        else:
            lines.append("  Autocomplete:  not configured")

        await self.show_output("/model status", "\n".join(lines))

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

    async def cmd_agent(self, args: list[str]):
        """Agent mode control. Usage: /agent [status|history|stats|stop|pause|resume|clear|save|load|list]"""
        if not args:
            await self._agent_toggle()
            return

        subcommand = args[0].lower()

        if subcommand == "status":
            await self._agent_status()
        elif subcommand == "history":
            limit = int(args[1]) if len(args) > 1 else 10
            await self._agent_history(limit)
        elif subcommand == "stats":
            await self._agent_stats()
        elif subcommand == "stop":
            self._agent_stop()
        elif subcommand == "pause":
            self._agent_pause()
        elif subcommand == "resume":
            self._agent_resume()
        elif subcommand == "clear":
            self._agent_clear()
        elif subcommand == "tools":
            await self._agent_tools()
        elif subcommand in ("on", "enable"):
            await self._agent_set_mode(True)
        elif subcommand in ("off", "disable"):
            await self._agent_set_mode(False)
        elif subcommand == "inspect":
            self._agent_inspect()
        elif subcommand == "config":
            await self._agent_config(args[1:] if len(args) > 1 else [])
        elif subcommand == "save":
            name = args[1] if len(args) > 1 else None
            await self._agent_save(name)
        elif subcommand == "load":
            if len(args) > 1:
                await self._agent_load(args[1])
            else:
                self.notify("Usage: /agent load <name_or_id>", severity="warning")
        elif subcommand == "list":
            await self._agent_list_saved()
        elif subcommand == "export":
            session_id = args[1] if len(args) > 1 else None
            await self._agent_export(session_id)
        elif subcommand == "delete":
            if len(args) > 1:
                self._agent_delete_saved(args[1])
            else:
                self.notify("Usage: /agent delete <name_or_id>", severity="warning")
        else:
            self.notify(
                "Usage: /agent [status|history|stats|stop|pause|resume|clear|tools|inspect|config|save|load|list|export|delete|on|off]",
                severity="warning",
            )

    async def _agent_toggle(self):
        current_mode = self.app.config.get("ai", {}).get("agent_mode", False)
        await self._agent_set_mode(not current_mode)

    async def _agent_set_mode(self, enabled: bool):
        Config.update_key(["ai", "agent_mode"], str(enabled).lower())
        self.app.config = Config.load_all()

        status = "enabled" if enabled else "disabled"
        self.notify(f"Agent mode {status}")

        if enabled:
            info = """Agent mode enabled. The AI will now:
- Automatically execute tool calls without confirmation
- Loop until task completion (max 10 iterations)
- Show each tool execution as a separate block
- Continue reasoning after receiving tool results

Use /agent off or /agent again to disable."""
            await self.show_output("Agent Mode", info)

    async def _agent_status(self):
        manager = self.app.agent_manager
        status = manager.get_status()

        lines = [
            f"Agent Mode: {'enabled' if self.app.config.get('ai', {}).get('agent_mode', False) else 'disabled'}"
        ]
        lines.append(f"State: {status['state']}")

        if status["active"] and status["current_session"]:
            session = status["current_session"]
            lines.extend(
                [
                    f"\nCurrent Session: {session['id']}",
                    f"  Task: {session['task'][:60]}{'...' if len(session['task']) > 60 else ''}",
                    f"  Iterations: {session['iterations']}",
                    f"  Tool calls: {session['tool_calls']}",
                    f"  Duration: {session['duration']:.1f}s",
                ]
            )
            if session["errors"]:
                lines.append(f"  Errors: {session['errors']}")
        else:
            lines.append("\nNo active session")

        lines.append(f"\nHistory: {status['history_count']} sessions")

        await self.show_output("/agent status", "\n".join(lines))

    async def _agent_history(self, limit: int):
        manager = self.app.agent_manager
        sessions = manager.get_history(limit=limit)

        if not sessions:
            await self.show_output("/agent history", "No session history available.")
            return

        lines = [f"Last {len(sessions)} agent sessions:\n"]
        for s in reversed(sessions):
            state = "cancelled" if s.state.value == "cancelled" else "completed"
            lines.append(
                f"{s.id} | {state:10} | {s.iterations:2} iters | {s.tool_calls:2} tools | {s.duration:6.1f}s"
            )
            if s.current_task:
                task_preview = s.current_task[:50] + (
                    "..." if len(s.current_task) > 50 else ""
                )
                lines.append(f"       Task: {task_preview}")
            if s.errors:
                lines.append(f"       Errors: {len(s.errors)}")

        await self.show_output("/agent history", "\n".join(lines))

    async def _agent_stats(self):
        manager = self.app.agent_manager
        stats = manager.stats.to_dict()

        if stats["total_sessions"] == 0:
            await self.show_output("/agent stats", "No agent sessions recorded yet.")
            return

        lines = [
            "Agent Statistics",
            "=" * 30,
            f"Total sessions:       {stats['total_sessions']}",
            f"Total iterations:     {stats['total_iterations']}",
            f"Total tool calls:     {stats['total_tool_calls']}",
            f"Total tokens:         {stats['total_tokens']}",
            f"Total duration:       {stats['total_duration']:.1f}s",
            f"Errors:               {stats['error_count']}",
            "",
            f"Avg iters/session:    {stats['avg_iterations_per_session']:.1f}",
            f"Avg tools/session:    {stats['avg_tools_per_session']:.1f}",
        ]

        if stats["tool_usage"]:
            lines.extend(["", "Tool Usage:"])
            for tool, count in sorted(
                stats["tool_usage"].items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  {tool:20} {count}")

        await self.show_output("/agent stats", "\n".join(lines))

    def _agent_stop(self):
        manager = self.app.agent_manager
        if manager.is_active:
            manager.request_cancel()
            self.notify("Agent session cancelled")
        else:
            self.notify("No active agent session", severity="warning")

    def _agent_pause(self):
        manager = self.app.agent_manager
        if manager.is_active:
            manager.request_pause()
            self.notify("Agent session paused")
        else:
            self.notify("No active agent session", severity="warning")

    def _agent_resume(self):
        manager = self.app.agent_manager
        if manager.should_pause():
            manager.resume()
            self.notify("Agent session resumed")
        else:
            self.notify("Agent is not paused", severity="warning")

    def _agent_clear(self):
        manager = self.app.agent_manager
        manager.clear_history()
        manager.reset_stats()
        self.notify("Agent history and stats cleared")

    def _agent_inspect(self):
        from screens import AgentScreen

        self.app.push_screen(AgentScreen())

    async def _agent_config(self, args: list[str]):
        if not args:
            ai_config = self.app.config.get("ai", {})
            lines = [
                "Agent Configuration:",
                "=" * 30,
                f"max_iterations:    {ai_config.get('agent_max_iterations', 10)}",
                f"approval_mode:     {ai_config.get('agent_approval_mode', 'auto')}",
                f"thinking_visible:  {ai_config.get('agent_thinking_visible', True)}",
                "",
                "Usage: /agent config <key> <value>",
                "  max_iterations   1-50     Maximum tool iterations",
                "  approval_mode    auto|per_tool|per_iteration",
                "  thinking_visible true|false  Show thinking process",
            ]
            await self.show_output("/agent config", "\n".join(lines))
            return

        if len(args) < 2:
            self.notify("Usage: /agent config <key> <value>", severity="warning")
            return

        key, value = args[0], args[1]

        if key == "max_iterations":
            try:
                val = int(value)
                if not 1 <= val <= 50:
                    self.notify("max_iterations must be 1-50", severity="error")
                    return
                Config.set("ai.agent_max_iterations", str(val))
                self.app.config = Config.load_all()
                self.notify(f"max_iterations set to {val}")
            except ValueError:
                self.notify("max_iterations must be a number", severity="error")

        elif key == "approval_mode":
            if value not in ("auto", "per_tool", "per_iteration"):
                self.notify(
                    "approval_mode must be: auto, per_tool, or per_iteration",
                    severity="error",
                )
                return
            Config.set("ai.agent_approval_mode", value)
            self.app.config = Config.load_all()
            self.notify(f"approval_mode set to {value}")

        elif key == "thinking_visible":
            if value.lower() not in ("true", "false"):
                self.notify("thinking_visible must be: true or false", severity="error")
                return
            Config.set("ai.agent_thinking_visible", value.lower())
            self.app.config = Config.load_all()
            self.notify(f"thinking_visible set to {value.lower()}")

        else:
            self.notify(f"Unknown config key: {key}", severity="error")

    async def _agent_tools(self):
        from tools.builtin import BUILTIN_TOOLS

        lines = ["Available Agent Tools:", "=" * 30, ""]

        for tool in BUILTIN_TOOLS:
            approval = "[requires approval]" if tool.requires_approval else ""
            lines.append(f"{tool.name:20} {approval}")
            lines.append(f"  {tool.description[:70]}")
            lines.append("")

        mcp_tools = []
        if self.app.mcp_manager:
            for tool in self.app.mcp_manager.get_all_tools():
                mcp_tools.append((tool.server_name, tool))

        if mcp_tools:
            lines.extend(["MCP Tools:", "=" * 30, ""])
            for server, tool in mcp_tools:
                lines.append(f"{tool.name:20} [{server}]")
                if tool.description:
                    lines.append(f"  {tool.description[:70]}")
                lines.append("")

        await self.show_output("/agent tools", "\n".join(lines))

    async def _agent_save(self, name: str | None):
        manager = self.app.agent_manager
        if manager.current_session:
            path = manager.save_current_session(name)
            if path:
                self.notify(f"Session saved: {path.name}")
            else:
                self.notify("Failed to save session", severity="error")
        elif manager.get_history(1):
            last_session = manager.get_history(1)[0]
            path = manager.save_session(last_session, name)
            self.notify(f"Last session saved: {path.name}")
        else:
            self.notify("No session to save", severity="warning")

    async def _agent_load(self, name_or_id: str):
        manager = self.app.agent_manager
        session = manager.load_session(name_or_id)
        if session:
            lines = [
                f"Loaded Session: {session.id}",
                f"Task: {session.current_task}",
                f"Started: {session.started_at.isoformat()}",
                f"Iterations: {session.iterations}",
                f"Tool Calls: {session.tool_calls}",
                "",
                "Tool History:",
            ]
            for i, call in enumerate(session.tool_history[-5:], 1):
                lines.append(
                    f"  {i}. {call.get('tool', 'Unknown')} - {'OK' if call.get('success') else 'FAIL'}"
                )
            await self.show_output(f"/agent load {name_or_id}", "\n".join(lines))
        else:
            self.notify(f"Session not found: {name_or_id}", severity="error")

    async def _agent_list_saved(self):
        manager = self.app.agent_manager
        sessions = manager.list_saved_sessions()
        if not sessions:
            await self.show_output("/agent list", "No saved sessions.")
            return

        lines = ["Saved Agent Sessions:", "=" * 50, ""]
        for s in sessions:
            lines.append(
                f"{s['id']:10} | {s['started_at'][:16]} | {s['iterations']:2} iters | {s['tool_calls']:2} tools"
            )
            if s.get("task"):
                lines.append(f"           Task: {s['task']}")
        await self.show_output("/agent list", "\n".join(lines))

    async def _agent_export(self, session_id: str | None):
        manager = self.app.agent_manager
        if session_id:
            session = manager.load_session(session_id)
        elif manager.current_session:
            session = manager.current_session
        elif manager.get_history(1):
            session = manager.get_history(1)[0]
        else:
            self.notify("No session to export", severity="warning")
            return

        if session:
            markdown = manager.export_session_to_markdown(session)
            await self.show_output(f"/agent export {session.id}", markdown)
        else:
            self.notify("Session not found", severity="error")

    def _agent_delete_saved(self, name_or_id: str):
        manager = self.app.agent_manager
        if manager.delete_saved_session(name_or_id):
            self.notify(f"Deleted session: {name_or_id}")
        else:
            self.notify(f"Session not found: {name_or_id}", severity="error")

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
                system_prompt="You are a helpful assistant that creates concise conversation summaries.",
            ):
                summary += chunk

            old_token_count = context_info.estimated_tokens
            self.app.blocks = []
            self.app.current_cli_block = None
            self.app.current_cli_widget = None

            try:
                history = self.app.query_one("#history")
                await history.remove_children()
            except Exception:
                pass

            summary_block = BlockState(
                type=BlockType.SYSTEM_MSG,
                content_input="Context Summary",
                content_output=summary,
                is_running=False,
            )
            self.app.blocks.append(summary_block)

            try:
                from widgets import BlockWidget, HistoryViewport

                block_widget = BlockWidget(summary_block)
                history = self.app.query_one("#history", HistoryViewport)
                await history.add_block(block_widget)
            except Exception:
                pass

            new_token_count = len(summary) // 4
            reduction = ((old_token_count - new_token_count) / old_token_count) * 100

            self.app._update_status_bar()
            self.notify(
                f"Compacted: ~{old_token_count} → ~{new_token_count} tokens ({reduction:.0f}% reduction)"
            )

        except Exception as e:
            self.notify(f"Compact failed: {e}", severity="error")

    async def cmd_context(self, args: list[str]):
        from screens.context import ContextScreen

        self.app.push_screen(ContextScreen())

    async def cmd_profile(self, args: list[str]):
        """Manage agent profiles. Usage: /profile [list|<name>|create|edit|export|import|delete]"""
        if not args:
            await self._profile_list()
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            await self._profile_list()
        elif subcommand == "create":
            await self._profile_create(args[1:] if len(args) > 1 else [])
        elif subcommand == "edit":
            if len(args) > 1:
                await self._profile_edit(args[1])
            else:
                self.notify("Usage: /profile edit <name>", severity="warning")
        elif subcommand == "export":
            if len(args) > 1:
                await self._profile_export(args[1])
            else:
                self.notify("Usage: /profile export <name>", severity="warning")
        elif subcommand == "import":
            if len(args) > 1:
                await self._profile_import(args[1])
            else:
                self.notify("Usage: /profile import <file>", severity="warning")
        elif subcommand == "delete":
            if len(args) > 1:
                await self._profile_delete(args[1])
            else:
                self.notify("Usage: /profile delete <name>", severity="warning")
        elif subcommand == "active":
            await self._profile_active()
        else:
            await self._profile_activate(subcommand)

    async def _profile_list(self):
        """List all available profiles."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profiles = pm.list_profiles()
        if not profiles:
            await self.show_output("/profile list", "No profiles available.")
            return

        lines = ["Available Agent Profiles:", "=" * 60, ""]

        for profile in profiles:
            source_label = "[builtin]" if profile.source == "builtin" else "[local]"
            active_marker = " ← active" if pm.active_profile_id == profile.id else ""
            lines.append(
                f"{profile.icon} {profile.name:25} {source_label:10}{active_marker}"
            )
            lines.append(f"   ID: {profile.id}")
            lines.append(f"   {profile.description}")
            if profile.tags:
                lines.append(f"   Tags: {', '.join(profile.tags)}")
            lines.append("")

        lines.extend(
            [
                "Commands:",
                "  /profile <name>           - Activate a profile",
                "  /profile create           - Create new profile",
                "  /profile edit <name>      - Edit a profile",
                "  /profile export <name>    - Export profile to YAML",
                "  /profile import <file>    - Import profile from YAML",
                "  /profile delete <name>    - Delete a profile",
                "  /profile active           - Show active profile",
            ]
        )

        await self.show_output("/profile list", "\n".join(lines))

    async def _profile_activate(self, profile_id: str):
        """Activate a profile by ID or name."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profile = pm.get_profile(profile_id)
        if not profile:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        pm.activate(profile_id)
        self.notify(f"Activated profile: {profile.name}")

        lines = [
            f"Profile: {profile.icon} {profile.name}",
            f"Description: {profile.description}",
            "",
            "Configuration:",
            f"  Temperature: {profile.temperature}",
            f"  Max Iterations: {profile.max_iterations}",
            f"  Max Tokens: {profile.max_tokens or 'unlimited'}",
        ]

        if profile.allowed_tools:
            lines.append(f"  Allowed Tools: {', '.join(profile.allowed_tools)}")
        else:
            lines.append("  Allowed Tools: all")

        if profile.blocked_tools:
            lines.append(f"  Blocked Tools: {', '.join(profile.blocked_tools)}")

        if profile.require_approval:
            lines.append(f"  Requires Approval: {', '.join(profile.require_approval)}")

        if profile.auto_include_files:
            lines.append(
                f"  Auto-Include Files: {', '.join(profile.auto_include_files)}"
            )

        await self.show_output(f"/profile {profile_id}", "\n".join(lines))

    async def _profile_active(self):
        """Show the currently active profile."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        if not pm.active_profile:
            self.notify("No active profile. Use /profile <name> to activate one.")
            return

        profile = pm.active_profile
        lines = [
            f"Active Profile: {profile.icon} {profile.name}",
            f"ID: {profile.id}",
            f"Description: {profile.description}",
            "",
            "Configuration:",
            f"  Temperature: {profile.temperature}",
            f"  Max Iterations: {profile.max_iterations}",
            f"  Max Tokens: {profile.max_tokens or 'unlimited'}",
        ]

        if profile.system_prompt:
            lines.extend(["", "System Prompt:", profile.system_prompt[:500]])
            if len(profile.system_prompt) > 500:
                lines.append("... (truncated)")

        await self.show_output("/profile active", "\n".join(lines))

    async def _profile_create(self, args: list[str]):
        """Create a new profile interactively."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        if args and args[0] == "from":
            if len(args) < 2:
                self.notify(
                    "Usage: /profile create from <source_id> <new_id> <new_name>",
                    severity="warning",
                )
                return

            source_id = args[1]
            new_id = args[2] if len(args) > 2 else source_id + "_copy"
            new_name = " ".join(args[3:]) if len(args) > 3 else f"{source_id} (Copy)"

            profile = pm.duplicate_profile(source_id, new_id, new_name)
            if profile:
                self.notify(f"Created profile: {new_id}")
                await self._profile_activate(new_id)
            else:
                self.notify(
                    f"Could not duplicate profile: {source_id}", severity="error"
                )
        else:
            self.notify(
                "Interactive profile creation not yet implemented. Use /profile create from <source_id>"
            )

    async def _profile_edit(self, profile_id: str):
        """Edit a profile."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profile = pm.get_profile(profile_id)
        if not profile:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        if profile.source == "builtin":
            self.notify(
                "Cannot edit builtin profiles. Duplicate and edit the copy.",
                severity="warning",
            )
            return

        self.notify(
            "Profile editing UI not yet implemented. Use /profile export to view/edit YAML."
        )

    async def _profile_export(self, profile_id: str):
        """Export a profile to YAML."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        yaml_content = pm.export_profile(profile_id)
        if not yaml_content:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        await self.show_output(f"/profile export {profile_id}", yaml_content)

    async def _profile_import(self, file_path: str):
        """Import a profile from YAML file."""
        from managers.profiles import ProfileManager
        from pathlib import Path

        try:
            yaml_file = Path(file_path).expanduser()
            if not yaml_file.exists():
                self.notify(f"File not found: {file_path}", severity="error")
                return

            content = yaml_file.read_text(encoding="utf-8")
            pm = ProfileManager()
            pm.initialize()

            profile = pm.import_profile(content)
            if profile:
                self.notify(f"Imported profile: {profile.id}")
                await self._profile_activate(profile.id)
            else:
                self.notify(
                    "Failed to import profile. Check YAML format.", severity="error"
                )
        except Exception as e:
            self.notify(f"Import error: {e}", severity="error")

    async def _profile_delete(self, profile_id: str):
        """Delete a profile."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profile = pm.get_profile(profile_id)
        if not profile:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        if profile.source == "builtin":
            self.notify("Cannot delete builtin profiles.", severity="warning")
            return

        if pm.delete_profile(profile_id):
            self.notify(f"Deleted profile: {profile_id}")
        else:
            self.notify(f"Failed to delete profile: {profile_id}", severity="error")

    async def cmd_plan(self, args: list[str]):
        """Planning mode. Usage: /plan <goal> | /plan status | /plan approve [step_id|all] | /plan skip <step_id> | /plan cancel | /plan execute"""
        from managers.planning import PlanManager, StepStatus

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
        from managers.planning import StepStatus, StepType
        import time

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

    async def cmd_bg(self, args: list[str]):
        """Background agents. Usage: /bg <goal> | /bg list | /bg status <id> | /bg cancel <id> | /bg logs <id> | /bg clear"""
        from managers.background import BackgroundAgentManager, TaskStatus

        manager: BackgroundAgentManager = (
            getattr(self.app, "background_manager", None) or BackgroundAgentManager()
        )
        if not hasattr(self.app, "background_manager"):
            object.__setattr__(self.app, "background_manager", manager)

        if not args:
            await self._bg_list(manager)
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            await self._bg_list(manager)
        elif subcommand == "status":
            if len(args) > 1:
                await self._bg_status(manager, args[1])
            else:
                self.notify("Usage: /bg status <task_id>", severity="warning")
        elif subcommand == "cancel":
            if len(args) > 1:
                await self._bg_cancel(manager, args[1])
            else:
                self.notify("Usage: /bg cancel <task_id>", severity="warning")
        elif subcommand == "logs":
            if len(args) > 1:
                await self._bg_logs(manager, args[1])
            else:
                self.notify("Usage: /bg logs <task_id>", severity="warning")
        elif subcommand == "clear":
            await self._bg_clear(manager)
        else:
            goal = " ".join(args)
            await self._bg_spawn(manager, goal)

    async def _bg_list(self, manager):
        from managers.background import TaskStatus

        tasks = manager.list_tasks(limit=20)
        if not tasks:
            self.notify("No background tasks")
            return

        lines = [
            f"Background Tasks (active: {manager.active_count}, queued: {manager.queued_count})",
            "",
        ]

        for task in tasks:
            lines.append(task.summary)
            if task.status == TaskStatus.RUNNING:
                lines.append(
                    f"  Progress: {task.progress * 100:.0f}% - {task.current_step}"
                )

        await self.show_output("/bg list", "\n".join(lines))

    async def _bg_status(self, manager, task_id: str):
        from managers.background import TaskStatus

        task = manager.get_task(task_id)
        if not task:
            self.notify(f"Task not found: {task_id}", severity="error")
            return

        lines = [
            f"Task: {task.id}",
            f"Goal: {task.goal}",
            f"Status: {task.status.value}",
            f"Progress: {task.progress * 100:.0f}%",
            f"Duration: {task.duration:.1f}s",
        ]

        if task.current_step:
            lines.append(f"Current: {task.current_step}")
        if task.result:
            lines.append(f"\nResult:\n{task.result[:500]}")
        if task.error:
            lines.append(f"\nError: {task.error}")

        await self.show_output(f"/bg status {task_id}", "\n".join(lines))

    async def _bg_cancel(self, manager, task_id: str):
        if manager.cancel_task(task_id):
            self.notify(f"Cancelled task: {task_id}")
        else:
            self.notify(f"Could not cancel task: {task_id}", severity="error")

    async def _bg_logs(self, manager, task_id: str):
        task = manager.get_task(task_id)
        if not task:
            self.notify(f"Task not found: {task_id}", severity="error")
            return

        if not task.logs:
            self.notify(f"No logs for task: {task_id}")
            return

        await self.show_output(f"/bg logs {task_id}", "\n".join(task.logs[-50:]))

    async def _bg_clear(self, manager):
        count = manager.clear_completed()
        self.notify(f"Cleared {count} completed tasks")

    async def _bg_spawn(self, manager, goal: str):
        if not self.app.ai_provider:
            self.notify("No AI provider configured", severity="error")
            return

        task = await manager.spawn(goal, self.app.ai_provider)
        self.notify(f"Started background task: {task.id}")

    async def cmd_orchestrate(self, args: list[str]):
        """Multi-agent orchestration. Usage: /orchestrate <goal> | /orchestrate status | /orchestrate stop"""
        from managers.orchestrator import AgentOrchestrator, AgentRole

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

            output = f"Orchestration Complete\n"
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
