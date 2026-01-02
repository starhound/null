from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Input
import asyncio

from config import Config
from models import BlockState, BlockType
from widgets import InputController, HistoryViewport, BlockWidget, CommandSuggester
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
        min-height: 3;
        padding: 1;
        background: $surface;
        border-top: solid $surface-lighten-2;
    }

    InputController {
        width: 100%;
    }

    /* AI mode input styling */
    .ai-mode {
        border: solid $warning;
        background: $surface-darken-1;
    }

    .ai-mode:focus {
        border: solid $warning-lighten-1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_history", "Clear History"),
        ("f1", "open_help", "Help"),
        ("f2", "select_model", "Select Model"),
        ("f3", "select_theme", "Change Theme"),
        ("f4", "select_provider", "Select Provider"),
        ("ctrl+space", "toggle_ai", "Toggle AI Mode"),
        ("ctrl+t", "toggle_ai", "Toggle AI Mode"),
        ("ctrl+b", "toggle_ai", "Toggle AI Mode"),
        # Textual adds Ctrl+P automatically, removing manual binding to avoid duplicate in Footer
    ]
    
    # Removed manual get_system_commands override as it was causing issues.
    # Bindings above will populate the palette.

    def action_toggle_ai_mode(self):
        self.query_one("#input", InputController).toggle_mode()
        # Toggle Footer description? 
        # The mode property in input controller handles the message posting if needed, 
        # but the border change is enough visual cue.

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
        
        yield HistoryViewport(id="history")
        with Container(id="input-container"):
            input_widget = InputController(placeholder="Type a command...", id="input")
            # Load history
            history = Config._get_storage().get_last_history()
            input_widget.history = history
            yield input_widget
        yield Footer()

    async def on_input_changed(self, message: Input.Changed):
        # We check filter here or let InputController drive?
        # Let's keep filter update here as it's clean, but key handling moves.
        suggester = self.query_one("#suggester", CommandSuggester)
        suggester.update_filter(message.value)


    async def on_input_submitted(self, message: InputController.Submitted):
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
             
             # Run AI worker
             # We pass the same block/widget for both purposes
             self.run_worker(self.execute_ai(cmd_text, block, block_widget))
             
        else:
            # CLI Mode Logic
            # Create new Block State
            block = BlockState(
                type=BlockType.COMMAND,
                content_input=cmd_text
            )
            self.blocks.append(block)

            # Clear input
            input_ctrl.value = ""

            # Create and Add Block Widget to History
            history_vp = self.query_one("#history", HistoryViewport)
            block_widget = BlockWidget(block)
            await history_vp.mount(block_widget)
            block_widget.scroll_visible() # Auto-scroll to new block

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
             # Implementation for clear history widget visual only
             history = self.query_one("#history", HistoryViewport)
             await history.remove_children()
             
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
                full_response += chunk
                block_state.content_output = full_response
                # Update widget with just the chunk as it appends
                widget.update_output(full_response)

            block_state.is_running = False

            # Update metadata with token estimate (rough: ~4 chars per token)
            response_tokens = len(full_response) // 4
            context_tokens = len(context_str) // 4
            block_state.metadata["tokens"] = f"~{response_tokens} out / ~{context_tokens} ctx"
            widget.update_metadata()

            widget.set_loading(False)

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
            
        except Exception as e:
            block_state.content_output = f"AI Error: {str(e)}"
            block_state.is_running = False
            widget.update_output(f"Error: {str(e)}")

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

    def action_clear_history(self):
        # Implementation for Phase 2, but stub shortcut is here
        pass

if __name__ == "__main__":
    app = NullApp()
    app.run()
