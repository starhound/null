"""Unit tests for commands/session.py - SessionCommands class."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.session import SessionCommands


@pytest.fixture
def mock_app():
    """Create a mock app with required attributes."""
    app = MagicMock()
    app.blocks = [MagicMock(), MagicMock()]
    app.current_cli_block = MagicMock()
    app.current_cli_widget = MagicMock()
    app._do_export = MagicMock()
    app.push_screen = MagicMock()
    app.call_later = MagicMock()
    app.run_worker = MagicMock()
    app.query_one = MagicMock()
    app.notify = MagicMock()
    return app


@pytest.fixture
def mock_storage():
    """Create a mock storage."""
    storage = MagicMock()
    storage.save_session = MagicMock(return_value="/path/to/session.json")
    storage.load_session = MagicMock(return_value=None)
    storage.list_sessions = MagicMock(return_value=[])
    storage.clear_current_session = MagicMock()
    return storage


@pytest.fixture
def session_commands(mock_app):
    """Create SessionCommands instance with mock app."""
    return SessionCommands(mock_app)


class TestSessionCommandsInit:
    """Tests for SessionCommands initialization."""

    def test_init_stores_app_reference(self):
        """SessionCommands should store app reference."""
        mock_app = MagicMock()
        commands = SessionCommands(mock_app)
        assert commands.app is mock_app


class TestCmdExport:
    """Tests for cmd_export method."""

    @pytest.mark.asyncio
    async def test_cmd_export_default_format_md(self, session_commands, mock_app):
        """cmd_export without args should default to md format."""
        await session_commands.cmd_export([])
        mock_app._do_export.assert_called_once_with("md")

    @pytest.mark.asyncio
    async def test_cmd_export_md_format(self, session_commands, mock_app):
        """cmd_export with 'md' should export as md."""
        await session_commands.cmd_export(["md"])
        mock_app._do_export.assert_called_once_with("md")

    @pytest.mark.asyncio
    async def test_cmd_export_json_format(self, session_commands, mock_app):
        """cmd_export with 'json' should export as json."""
        await session_commands.cmd_export(["json"])
        mock_app._do_export.assert_called_once_with("json")

    @pytest.mark.asyncio
    async def test_cmd_export_markdown_alias(self, session_commands, mock_app):
        """cmd_export with 'markdown' should normalize to 'md'."""
        await session_commands.cmd_export(["markdown"])
        mock_app._do_export.assert_called_once_with("md")

    @pytest.mark.asyncio
    async def test_cmd_export_invalid_format_shows_error(
        self, session_commands, mock_app
    ):
        """cmd_export with invalid format should show error."""
        with patch.object(session_commands, "notify") as mock_notify:
            await session_commands.cmd_export(["csv"])

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "Usage" in call_args[0][0]
        assert call_args[1]["severity"] == "error"
        mock_app._do_export.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_export_multiple_args_uses_first(
        self, session_commands, mock_app
    ):
        """cmd_export with multiple args should use first."""
        await session_commands.cmd_export(["json", "extra", "args"])
        mock_app._do_export.assert_called_once_with("json")


class TestCmdSession:
    """Tests for cmd_session method."""

    @pytest.mark.asyncio
    async def test_cmd_session_no_args_shows_usage(self, session_commands, mock_app):
        """cmd_session without args should show usage."""
        with patch.object(session_commands, "notify") as mock_notify:
            await session_commands.cmd_session([])

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "Usage" in call_args[0][0]
        assert call_args[1]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_cmd_session_unknown_subcommand_shows_error(
        self, session_commands, mock_app
    ):
        """cmd_session with unknown subcommand should show error."""
        with (
            patch("config.Config._get_storage"),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["unknown"])

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "Usage" in call_args[0][0]
        assert call_args[1]["severity"] == "error"


class TestCmdSessionSave:
    """Tests for session save subcommand."""

    @pytest.mark.asyncio
    async def test_cmd_session_save_without_name(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session save without name should save with auto-generated name."""
        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["save"])

        mock_storage.save_session.assert_called_once_with(mock_app.blocks, None)
        mock_notify.assert_called_once()
        assert "saved" in mock_notify.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_cmd_session_save_with_name(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session save with name should save with given name."""
        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["save", "my-session"])

        mock_storage.save_session.assert_called_once_with(mock_app.blocks, "my-session")
        mock_notify.assert_called_once()
        assert "/path/to/session.json" in mock_notify.call_args[0][0]


class TestCmdSessionLoad:
    """Tests for session load subcommand."""

    @pytest.mark.asyncio
    async def test_cmd_session_load_with_name_success(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load with valid name should load session."""
        mock_blocks = [MagicMock(is_running=True), MagicMock(is_running=True)]
        mock_storage.load_session.return_value = mock_blocks

        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_history.add_block = AsyncMock()
        mock_history.scroll_end = MagicMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch("widgets.create_block", return_value=MagicMock()),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["load", "my-session"])

        mock_storage.load_session.assert_called_once_with("my-session")
        assert mock_app.blocks == mock_blocks
        assert mock_app.current_cli_block is None
        assert mock_app.current_cli_widget is None
        mock_notify.assert_called_once()
        assert "Loaded session" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_session_load_with_name_not_found(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load with invalid name should show error."""
        mock_storage.load_session.return_value = None

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["load", "nonexistent"])

        mock_storage.load_session.assert_called_once_with("nonexistent")
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "not found" in call_args[0][0].lower()
        assert call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_cmd_session_load_without_name_shows_selection(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load without name should show session selection."""
        mock_storage.list_sessions.return_value = [
            {"name": "session1"},
            {"name": "session2"},
        ]

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch("screens.SelectionListScreen") as MockScreen,
        ):
            await session_commands.cmd_session(["load"])

        MockScreen.assert_called_once_with("Load Session", ["session1", "session2"])
        mock_app.push_screen.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_session_load_without_name_no_sessions(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load without name and no sessions should show warning."""
        mock_storage.list_sessions.return_value = []

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["load"])

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "No saved sessions" in call_args[0][0]
        assert call_args[1]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_cmd_session_load_resets_blocks_is_running(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load should set is_running=False on loaded blocks."""
        mock_block = MagicMock(is_running=True)
        mock_storage.load_session.return_value = [mock_block]

        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_history.add_block = AsyncMock()
        mock_history.scroll_end = MagicMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch("widgets.create_block", return_value=MagicMock()),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["load", "test"])

        assert mock_block.is_running is False

    @pytest.mark.asyncio
    async def test_cmd_session_load_handles_query_exception(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load should handle widget query exceptions gracefully."""
        mock_storage.load_session.return_value = [MagicMock()]
        mock_app.query_one.side_effect = Exception("Widget not found")

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            # Should not raise
            await session_commands.cmd_session(["load", "test"])

        # Should still notify about the load
        mock_notify.assert_called_once()
        assert "Loaded session" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_session_load_resets_status_bar(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session load should reset status bar token usage."""
        mock_storage.load_session.return_value = [MagicMock()]

        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_history.add_block = AsyncMock()
        mock_history.scroll_end = MagicMock()

        mock_status_bar = MagicMock()
        mock_status_bar.reset_token_usage = MagicMock()

        def query_side_effect(query):
            if query == "#history":
                return mock_history
            elif query == "#status-bar":
                return mock_status_bar
            raise Exception("Unknown query")

        mock_app.query_one.side_effect = query_side_effect

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch("widgets.create_block", return_value=MagicMock()),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["load", "test"])

        mock_status_bar.reset_token_usage.assert_called_once()


class TestCmdSessionList:
    """Tests for session list subcommand."""

    @pytest.mark.asyncio
    async def test_cmd_session_list_shows_sessions(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session list should display saved sessions."""
        mock_storage.list_sessions.return_value = [
            {
                "name": "session1",
                "saved_at": "2024-01-15T10:30:00",
                "block_count": 5,
            },
            {
                "name": "session2",
                "saved_at": "2024-01-16T14:45:00",
                "block_count": 12,
            },
        ]

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(
                session_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await session_commands.cmd_session(["list"])

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "session1" in output
        assert "session2" in output
        assert "5 blocks" in output
        assert "12 blocks" in output

    @pytest.mark.asyncio
    async def test_cmd_session_list_no_sessions(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session list with no sessions should show warning."""
        mock_storage.list_sessions.return_value = []

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["list"])

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "No saved sessions" in call_args[0][0]
        assert call_args[1]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_cmd_session_list_formats_dates(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session list should format dates properly."""
        mock_storage.list_sessions.return_value = [
            {
                "name": "test",
                "saved_at": "2024-01-15T10:30:45.123456",
                "block_count": 3,
            },
        ]

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(
                session_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await session_commands.cmd_session(["list"])

        output = mock_show.call_args[0][1]
        # Should truncate to 16 chars and replace T with space
        assert "2024-01-15 10:30" in output


class TestCmdSessionNew:
    """Tests for session new subcommand."""

    @pytest.mark.asyncio
    async def test_cmd_session_new_clears_blocks(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should clear blocks list."""
        mock_app.blocks = [MagicMock(), MagicMock()]

        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["new"])

        assert mock_app.blocks == []

    @pytest.mark.asyncio
    async def test_cmd_session_new_resets_cli_state(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should reset current CLI block and widget."""
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["new"])

        assert mock_app.current_cli_block is None
        assert mock_app.current_cli_widget is None

    @pytest.mark.asyncio
    async def test_cmd_session_new_clears_storage(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should clear current session in storage."""
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["new"])

        mock_storage.clear_current_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_session_new_removes_history_children(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should remove children from history widget."""
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["new"])

        mock_history.remove_children.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_session_new_resets_token_usage(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should reset status bar token usage."""
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()

        mock_status_bar = MagicMock()
        mock_status_bar.reset_token_usage = MagicMock()

        def query_side_effect(query):
            if query == "#history":
                return mock_history
            elif query == "#status-bar":
                return mock_status_bar
            raise Exception("Unknown query")

        mock_app.query_one.side_effect = query_side_effect

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify"),
        ):
            await session_commands.cmd_session(["new"])

        mock_status_bar.reset_token_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_session_new_notifies_user(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should notify user."""
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            await session_commands.cmd_session(["new"])

        mock_notify.assert_called_once()
        assert "Started new session" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_session_new_handles_query_exceptions(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should handle widget query exceptions gracefully."""
        mock_app.query_one.side_effect = Exception("Widget not found")

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify") as mock_notify,
        ):
            # Should not raise
            await session_commands.cmd_session(["new"])

        # Should still notify
        mock_notify.assert_called_once()
        assert "Started new session" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_session_new_status_bar_without_reset_method(
        self, session_commands, mock_app, mock_storage
    ):
        """cmd_session new should handle status bar without reset_token_usage."""
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()

        mock_status_bar = MagicMock(spec=[])  # No reset_token_usage method

        def query_side_effect(query):
            if query == "#history":
                return mock_history
            elif query == "#status-bar":
                return mock_status_bar
            raise Exception("Unknown query")

        mock_app.query_one.side_effect = query_side_effect

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(session_commands, "notify"),
        ):
            # Should not raise even without reset_token_usage
            await session_commands.cmd_session(["new"])


class TestSessionLoadSelectionCallback:
    """Tests for session load selection callback."""

    @pytest.mark.asyncio
    async def test_load_selection_callback_triggers_load(
        self, session_commands, mock_app, mock_storage
    ):
        """Selection callback should trigger session load."""
        mock_storage.list_sessions.return_value = [
            {"name": "session1"},
            {"name": "session2"},
        ]

        captured_callback = None

        def capture_push_screen(screen, callback=None):
            nonlocal captured_callback
            captured_callback = callback

        mock_app.push_screen.side_effect = capture_push_screen

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch("screens.SelectionListScreen"),
        ):
            await session_commands.cmd_session(["load"])

        # Simulate selection
        assert captured_callback is not None
        captured_callback("session1")

        # Verify call_later was invoked
        mock_app.call_later.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_selection_callback_ignores_none(
        self, session_commands, mock_app, mock_storage
    ):
        """Selection callback should ignore None selection (cancelled)."""
        mock_storage.list_sessions.return_value = [{"name": "session1"}]

        captured_callback = None

        def capture_push_screen(screen, callback=None):
            nonlocal captured_callback
            captured_callback = callback

        mock_app.push_screen.side_effect = capture_push_screen

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch("screens.SelectionListScreen"),
        ):
            await session_commands.cmd_session(["load"])

        # Simulate cancel (None selection)
        assert captured_callback is not None
        captured_callback(None)

        # Verify call_later was NOT invoked
        mock_app.call_later.assert_not_called()


class TestCommandMixinIntegration:
    """Tests for CommandMixin integration."""

    def test_inherits_command_mixin(self):
        """SessionCommands should inherit from CommandMixin."""
        from commands.base import CommandMixin

        assert issubclass(SessionCommands, CommandMixin)

    def test_has_notify_method(self):
        """SessionCommands should have notify method from mixin."""
        mock_app = MagicMock()
        commands = SessionCommands(mock_app)
        assert hasattr(commands, "notify")

    def test_has_show_output_method(self):
        """SessionCommands should have show_output method from mixin."""
        mock_app = MagicMock()
        commands = SessionCommands(mock_app)
        assert hasattr(commands, "show_output")

    def test_notify_delegates_to_app(self):
        """notify should delegate to app.notify."""
        mock_app = MagicMock()
        commands = SessionCommands(mock_app)

        commands.notify("test message", severity="warning")

        mock_app.notify.assert_called_once()
        args, kwargs = mock_app.notify.call_args
        assert args[0] == "test message"
        assert kwargs["severity"] == "warning"
