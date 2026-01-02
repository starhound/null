"""Slash command handlers for the Null terminal."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from config import Config
from models import BlockState, BlockType
from widgets import BlockWidget, HistoryViewport, StatusBar
from screens import HelpScreen, ModelListScreen, SelectionListScreen
from ai.factory import AIFactory


class SlashCommandHandler:
    """Handles all slash command processing."""

    def __init__(self, app: "NullApp"):
        self.app = app

    async def handle(self, text: str):
        """Route and execute a slash command."""
        parts = text.split()
        command = parts[0][1:]  # strip /
        args = parts[1:]

        # Command routing
        handler = getattr(self, f"cmd_{command}", None)
        if handler:
            await handler(args)
        else:
            self.app.notify(f"Unknown command: {command}", severity="warning")

    async def cmd_help(self, args: list[str]):
        """Show help screen."""
        self.app.push_screen(HelpScreen())

    async def cmd_provider(self, args: list[str]):
        """Switch AI provider."""
        self.app.action_select_provider()

    async def cmd_theme(self, args: list[str]):
        """Set theme."""
        if not args:
            # Show theme selector
            self.app.action_select_theme()
            return
        theme_name = args[0]
        if theme_name in self.app.available_themes:
            Config.update_key(["theme"], theme_name)
            self.app.theme = theme_name
            self.app.notify(f"Theme set to {theme_name}")
        else:
            self.app.notify(f"Unknown theme: {theme_name}", severity="error")

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
                self.app.notify("AI Provider not initialized.", severity="error")
                return

            self.app.notify("Fetching models...")
            models = await self.app.ai_provider.list_models()

            def on_model_select(selected_model):
                if selected_model:
                    Config.update_key(["ai", "model"], str(selected_model))
                    self.app.ai_provider.model = str(selected_model)
                    self.app.notify(f"Model set to {selected_model}")

            self.app.push_screen(ModelListScreen(models), on_model_select)

        elif len(args) == 2:
            Config.update_key(["ai", "provider"], args[0])
            Config.update_key(["ai", "model"], args[1])
            self.app.notify(f"AI Model set to {args[0]}/{args[1]}")
            self.app.config = Config.load_all()
            self.app.ai_provider = AIFactory.get_provider(self.app.config["ai"])
        else:
            self.app.notify("Usage: /model OR /model <provider> <model_name>", severity="error")

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
            self.app.notify("Prompts reloaded from ~/.null/prompts/")
        elif subcommand == "show" and len(args) >= 2:
            await self._prompts_show(args[1])
        elif subcommand == "dir":
            from prompts import get_prompt_manager
            pm = get_prompt_manager()
            self.app.notify(f"Prompts directory: {pm.prompts_dir}")
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

        await self.app._show_system_output("/prompts list", "\n".join(lines))

    async def _prompts_show(self, key: str):
        """Show a prompt's content."""
        from prompts import get_prompt_manager

        pm = get_prompt_manager()
        prompt = pm.get_prompt(key)

        if not prompt:
            self.app.notify(f"Prompt not found: {key}", severity="error")
            return

        content = prompt.get("content", "")[:500]
        if len(prompt.get("content", "")) > 500:
            content += "\n... (truncated)"

        await self.app._show_system_output(f"/prompts show {key}", content)

    async def cmd_clear(self, args: list[str]):
        """Clear history and context."""
        self.app.blocks = []
        self.app.current_cli_block = None
        self.app.current_cli_widget = None
        history = self.app.query_one("#history", HistoryViewport)
        await history.remove_children()
        self.app._update_status_bar()
        self.app.notify("History and context cleared")

    async def cmd_compact(self, args: list[str]):
        """Summarize context to reduce token usage."""
        if not self.app.blocks:
            self.app.notify("Nothing to compact", severity="warning")
            return

        if not self.app.ai_provider:
            self.app.notify("AI provider not configured", severity="error")
            return

        # Build context summary from current blocks
        from context import ContextManager
        context_info = ContextManager.build_messages(self.app.blocks)

        if context_info.estimated_tokens < 500:
            self.app.notify("Context too small to compact", severity="warning")
            return

        self.app.notify("Compacting context...")

        # Build a summary prompt
        summary_prompt = """Summarize this conversation concisely. Include:
- Key topics discussed
- Important decisions or conclusions
- Any code/commands that were significant
- Current state/context needed for continuity

Be brief but preserve essential context. Output only the summary."""

        # Collect all content for summarization
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

        # Generate summary
        try:
            summary = ""
            async for chunk in self.app.ai_provider.generate(
                summary_prompt,
                [{"role": "user", "content": context_text}],
                system_prompt="You are a helpful assistant that creates concise conversation summaries."
            ):
                summary += chunk

            # Clear current context
            old_token_count = context_info.estimated_tokens
            self.app.blocks = []
            self.app.current_cli_block = None
            self.app.current_cli_widget = None
            history = self.app.query_one("#history", HistoryViewport)
            await history.remove_children()

            # Create a new system block with the summary
            summary_block = BlockState(
                type=BlockType.SYSTEM_MSG,
                content_input="Context Summary",
                content_output=summary,
                is_running=False
            )
            self.app.blocks.append(summary_block)

            # Mount the summary block
            block_widget = BlockWidget(summary_block)
            await history.mount(block_widget)

            new_token_count = len(summary) // 4
            reduction = ((old_token_count - new_token_count) / old_token_count) * 100

            self.app._update_status_bar()
            self.app.notify(f"Compacted: ~{old_token_count} → ~{new_token_count} tokens ({reduction:.0f}% reduction)")

        except Exception as e:
            self.app.notify(f"Compact failed: {e}", severity="error")

    async def cmd_export(self, args: list[str]):
        """Export conversation."""
        format = args[0] if args else "md"
        if format not in ("md", "json", "markdown"):
            self.app.notify("Usage: /export [md|json]", severity="error")
            return
        if format == "markdown":
            format = "md"
        self.app._do_export(format)

    async def cmd_session(self, args: list[str]):
        """Session management."""
        if not args:
            self.app.notify("Usage: /session [save|load|list|new] [name]", severity="warning")
            return

        subcommand = args[0]
        name = args[1] if len(args) > 1 else None
        storage = Config._get_storage()

        if subcommand == "save":
            filepath = storage.save_session(self.app.blocks, name)
            self.app.notify(f"Session saved to {filepath}")

        elif subcommand == "load":
            await self._session_load(name, storage)

        elif subcommand == "list":
            await self._session_list(storage)

        elif subcommand == "new":
            self.app.blocks = []
            self.app.current_cli_block = None
            self.app.current_cli_widget = None
            storage.clear_current_session()
            history = self.app.query_one("#history", HistoryViewport)
            await history.remove_children()
            self.app.notify("Started new session")

        else:
            self.app.notify("Usage: /session [save|load|list|new] [name]", severity="error")

    async def _session_load(self, name: str | None, storage):
        """Load a session by name or show selection."""
        if name:
            blocks = storage.load_session(name)
            if blocks:
                self.app.blocks = blocks
                self.app.current_cli_block = None
                self.app.current_cli_widget = None
                history = self.app.query_one("#history", HistoryViewport)
                await history.remove_children()
                for block in self.app.blocks:
                    block.is_running = False
                    block_widget = BlockWidget(block)
                    await history.mount(block_widget)
                history.scroll_end(animate=False)
                self.app.notify(f"Loaded session: {name}")
            else:
                self.app.notify(f"Session not found: {name}", severity="error")
        else:
            sessions = storage.list_sessions()
            if sessions:
                names = [s["name"] for s in sessions]

                def on_select(selected):
                    if selected:
                        self.app.call_later(
                            lambda: self.app.run_worker(self.handle(f"/session load {selected}"))
                        )

                self.app.push_screen(SelectionListScreen("Load Session", names), on_select)
            else:
                self.app.notify("No saved sessions found", severity="warning")

    async def _session_list(self, storage):
        """List all saved sessions."""
        sessions = storage.list_sessions()
        if sessions:
            lines = []
            for s in sessions:
                saved_at = s.get("saved_at", "")[:16].replace("T", " ")
                blocks = s.get("block_count", 0)
                lines.append(f"  {s['name']:20} {saved_at:16} ({blocks} blocks)")
            content = "\n".join(lines)
            await self.app._show_system_output("/session list", content)
        else:
            self.app.notify("No saved sessions", severity="warning")

    async def cmd_status(self, args: list[str]):
        """Show current status."""
        from context import ContextManager

        provider = self.app.config.get("ai", {}).get("provider", "none")
        model = self.app.config.get("ai", {}).get("model", "none")
        persona = self.app.config.get("ai", {}).get("active_prompt", "default")
        blocks_count = len(self.app.blocks)

        context_str = ContextManager.get_context(self.app.blocks)
        context_chars = len(context_str)
        context_tokens = context_chars // 4

        status_bar = self.app.query_one("#status-bar", StatusBar)
        provider_status = status_bar.provider_status

        lines = [
            f"  Provider:      {provider} ({provider_status})",
            f"  Model:         {model}",
            f"  Persona:       {persona}",
            f"  Blocks:        {blocks_count}",
            f"  Context:       ~{context_tokens} tokens ({context_chars} chars)",
        ]
        await self.app._show_system_output("/status", "\n".join(lines))

    async def cmd_mcp(self, args: list[str]):
        """MCP server management."""
        if not args:
            args = ["list"]

        subcommand = args[0]

        if subcommand == "list":
            await self._mcp_list()
        elif subcommand == "tools":
            await self._mcp_tools()
        elif subcommand == "add":
            await self._mcp_add()
        elif subcommand == "edit" and len(args) >= 2:
            await self._mcp_edit(args[1])
        elif subcommand == "remove" and len(args) >= 2:
            self._mcp_remove(args[1])
        elif subcommand == "enable" and len(args) >= 2:
            await self._mcp_enable(args[1])
        elif subcommand == "disable" and len(args) >= 2:
            await self._mcp_disable(args[1])
        elif subcommand == "reconnect":
            await self._mcp_reconnect(args[1] if len(args) >= 2 else None)
        else:
            self.app.notify(
                "Usage: /mcp [list|tools|add|edit|remove|enable|disable|reconnect]",
                severity="warning"
            )

    async def _mcp_list(self):
        """List MCP servers."""
        status = self.app.mcp_manager.get_status()
        if not status:
            self.app.notify("No MCP servers configured. Edit ~/.null/mcp.json", severity="warning")
            return

        lines = []
        for name, info in status.items():
            state = "connected" if info["connected"] else ("disabled" if not info["enabled"] else "disconnected")
            tools = info["tools"]
            lines.append(f"  {name:20} {state:12} {tools} tools")
        await self.app._show_system_output("/mcp list", "\n".join(lines))

    async def _mcp_tools(self):
        """List available MCP tools."""
        tools = self.app.mcp_manager.get_all_tools()
        if not tools:
            self.app.notify("No MCP tools available", severity="warning")
            return

        lines = []
        for tool in tools:
            desc = tool.description[:40] + "..." if len(tool.description) > 40 else tool.description
            lines.append(f"  {tool.name:25} {tool.server_name:15} {desc}")
        await self.app._show_system_output("/mcp tools", "\n".join(lines))

    async def _mcp_add(self):
        """Add a new MCP server."""
        from screens import MCPServerConfigScreen

        def on_server_added(result):
            if result:
                name = result["name"]
                self.app.mcp_manager.add_server(
                    name,
                    result["command"],
                    result["args"],
                    result["env"]
                )
                self.app.notify(f"Added MCP server: {name}")
                self.app.run_worker(self.app._connect_new_mcp_server(name))

        self.app.push_screen(MCPServerConfigScreen(), on_server_added)

    async def _mcp_edit(self, name: str):
        """Edit an MCP server."""
        if name not in self.app.mcp_manager.config.servers:
            self.app.notify(f"Server not found: {name}", severity="error")
            return

        from screens import MCPServerConfigScreen
        server = self.app.mcp_manager.config.servers[name]
        current = {
            "command": server.command,
            "args": server.args,
            "env": server.env
        }

        def on_server_edited(result):
            if result:
                server.command = result["command"]
                server.args = result["args"]
                server.env = result["env"]
                self.app.mcp_manager.config.save()
                self.app.notify(f"Updated MCP server: {name}")
                self.app.run_worker(self.app.mcp_manager.reconnect_server(name))

        self.app.push_screen(MCPServerConfigScreen(name, current), on_server_edited)

    def _mcp_remove(self, name: str):
        """Remove an MCP server."""
        if self.app.mcp_manager.remove_server(name):
            self.app.notify(f"Removed MCP server: {name}")
        else:
            self.app.notify(f"Server not found: {name}", severity="error")

    async def _mcp_enable(self, name: str):
        """Enable an MCP server."""
        if name in self.app.mcp_manager.config.servers:
            self.app.mcp_manager.config.servers[name].enabled = True
            self.app.mcp_manager.config.save()
            await self.app.mcp_manager.connect_server(name)
            self.app.notify(f"Enabled MCP server: {name}")
        else:
            self.app.notify(f"Server not found: {name}", severity="error")

    async def _mcp_disable(self, name: str):
        """Disable an MCP server."""
        if name in self.app.mcp_manager.config.servers:
            self.app.mcp_manager.config.servers[name].enabled = False
            self.app.mcp_manager.config.save()
            await self.app.mcp_manager.disconnect_server(name)
            self.app.notify(f"Disabled MCP server: {name}")
        else:
            self.app.notify(f"Server not found: {name}", severity="error")

    async def _mcp_reconnect(self, name: str | None):
        """Reconnect MCP server(s)."""
        if name:
            if await self.app.mcp_manager.reconnect_server(name):
                self.app.notify(f"Reconnected: {name}")
            else:
                self.app.notify(f"Failed to reconnect: {name}", severity="error")
        else:
            await self.app.mcp_manager.disconnect_all()
            await self.app.mcp_manager.initialize()
            tools = self.app.mcp_manager.get_all_tools()
            self.app.notify(f"Reconnected all servers ({len(tools)} tools)")

    async def cmd_quit(self, args: list[str]):
        """Quit the application."""
        self.app.exit()

    async def cmd_exit(self, args: list[str]):
        """Exit the application (alias)."""
        self.app.exit()
