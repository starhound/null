"""Main application module for Null terminal."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from textual.worker import Worker

from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Label, TextArea, DirectoryTree

from ai.factory import AIFactory
from ai.manager import AIManager
from config import Config, get_settings
from handlers import ExecutionHandler, InputHandler, SlashCommandHandler
from managers import ProcessManager, BranchManager

# from executor import ExecutionEngine  # Removed global import
from mcp import MCPManager
from models import BlockState, BlockType
from screens import ConfirmDialog, HelpScreen, ModelListScreen
from themes import get_all_themes
from widgets import (
    AppHeader,
    BaseBlockWidget,
    BlockSearch,
    create_block,
    CommandPalette,
    CommandSuggester,
    HistorySearch,
    HistoryViewport,
    InputController,
    StatusBar,
)

# For backwards compatibility
BlockWidget = create_block


class NullApp(App):
    """Main Null terminal application."""

    CSS_PATH = "styles/main.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "cancel_operation", "Cancel"),
        ("escape", "cancel_operation", "Cancel"),
        # ("ctrl+c", "smart_quit", "Quit"),  # Handled in on_key to allow terminal capture
        ("ctrl+l", "clear_history", "Clear History"),
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
        ("ctrl+backslash", "toggle_file_tree", "Files"),
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
        from config import StorageManager

        self.storage = StorageManager()

        # self.executor removed - executor is now per-process
        self.process_manager = ProcessManager()
        self.branch_manager = BranchManager()

        # CLI session tracking
        self.current_cli_block: BlockState | None = None
        self.current_cli_widget: BaseBlockWidget | None = None

        # AI state
        self._ai_cancelled = False
        self._active_worker: Worker | None = None

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
        yield AppHeader(id="app-header")
        yield CommandSuggester(id="suggester")
        yield CommandPalette(id="command-palette")

        with Horizontal(id="main-area"):
            tree = DirectoryTree(".", id="file-tree")
            tree.display = False
            yield tree
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

    async def push_screen_wait(self, screen) -> Any:
        """Push a screen and wait for it to be dismissed with a result."""
        future: asyncio.Future[Any] = asyncio.Future()

        def on_dismiss(result: Any) -> None:
            if not future.done():
                future.set_result(result)

        self.push_screen(screen, on_dismiss)
        return await future

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def on_mount(self):
        """Load previous session on startup."""
        # Check for first-run disclaimer
        storage = Config._get_storage()
        if not storage.get_config("disclaimer_accepted"):
            from screens import DisclaimerScreen

            def on_disclaimer_accepted(accepted: bool | None):
                if accepted:
                    storage.set_config("disclaimer_accepted", "true")
                else:
                    # User didn't accept - exit the app
                    self.exit()

            self.push_screen(DisclaimerScreen(), on_disclaimer_accepted)

        saved_blocks = storage.load_session()

        if saved_blocks:
            self.blocks = saved_blocks
            history_vp = self.query_one("#history", HistoryViewport)
            for block in self.blocks:
                block.is_running = False
                block_widget = BlockWidget(block)
                await history_vp.add_block(block_widget)
            history_vp.scroll_end(animate=False)
            self.notify(f"Restored {len(saved_blocks)} blocks from previous session")

        self._update_status_bar()

        # Initial provider/header update - use run_worker for async
        self.run_worker(self._check_provider_health())

        # Periodic health check
        self.set_interval(30, self._check_provider_health)

        # Initialize MCP
        self.run_worker(self._init_mcp())

        # Auto-detect model for local providers
        self.run_worker(self._detect_local_model())

        # Register process manager callback
        self.process_manager.on_change(self._update_process_count)

        # Apply cursor settings from config
        self._apply_cursor_settings()

        # Auto-focus the input prompt
        self.query_one("#input", InputController).focus()

        # Set up periodic auto-save if enabled
        settings = get_settings()
        if settings.terminal.auto_save_session:
            self.set_interval(settings.terminal.auto_save_interval, self._auto_save)

    def _apply_cursor_settings(self):
        """Apply cursor style and blink settings from config."""
        from utils.terminal import apply_cursor_settings

        settings = get_settings()
        apply_cursor_settings(
            style=settings.terminal.cursor_style, blink=settings.terminal.cursor_blink
        )

    async def on_key(self, event) -> None:
        """Handle global key events."""
        if event.key == "ctrl+c":
            self.action_smart_quit()

    def _update_process_count(self):
        """Update process count in status bar."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            count = self.process_manager.get_count()
            status_bar.set_process_count(count)
        except Exception:
            pass

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
            _, models, _ = await self.ai_manager._fetch_models_for_provider(
                provider_name
            )

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

        # Determine target process to stop
        target_block_id = None

        # 1. Check if a specific block is focused
        focused = self.screen.focused
        if focused is not None and hasattr(focused, "block_id"):  # TerminalBlock
            target_block_id = getattr(focused, "block_id", None)
        elif focused is not None and hasattr(
            focused, "block"
        ):  # CommandBlock/BlockWidget
            block = getattr(focused, "block", None)
            if block:
                target_block_id = block.id

        # 2. Fallback to current CLI session block
        if not target_block_id and self.current_cli_block:
            target_block_id = self.current_cli_block.id

        # Stop specific process if identified
        if target_block_id and self.process_manager.is_running(target_block_id):
            if self.process_manager.stop(target_block_id):
                cancelled = True

        # Only stop all if we really assume that's what Ctrl+C means globally?
        # No, 'stop all' is dangerous.
        # If nothing stopped and we have active processes, maybe we should warn?
        # For now, let's strictly stop only what's in context.

        # Reset CLI session
        if self.current_cli_widget:
            self.current_cli_widget.set_loading(False)
        if self.current_cli_block:
            self.current_cli_block.is_running = False
        self.current_cli_block = None
        self.current_cli_widget = None

        if self._active_worker and not self._active_worker.is_finished:
            self._ai_cancelled = True
            self._active_worker.cancel()
            cancelled = True

        if cancelled:
            self.notify("Operation cancelled", severity="warning")

    def action_smart_quit(self):
        """Smart Ctrl+C: Cancel if busy, quit if idle."""
        if self.is_busy():
            self.action_cancel_operation()
        else:
            self._do_quit()

    def _do_quit(self):
        """Handle quit with confirm_on_exit and clear_on_exit settings."""
        settings = get_settings()

        if settings.terminal.confirm_on_exit:
            # Show confirmation dialog
            async def on_confirm(confirmed: bool | None):
                if confirmed:
                    await self._perform_exit(settings.terminal.clear_on_exit)

            self.push_screen(
                ConfirmDialog(
                    title="Confirm Exit", message="Are you sure you want to quit?"
                ),
                on_confirm,
            )
        else:
            self.run_worker(self._perform_exit(settings.terminal.clear_on_exit))

    async def _perform_exit(self, clear_session: bool):
        """Perform the actual exit, optionally clearing the session."""
        if hasattr(self, "ai_manager"):
            await self.ai_manager.close_all()

        if clear_session:
            try:
                # Clear the saved session
                Config._get_storage().save_current_session([])
            except Exception:
                pass
        self.exit()

    def is_busy(self) -> bool:
        """Check if any operation is currently running."""
        worker_active = (
            self._active_worker is not None and not self._active_worker.is_finished
        )
        return self.process_manager.get_count() > 0 or worker_active

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

                    try:
                        # Refresh config loading
                        self.config = Config.load_all()

                        # Re-initialize the specific provider through the manager
                        # This ensures the manager has the latest instance
                        self.ai_manager.get_provider(provider_name)

                        # Update raw pointer for legacy support
                        self.ai_provider = self.ai_manager.get_provider(provider_name)
                    except Exception as e:
                        self.notify(
                            f"Error initializing provider: {e}", severity="error"
                        )

            self.push_screen(
                ProviderConfigScreen(provider_name, current_conf), on_config_saved
            )

        from screens import SelectionListScreen

        self.push_screen(
            SelectionListScreen("Select Provider", providers), on_provider_selected
        )

    def action_toggle_file_tree(self):
        try:
            tree = self.query_one("#file-tree", DirectoryTree)
            tree.display = not tree.display
            if tree.display:
                tree.focus()
            else:
                self.query_one("#input", InputController).focus()
        except Exception:
            pass

    def action_select_model(self):
        """Select an AI model from ALL providers."""

        def on_model_select(selection):
            if selection:
                provider_name, model_name = selection

                # Normalize provider name
                provider_name = provider_name.lower()

                # Check if we need to switch active provider
                current_provider = Config.get("ai.provider", "").lower()

                if provider_name != current_provider:
                    Config.set("ai.provider", provider_name)
                    # Also sync to JSON settings
                    from config import SettingsManager

                    SettingsManager().set("ai", "provider", provider_name)
                    self.notify(f"Switched provider to {provider_name}")

                # Update the model for that provider
                Config.set(f"ai.{provider_name}.model", str(model_name))
                self.notify(f"Model set to {model_name}")

                # Force refresh of provider instance
                self.ai_provider = self.ai_manager.get_provider(provider_name)
                # Ensure the provider instance knows its model (some store it internally)
                if self.ai_provider:
                    self.ai_provider.model = str(model_name)

                self._update_status_bar()
                self._update_header(provider_name, str(model_name), connected=True)

        # Show screen immediately with async fetch
        self.push_screen(
            ModelListScreen(fetch_func=self.ai_manager.list_all_models), on_model_select
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
        for key, name, _desc, is_user in prompts_list:
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

        self.push_screen(
            SelectionListScreen("Select Persona", display_items), on_prompt_select
        )

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

    async def on_command_palette_action_selected(
        self, message: CommandPalette.ActionSelected
    ):
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

    async def on_base_block_widget_retry_requested(
        self, message: BaseBlockWidget.RetryRequested
    ):
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

    async def on_base_block_widget_edit_requested(
        self, message: BaseBlockWidget.EditRequested
    ):
        """Handle edit button click."""
        input_ctrl = self.query_one("#input", InputController)
        input_ctrl.text = message.content
        input_ctrl.focus()
        if not input_ctrl.is_ai_mode:
            input_ctrl.toggle_mode()
        self.notify("Edit and resubmit your query")

    async def on_base_block_widget_copy_requested(
        self, message: BaseBlockWidget.CopyRequested
    ):
        """Handle copy button click."""
        try:
            import pyperclip

            pyperclip.copy(message.content)
            self.notify("Copied to clipboard")
        except ImportError:
            # Fallback: try to use xclip/xsel on Linux or pbcopy on macOS
            import asyncio
            import subprocess
            import sys

            try:
                if sys.platform == "darwin":
                    await asyncio.to_thread(
                        subprocess.run,
                        ["pbcopy"],
                        input=message.content.encode(),
                        check=True,
                    )
                else:
                    await asyncio.to_thread(
                        subprocess.run,
                        ["xclip", "-selection", "clipboard"],
                        input=message.content.encode(),
                        check=True,
                    )
                self.notify("Copied to clipboard")
            except Exception:
                self.notify("Failed to copy - install pyperclip", severity="error")
        except Exception as e:
            self.notify(f"Copy failed: {e}", severity="error")

    async def on_base_block_widget_fork_requested(
        self, message: BaseBlockWidget.ForkRequested
    ):
        """Handle fork button click to create a conversation branch."""
        block = next((b for b in self.blocks if b.id == message.block_id), None)
        if not block:
            self.notify("Block not found", severity="error")
            return

        # Create a fork point
        branch_name = f"fork-{block.id[:4]}-{datetime.now().strftime('%H%M')}"
        try:
            self.branch_manager.fork(branch_name, self.blocks, block.id)
            self.notify(f"Created branch: {branch_name}")

            # Switch UI to the new branch (for now, we just truncate the view)
            # In a full implementation, we'd clear history and re-mount blocks from branch
            self.blocks = list(self.branch_manager.branches[branch_name])

            # Refresh view
            history_vp = self.query_one("#history", HistoryViewport)
            await history_vp.query(BaseBlockWidget).remove()
            for b in self.blocks:
                await history_vp.mount(create_block(b))
            history_vp.scroll_end()

        except Exception as e:
            self.notify(f"Fork failed: {e}", severity="error")

    async def on_code_block_widget_run_code_requested(self, message):
        """Handle run code button click from code blocks."""
        from widgets.blocks import execute_code

        code = message.code
        language = message.language

        self.notify(f"Running {language} code...")

        # Execute the code (output and exit_code unused - showing result handled elsewhere)
        await execute_code(code, language)

    async def on_code_block_widget_save_code_requested(self, message):
        """Handle save code button click from code blocks."""
        from screens import SaveFileDialog
        from widgets.blocks import get_file_extension

        code = message.code
        language = message.language

        # Suggest a filename based on language
        ext = get_file_extension(language)
        suggested_name = f"code{ext}"

        def on_saved(filepath):
            if filepath:
                self.notify(f"Code saved to {filepath}")

        self.push_screen(SaveFileDialog(suggested_name, code), on_saved)

    async def on_stop_button_pressed(self, message):
        """Handle stop button press from BlockFooter."""
        await self._stop_process(message.block_id)

    async def _stop_process(self, block_id: str):
        """Stop a running process by block ID."""
        stopped = False

        # Try to stop via process manager (executor cancellation happens inside stop if mapped)
        if self.process_manager.stop(block_id):
            stopped = True

        if stopped:
            self.notify("Process stopped", severity="warning")

            # Reset CLI session so new commands create new blocks
            if self.current_cli_block and self.current_cli_block.id == block_id:
                # Update the widget state
                if self.current_cli_widget:
                    self.current_cli_widget.set_loading(False)
                    self.current_cli_block.is_running = False
                self.current_cli_block = None
                self.current_cli_widget = None
        else:
            self.notify("No process to stop", severity="warning")

    async def on_terminal_block_input_requested(self, message):
        """Handle keyboard input from TUI terminal blocks."""

        block_id = message.block_id
        data = message.data

        # Send input to the process via process manager
        self.process_manager.send_input(block_id, data)

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

    def _update_header(
        self, provider: str, model: str = "", connected: bool = True
    ) -> None:
        """Update the app header with provider/model info and connectivity icon."""
        try:
            header = self.query_one("#app-header", AppHeader)
            header.set_provider(provider, model, connected)
        except Exception:
            pass

    async def _check_provider_health(self):
        """Check if AI provider is connected."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)

            # Refresh provider reference from manager
            if self.ai_manager:
                self.ai_provider = self.ai_manager.get_active_provider()

            # Update provider status and header
            if self.ai_provider:
                provider_name = Config.get("ai.provider") or "Provider"
                model_name = getattr(self.ai_provider, "model", "") or ""
                status_bar.set_provider(str(provider_name), "connected")
                self._update_header(str(provider_name), model_name, connected=True)
            else:
                status_bar.set_provider("No Provider", "disconnected")
                self._update_header("No Provider", "", connected=False)

            # Update MCP status
            active_mcp = 0
            if self.mcp_manager:
                status = self.mcp_manager.get_status()
                active_mcp = sum(1 for s in status.values() if s.get("connected"))

            status_bar.set_mcp_status(active_mcp)

            # Update process count
            status_bar.set_process_count(self.process_manager.get_count())

        except Exception:
            try:
                self.query_one(
                    "#status-bar", StatusBar
                ).provider_status = "disconnected"
                self._update_header("Error", "", connected=False)
            except Exception:
                pass

    def _find_widget_for_block(self, block_id: str) -> BaseBlockWidget | None:
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
            is_running=False,
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
        except Exception as e:
            self.log(f"Auto-save failed: {e}")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected):
        try:
            path = str(event.path)
            input_ctrl = self.query_one("#input", InputController)
            current = input_ctrl.value
            if current and not current.endswith(" "):
                input_ctrl.value += f" {path}"
            else:
                input_ctrl.value += path
            input_ctrl.focus()
        except Exception:
            pass


if __name__ == "__main__":
    app = NullApp()
    app.run()
