from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer
import asyncio

from config import Config
from models import BlockState, BlockType
from widgets import InputController, HistoryViewport, BlockWidget
from executor import ExecutionEngine

from ai.factory import AIFactory
from screens import HelpScreen, ModelListScreen

class NullApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #input-container {
        height: 3;
        padding: 0 1; 
        background: $surface;
    }

    InputController {
        width: 100%;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_history", "Clear History"),
        ("f1", "open_help", "Help"),
        ("f2", "select_model", "Select Model"),
        ("f3", "select_theme", "Change Theme"),
        ("f4", "select_provider", "Select Provider"),
        ("ctrl+p", "command_palette", "Palette"), 
    ]
    
    # Removed manual get_system_commands override as it was causing issues.
    # Bindings above will populate the palette.

    def action_open_help(self):
        """Show the help screen."""
        self.push_screen(HelpScreen())

    def action_select_provider(self):
        """Switch and configure AI Provider."""
        providers = ["ollama", "openai", "lm_studio", "azure", "bedrock", "xai"]
        
        def on_provider_selected(provider_name):
            if not provider_name:
                return
            
            # Now show config screen
            # Load existing config for this provider if any
            # Note: config structure right now is flat under 'ai'. 
            # We should probably store per-provider config?
            # For MVP, we just overwrite the 'ai' keys.
            current = self.config.get("ai", {})
            
            # Pre-fill if we are editing the currently active provider, otherwise empty?
            # User might want to switch back to openai and keep key.
            # Ideally Config should store `ai.openai.api_key`, `ai.ollama.endpoint`.
            # But Config.load_all() currently flattens it.
            # Let's assume we just ask every time for now or read standard keys if I updated Config.
            # To respect "Secure" storage, we can't easily peek all keys without `get_config`.
            
            from screens import ProviderConfigScreen
            
            def on_config_saved(result):
                if result:
                    # Save all
                    Config.update_key(["ai", "provider"], provider_name)
                    for k, v in result.items():
                        if v: # Only save if not empty
                            Config.update_key(["ai", k], v)
                    
                    self.notify(f"Provider switched to {provider_name}")
                    # Re-init
                    self.config = Config.load_all()
                    try:
                        self.ai_provider = AIFactory.get_provider(self.config["ai"])
                    except Exception as e:
                        self.notify(f"Error initializing provider: {e}", severity="error")

            self.push_screen(ProviderConfigScreen(provider_name, current), on_config_saved)

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
        yield HistoryViewport(id="history")
        with Container(id="input-container"):
            input_widget = InputController(placeholder="Type a command...", id="input")
            # Load history
            history = Config._get_storage().get_last_history()
            input_widget.history = history
            yield input_widget
        yield Footer()

    async def on_input_submitted(self, message: InputController.Submitted):
        if not message.value.strip():
            return
            
        cmd_text = message.value
        
        # Add to widgets history
        input_ctrl = self.query_one("#input", InputController)
        input_ctrl.add_to_history(cmd_text)

        # Persist to DB
        Config._get_storage().add_history(cmd_text)

        # Slash Command Handling
        if cmd_text.startswith("/"):
            await self.handle_slash_command(cmd_text)
            self.query_one("#input", InputController).value = ""
            return

        # Create new Block State
        block = BlockState(
            type=BlockType.COMMAND,
            content_input=cmd_text
        )
        self.blocks.append(block)

        # Clear input
        self.query_one("#input", InputController).value = ""

        # Create and Add Block Widget to History
        history = self.query_one("#history", HistoryViewport)
        block_widget = BlockWidget(block)
        await history.mount(block_widget)
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
            
        elif command == "clear":
             # Implementation for clear history widget visual only
             history = self.query_one("#history", HistoryViewport)
             await history.remove_children()
             
        elif command == "quit" or command == "exit":
            self.exit()
        else:
            self.notify(f"Unknown command: {command}", severity="warning")


    async def execute_block(self, block: BlockState, widget: BlockWidget):
        """Helper to run the command and update the widget."""
        
        # Callback to update the widget interface from the executor stream
        def update_callback(line: str):
            # We must schedule the update on the main thread/loop if we were outside of it,
            # but run_worker runs in asyncio context where we can modify properties unless
            # threading is involved. Textual is async-native.
            # However, `ExecutionEngine` logic might run blocking if not carefully designed,
            # but ours is using asyncio.create_subprocess_shell.
            
            # Since ExecutionEngine calls this callback, let's update the widget.
            # Safe to update reactive properties directly as we are on the main loop.
            widget.update_output(line)

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
