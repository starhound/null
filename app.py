from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, TextArea, Label
from pathlib import Path
import asyncio
import os

from config import Config
from models import BlockState, BlockType
from widgets import InputController, HistoryViewport, BlockWidget, CommandSuggester, StatusBar, HistorySearch
from executor import ExecutionEngine

from ai.factory import AIFactory
from screens import HelpScreen, ModelListScreen

class NullApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    HistoryViewport {
        height: 1fr;
    }

    #input-container {
        height: auto;
        min-height: 4;
        padding: 0 1;
        background: $surface;
        border-top: solid $surface-lighten-2;
    }

    #prompt-line {
        height: 1;
        padding: 0;
        color: $success;
        text-style: bold;
    }

    #prompt-line.ai-mode {
        color: $warning;
    }

    InputController {
        width: 100%;
    }
    """

    BINDINGS = [
        ("escape", "cancel_operation", "Cancel"),
        ("ctrl+c", "smart_quit", "Quit"),
        ("ctrl+l", "clear_history", "Clear History"),
        ("ctrl+s", "quick_export", "Export"),
        ("ctrl+r", "search_history", "Search History"),
        ("f1", "open_help", "Help"),
        ("f2", "select_model", "Select Model"),
        ("f3", "select_theme", "Change Theme"),
        ("f4", "select_provider", "Select Provider"),
        ("ctrl+space", "toggle_ai", "Toggle AI Mode"),
        ("ctrl+t", "toggle_ai", "Toggle AI Mode"),
        ("ctrl+b", "toggle_ai", "Toggle AI Mode"),
    ]
    
    # Removed manual get_system_commands override as it was causing issues.
    # Bindings above will populate the palette.

    def action_toggle_ai_mode(self):
        self.query_one("#input", InputController).toggle_mode()

    def action_cancel_operation(self):
        """Cancel any running operation (Escape key)."""
        cancelled = False

        # Cancel CLI command execution
        if self.executor.is_running:
            self.executor.cancel()
            cancelled = True

        # Cancel AI generation
        if self._active_worker and not self._active_worker.is_finished:
            self._ai_cancelled = True
            self._active_worker.cancel()
            cancelled = True

        if cancelled:
            self.notify("Operation cancelled", severity="warning")

    def action_smart_quit(self):
        """Smart Ctrl+C: Cancel if busy, quit if idle."""
        if self.executor.is_running or (self._active_worker and not self._active_worker.is_finished):
            self.action_cancel_operation()
        else:
            self.exit()

    @property
    def is_busy(self) -> bool:
        """Check if any operation is currently running."""
        return self.executor.is_running or (self._active_worker and not self._active_worker.is_finished)

    def action_quick_export(self):
        """Quick export to markdown (Ctrl+S)."""
        self._do_export("md")

    def action_search_history(self):
        """Open history search (Ctrl+R)."""
        try:
            history_search = self.query_one("#history-search", HistorySearch)
            history_search.show()
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
        input_ctrl = self.query_one("#input", InputController)
        input_ctrl.focus()

    async def _show_system_output(self, title: str, content: str):
        """Display system output in a dedicated block."""
        block = BlockState(
            type=BlockType.SYSTEM_MSG,
            content_input=title,
            content_output=content,
            is_running=False
        )
        # Don't add to blocks list (ephemeral system output)
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

    def action_open_help(self):
        """Show the help screen."""
        self.push_screen(HelpScreen())

    def action_select_provider(self):
        """Switch and configure AI Provider."""
        providers = ["ollama", "openai", "lm_studio", "azure", "bedrock", "xai"]
        
        def on_provider_selected(provider_name):
            if not provider_name:
                return
            
            # Load config for this SPECIFIC provider from DB to pre-fill
            # structure: ai.<provider_name>.api_key, etc.
            sm = Config._get_storage()
            current_conf = {
                "api_key": sm.get_config(f"ai.{provider_name}.api_key", ""),
                "endpoint": sm.get_config(f"ai.{provider_name}.endpoint", ""),
                "region": sm.get_config(f"ai.{provider_name}.region", ""),
                "model": sm.get_config(f"ai.{provider_name}.model", ""),
                # Special defaults fallback if empty
            }
            
            from screens import ProviderConfigScreen
            
            def on_config_saved(result):
                if result is not None:
                    # Save provider-specific config
                    for k, v in result.items():
                         # We allow saving empty strings to clear configs if needed, or just ignore
                         Config.set(f"ai.{provider_name}.{k}", v)
                    
                    # Set active provider
                    Config.set("ai.provider", provider_name)
                    
                    self.notify(f"Provider switched to {provider_name}")
                    
                    # Re-init AI Provider with new settings
                    # We need to construct the config dict expected by AIFactory
                    # which expects keys like 'api_key', 'endpoint' at top level of the dict passed to it.
                    provider_config = {
                        "provider": provider_name,
                        "api_key": result.get("api_key") or Config.get(f"ai.{provider_name}.api_key"),
                        "endpoint": result.get("endpoint") or Config.get(f"ai.{provider_name}.endpoint"),
                        "region": result.get("region") or Config.get(f"ai.{provider_name}.region"),
                        "model": result.get("model") or Config.get(f"ai.{provider_name}.model"),
                        "api_version": Config.get(f"ai.{provider_name}.api_version"), # For Azure if we added it to UI
                    }
                    
                    try:
                        self.ai_provider = AIFactory.get_provider(provider_config)
                        # Also update local config object if we rely on it elsewhere? 
                        # self.config["ai"] is getting stale. 
                        # Let's verify if we need to reload Config.load_all().
                        self.config = Config.load_all() # This might need updating to pull from specific provider
                    except Exception as e:
                        self.notify(f"Error initializing provider: {e}", severity="error")

            self.push_screen(ProviderConfigScreen(provider_name, current_conf), on_config_saved)

        from screens import SelectionListScreen
        self.push_screen(SelectionListScreen("Select Provider", providers), on_provider_selected)

    def action_select_model(self):
        """Select an AI model."""
        async def populate_and_show():
            if not self.ai_provider:
                self.notify("AI Provider not initialized. Selecting provider...", severity="warning")
                self.action_select_provider()
                return
            
            self.notify("Fetching models...")
            models = await self.ai_provider.list_models()
            
            def on_model_select(selected_model):
                if selected_model:
                    Config.update_key(["ai", "model"], str(selected_model))
                    self.notify(f"Model set to {selected_model}")
                    if self.ai_provider:
                         self.ai_provider.model = str(selected_model)

            self.push_screen(ModelListScreen(models), on_model_select)
        
        self.run_worker(populate_and_show())

    def action_select_theme(self):
        """Change the application theme."""
        themes = ["monokai", "dracula", "nord", "solarized-light", "solarized-dark"]
        
        def on_theme_select(selected_theme):
            if selected_theme:
                Config.update_key(["theme"], str(selected_theme))
                self.notify(f"Theme set to {selected_theme} (Restart required for full effect)")
                
        from screens import SelectionListScreen
        self.push_screen(SelectionListScreen("Select Theme", themes), on_theme_select)

    def action_select_prompt(self):
        """Select a system prompt (persona)."""
        # Load latest pointers (in case edited)
        store = Config._get_storage()
        # Need to handle retrieving dictionary from simpler storage if valid
        # Our simple storage handles flattened keys well, but for a dict of prompts it might be tricky
        # if using key-value. 
        # Actually our Config.load_all loads everything.
        # But we added defaults in code, which might not be in DB yet if not saved.
        # Let's rely on self.config["ai"]["prompts"] merging with defaults.
        
        prompts_dict = self.config.get("ai", {}).get("prompts", {})
        # If empty (first run with new code), use defaults from Config class manually? 
        # Config.load_all should have merged it if we used standard merge logic, 
        # but our Config implementation might be simple.
        # Let's import defaults if missing.
        if not prompts_dict:
             prompts_dict = Config.DEFAULT_CONFIG["ai"]["prompts"]
        
        prompt_names = list(prompts_dict.keys())
        
        def on_prompt_select(selected):
            if selected:
                Config.update_key(["ai", "active_prompt"], selected)
                self.notify(f"System Persona set to: {selected}")
                # We need to make sure execute_ai uses this.
                # It will read from self.config (reloaded) or we just update current state logic.
                self.config["ai"]["active_prompt"] = selected

        from screens import SelectionListScreen
        self.push_screen(SelectionListScreen("Select Persona", prompt_names), on_prompt_select)

    def __init__(self):
        super().__init__()
        self.config = Config.load_all()
        self.blocks = [] # List[BlockState]
        self.executor = ExecutionEngine()
        # Track active CLI session for continuous block
        self.current_cli_block = None
        self.current_cli_widget = None
        # Track active operations for cancellation
        self._ai_cancelled = False
        self._active_worker = None
        # AI Provider
        try:
            self.ai_provider = AIFactory.get_provider(self.config["ai"])
        except Exception as e:
            # Fallback/Log, potentially notify user later
            self.ai_provider = None

    def compose(self) -> ComposeResult:
        # Suggester layer at Screen level to avoid clipping (overlay)
        from widgets import CommandSuggester
        yield CommandSuggester(id="suggester")
        yield HistorySearch(id="history-search")

        yield HistoryViewport(id="history")
        with Container(id="input-container"):
            yield Label(self._get_prompt_text(), id="prompt-line")
            input_widget = InputController(placeholder="Type a command...", id="input")
            # Load history
            cmd_history = Config._get_storage().get_last_history()
            input_widget.cmd_history = cmd_history
            yield input_widget
        yield StatusBar(id="status-bar")
        yield Footer()

    def _get_prompt_text(self) -> str:
        """Get the prompt text showing cwd."""
        try:
            cwd = Path.cwd()
            home = Path.home()
            # Replace home with ~
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

            # Update styling based on mode
            if input_ctrl.is_ai_mode:
                prompt_label.add_class("ai-mode")
                # Change prompt symbol for AI mode
                cwd_part = self._get_prompt_text()[2:]  # Remove "$ "
                prompt_label.update(f"? {cwd_part}")
            else:
                prompt_label.remove_class("ai-mode")
        except Exception:
            pass

    async def _handle_builtin_command(self, cmd: str) -> bool:
        """Handle shell builtins that need special handling. Returns True if handled."""
        cmd_stripped = cmd.strip()

        # Handle cd command
        if cmd_stripped == "cd" or cmd_stripped.startswith("cd "):
            parts = cmd_stripped.split(maxsplit=1)
            if len(parts) == 1:
                # cd with no args -> go home
                target = Path.home()
            else:
                path_arg = parts[1].strip()
                # Handle ~ expansion
                if path_arg.startswith("~"):
                    if path_arg == "~" or path_arg.startswith("~/"):
                        path_arg = str(Path.home()) + path_arg[1:]
                # Handle - (previous directory) - simplified, just ignore for now
                if path_arg == "-":
                    self.notify("cd - not supported", severity="warning")
                    return True
                target = Path(path_arg)

            try:
                # Resolve relative to current directory
                if not target.is_absolute():
                    target = Path.cwd() / target
                target = target.resolve()

                if not target.exists():
                    self.notify(f"cd: no such directory: {parts[1] if len(parts) > 1 else '~'}", severity="error")
                    return True
                if not target.is_dir():
                    self.notify(f"cd: not a directory: {parts[1]}", severity="error")
                    return True

                os.chdir(target)
                self._update_prompt()
            except PermissionError:
                self.notify(f"cd: permission denied: {parts[1] if len(parts) > 1 else '~'}", severity="error")
            except Exception as e:
                self.notify(f"cd: {e}", severity="error")
            return True

        # Handle pwd command
        if cmd_stripped == "pwd":
            await self._show_system_output("pwd", str(Path.cwd()))
            return True

        return False

    async def on_mount(self):
        """Load previous session on startup."""
        storage = Config._get_storage()
        saved_blocks = storage.load_session()
        if saved_blocks:
            self.blocks = saved_blocks
            history_vp = self.query_one("#history", HistoryViewport)
            for block in self.blocks:
                block.is_running = False  # Mark as complete
                block_widget = BlockWidget(block)
                await history_vp.mount(block_widget)
            history_vp.scroll_end(animate=False)
            self.notify(f"Restored {len(saved_blocks)} blocks from previous session")

        # Initialize status bar
        self._update_status_bar()

        # Start periodic health check for AI provider
        self.set_interval(30, self._check_provider_health)
        # Also check immediately
        self.call_later(self._check_provider_health)

    def _auto_save(self):
        """Auto-save current session (debounced)."""
        try:
            Config._get_storage().save_current_session(self.blocks)
            # Also update status bar with new context size
            self._update_status_bar()
        except Exception:
            pass

    def _update_status_bar(self):
        """Update status bar with current state."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)

            # Update mode
            input_ctrl = self.query_one("#input", InputController)
            status_bar.set_mode(input_ctrl.mode)

            # Update context size
            from context import ContextManager
            context_str = ContextManager.get_context(self.blocks)
            status_bar.set_context(len(context_str))

            # Update provider
            provider_name = self.config.get("ai", {}).get("provider", "none")
            status_bar.provider_name = provider_name
        except Exception:
            pass

    async def _check_provider_health(self):
        """Check if AI provider is connected."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)

            if not self.ai_provider:
                status_bar.provider_status = "disconnected"
                return

            status_bar.provider_status = "checking"
            connected = await self.ai_provider.validate_connection()
            status_bar.provider_status = "connected" if connected else "disconnected"
        except Exception:
            try:
                status_bar = self.query_one("#status-bar", StatusBar)
                status_bar.provider_status = "disconnected"
            except Exception:
                pass

    def on_input_controller_toggled(self, message: InputController.Toggled):
        """Handle mode toggle from InputController."""
        self._update_status_bar()
        self._update_prompt()

    async def on_block_widget_retry_requested(self, message: BlockWidget.RetryRequested):
        """Handle retry button click - regenerate AI response."""
        # Find the block
        block = next((b for b in self.blocks if b.id == message.block_id), None)
        if not block:
            self.notify("Block not found", severity="error")
            return

        # Find the widget
        widget = self._find_widget_for_block(message.block_id)
        if not widget:
            self.notify("Widget not found", severity="error")
            return

        await self.regenerate_block(block, widget)

    async def on_block_widget_edit_requested(self, message: BlockWidget.EditRequested):
        """Handle edit button click - populate input with original query."""
        input_ctrl = self.query_one("#input", InputController)
        input_ctrl.text = message.content
        input_ctrl.focus()
        # Ensure we're in AI mode
        if not input_ctrl.is_ai_mode:
            input_ctrl.toggle_mode()
        self.notify("Edit and resubmit your query")

    def _find_widget_for_block(self, block_id: str) -> BlockWidget:
        """Find the BlockWidget for a given block ID."""
        history_vp = self.query_one("#history", HistoryViewport)
        for widget in history_vp.query(BlockWidget):
            if widget.block.id == block_id:
                return widget
        return None

    async def regenerate_block(self, block: BlockState, widget: BlockWidget):
        """Regenerate an AI response block with the same query."""
        if not self.ai_provider:
            self.notify("AI Provider not configured", severity="error")
            return

        # Clear output and reset state
        block.content_output = ""
        block.content_exec_output = ""
        block.is_running = True
        block.exit_code = None

        # Reset widget display
        widget.set_loading(True)
        if widget.thinking_widget:
            widget.thinking_widget.thinking_text = ""
            widget.thinking_widget.start_loading()
        if widget.exec_widget:
            widget.exec_widget.exec_output = ""

        # Update metadata to show regenerating
        widget.update_metadata()

        # Run AI worker
        self._ai_cancelled = False
        self._active_worker = self.run_worker(
            self.execute_ai(block.content_input, block, widget)
        )

    async def on_text_area_changed(self, message: TextArea.Changed):
        # Update command suggester when text changes
        suggester = self.query_one("#suggester", CommandSuggester)
        suggester.update_filter(message.text_area.text)


    async def on_input_controller_submitted(self, message: InputController.Submitted):
        # Hide suggester
        self.query_one("#suggester", CommandSuggester).display = False
        
        if not message.value.strip():
            return
            
        cmd_text = message.value
        input_ctrl = self.query_one("#input", InputController)
        
        # Add to widgets history
        input_ctrl.add_to_history(cmd_text)

        # Persist to DB if command
        # For AI queries, maybe we don't persist to command history or maybe we do?
        # Typically command history assumes repeatable commands. AI queries are just chats.
        # Let's persist everything for now so user can up-arrow.
        Config._get_storage().add_history(cmd_text)

        # Slash Command Handling
        if cmd_text.startswith("/"):
            await self.handle_slash_command(cmd_text)
            input_ctrl.value = ""
            return
            
        # Check Mode
        if input_ctrl.is_ai_mode:
             # Switching to AI mode ends CLI session
             self.current_cli_block = None
             self.current_cli_widget = None
             # AI Mode Logic
             if not self.ai_provider:
                 self.notify("AI Provider not configured. Use /provider.", severity="error")
                 self.action_select_provider()
                 return
                 
             # Create Combined AI Block (Input + Placeholder Output)
             # We want a single block for the whole interaction.
             # BlockType.AI_RESPONSE is fine, we just set content_input to the query.
             block = BlockState(
                 type=BlockType.AI_RESPONSE, 
                 content_input=cmd_text,
                 content_output=""
             )
             self.blocks.append(block)
             input_ctrl.value = ""
             
             history_vp = self.query_one("#history", HistoryViewport)
             block_widget = BlockWidget(block)
             await history_vp.mount(block_widget)
             block_widget.scroll_visible()
             
             # Run AI worker and track for cancellation
             self._ai_cancelled = False
             self._active_worker = self.run_worker(self.execute_ai(cmd_text, block, block_widget))
             
        else:
            # CLI Mode Logic - Use continuous block
            input_ctrl.value = ""

            # Handle cd command specially (subprocess can't change parent's cwd)
            if await self._handle_builtin_command(cmd_text):
                return

            # Check if we have an active CLI block to append to
            if self.current_cli_block and self.current_cli_widget:
                # Append to existing CLI block
                block = self.current_cli_block
                widget = self.current_cli_widget

                # Add separator and new command prompt
                if block.content_output:
                    block.content_output += "\n"
                block.content_output += f"$ {cmd_text}\n"
                widget.update_output()
                widget.scroll_visible()

                # Execute and append output
                self.run_worker(self.execute_cli_append(cmd_text, block, widget))
            else:
                # Create new CLI block
                block = BlockState(
                    type=BlockType.COMMAND,
                    content_input=cmd_text
                )
                self.blocks.append(block)

                # Track as current CLI session
                self.current_cli_block = block

                # Create and Add Block Widget to History
                history_vp = self.query_one("#history", HistoryViewport)
                block_widget = BlockWidget(block)
                self.current_cli_widget = block_widget
                await history_vp.mount(block_widget)
                block_widget.scroll_visible()

                # Execute Command
                self.run_worker(self.execute_block(block, block_widget))

    async def handle_slash_command(self, text: str):
        parts = text.split()
        command = parts[0][1:] # strip /
        args = parts[1:]
        
        if command == "help":
            self.push_screen(HelpScreen())

        elif command == "provider":
            self.action_select_provider()

        elif command == "theme":
            if not args:
                self.notify("Usage: /theme <name>", severity="error")
                return
            Config.update_key(["theme"], args[0])
            self.notify(f"Theme set to {args[0]}")
            
        elif command == "ai" or command == "chat":
            self.action_toggle_ai_mode()
            
        elif command == "model":
            if not args:
                # List models
                if not self.ai_provider:
                    self.notify("AI Provider not initialized.", severity="error")
                    return
                
                self.notify("Fetching models...")
                models = await self.ai_provider.list_models()
                
                def on_model_select(selected_model):
                    if selected_model:
                        Config.update_key(["ai", "model"], str(selected_model))
                        # Update provider instance
                        # (Ideally we'd re-init the provider or update its prop)
                        self.ai_provider.model = str(selected_model) 
                        self.notify(f"Model set to {selected_model}")

                self.push_screen(ModelListScreen(models), on_model_select)
            
            elif len(args) == 2:
                Config.update_key(["ai", "provider"], args[0])
                Config.update_key(["ai", "model"], args[1])
                self.notify(f"AI Model set to {args[0]}/{args[1]}")
                # Re-init provider
                self.config = Config.load_all() # reload
                self.ai_provider = AIFactory.get_provider(self.config["ai"])
            else:
                self.notify("Usage: /model OR /model <provider> <model_name>", severity="error")

        elif command == "prompts":
            self.action_select_prompt()
            
        elif command == "clear":
             # Clear history and reset CLI session
             self.current_cli_block = None
             self.current_cli_widget = None
             history = self.query_one("#history", HistoryViewport)
             await history.remove_children()
             
        elif command == "export":
            # Export conversation: /export [md|json]
            format = args[0] if args else "md"
            if format not in ("md", "json", "markdown"):
                self.notify("Usage: /export [md|json]", severity="error")
                return
            if format == "markdown":
                format = "md"
            self._do_export(format)

        elif command == "session":
            # Session management: /session [save|load|list|new] [name]
            if not args:
                self.notify("Usage: /session [save|load|list|new] [name]", severity="warning")
                return

            subcommand = args[0]
            name = args[1] if len(args) > 1 else None
            storage = Config._get_storage()

            if subcommand == "save":
                filepath = storage.save_session(self.blocks, name)
                self.notify(f"Session saved to {filepath}")

            elif subcommand == "load":
                if name:
                    blocks = storage.load_session(name)
                    if blocks:
                        # Clear current and load
                        self.blocks = blocks
                        self.current_cli_block = None
                        self.current_cli_widget = None
                        history = self.query_one("#history", HistoryViewport)
                        await history.remove_children()
                        for block in self.blocks:
                            block.is_running = False
                            block_widget = BlockWidget(block)
                            await history.mount(block_widget)
                        history.scroll_end(animate=False)
                        self.notify(f"Loaded session: {name}")
                    else:
                        self.notify(f"Session not found: {name}", severity="error")
                else:
                    # Show session list for selection
                    sessions = storage.list_sessions()
                    if sessions:
                        names = [s["name"] for s in sessions]
                        from screens import SelectionListScreen

                        def on_select(selected):
                            if selected:
                                # Run load with selected name
                                self.call_later(lambda: self.run_worker(self.handle_slash_command(f"/session load {selected}")))

                        self.push_screen(SelectionListScreen("Load Session", names), on_select)
                    else:
                        self.notify("No saved sessions found", severity="warning")

            elif subcommand == "list":
                sessions = storage.list_sessions()
                if sessions:
                    lines = []
                    for s in sessions:
                        saved_at = s.get("saved_at", "")[:16].replace("T", " ")
                        blocks = s.get("block_count", 0)
                        lines.append(f"  {s['name']:20} {saved_at:16} ({blocks} blocks)")
                    content = "\n".join(lines)
                    await self._show_system_output("/session list", content)
                else:
                    self.notify("No saved sessions", severity="warning")

            elif subcommand == "new":
                # Clear and start fresh
                self.blocks = []
                self.current_cli_block = None
                self.current_cli_widget = None
                storage.clear_current_session()
                history = self.query_one("#history", HistoryViewport)
                await history.remove_children()
                self.notify("Started new session")

            else:
                self.notify("Usage: /session [save|load|list|new] [name]", severity="error")

        elif command == "status":
            # Show current status in a system block
            provider = self.config.get("ai", {}).get("provider", "none")
            model = self.config.get("ai", {}).get("model", "none")
            persona = self.config.get("ai", {}).get("active_prompt", "default")
            blocks_count = len(self.blocks)

            from context import ContextManager
            context_str = ContextManager.get_context(self.blocks)
            context_chars = len(context_str)
            context_tokens = context_chars // 4

            status_bar = self.query_one("#status-bar", StatusBar)
            provider_status = status_bar.provider_status

            lines = [
                f"  Provider:      {provider} ({provider_status})",
                f"  Model:         {model}",
                f"  Persona:       {persona}",
                f"  Blocks:        {blocks_count}",
                f"  Context:       ~{context_tokens} tokens ({context_chars} chars)",
            ]
            await self._show_system_output("/status", "\n".join(lines))

        elif command == "quit" or command == "exit":
            self.exit()
        else:
            self.notify(f"Unknown command: {command}", severity="warning")


    async def execute_ai(self, prompt: str, block_state: BlockState, widget: BlockWidget):
        """Worker to execute AI generation."""
        try:
            from context import ContextManager # Lazy import
            
            # Helper to get system prompt
            prompts = self.config.get("ai", {}).get("prompts", {})
            active_key = self.config.get("ai", {}).get("active_prompt", "default")
            system_prompt = prompts.get(active_key, prompts.get("default", ""))

            # Gather context
            # We used to slice [:-2] when we added 2 blocks (Query + ResponsePlaceholder).
            # Now we only add 1 block (Combined).
            # So we should exclude the *current* block, which is the last one [:-1].
            context_str = ContextManager.get_context(self.blocks[:-1])
            
            # Store metadata
            block_state.metadata = {
                "model": f"{self.config['ai']['provider']}/{self.config['ai']['model']}",
                "context": f"{len(context_str)} chars",
                "persona": active_key
            }
            # Update widget header if possible? Widget reads block. 
            # If we update block metadata, we might need to tell widget to refresh header.
            # But widget is created with block. 
            # We can expose a refresh method on widget or just access header.
            if widget:
                widget.update_metadata()
            
            full_response = ""
            
            # Streaming generation
            # Provider needs to handle system_prompt.
            # We can prepend it to context OR update provider interface.
            # Modifying interface is cleaner but requires touching all files.
            # Prepending to context is easier for now:
            # effective_context = f" System Instruction: {system_prompt}\n\n{context_str}"
            # Actually, most providers (Ollama, OpenAI) take system prompts in messages.
            # Let's pass it as a kwargs or separate arg if generate supports it.
            # I will update generate signature in base and all providers.
            async for chunk in self.ai_provider.generate(prompt, context_str, system_prompt=system_prompt):
                # Check for cancellation
                if self._ai_cancelled:
                    full_response += "\n\n[Cancelled]"
                    block_state.content_output = full_response
                    widget.update_output(full_response)
                    break

                full_response += chunk
                block_state.content_output = full_response
                widget.update_output(full_response)

            block_state.is_running = False
            self._active_worker = None

            # Update metadata with token estimate (rough: ~4 chars per token)
            response_tokens = len(full_response) // 4
            context_tokens = len(context_str) // 4
            block_state.metadata["tokens"] = f"~{response_tokens} out / ~{context_tokens} ctx"
            widget.update_metadata()

            widget.set_loading(False)

            # Auto-save session
            self._auto_save()

            # Post-generation: Check for Agentic Command
            # Parser for Markdown Code Blocks
            # We look for ```bash ... ``` or ```sh ... ```
            import re
            # Matches ```(bash|sh|console|shell)\n(content)\n```
            # Allow permissive whitespace around language
            code_block_match = re.search(r"```\s*(bash|sh|console|shell)\s+\n?(.*?)```", full_response, re.DOTALL)
            
            command_to_run = None
            if code_block_match:
                command_to_run = code_block_match.group(2).strip()
            else:
                 # Fallback to [COMMAND] tag just in case
                 tag_match = re.search(r"\[COMMAND\](.*?)\[/COMMAND\]", full_response, re.DOTALL)
                 if tag_match:
                     command_to_run = tag_match.group(1).strip()

            if command_to_run:
                self.notify(f"🤖 Agent requested execution: {command_to_run}")
                # We are already on the main thread (async worker), so call_later is sufficient/correct
                self.call_later(self.run_agent_command, command_to_run, block_state, widget)
            
        except asyncio.CancelledError:
            block_state.content_output += "\n\n[Cancelled]"
            block_state.is_running = False
            widget.update_output(block_state.content_output)
            widget.set_loading(False)
            self._active_worker = None
        except Exception as e:
            block_state.content_output = f"AI Error: {str(e)}"
            block_state.is_running = False
            widget.update_output(f"Error: {str(e)}")
            self._active_worker = None

    def run_agent_command(self, command: str, ai_block: BlockState, ai_widget: BlockWidget):
        """Execute a command requested by the Agent, executing INLINE."""
        
        # Append status
        status_msg = f"\n\n> 🤖 **Executing:** `{command}`...\n"
        # We can put this in exec output temporarily or thinking?
        # Let's put it in thinking to show transition.
        # DEBUG: Temporarily disable appending to thinking to see if it fixes "jumbling"
        # ai_block.content_output += status_msg
        # ai_widget.update_output(ai_block.content_output)
        
        async def run_inline():
            try:
                output_buffer = []
                def callback(line):
                    output_buffer.append(line)
                    # Stream update
                    current_text = "".join(output_buffer)
                    ai_block.content_exec_output = f"\n```text\n{current_text}\n```\n"
                    # Describe the update on the main thread via call_from_thread just in case?
                    # Textual apps are not thread safe if modifying widgets from threads.
                    # But run_worker runs in the same event loop usually.
                    # However, read_line await is async.
                    # Let's try direct update first.
                    ai_widget.update_output("")

                
                # Execute
                rc = await self.executor.run_command_and_get_rc(command, callback)
                
                output_text = "".join(output_buffer)
                
                if not output_text.strip():
                     output_text = "(Command execution completed with no output)"
                
                # Append Output
                result_md = f"\n```text\n{output_text}\n```\n"
                if rc != 0:
                    result_md += f"\n*Exit Code: {rc}*\n"
                
                # Final store
                ai_block.content_exec_output = result_md
                
                # Trigger widget update
                # We need to manually call update_output (or a specific method)
                # Our widget.update_output implementation now looks at block state.
                ai_widget.update_output("") # Argument ignored for AI_RESPONSE in new logic
                
            except Exception as e:
                err_msg = f"\n**Error Running Command:** {str(e)}\n"
                ai_block.content_exec_output = err_msg
                ai_widget.update_output("")
                self.notify(f"Agent Execution Error: {e}", severity="error")
            finally:
                # Stop loading
                ai_widget.set_loading(False)
                ai_block.is_running = False
            
        self.run_worker(run_inline())

    async def execute_block(self, block: BlockState, widget: BlockWidget):
        """Helper to run the command and update the widget."""

        # Callback to update the widget interface from the executor stream
        def update_callback(line: str):
            # Accumulate output to block state
            block.content_output += line
            # Update widget display
            widget.update_output()

        # Non-blocking run
        exit_code = await self.executor.run_command_and_get_rc(block.content_input, update_callback)

        # Final update
        widget.set_exit_code(exit_code)

        # Auto-save session
        self._auto_save()

    async def execute_cli_append(self, cmd: str, block: BlockState, widget: BlockWidget):
        """Execute a command and append output to existing CLI block."""

        def update_callback(line: str):
            block.content_output += line
            widget.update_output()

        exit_code = await self.executor.run_command_and_get_rc(cmd, update_callback)

        # Show exit code inline if non-zero
        if exit_code != 0:
            block.content_output += f"[exit: {exit_code}]\n"
            widget.update_output()

        # Auto-save session
        self._auto_save()

    def action_clear_history(self):
        # Implementation for Phase 2, but stub shortcut is here
        pass

if __name__ == "__main__":
    app = NullApp()
    app.run()
