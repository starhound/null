"""Main application module for Null terminal."""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, TextArea, Label
from pathlib import Path
import os

from config import Config
from models import BlockState, BlockType
from widgets import (
    InputController, HistoryViewport, BlockWidget, BaseBlockWidget,
    CommandSuggester, StatusBar, HistorySearch, BlockSearch,
    CommandPalette
)
from executor import ExecutionEngine
from mcp import MCPManager
from handlers import SlashCommandHandler, ExecutionHandler, InputHandler

from ai.factory import AIFactory
from ai.manager import AIManager
from screens import HelpScreen, ModelListScreen
from themes import get_all_themes


class NullApp(App):
    """Main Null terminal application."""

    CSS_PATH = "styles/main.tcss"

    BINDINGS = [
        ("escape", "cancel_operation", "Cancel"),
        ("ctrl+c", "smart_quit", "Quit"),
        ("ctrl+l", "clear_history", "Clear History"),
        ("ctrl+s", "quick_export", "Export"),
        ("ctrl+r", "search_history", "Search History"),
        ("ctrl+f", "search_blocks", "Search Blocks"),
        ("ctrl+p", "open_command_palette", "Command Palette"),
        ("f1", "open_help", "Help"),
        ("f2", "select_model", "Select Model"),
        ("f3", "select_theme", "Change Theme"),
        ("f4", "select_provider", "Select Provider"),
        ("ctrl+space", "toggle_ai_mode", "Toggle AI Mode"),
        ("ctrl+t", "toggle_ai_mode", "Toggle AI Mode"),
        ("ctrl+b", "toggle_ai_mode", "Toggle AI Mode"),
    ]

    def __init__(self):
        super().__init__()

        # Register custom themes (built-in + user themes from ~/.null/themes/)
        for theme in get_all_themes().values():
            self.register_theme(theme)

        self.config = Config.load_all()

        # Apply saved theme or default to null-dark
        saved_theme = self.config.get("theme", "null-dark")
        if saved_theme in self.available_themes:
            self.theme = saved_theme
        else:
            self.theme = "null-dark"

        self.blocks = []
        
        # Initialize Storage
        from storage import StorageManager
        self.storage = StorageManager()
        
        self.executor = ExecutionEngine()

        # CLI session tracking
        self.current_cli_block = None
        self.current_cli_widget = None

        # AI state
        self._ai_cancelled = False
        self._active_worker = None

        # AI Manager
        self.ai_manager = AIManager()
        
        # Legacy/Convenience pointer to active provider for existing checks
        self.ai_provider = self.ai_manager.get_active_provider()

        # MCP Manager
        self.mcp_manager = MCPManager()

        # Initialize handlers
        self.command_handler = SlashCommandHandler(self)
        self.execution_handler = ExecutionHandler(self)
        self.input_handler = InputHandler(self)

    def compose(self) -> ComposeResult:
        yield CommandSuggester(id="suggester")
        yield CommandPalette(id="command-palette")
        yield HistoryViewport(id="history")

        # History search replaces input container when active
        yield HistorySearch(id="history-search")
        yield BlockSearch(id="block-search")

        with Container(id="input-container"):
            yield Label(self._get_prompt_text(), id="prompt-line")
            input_widget = InputController(placeholder="Type a command...", id="input")
            input_widget.cmd_history = Config._get_storage().get_last_history()
            yield input_widget

        yield StatusBar(id="status-bar")
        yield Footer()

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def on_mount(self):
        """Load previous session on startup."""
        storage = Config._get_storage()
        saved_blocks = storage.load_session()

        if saved_blocks:
            self.blocks = saved_blocks
            history_vp = self.query_one("#history", HistoryViewport)
            for block in self.blocks:
                block.is_running = False
                block_widget = BlockWidget(block)
                await history_vp.mount(block_widget)
            history_vp.scroll_end(animate=False)
            self.notify(f"Restored {len(saved_blocks)} blocks from previous session")

        self._update_status_bar()
        self.set_interval(30, self._check_provider_health)
        self.call_later(self._check_provider_health)
        self.run_worker(self._init_mcp())

        # Auto-detect model for local providers
        self.run_worker(self._detect_local_model())

        # Auto-focus the input prompt
        self.query_one("#input", InputController).focus()

    async def _init_mcp(self):
        """Initialize MCP server connections."""
        try:
            await self.mcp_manager.initialize()
            tools = self.mcp_manager.get_all_tools()
            if tools:
                self.notify(f"MCP: Connected with {len(tools)} tools available")
        except Exception:
            pass

    async def _detect_local_model(self):
        """Auto-detect model for local providers (lm_studio, ollama)."""
        try:
            provider_name = Config.get("ai.provider")
            if provider_name not in ("lm_studio", "ollama"):
                return
            
            # Fetch models to trigger auto-detection
            _, models, _ = await self.ai_manager._fetch_models_for_provider(provider_name)
            
            if models and self.ai_provider:
                # Update the cached provider reference
                self.ai_provider = self.ai_manager.get_provider(provider_name)
                self._update_status_bar()
        except Exception:
            pass

    async def _connect_new_mcp_server(self, name: str):
        """Connect to a newly added MCP server."""
        try:
            if await self.mcp_manager.connect_server(name):
                client = self.mcp_manager.clients.get(name)
                if client:
                    self.notify(f"Connected to {name} ({len(client.tools)} tools)")
            else:
                self.notify(f"Failed to connect to {name}", severity="warning")
        except Exception as e:
            self.notify(f"Error connecting to {name}: {e}", severity="error")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_toggle_ai_mode(self):
        """Toggle between CLI and AI mode."""
        self.query_one("#input", InputController).toggle_mode()

    def action_cancel_operation(self):
        """Cancel any running operation."""
        cancelled = False

        if self.executor.is_running:
            self.executor.cancel()
            cancelled = True

        if self._active_worker and not self._active_worker.is_finished:
            self._ai_cancelled = True
            self._active_worker.cancel()
            cancelled = True

        if cancelled:
            self.notify("Operation cancelled", severity="warning")

    def action_smart_quit(self):
        """Smart Ctrl+C: Cancel if busy, quit if idle."""
        if self.is_busy:
            self.action_cancel_operation()
        else:
            self.exit()

    @property
    def is_busy(self) -> bool:
        """Check if any operation is currently running."""
        return self.executor.is_running or (
            self._active_worker and not self._active_worker.is_finished
        )

    def action_quick_export(self):
        """Quick export to markdown."""
        self._do_export("md")

    def action_search_history(self):
        """Open history search."""
        try:
            self.query_one("#history-search", HistorySearch).show()
        except Exception:
            pass

    def action_search_blocks(self):
        """Open block content search."""
        try:
            self.query_one("#block-search", BlockSearch).show()
        except Exception:
            pass

    def action_open_command_palette(self):
        """Open the command palette."""
        try:
            self.query_one("#command-palette", CommandPalette).show()
        except Exception:
            pass

    def action_open_help(self):
        """Show the help screen."""
        self.push_screen(HelpScreen())

    def action_select_provider(self):
        """Switch and configure AI Provider."""
        from ai.factory import AIFactory
        providers = AIFactory.list_providers()

        def on_provider_selected(provider_name):
            if not provider_name:
                return

            sm = Config._get_storage()
            current_conf = {
                "api_key": sm.get_config(f"ai.{provider_name}.api_key", ""),
                "endpoint": sm.get_config(f"ai.{provider_name}.endpoint", ""),
                "region": sm.get_config(f"ai.{provider_name}.region", ""),
                "model": sm.get_config(f"ai.{provider_name}.model", ""),
            }

            from screens import ProviderConfigScreen

            def on_config_saved(result):
                if result is not None:
                    for k, v in result.items():
                        Config.set(f"ai.{provider_name}.{k}", v)

                    Config.set("ai.provider", provider_name)
                    self.notify(f"Provider switched to {provider_name}")

                    provider_config = {
                        "provider": provider_name,
                        "api_key": result.get("api_key") or Config.get(f"ai.{provider_name}.api_key"),
                        "endpoint": result.get("endpoint") or Config.get(f"ai.{provider_name}.endpoint"),
                        "region": result.get("region") or Config.get(f"ai.{provider_name}.region"),
                        "model": result.get("model") or Config.get(f"ai.{provider_name}.model"),
                        "api_version": Config.get(f"ai.{provider_name}.api_version"),
                    }

                    try:
                        # Refresh config loading
                        self.config = Config.load_all()
                        
                        # Re-initialize the specific provider through the manager
                        # This ensures the manager has the latest instance
                        self.ai_manager.get_provider(provider_name)
                        
                        # Update raw pointer for legacy support
                        self.ai_provider = self.ai_manager.get_provider(provider_name)
                    except Exception as e:
                        self.notify(f"Error initializing provider: {e}", severity="error")

            self.push_screen(ProviderConfigScreen(provider_name, current_conf), on_config_saved)

        from screens import SelectionListScreen
        self.push_screen(SelectionListScreen("Select Provider", providers), on_provider_selected)

    def action_select_model(self):
        """Select an AI model from ALL providers."""
        
        def on_model_select(selection):
            if selection:
                provider_name, model_name = selection
                
                # If the selected model belongs to a DIFFERENT provider than active,
                # we should switch the active provider to match!
                current_provider_name = Config.get("ai.provider")
                
                if provider_name != current_provider_name:
                     Config.set("ai.provider", provider_name)
                     self.notify(f"Switched provider to {provider_name}")
                
                # Update the model for that provider
                Config.set(f"ai.{provider_name}.model", str(model_name))
                self.notify(f"Model set to {model_name}")
                
                # Refresh everything
                self.ai_provider = self.ai_manager.get_provider(provider_name)
                # Ensure the provider instance knows its model (some store it internally)
                if self.ai_provider:
                    self.ai_provider.model = str(model_name)
                    
                self._update_status_bar()

        # Show screen immediately with async fetch
        self.push_screen(
            ModelListScreen(fetch_func=self.ai_manager.list_all_models),
            on_model_select
        )

    def action_select_theme(self):
        """Change the application theme."""
        # Get all available themes, with custom null-* themes first
        all_themes = list(self.available_themes)
        null_themes = sorted([t for t in all_themes if t.startswith("null-")])
        other_themes = sorted([t for t in all_themes if not t.startswith("null-")])
        themes = null_themes + other_themes

        def on_theme_select(selected_theme):
            if selected_theme:
                Config.update_key(["theme"], str(selected_theme))
                self.theme = selected_theme
                self.notify(f"Theme set to {selected_theme}")

        from screens import ThemeSelectionScreen
        self.push_screen(ThemeSelectionScreen("Select Theme", themes), on_theme_select)

    def action_select_prompt(self):
        """Select a system prompt (persona)."""
        from prompts import get_prompt_manager

        prompt_manager = get_prompt_manager()
        prompts_list = prompt_manager.list_prompts()

        # Format: "key - description" for display
        display_items = []
        key_map = {}
        for key, name, desc, is_user in prompts_list:
            prefix = "[user] " if is_user else ""
            display = f"{prefix}{name}"
            display_items.append(display)
            key_map[display] = key

        def on_prompt_select(selected):
            if selected and selected in key_map:
                key = key_map[selected]
                Config.update_key(["ai", "active_prompt"], key)
                self.notify(f"System Persona set to: {selected}")
                self.config["ai"]["active_prompt"] = key

        from screens import SelectionListScreen
        self.push_screen(SelectionListScreen("Select Persona", display_items), on_prompt_select)

    def action_clear_history(self):
        """Clear history and context."""
        async def do_clear():
            await self.command_handler.handle("/clear")
        self.run_worker(do_clear())

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def on_click(self, event) -> None:
        """Handle clicks - dismiss popups and focus input on background clicks."""
        # Dismiss command suggester
        try:
            suggester = self.query_one("#suggester", CommandSuggester)
            if suggester.display:
                if not suggester.region.contains(event.x, event.y):
                    suggester.display = False
        except Exception:
            pass

        # Dismiss history search
        try:
            history_search = self.query_one("#history-search", HistorySearch)
            if history_search.has_class("visible"):
                if not history_search.region.contains(event.x, event.y):
                    history_search.hide()
                return  # Don't focus input if we just closed search
        except Exception:
            pass

        # Focus input when clicking on empty areas (history viewport background)
        try:
            history_vp = self.query_one("#history", HistoryViewport)
            input_ctrl = self.query_one("#input", InputController)

            # Check if click is in history viewport area
            if history_vp.region.contains(event.x, event.y):
                # Check if we clicked on actual content or empty space
                # by seeing if any block contains the click point
                clicked_on_block = False
                for block in history_vp.query(BaseBlockWidget):
                    if block.region.contains(event.x, event.y):
                        clicked_on_block = True
                        break

                # If clicked on empty space, focus input
                if not clicked_on_block:
                    input_ctrl.focus()
        except Exception:
            pass

    async def on_input_controller_submitted(self, message: InputController.Submitted):
        """Handle input submission."""
        await self.input_handler.handle_submission(message.value)

    async def on_text_area_changed(self, message: TextArea.Changed):
        """Update command suggester."""
        suggester = self.query_one("#suggester", CommandSuggester)
        suggester.update_filter(message.text_area.text)

    def on_input_controller_toggled(self, message: InputController.Toggled):
        """Handle mode toggle."""
        self._update_status_bar()
        self._update_prompt()
        # Update container class for focus styling
        try:
            container = self.query_one("#input-container", Container)
            if message.mode == "AI":
                container.add_class("ai-mode")
            else:
                container.remove_class("ai-mode")
        except Exception:
            pass

    def on_history_search_selected(self, message: HistorySearch.Selected):
        """Handle history search selection."""
        input_ctrl = self.query_one("#input", InputController)
        input_ctrl.text = message.command
        input_ctrl.focus()
        input_ctrl.move_cursor((len(message.command), 0))

    def on_history_search_cancelled(self, message: HistorySearch.Cancelled):
        """Handle history search cancellation."""
        self.query_one("#input", InputController).focus()

    async def on_command_palette_action_selected(self, message: CommandPalette.ActionSelected):
        """Handle command palette action selection."""
        action = message.action
        action_id = action.action_id

        # Focus main input after palette closes
        try:
            self.query_one("#input", InputController).focus()
        except Exception:
            pass

        if action_id.startswith("slash:"):
            # Execute slash command
            cmd = action_id[6:]  # Remove "slash:" prefix
            await self.input_handler.handle_submission(cmd)

        elif action_id.startswith("action:"):
            # Execute action
            action_name = action_id[7:]  # Remove "action:" prefix
            action_map = {
                "toggle_ai_mode": self.action_toggle_ai_mode,
                "clear_history": self.action_clear_history,
                "quick_export": self.action_quick_export,
                "search_history": self.action_search_history,
                "open_help": self.action_open_help,
                "select_model": self.action_select_model,
                "change_theme": self.action_select_theme,
                "select_provider": self.action_select_provider,
                "cancel_operation": self.action_cancel_operation,
            }
            if action_name in action_map:
                action_map[action_name]()

        elif action_id.startswith("history:"):
            # Put command in input
            cmd = action_id[8:]  # Remove "history:" prefix
            input_ctrl = self.query_one("#input", InputController)
            input_ctrl.text = cmd
            input_ctrl.move_cursor((len(cmd), 0))

    def on_command_palette_closed(self, message: CommandPalette.Closed):
        """Handle command palette close."""
        try:
            self.query_one("#input", InputController).focus()
        except Exception:
            pass

    async def on_base_block_widget_retry_requested(self, message: BaseBlockWidget.RetryRequested):
        """Handle retry button click."""
        block = next((b for b in self.blocks if b.id == message.block_id), None)
        if not block:
            self.notify("Block not found", severity="error")
            return

        widget = self._find_widget_for_block(message.block_id)
        if not widget:
            self.notify("Widget not found", severity="error")
            return

        await self.execution_handler.regenerate_ai(block, widget)

    async def on_base_block_widget_edit_requested(self, message: BaseBlockWidget.EditRequested):
        """Handle edit button click."""
        input_ctrl = self.query_one("#input", InputController)
        input_ctrl.text = message.content
        input_ctrl.focus()
        if not input_ctrl.is_ai_mode:
            input_ctrl.toggle_mode()
        self.notify("Edit and resubmit your query")

    async def on_code_block_widget_run_code_requested(self, message):
        """Handle run code button click from code blocks."""
        from widgets.blocks import CodeBlockWidget, execute_code

        code = message.code
        language = message.language

        self.notify(f"Running {language} code...")

        # Execute the code
        output, exit_code = await execute_code(code, language)

        # Create a system block to show the output
        result_title = f"Code Execution ({language})"
        if exit_code != 0:
            result_title += f" [exit: {exit_code}]"

        # Format output as code block
        formatted_output = f"```\n{output.rstrip()}\n```" if output else "*(no output)*"

        block = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input=result_title,
            content_output=formatted_output,
            exit_code=exit_code,
            is_running=False
        )
        self.blocks.append(block)
        history_vp = self.query_one("#history", HistoryViewport)
        block_widget = BlockWidget(block)
        await history_vp.mount(block_widget)
        block_widget.scroll_visible()
        self._auto_save()

    async def on_code_block_widget_save_code_requested(self, message):
        """Handle save code button click from code blocks."""
        from widgets.blocks import get_file_extension
        from screens import SaveFileDialog

        code = message.code
        language = message.language

        # Suggest a filename based on language
        ext = get_file_extension(language)
        suggested_name = f"code{ext}"

        def on_saved(filepath):
            if filepath:
                self.notify(f"Code saved to {filepath}")

        self.push_screen(SaveFileDialog(suggested_name, code), on_saved)

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _get_prompt_text(self) -> str:
        """Get the prompt text showing cwd."""
        try:
            cwd = Path.cwd()
            home = Path.home()
            try:
                rel = "~/" + str(cwd.relative_to(home))
            except ValueError:
                rel = str(cwd)
            return f"$ {rel}"
        except Exception:
            return "$ ."

    def _update_prompt(self):
        """Update the prompt line with current directory."""
        try:
            prompt_label = self.query_one("#prompt-line", Label)
            input_ctrl = self.query_one("#input", InputController)

            prompt_label.update(self._get_prompt_text())

            if input_ctrl.is_ai_mode:
                prompt_label.add_class("ai-mode")
                cwd_part = self._get_prompt_text()[2:]
                prompt_label.update(f"? {cwd_part}")
            else:
                prompt_label.remove_class("ai-mode")
        except Exception:
            pass

    def _update_status_bar(self):
        """Update status bar with current state."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            input_ctrl = self.query_one("#input", InputController)
            status_bar.set_mode(input_ctrl.mode)

            # Get FRESH config values (Config.get reads from storage)
            agent_mode = Config.get("ai.agent_mode") or False
            status_bar.set_agent_mode(agent_mode)

            from context import ContextManager
            context_str = ContextManager.get_context(self.blocks)

            # Get context limit from model info
            context_limit = 4000 * 4  # Default fallback (4k tokens * 4 chars)
            if self.ai_provider:
                model_info = self.ai_provider.get_model_info()
                context_limit = model_info.context_window * 4  # tokens to chars

            status_bar.set_context(len(context_str), context_limit)

            # Get fresh provider name
            provider_name = Config.get("ai.provider") or "none"
            status_bar.provider_name = provider_name
        except Exception:
            pass

    async def _check_provider_health(self):
        """Check if AI provider is connected."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)

            # Update provider status
            if self.ai_provider:
                status_bar.set_provider(self.ai_provider.name, "connected")
            else:
                status_bar.set_provider("No Provider", "disconnected")

            # Update MCP status
            active_mcp = 0
            if self.mcp_manager:
                status = self.mcp_manager.get_status()
                active_mcp = sum(1 for s in status.values() if s.get("connected"))
            
            status_bar.set_mcp_status(active_mcp)

        except Exception:
            try:
                self.query_one("#status-bar", StatusBar).provider_status = "disconnected"
            except Exception:
                pass

    def _find_widget_for_block(self, block_id: str) -> BaseBlockWidget:
        """Find the BlockWidget for a given block ID."""
        history_vp = self.query_one("#history", HistoryViewport)
        for widget in history_vp.query(BaseBlockWidget):
            if widget.block.id == block_id:
                return widget
        return None

    async def _show_system_output(self, title: str, content: str):
        """Display system output in a dedicated block."""
        block = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input=title,
            content_output=content,
            is_running=False
        )
        history_vp = self.query_one("#history", HistoryViewport)
        block_widget = BlockWidget(block)
        await history_vp.mount(block_widget)
        block_widget.scroll_visible()

    def _do_export(self, format: str = "md"):
        """Export conversation to file."""
        from models import save_export

        if not self.blocks:
            self.notify("Nothing to export", severity="warning")
            return

        try:
            filepath = save_export(self.blocks, format)
            self.notify(f"Exported to {filepath}")
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def _auto_save(self):
        """Auto-save current session."""
        try:
            Config._get_storage().save_current_session(self.blocks)
            self._update_status_bar()
        except Exception:
            pass


if __name__ == "__main__":
    app = NullApp()
    app.run()
