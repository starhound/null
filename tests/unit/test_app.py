"""Unit tests for app.py - NullApp class without full TUI mounting.

Tests focus on:
- Initialization and manager setup
- Helper methods (_get_prompt_text, _apply_cursor_settings, etc.)
- Action methods that can be called directly
- State management (is_busy, block management)
- Utility functions
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_managers():
    """Create mock managers for NullApp initialization."""
    mocks = {}

    # AIManager
    mock_ai_manager = MagicMock()
    mock_ai_manager.get_active_provider.return_value = None
    mock_ai_manager.get_provider.return_value = None
    mock_ai_manager.list_all_models = AsyncMock(return_value={})
    mock_ai_manager._fetch_models_for_provider = AsyncMock(
        return_value=("test", [], None)
    )
    mock_ai_manager.close_all = AsyncMock()
    mocks["ai_manager"] = mock_ai_manager

    # MCPManager
    mock_mcp_manager = MagicMock()
    mock_mcp_manager.initialize = AsyncMock()
    mock_mcp_manager.get_all_tools.return_value = []
    mock_mcp_manager.get_status.return_value = {}
    mock_mcp_manager.clients = {}
    mocks["mcp_manager"] = mock_mcp_manager

    # ProcessManager
    mock_process_manager = MagicMock()
    mock_process_manager.get_count.return_value = 0
    mock_process_manager.is_running.return_value = False
    mock_process_manager.stop.return_value = False
    mock_process_manager.on_change = MagicMock()
    mock_process_manager.send_input = MagicMock()
    mocks["process_manager"] = mock_process_manager

    # StorageManager
    mock_storage = MagicMock()
    mock_storage.load_session.return_value = []
    mock_storage.save_current_session = MagicMock()
    mock_storage.get_config.return_value = "true"  # disclaimer_accepted
    mock_storage.set_config = MagicMock()
    mock_storage.get_last_history.return_value = []
    mocks["storage"] = mock_storage

    return mocks


@pytest.fixture
def mock_app_dependencies(mock_home, mock_managers, monkeypatch):
    """Set up all dependencies needed for NullApp instantiation."""
    monkeypatch.setattr("app.AIManager", lambda: mock_managers["ai_manager"])
    monkeypatch.setattr("app.MCPManager", lambda: mock_managers["mcp_manager"])
    monkeypatch.setattr("app.ProcessManager", lambda: mock_managers["process_manager"])

    monkeypatch.setattr("config.StorageManager", lambda: mock_managers["storage"])

    mock_config = MagicMock()
    mock_config.load_all.return_value = {
        "theme": "textual-dark",
        "shell": "/bin/bash",
        "ai": {
            "provider": "ollama",
            "model": "llama3.2",
            "endpoint": "",
            "api_key": "",
            "region": "",
            "agent_mode": False,
            "active_prompt": "default",
        },
    }
    mock_config.get.return_value = None
    mock_config._get_storage.return_value = mock_managers["storage"]
    monkeypatch.setattr("app.Config", mock_config)

    mock_settings = MagicMock()
    mock_settings.terminal.cursor_style = "block"
    mock_settings.terminal.cursor_blink = True
    mock_settings.terminal.auto_save_session = False
    mock_settings.terminal.auto_save_interval = 60
    mock_settings.terminal.confirm_on_exit = False
    mock_settings.terminal.clear_on_exit = False
    monkeypatch.setattr("app.get_settings", lambda: mock_settings)

    monkeypatch.setattr("app.get_all_themes", lambda: {})

    monkeypatch.setattr("tools.builtin.set_agent_manager", lambda x: None)

    return mock_managers, mock_config, mock_settings


@pytest.fixture
def null_app(mock_app_dependencies):
    """Create a NullApp instance without running it."""
    from app import NullApp

    app = NullApp()
    return app


@pytest.fixture
def null_app_with_mocks(null_app, mock_app_dependencies):
    """Return NullApp with access to its mocked dependencies."""
    managers, config, settings = mock_app_dependencies
    return null_app, managers, config, settings


# ---------------------------------------------------------------------------
# Test: Initialization
# ---------------------------------------------------------------------------


class TestNullAppInitialization:
    """Tests for NullApp.__init__() without full mounting."""

    def test_app_creates_successfully(self, null_app):
        """NullApp should instantiate without errors."""
        assert null_app is not None

    def test_app_has_managers(self, null_app):
        """NullApp should have all required managers."""
        assert null_app.ai_manager is not None
        assert null_app.mcp_manager is not None
        assert null_app.process_manager is not None
        assert null_app.branch_manager is not None
        assert null_app.agent_manager is not None
        assert null_app.plan_manager is not None
        assert null_app.error_detector is not None
        assert null_app.review_manager is not None
        assert null_app.suggestion_engine is not None

    def test_app_has_handlers(self, null_app):
        """NullApp should have all required handlers."""
        assert null_app.command_handler is not None
        assert null_app.execution_handler is not None
        assert null_app.input_handler is not None

    def test_app_initializes_blocks_list(self, null_app):
        """NullApp should have empty blocks list."""
        assert isinstance(null_app.blocks, list)
        assert len(null_app.blocks) == 0

    def test_app_initializes_cli_session_state(self, null_app):
        """NullApp should have None CLI session state."""
        assert null_app.current_cli_block is None
        assert null_app.current_cli_widget is None

    def test_app_initializes_ai_state(self, null_app):
        """NullApp should have initial AI state."""
        assert null_app._ai_cancelled is False
        assert null_app._active_worker is None

    def test_app_initializes_watch_mode_false(self, null_app):
        """NullApp should have watch mode disabled."""
        assert null_app._watch_mode is False

    def test_app_has_config_dict(self, null_app):
        """NullApp should have loaded config dictionary."""
        assert isinstance(null_app.config, dict)

    def test_app_has_storage(self, null_app):
        """NullApp should have storage manager."""
        assert null_app.storage is not None


# ---------------------------------------------------------------------------
# Test: Helper Methods
# ---------------------------------------------------------------------------


class TestGetPromptText:
    """Tests for NullApp._get_prompt_text() method."""

    def test_get_prompt_text_returns_string(self, null_app, monkeypatch):
        """_get_prompt_text should return a string."""
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))
        result = null_app._get_prompt_text()
        assert isinstance(result, str)

    def test_get_prompt_text_starts_with_dollar(self, null_app, monkeypatch):
        """_get_prompt_text should start with '$ '."""
        monkeypatch.setattr(Path, "cwd", lambda: Path("/tmp/test"))
        result = null_app._get_prompt_text()
        assert result.startswith("$ ")

    def test_get_prompt_text_shortens_home_directory(self, null_app, monkeypatch):
        """_get_prompt_text should replace home dir with ~."""
        home = Path("/home/testuser")
        cwd = Path("/home/testuser/projects/myapp")
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setattr(Path, "cwd", lambda: cwd)

        result = null_app._get_prompt_text()
        assert result == "$ ~/projects/myapp"

    def test_get_prompt_text_shows_full_path_outside_home(self, null_app, monkeypatch):
        """_get_prompt_text should show full path outside home."""
        home = Path("/home/testuser")
        cwd = Path("/var/log")
        monkeypatch.setattr(Path, "home", lambda: home)
        monkeypatch.setattr(Path, "cwd", lambda: cwd)

        result = null_app._get_prompt_text()
        assert result == "$ /var/log"

    def test_get_prompt_text_handles_exception(self, null_app, monkeypatch):
        """_get_prompt_text should return fallback on exception."""

        def raise_error():
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "cwd", raise_error)
        result = null_app._get_prompt_text()
        assert result == "$ ."


class TestApplyCursorSettings:
    """Tests for NullApp._apply_cursor_settings() method."""

    def test_apply_cursor_settings_calls_utility(
        self, null_app_with_mocks, monkeypatch
    ):
        """_apply_cursor_settings should call apply_cursor_settings utility."""
        app, _managers, _config, _settings = null_app_with_mocks

        mock_apply = MagicMock()
        monkeypatch.setattr("utils.terminal.apply_cursor_settings", mock_apply)

        mock_settings = MagicMock()
        mock_settings.terminal.cursor_style = "underline"
        mock_settings.terminal.cursor_blink = False
        monkeypatch.setattr("app.get_settings", lambda: mock_settings)

        app._apply_cursor_settings()

        mock_apply.assert_called_once_with(style="underline", blink=False)


# ---------------------------------------------------------------------------
# Test: State Methods
# ---------------------------------------------------------------------------


class TestIsBusy:
    """Tests for NullApp.is_busy() method."""

    def test_is_busy_false_when_no_workers_or_processes(self, null_app_with_mocks):
        """is_busy should return False when nothing running."""
        app, managers, _config, _settings = null_app_with_mocks
        managers["process_manager"].get_count.return_value = 0
        app._active_worker = None

        assert app.is_busy() is False

    def test_is_busy_true_when_process_running(self, null_app_with_mocks):
        """is_busy should return True when processes are running."""
        app, managers, _config, _settings = null_app_with_mocks
        managers["process_manager"].get_count.return_value = 1

        assert app.is_busy() is True

    def test_is_busy_true_when_worker_active(self, null_app_with_mocks):
        """is_busy should return True when worker is active."""
        app, managers, _config, _settings = null_app_with_mocks
        managers["process_manager"].get_count.return_value = 0

        mock_worker = MagicMock()
        mock_worker.is_finished = False
        app._active_worker = mock_worker

        assert app.is_busy() is True

    def test_is_busy_false_when_worker_finished(self, null_app_with_mocks):
        """is_busy should return False when worker is finished."""
        app, managers, _config, _settings = null_app_with_mocks
        managers["process_manager"].get_count.return_value = 0

        mock_worker = MagicMock()
        mock_worker.is_finished = True
        app._active_worker = mock_worker

        assert app.is_busy() is False


class TestUpdateProcessCount:
    """Tests for NullApp._update_process_count() method."""

    def test_update_process_count_handles_missing_widget(self, null_app_with_mocks):
        """_update_process_count should handle missing status bar gracefully."""
        app, _managers, _config, _settings = null_app_with_mocks
        # Should not raise - widgets aren't mounted
        app._update_process_count()


# ---------------------------------------------------------------------------
# Test: Export Functionality
# ---------------------------------------------------------------------------


class TestDoExport:
    """Tests for NullApp._do_export() method."""

    def test_do_export_warns_on_empty_blocks(self, null_app_with_mocks, monkeypatch):
        """_do_export should warn when blocks list is empty."""
        app, _managers, _config, _settings = null_app_with_mocks
        app.blocks = []

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        app._do_export("md")

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "Nothing to export" in call_args[0][0]
        assert call_args[1]["severity"] == "warning"

    def test_do_export_calls_save_export(self, null_app_with_mocks, monkeypatch):
        """_do_export should call save_export with blocks."""
        app, _managers, _config, _settings = null_app_with_mocks

        mock_block = MagicMock()
        app.blocks = [mock_block]

        mock_save = MagicMock(return_value="/tmp/export.md")
        monkeypatch.setattr("models.save_export", mock_save)

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        app._do_export("md")

        mock_save.assert_called_once_with([mock_block], "md")
        assert "Exported to /tmp/export.md" in mock_notify.call_args[0][0]

    def test_do_export_handles_exception(self, null_app_with_mocks, monkeypatch):
        """_do_export should notify on exception."""
        app, _managers, _config, _settings = null_app_with_mocks

        mock_block = MagicMock()
        app.blocks = [mock_block]

        def raise_error(*args, **kwargs):
            raise OSError("Disk full")

        monkeypatch.setattr("models.save_export", raise_error)

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        app._do_export("md")

        mock_notify.assert_called_once()
        assert "Export failed" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"


class TestAutoSave:
    """Tests for NullApp._auto_save() method."""

    def test_auto_save_saves_session(self, null_app_with_mocks):
        """_auto_save should call save_current_session."""
        app, managers, _config, _settings = null_app_with_mocks

        mock_block = MagicMock()
        app.blocks = [mock_block]

        # Mock _update_status_bar to avoid widget access
        app._update_status_bar = MagicMock()

        app._auto_save()

        managers["storage"].save_current_session.assert_called_once_with([mock_block])

    def test_auto_save_handles_exception(self, null_app_with_mocks):
        """_auto_save should handle exception gracefully."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["storage"].save_current_session.side_effect = Exception("DB error")

        app._auto_save()


# ---------------------------------------------------------------------------
# Test: Action Methods (cancel, quit, etc.)
# ---------------------------------------------------------------------------


class TestActionSmartQuit:
    """Tests for NullApp.action_smart_quit() method."""

    def test_smart_quit_cancels_when_busy(self, null_app_with_mocks, monkeypatch):
        """action_smart_quit should cancel operation when busy."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["process_manager"].get_count.return_value = 1

        mock_cancel = MagicMock()
        monkeypatch.setattr(app, "action_cancel_operation", mock_cancel)

        app.action_smart_quit()

        mock_cancel.assert_called_once()

    def test_smart_quit_quits_when_idle(self, null_app_with_mocks, monkeypatch):
        """action_smart_quit should quit when idle."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["process_manager"].get_count.return_value = 0
        app._active_worker = None

        mock_do_quit = MagicMock()
        monkeypatch.setattr(app, "_do_quit", mock_do_quit)

        app.action_smart_quit()

        mock_do_quit.assert_called_once()


class TestActionQuickExport:
    """Tests for NullApp.action_quick_export() method."""

    def test_quick_export_calls_do_export_with_md(
        self, null_app_with_mocks, monkeypatch
    ):
        """action_quick_export should call _do_export with 'md' format."""
        app, _managers, _config, _settings = null_app_with_mocks

        mock_do_export = MagicMock()
        monkeypatch.setattr(app, "_do_export", mock_do_export)

        app.action_quick_export()

        mock_do_export.assert_called_once_with("md")


class TestActionClearHistory:
    """Tests for NullApp.action_clear_history() method."""

    def test_clear_history_clears_blocks_directly(
        self, null_app_with_mocks, monkeypatch
    ):
        """action_clear_history should clear blocks and reset CLI state."""
        app, _managers, _config, _settings = null_app_with_mocks

        # Set up initial state
        mock_block = MagicMock()
        app.blocks = [mock_block]
        app.current_cli_block = MagicMock()
        app.current_cli_widget = MagicMock()

        # Mock notify to avoid widget access issues
        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        app.action_clear_history()

        # Verify blocks are cleared
        assert app.blocks == []
        # Verify CLI state is reset
        assert app.current_cli_block is None
        assert app.current_cli_widget is None
        # Verify user notification
        mock_notify.assert_called_once_with("History cleared")


# ---------------------------------------------------------------------------
# Test: Block Widget Finding
# ---------------------------------------------------------------------------


class TestFindWidgetForBlock:
    """Tests for NullApp._find_widget_for_block() method."""

    def test_find_widget_returns_none_when_not_mounted(
        self, null_app_with_mocks, monkeypatch
    ):
        """_find_widget_for_block should handle query errors gracefully."""
        app, _managers, _config, _settings = null_app_with_mocks

        # query_one will raise since widgets aren't mounted
        # But the method accesses query_one, so we mock it
        mock_history = MagicMock()
        mock_history.query.return_value = []

        def mock_query_one(*args, **kwargs):
            return mock_history

        monkeypatch.setattr(app, "query_one", mock_query_one)

        result = app._find_widget_for_block("some-block-id")

        assert result is None

    def test_find_widget_returns_matching_widget(
        self, null_app_with_mocks, monkeypatch
    ):
        """_find_widget_for_block should return matching widget."""
        app, _managers, _config, _settings = null_app_with_mocks

        # Create mock widgets
        mock_block1 = MagicMock()
        mock_block1.id = "block-1"
        mock_widget1 = MagicMock()
        mock_widget1.block = mock_block1

        mock_block2 = MagicMock()
        mock_block2.id = "block-2"
        mock_widget2 = MagicMock()
        mock_widget2.block = mock_block2

        mock_history = MagicMock()
        mock_history.query.return_value = [mock_widget1, mock_widget2]

        def mock_query_one(*args, **kwargs):
            return mock_history

        monkeypatch.setattr(app, "query_one", mock_query_one)

        result = app._find_widget_for_block("block-2")

        assert result is mock_widget2


# ---------------------------------------------------------------------------
# Test: Push Screen Wait
# ---------------------------------------------------------------------------


class TestPushScreenWait:
    """Tests for NullApp.push_screen_wait() method."""

    @pytest.mark.asyncio
    async def test_push_screen_wait_returns_future_result(
        self, null_app_with_mocks, monkeypatch
    ):
        """push_screen_wait should return the dismiss result."""
        app, _managers, _config, _settings = null_app_with_mocks

        expected_result = {"key": "value"}

        captured_callbacks: list = []

        def mock_push_screen(screen, callback):
            captured_callbacks.append(callback)

        monkeypatch.setattr(app, "push_screen", mock_push_screen)

        mock_screen = MagicMock()

        async def run_test():
            task = asyncio.create_task(app.push_screen_wait(mock_screen))
            await asyncio.sleep(0.01)
            captured_callbacks[0](expected_result)
            return await task

        result = await run_test()

        assert result == expected_result


# ---------------------------------------------------------------------------
# Test: Perform Exit
# ---------------------------------------------------------------------------


class TestPerformExit:
    """Tests for NullApp._perform_exit() method."""

    @pytest.mark.asyncio
    async def test_perform_exit_closes_ai_manager(self, null_app_with_mocks):
        """_perform_exit should close AI manager."""
        app, managers, _config, _settings = null_app_with_mocks

        # Mock exit
        app.exit = MagicMock()

        await app._perform_exit(clear_session=False)

        managers["ai_manager"].close_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_exit_clears_session_when_requested(
        self, null_app_with_mocks
    ):
        """_perform_exit should clear session when clear_session=True."""
        app, managers, _config, _settings = null_app_with_mocks

        # Mock exit
        app.exit = MagicMock()

        await app._perform_exit(clear_session=True)

        managers["storage"].save_current_session.assert_called_with([])

    @pytest.mark.asyncio
    async def test_perform_exit_calls_exit(self, null_app_with_mocks):
        """_perform_exit should call app.exit()."""
        app, _managers, _config, _settings = null_app_with_mocks

        app.exit = MagicMock()

        await app._perform_exit(clear_session=False)

        app.exit.assert_called_once()


# ---------------------------------------------------------------------------
# Test: Async Init Methods
# ---------------------------------------------------------------------------


class TestInitMCP:
    """Tests for NullApp._init_mcp() method."""

    @pytest.mark.asyncio
    async def test_init_mcp_initializes_manager(self, null_app_with_mocks):
        """_init_mcp should call mcp_manager.initialize()."""
        app, managers, _config, _settings = null_app_with_mocks

        await app._init_mcp()

        managers["mcp_manager"].initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_mcp_notifies_on_tools(self, null_app_with_mocks, monkeypatch):
        """_init_mcp should notify when tools are available."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["mcp_manager"].get_all_tools.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        await app._init_mcp()

        mock_notify.assert_called_once()
        assert "3 tools" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_init_mcp_handles_exception(self, null_app_with_mocks):
        """_init_mcp should handle exceptions gracefully."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["mcp_manager"].initialize.side_effect = Exception("Connection failed")

        await app._init_mcp()


class TestConnectNewMCPServer:
    """Tests for NullApp._connect_new_mcp_server() method."""

    @pytest.mark.asyncio
    async def test_connect_success_notifies(self, null_app_with_mocks, monkeypatch):
        """_connect_new_mcp_server should notify on success."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["mcp_manager"].connect_server = AsyncMock(return_value=True)

        mock_client = MagicMock()
        mock_client.tools = [MagicMock(), MagicMock()]
        managers["mcp_manager"].clients = {"test-server": mock_client}

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        await app._connect_new_mcp_server("test-server")

        mock_notify.assert_called_once()
        assert "Connected to test-server" in mock_notify.call_args[0][0]
        assert "2 tools" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_connect_failure_warns(self, null_app_with_mocks, monkeypatch):
        """_connect_new_mcp_server should warn on failure."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["mcp_manager"].connect_server = AsyncMock(return_value=False)

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        await app._connect_new_mcp_server("test-server")

        mock_notify.assert_called_once()
        assert "Failed to connect" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_connect_exception_errors(self, null_app_with_mocks, monkeypatch):
        """_connect_new_mcp_server should error on exception."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["mcp_manager"].connect_server = AsyncMock(
            side_effect=Exception("Timeout")
        )

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        await app._connect_new_mcp_server("test-server")

        mock_notify.assert_called_once()
        assert "Error connecting" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"


# ---------------------------------------------------------------------------
# Test: Update Header
# ---------------------------------------------------------------------------


class TestUpdateHeader:
    """Tests for NullApp._update_header() method."""

    def test_update_header_handles_missing_widget(self, null_app_with_mocks):
        """_update_header should handle missing header gracefully."""
        app, _managers, _config, _settings = null_app_with_mocks

        # Should not raise - widget not mounted
        app._update_header("openai", "gpt-4", connected=True)

    def test_update_header_calls_widget_method(self, null_app_with_mocks, monkeypatch):
        """_update_header should call header.set_provider()."""
        app, _managers, _config, _settings = null_app_with_mocks

        mock_header = MagicMock()

        def mock_query_one(selector, widget_type=None):
            if selector == "#app-header":
                return mock_header
            raise Exception("Not found")

        monkeypatch.setattr(app, "query_one", mock_query_one)

        app._update_header("anthropic", "claude-3", connected=True)

        mock_header.set_provider.assert_called_once_with("anthropic", "claude-3", True)


# ---------------------------------------------------------------------------
# Test: Check Provider Health
# ---------------------------------------------------------------------------


class TestCheckProviderHealth:
    """Tests for NullApp._check_provider_health() method."""

    @pytest.mark.asyncio
    async def test_check_health_updates_provider_reference(self, null_app_with_mocks):
        """_check_provider_health should refresh provider reference."""
        app, managers, _config, _settings = null_app_with_mocks

        mock_provider = MagicMock()
        mock_provider.model = "test-model"
        managers["ai_manager"].get_active_provider.return_value = mock_provider

        # Mock query_one to avoid widget errors
        mock_status_bar = MagicMock()

        def mock_query_one(*args, **kwargs):
            return mock_status_bar

        app.query_one = mock_query_one

        await app._check_provider_health()

        assert app.ai_provider is mock_provider

    @pytest.mark.asyncio
    async def test_check_health_handles_no_provider(
        self, null_app_with_mocks, monkeypatch
    ):
        """_check_provider_health should handle no active provider."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["ai_manager"].get_active_provider.return_value = None

        mock_status_bar = MagicMock()
        mock_update_header = MagicMock()

        def mock_query_one(*args, **kwargs):
            return mock_status_bar

        monkeypatch.setattr(app, "query_one", mock_query_one)
        monkeypatch.setattr(app, "_update_header", mock_update_header)

        await app._check_provider_health()

        mock_status_bar.set_provider.assert_called_with("No Provider", "disconnected")
        mock_update_header.assert_called_with("No Provider", "", connected=False)

    @pytest.mark.asyncio
    async def test_check_health_handles_exception(
        self, null_app_with_mocks, monkeypatch
    ):
        """_check_provider_health should handle exceptions."""
        app, _managers, _config, _settings = null_app_with_mocks

        def raise_error(*args, **kwargs):
            raise Exception("Query failed")

        monkeypatch.setattr(app, "query_one", raise_error)

        await app._check_provider_health()


# ---------------------------------------------------------------------------
# Test: Stop Process
# ---------------------------------------------------------------------------


class TestStopProcess:
    """Tests for NullApp._stop_process() method."""

    @pytest.mark.asyncio
    async def test_stop_process_calls_manager(self, null_app_with_mocks, monkeypatch):
        """_stop_process should call process_manager.stop()."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["process_manager"].stop.return_value = True

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        await app._stop_process("block-123")

        managers["process_manager"].stop.assert_called_with("block-123")
        mock_notify.assert_called_with("Process stopped", severity="warning")

    @pytest.mark.asyncio
    async def test_stop_process_resets_cli_session(
        self, null_app_with_mocks, monkeypatch
    ):
        """_stop_process should reset CLI session if matching block."""
        app, managers, _config, _settings = null_app_with_mocks

        mock_block = MagicMock()
        mock_block.id = "block-123"
        mock_block.is_running = True
        app.current_cli_block = mock_block

        mock_widget = MagicMock()
        app.current_cli_widget = mock_widget

        managers["process_manager"].stop.return_value = True

        app.notify = MagicMock()

        await app._stop_process("block-123")

        assert app.current_cli_block is None
        assert app.current_cli_widget is None
        mock_widget.set_loading.assert_called_with(False)
        assert mock_block.is_running is False

    @pytest.mark.asyncio
    async def test_stop_process_warns_when_no_process(
        self, null_app_with_mocks, monkeypatch
    ):
        """_stop_process should warn when no process to stop."""
        app, managers, _config, _settings = null_app_with_mocks

        managers["process_manager"].stop.return_value = False

        mock_notify = MagicMock()
        monkeypatch.setattr(app, "notify", mock_notify)

        await app._stop_process("block-123")

        mock_notify.assert_called_with("No process to stop", severity="warning")


# ---------------------------------------------------------------------------
# Test: Show Copy Feedback
# ---------------------------------------------------------------------------


class TestShowCopyFeedback:
    """Tests for NullApp._show_copy_feedback() method."""

    def test_show_copy_feedback_handles_missing_widget(self, null_app_with_mocks):
        """_show_copy_feedback should handle missing widgets gracefully."""
        app, _managers, _config, _settings = null_app_with_mocks

        # Should not raise - widget not mounted
        app._show_copy_feedback("block-123")

    def test_show_copy_feedback_calls_widget_method(
        self, null_app_with_mocks, monkeypatch
    ):
        """_show_copy_feedback should call action bar method."""
        app, _managers, _config, _settings = null_app_with_mocks

        from widgets.blocks.actions import ActionBar

        mock_action_bar = MagicMock(spec=ActionBar)
        mock_action_bar.block_id = "block-123"

        mock_history = MagicMock()
        mock_history.query.return_value = [mock_action_bar]

        def mock_query_one(*args, **kwargs):
            return mock_history

        monkeypatch.setattr(app, "query_one", mock_query_one)

        app._show_copy_feedback("block-123")

        mock_action_bar.show_copy_feedback.assert_called_once()
