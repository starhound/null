"""Tests for widgets/input.py - InputController and GhostLabel widgets."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from widgets.input import GhostLabel, InputController


class TestGhostLabelInit:
    """Test GhostLabel initialization and CSS."""

    def test_default_css_sets_display_none(self):
        """GhostLabel should be hidden by default."""
        assert "display: none" in GhostLabel.DEFAULT_CSS

    def test_default_css_sets_transparent_background(self):
        """GhostLabel should have transparent background."""
        assert "background: transparent" in GhostLabel.DEFAULT_CSS

    def test_default_css_sets_overlay_layer(self):
        """GhostLabel should be on overlay layer."""
        assert "layer: overlay" in GhostLabel.DEFAULT_CSS

    def test_default_css_sets_gray_color(self):
        """GhostLabel should have gray color for ghost text."""
        assert "#666666" in GhostLabel.DEFAULT_CSS


class TestInputControllerInit:
    """Test InputController initialization."""

    def test_default_initialization(self):
        """InputController should initialize with defaults."""
        controller = InputController()
        assert controller.placeholder == ""
        assert controller.cmd_history == []
        assert controller.cmd_history_index == -1
        assert controller.current_input == ""
        assert controller.mode == "CLI"

    def test_custom_placeholder(self):
        """InputController should accept custom placeholder."""
        controller = InputController(placeholder="Enter command...")
        assert controller.placeholder == "Enter command..."

    def test_initial_mode_is_cli(self):
        """InputController should start in CLI mode."""
        controller = InputController()
        assert controller.mode == "CLI"
        assert not controller.is_ai_mode

    def test_show_line_numbers_disabled(self):
        """Line numbers should be disabled by default."""
        controller = InputController()
        assert controller.show_line_numbers is False

    def test_tab_behavior_is_indent(self):
        """Tab behavior should be indent by default."""
        controller = InputController()
        assert controller.tab_behavior == "indent"

    def test_theme_is_vscode_dark(self):
        """Theme should be vscode_dark by default."""
        controller = InputController()
        assert controller.theme == "vscode_dark"

    def test_ghost_label_created(self):
        """Ghost label should be created on init."""
        controller = InputController()
        assert controller.ghost_label is not None
        assert isinstance(controller.ghost_label, GhostLabel)

    def test_current_suggestion_empty(self):
        """Current suggestion should be empty initially."""
        controller = InputController()
        assert controller.current_suggestion == ""


class TestInputControllerValueProperty:
    """Test the value property for Input-like API compatibility."""

    def test_value_getter_returns_text(self):
        """value property should return text content."""
        controller = InputController()
        controller.text = "test command"
        assert controller.value == "test command"

    def test_value_setter_updates_text(self):
        """value setter should update text content."""
        controller = InputController()
        controller.value = "new command"
        assert controller.text == "new command"

    def test_value_empty_string(self):
        """value should handle empty string."""
        controller = InputController()
        controller.value = ""
        assert controller.value == ""
        assert controller.text == ""


class TestInputControllerIsAiMode:
    """Test is_ai_mode property."""

    def test_is_ai_mode_false_in_cli_mode(self):
        """is_ai_mode should be False in CLI mode."""
        controller = InputController()
        controller.mode = "CLI"
        assert controller.is_ai_mode is False

    def test_is_ai_mode_true_in_ai_mode(self):
        """is_ai_mode should be True in AI mode."""
        controller = InputController()
        controller.mode = "AI"
        assert controller.is_ai_mode is True


class TestInputControllerToggleMode:
    """Test mode toggling between CLI and AI."""

    def test_toggle_from_cli_to_ai(self):
        """toggle_mode should switch from CLI to AI."""
        controller = InputController()
        controller.post_message = MagicMock()

        controller.toggle_mode()

        assert controller.mode == "AI"
        assert controller.is_ai_mode is True

    def test_toggle_from_ai_to_cli(self):
        """toggle_mode should switch from AI to CLI."""
        controller = InputController()
        controller.mode = "AI"
        controller.post_message = MagicMock()

        controller.toggle_mode()

        assert controller.mode == "CLI"
        assert controller.is_ai_mode is False

    def test_toggle_adds_ai_mode_class(self):
        """Toggling to AI mode should add ai-mode class."""
        controller = InputController()
        controller.post_message = MagicMock()

        controller.toggle_mode()

        assert "ai-mode" in controller.classes

    def test_toggle_removes_ai_mode_class(self):
        """Toggling to CLI mode should remove ai-mode class."""
        controller = InputController()
        controller.post_message = MagicMock()
        controller.toggle_mode()  # To AI

        controller.toggle_mode()  # Back to CLI

        assert "ai-mode" not in controller.classes

    def test_toggle_updates_placeholder_to_ai(self):
        """Toggling to AI should update placeholder."""
        controller = InputController()
        controller.post_message = MagicMock()

        controller.toggle_mode()

        assert controller.placeholder == "Ask AI..."

    def test_toggle_updates_placeholder_to_cli(self):
        """Toggling to CLI should update placeholder."""
        controller = InputController()
        controller.post_message = MagicMock()
        controller.toggle_mode()

        controller.toggle_mode()

        assert controller.placeholder == "Type a command..."

    def test_toggle_posts_toggled_message(self):
        """toggle_mode should post Toggled message."""
        controller = InputController()
        controller.post_message = MagicMock()

        controller.toggle_mode()

        controller.post_message.assert_called()
        msg = controller.post_message.call_args[0][0]
        assert isinstance(msg, InputController.Toggled)
        assert msg.mode == "AI"


class TestInputControllerSubmittedMessage:
    """Test Submitted message class."""

    def test_submitted_message_stores_value(self):
        """Submitted message should store submitted value."""
        msg = InputController.Submitted("test command")
        assert msg.value == "test command"

    def test_submitted_message_empty_value(self):
        """Submitted message should handle empty value."""
        msg = InputController.Submitted("")
        assert msg.value == ""

    def test_submitted_message_multiline_value(self):
        """Submitted message should handle multiline value."""
        msg = InputController.Submitted("line1\nline2\nline3")
        assert msg.value == "line1\nline2\nline3"


class TestInputControllerToggledMessage:
    """Test Toggled message class."""

    def test_toggled_message_stores_mode(self):
        """Toggled message should store mode."""
        msg = InputController.Toggled("AI")
        assert msg.mode == "AI"

    def test_toggled_message_cli_mode(self):
        """Toggled message should handle CLI mode."""
        msg = InputController.Toggled("CLI")
        assert msg.mode == "CLI"


class TestInputControllerSubmit:
    """Test action_submit method."""

    def test_submit_posts_message_with_stripped_text(self):
        """Submit should post message with stripped text."""
        controller = InputController()
        controller.post_message = MagicMock()
        controller.text = "  test command  "

        controller.action_submit()

        controller.post_message.assert_called()
        msg = controller.post_message.call_args[0][0]
        assert isinstance(msg, InputController.Submitted)
        assert msg.value == "test command"

    def test_submit_does_not_post_empty_text(self):
        """Submit should not post message if text is empty."""
        controller = InputController()
        controller.text = "   "
        controller.post_message = MagicMock()

        controller.action_submit()

        for call in controller.post_message.call_args_list:
            msg = call[0][0]
            assert not isinstance(msg, InputController.Submitted)

    def test_submit_does_not_post_whitespace_only(self):
        """Submit should not post message if text is whitespace only."""
        controller = InputController()
        controller.text = "\n\t  \n"
        controller.post_message = MagicMock()

        controller.action_submit()

        for call in controller.post_message.call_args_list:
            msg = call[0][0]
            assert not isinstance(msg, InputController.Submitted)


class TestInputControllerNewline:
    """Test action_newline method."""

    def test_newline_inserts_newline(self):
        """action_newline should insert newline character."""
        controller = InputController()
        controller.insert = MagicMock()

        controller.action_newline()

        controller.insert.assert_called_once_with("\n")


class TestInputControllerClearToStart:
    """Test action_clear_to_start method."""

    def test_clear_to_start_deletes_from_cursor(self):
        """action_clear_to_start should delete from start to cursor."""
        controller = InputController()
        controller.text = "hello world"
        controller.move_cursor((0, 5))

        controller.action_clear_to_start()

        assert controller.text == " world"

    def test_clear_to_start_no_op_at_line_start(self):
        """action_clear_to_start should do nothing at line start."""
        controller = InputController()
        controller.text = "hello"
        controller.move_cursor((0, 0))

        controller.action_clear_to_start()

        assert controller.text == "hello"


class TestInputControllerHistory:
    """Test command history functionality."""

    def test_add_to_history_appends_command(self):
        """add_to_history should append new command."""
        controller = InputController()
        controller.add_to_history("ls -la")

        assert "ls -la" in controller.cmd_history

    def test_add_to_history_resets_index(self):
        """add_to_history should reset history index."""
        controller = InputController()
        controller.cmd_history_index = 2

        controller.add_to_history("new command")

        assert controller.cmd_history_index == -1

    def test_add_to_history_ignores_empty(self):
        """add_to_history should ignore empty commands."""
        controller = InputController()
        controller.add_to_history("")

        assert len(controller.cmd_history) == 0

    def test_add_to_history_ignores_duplicate_last(self):
        """add_to_history should not duplicate last command."""
        controller = InputController()
        controller.add_to_history("ls")
        controller.add_to_history("ls")

        assert len(controller.cmd_history) == 1

    def test_add_to_history_allows_duplicate_not_last(self):
        """add_to_history should allow duplicate if not last."""
        controller = InputController()
        controller.add_to_history("ls")
        controller.add_to_history("pwd")
        controller.add_to_history("ls")

        assert controller.cmd_history == ["ls", "pwd", "ls"]


class TestInputControllerHistoryNavigation:
    """Test history up/down navigation."""

    def test_history_up_no_history_does_nothing(self):
        """history_up should do nothing with empty history."""
        controller = InputController()
        controller.text = "current"

        controller.action_history_up()

        assert controller.text == "current"

    def test_history_up_shows_last_command(self):
        """history_up should show last command."""
        controller = InputController()
        controller.cmd_history = ["cmd1", "cmd2", "cmd3"]
        controller.move_cursor = MagicMock()

        controller.action_history_up()

        assert controller.text == "cmd3"

    def test_history_up_saves_current_input(self):
        """history_up should save current input."""
        controller = InputController()
        controller.cmd_history = ["cmd1"]
        controller.text = "my input"
        controller.move_cursor = MagicMock()

        controller.action_history_up()

        assert controller.current_input == "my input"

    def test_history_up_navigates_backwards(self):
        """history_up should navigate backwards through history."""
        controller = InputController()
        controller.cmd_history = ["cmd1", "cmd2", "cmd3"]
        controller.move_cursor = MagicMock()

        controller.action_history_up()
        assert controller.text == "cmd3"

        controller.action_history_up()
        assert controller.text == "cmd2"

        controller.action_history_up()
        assert controller.text == "cmd1"

    def test_history_up_stops_at_beginning(self):
        """history_up should stop at beginning of history."""
        controller = InputController()
        controller.cmd_history = ["cmd1", "cmd2"]
        controller.move_cursor = MagicMock()

        controller.action_history_up()
        controller.action_history_up()
        controller.action_history_up()  # Extra call

        assert controller.text == "cmd1"
        assert controller.cmd_history_index == 0

    def test_history_down_does_nothing_at_start(self):
        """history_down should do nothing when not navigating history."""
        controller = InputController()
        controller.cmd_history = ["cmd1", "cmd2"]
        controller.text = "current"

        controller.action_history_down()

        assert controller.text == "current"
        assert controller.cmd_history_index == -1

    def test_history_down_navigates_forward(self):
        """history_down should navigate forward through history."""
        controller = InputController()
        controller.cmd_history = ["cmd1", "cmd2", "cmd3"]
        controller.move_cursor = MagicMock()

        controller.action_history_up()
        controller.action_history_up()
        controller.action_history_up()

        controller.action_history_down()
        assert controller.text == "cmd2"

        controller.action_history_down()
        assert controller.text == "cmd3"

    def test_history_down_restores_current_input(self):
        """history_down should restore current input at end."""
        controller = InputController()
        controller.cmd_history = ["cmd1"]
        controller.text = "my input"
        controller.move_cursor = MagicMock()

        controller.action_history_up()
        assert controller.text == "cmd1"

        controller.action_history_down()
        assert controller.text == "my input"
        assert controller.cmd_history_index == -1

    def test_history_moves_cursor_to_end(self):
        """History navigation should move cursor to end."""
        controller = InputController()
        controller.cmd_history = ["test command"]
        controller.move_cursor = MagicMock()

        controller.action_history_up()

        controller.move_cursor.assert_called_with((len("test command"), 0))


class TestInputControllerGhostText:
    """Test ghost text suggestion functionality."""

    def test_watch_text_clears_ghost_when_diverges(self):
        """watch_text should clear ghost when text diverges from suggestion."""
        controller = InputController()
        controller.current_suggestion = "ls -la"
        controller.ghost_label.display = True

        controller.watch_text("cd")  # Diverges from "ls -la"

        assert controller.ghost_label.display is False
        assert controller.current_suggestion == ""

    def test_watch_text_updates_ghost_when_matches(self):
        """watch_text should update ghost when text still matches."""
        controller = InputController()
        controller.current_suggestion = "ls -la"
        controller.ghost_label = MagicMock()
        controller._update_ghost_position = MagicMock()

        controller.watch_text("ls ")

        controller.ghost_label.update.assert_called_with("-la")

    def test_accept_ghost_with_suggestion(self):
        """action_accept_ghost should accept full suggestion."""
        controller = InputController()
        controller.current_suggestion = "ls -la /tmp"
        controller.ghost_label.display = True
        controller.text = "ls "
        controller.move_cursor = MagicMock()

        controller.action_accept_ghost()

        assert controller.text == "ls -la /tmp"
        assert controller.ghost_label.display is False

    def test_accept_ghost_without_suggestion_moves_cursor(self):
        """action_accept_ghost without suggestion should move cursor right."""
        controller = InputController()
        controller.ghost_label.display = False
        controller.cursor_location = (0, 5)
        controller.document = MagicMock()
        controller.document.get_line.return_value = "hello world"
        controller.move_cursor_relative = MagicMock()

        controller.action_accept_ghost()

        controller.move_cursor_relative.assert_called_with(0, 1)


class TestInputControllerGetCurrentWord:
    """Test _get_current_word method."""

    def test_get_current_word_returns_last_word(self):
        """_get_current_word should return last word."""
        controller = InputController()
        controller.text = "cd /home/user"

        assert controller._get_current_word() == "/home/user"

    def test_get_current_word_single_word(self):
        """_get_current_word should return single word."""
        controller = InputController()
        controller.text = "ls"

        assert controller._get_current_word() == "ls"

    def test_get_current_word_empty_text(self):
        """_get_current_word should return empty for empty text."""
        controller = InputController()
        controller.text = ""

        assert controller._get_current_word() == ""


class TestInputControllerIsPathContext:
    """Test _is_path_context method."""

    def test_is_path_context_tilde(self):
        """_is_path_context should detect ~ paths."""
        controller = InputController()
        controller.text = "cd ~/Documents"

        assert controller._is_path_context() is True

    def test_is_path_context_dot_slash(self):
        """_is_path_context should detect ./ paths."""
        controller = InputController()
        controller.text = "ls ./src"

        assert controller._is_path_context() is True

    def test_is_path_context_dotdot_slash(self):
        """_is_path_context should detect ../ paths."""
        controller = InputController()
        controller.text = "cat ../README.md"

        assert controller._is_path_context() is True

    def test_is_path_context_absolute(self):
        """_is_path_context should detect absolute paths."""
        controller = InputController()
        controller.text = "ls /etc/passwd"

        assert controller._is_path_context() is True

    def test_is_path_context_not_path(self):
        """_is_path_context should return False for non-paths."""
        controller = InputController()
        controller.text = "echo hello"

        assert controller._is_path_context() is False

    def test_is_path_context_empty(self):
        """_is_path_context should return False for empty."""
        controller = InputController()
        controller.text = ""

        assert controller._is_path_context() is False


class TestInputControllerPathCompletions:
    """Test _get_path_completions method."""

    def test_get_path_completions_home_dir(self, tmp_path, monkeypatch):
        """_get_path_completions should handle ~ paths."""
        # Create test directory structure
        docs = tmp_path / "Documents"
        docs.mkdir()
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        controller = InputController()
        completions = controller._get_path_completions("~/")

        # Should return items in home directory
        assert any("Documents" in c for c in completions)

    def test_get_path_completions_current_dir(self, tmp_path, monkeypatch):
        """_get_path_completions should handle ./ paths."""
        # Create test file
        (tmp_path / "test.txt").touch()
        monkeypatch.chdir(tmp_path)

        controller = InputController()
        completions = controller._get_path_completions("./")

        assert any("test.txt" in c for c in completions)

    def test_get_path_completions_adds_slash_to_dirs(self, tmp_path, monkeypatch):
        """_get_path_completions should add / to directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(tmp_path)

        controller = InputController()
        completions = controller._get_path_completions("./")

        dir_completions = [c for c in completions if "subdir" in c]
        assert len(dir_completions) > 0
        assert all(c.endswith("/") for c in dir_completions)

    def test_get_path_completions_limits_results(self, tmp_path, monkeypatch):
        """_get_path_completions should limit to 10 results."""
        # Create many files
        for i in range(20):
            (tmp_path / f"file{i:02d}.txt").touch()
        monkeypatch.chdir(tmp_path)

        controller = InputController()
        completions = controller._get_path_completions("./")

        assert len(completions) <= 10

    def test_get_path_completions_nonexistent(self):
        """_get_path_completions should return empty for nonexistent."""
        controller = InputController()
        completions = controller._get_path_completions("/nonexistent/path/xyz")

        assert completions == []


class TestInputControllerCompletePath:
    """Test _complete_path method."""

    def test_complete_path_single_match(self):
        """_complete_path should complete with single match."""
        controller = InputController()
        controller.text = "cd /home/us"
        controller.move_cursor = MagicMock()

        controller._complete_path(["/home/user/"])

        assert controller.text == "cd /home/user/"

    def test_complete_path_no_matches(self):
        """_complete_path should do nothing with no matches."""
        controller = InputController()
        controller.text = "cd /path"

        controller._complete_path([])

        assert controller.text == "cd /path"

    def test_complete_path_common_prefix(self):
        """_complete_path should complete common prefix with multiple matches."""
        controller = InputController()
        controller.text = "ls /ho"
        controller.move_cursor = MagicMock()

        controller._complete_path(["/home/user1", "/home/user2"])

        assert controller.text == "ls /home/user"

    def test_complete_path_empty_text(self):
        """_complete_path should do nothing with empty text."""
        controller = InputController()
        controller.text = ""

        controller._complete_path(["/some/path"])

        assert controller.text == ""


class TestInputControllerCursorLineDetection:
    """Test cursor line detection methods."""

    def test_on_cursor_first_line_true(self):
        """_on_cursor_first_line should return True on row 0."""
        controller = InputController()
        controller.text = "single line"

        assert controller._on_cursor_first_line() is True

    def test_on_cursor_first_line_false(self):
        """_on_cursor_first_line should return False on other rows."""
        controller = InputController()
        controller.text = "line1\nline2"
        controller.move_cursor((1, 0))

        assert controller._on_cursor_first_line() is False

    def test_on_cursor_last_line_true(self):
        """_on_cursor_last_line should return True on last line."""
        controller = InputController()
        controller.text = "line1\nline2\nline3"
        controller.move_cursor((2, 0))

        assert controller._on_cursor_last_line() is True

    def test_on_cursor_last_line_false(self):
        """_on_cursor_last_line should return False on other lines."""
        controller = InputController()
        controller.text = "line1\nline2\nline3"
        controller.move_cursor((0, 0))

        assert controller._on_cursor_last_line() is False


class TestInputControllerBindings:
    """Test key bindings configuration."""

    def test_enter_binding_defined(self):
        """Enter binding should be defined."""
        from textual.binding import Binding

        bindings = InputController.BINDINGS
        enter_bindings = [
            b for b in bindings if isinstance(b, Binding) and b.key == "enter"
        ]

        assert len(enter_bindings) == 1
        assert enter_bindings[0].action == "submit"

    def test_shift_enter_binding_defined(self):
        """Shift+Enter binding should be defined."""
        from textual.binding import Binding

        bindings = InputController.BINDINGS
        shift_enter_bindings = [
            b for b in bindings if isinstance(b, Binding) and b.key == "shift+enter"
        ]

        assert len(shift_enter_bindings) == 1
        assert shift_enter_bindings[0].action == "newline"

    def test_ctrl_u_binding_defined(self):
        """Ctrl+U binding should be defined."""
        from textual.binding import Binding

        bindings = InputController.BINDINGS
        ctrl_u_bindings = [
            b for b in bindings if isinstance(b, Binding) and b.key == "ctrl+u"
        ]

        assert len(ctrl_u_bindings) == 1
        assert ctrl_u_bindings[0].action == "clear_to_start"

    def test_copy_selection_binding_defined(self):
        """Ctrl+Shift+C binding should be defined."""
        from textual.binding import Binding

        bindings = InputController.BINDINGS
        copy_bindings = [
            b for b in bindings if isinstance(b, Binding) and b.key == "ctrl+shift+c"
        ]

        assert len(copy_bindings) == 1
        assert copy_bindings[0].action == "copy_selection"

    def test_accept_ghost_binding_defined(self):
        """Right arrow binding for ghost acceptance should be defined."""
        from textual.binding import Binding

        bindings = InputController.BINDINGS
        right_bindings = [
            b for b in bindings if isinstance(b, Binding) and b.key == "right"
        ]

        assert len(right_bindings) == 1
        assert right_bindings[0].action == "accept_ghost"

    def test_priority_bindings(self):
        """Critical bindings should have priority=True."""
        from textual.binding import Binding

        bindings = InputController.BINDINGS
        priority_keys = ["enter", "shift+enter", "ctrl+shift+c", "ctrl+u"]

        for b in bindings:
            if isinstance(b, Binding) and b.key in priority_keys:
                assert b.priority is True


class TestInputControllerCopySelection:
    """Test copy selection functionality."""

    def test_action_copy_selection_with_selection(self):
        """action_copy_selection should copy selected text."""
        mock_app = MagicMock()
        mock_app.run_worker = MagicMock()

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "selected content"
            controller.select_all()

            controller.action_copy_selection()

            mock_app.run_worker.assert_called_once()

    def test_action_copy_selection_without_selection(self):
        """action_copy_selection should do nothing without selection."""
        mock_app = MagicMock()
        mock_app.run_worker = MagicMock()

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "some text"

            controller.action_copy_selection()

            mock_app.run_worker.assert_not_called()


class TestInputControllerPasteFromClipboard:
    """Test paste from clipboard functionality."""

    @pytest.mark.asyncio
    async def test_paste_with_pyperclip(self):
        """_paste_from_clipboard should use pyperclip if available."""
        controller = InputController()
        controller.insert = MagicMock()

        with patch("widgets.input.pyperclip") as mock_pyperclip:
            mock_pyperclip.paste.return_value = "clipboard content"

            await controller._paste_from_clipboard()

            controller.insert.assert_called_once_with("clipboard content")

    @pytest.mark.asyncio
    async def test_paste_empty_content(self):
        """_paste_from_clipboard should handle empty clipboard."""
        controller = InputController()
        controller.insert = MagicMock()

        with patch("widgets.input.pyperclip") as mock_pyperclip:
            mock_pyperclip.paste.return_value = ""

            await controller._paste_from_clipboard()

            controller.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_paste_without_pyperclip_fallback(self):
        """_paste_from_clipboard should fallback to xclip."""
        controller = InputController()
        controller.insert = MagicMock()
        controller.notify = MagicMock()

        with patch("widgets.input.pyperclip", None):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = AsyncMock()
                mock_process.communicate = AsyncMock(
                    return_value=(b"xclip content", b"")
                )
                mock_process.returncode = 0
                mock_exec.return_value = mock_process

                await controller._paste_from_clipboard()

                controller.insert.assert_called_once_with("xclip content")


class TestInputControllerOnClick:
    """Test mouse click handling."""

    @pytest.mark.asyncio
    async def test_right_click_triggers_paste(self):
        """Right-click should trigger paste."""
        from textual.events import Click

        controller = InputController()
        controller._paste_from_clipboard = AsyncMock()

        event = MagicMock(spec=Click)
        event.button = 3
        event.stop = MagicMock()

        await controller.on_click(event)

        event.stop.assert_called()
        controller._paste_from_clipboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_left_click_does_not_paste(self):
        """Left-click should not trigger paste."""
        from textual.events import Click

        controller = InputController()
        controller._paste_from_clipboard = AsyncMock()

        event = MagicMock(spec=Click)
        event.button = 1

        await controller.on_click(event)

        controller._paste_from_clipboard.assert_not_awaited()


class TestInputControllerKeyHandling:
    """Test on_key event handling."""

    @pytest.mark.asyncio
    async def test_escape_hides_suggester(self):
        """Escape key should hide suggester."""
        mock_suggester = MagicMock()
        mock_suggester.display = True
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "/help"

            event = MagicMock()
            event.key = "escape"
            event.stop = MagicMock()

            await controller.on_key(event)

            assert mock_suggester.display is False
            event.stop.assert_called()

    @pytest.mark.asyncio
    async def test_up_arrow_with_suggester_selects_prev(self):
        """Up arrow with suggester visible should select previous."""
        mock_suggester = MagicMock()
        mock_suggester.display = True
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "/h"

            event = MagicMock()
            event.key = "up"
            event.stop = MagicMock()

            await controller.on_key(event)

            mock_suggester.select_prev.assert_called_once()
            event.stop.assert_called()

    @pytest.mark.asyncio
    async def test_down_arrow_with_suggester_selects_next(self):
        """Down arrow with suggester visible should select next."""
        mock_suggester = MagicMock()
        mock_suggester.display = True
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "/h"

            event = MagicMock()
            event.key = "down"
            event.stop = MagicMock()

            await controller.on_key(event)

            mock_suggester.select_next.assert_called_once()
            event.stop.assert_called()

    @pytest.mark.asyncio
    async def test_tab_completes_from_suggester(self):
        """Tab with suggester should complete command."""
        mock_suggester = MagicMock()
        mock_suggester.display = True
        mock_suggester.get_selected.return_value = "/help"
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "/hel"

            event = MagicMock()
            event.key = "tab"
            event.stop = MagicMock()

            await controller.on_key(event)

            assert controller.text == "/help "
            event.stop.assert_called()

    @pytest.mark.asyncio
    async def test_tab_path_completion_in_cli_mode(self):
        """Tab should complete paths in CLI mode."""
        mock_suggester = MagicMock()
        mock_suggester.display = False
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "cd ./"
            controller.mode = "CLI"
            controller._is_path_context = MagicMock(return_value=True)
            controller._get_current_word = MagicMock(return_value="./")
            controller._get_path_completions = MagicMock(return_value=["./test.txt"])
            controller._complete_path = MagicMock()

            event = MagicMock()
            event.key = "tab"
            event.stop = MagicMock()

            await controller.on_key(event)

            controller._complete_path.assert_called_once_with(["./test.txt"])
            event.stop.assert_called()

    @pytest.mark.asyncio
    async def test_up_arrow_history_navigation(self):
        """Up arrow should navigate history when on first line."""
        mock_suggester = MagicMock()
        mock_suggester.display = False
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "current"
            controller.cmd_history = ["old command"]
            controller._on_cursor_first_line = MagicMock(return_value=True)
            controller.action_history_up = MagicMock()

            event = MagicMock()
            event.key = "up"
            event.stop = MagicMock()

            await controller.on_key(event)

            controller.action_history_up.assert_called_once()
            event.stop.assert_called()

    @pytest.mark.asyncio
    async def test_down_arrow_history_navigation(self):
        """Down arrow should navigate history when on last line."""
        mock_suggester = MagicMock()
        mock_suggester.display = False
        mock_app = MagicMock()
        mock_app.query_one.return_value = mock_suggester

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()
            controller.text = "old command"
            controller.cmd_history = ["old command"]
            controller.cmd_history_index = 0
            controller._on_cursor_last_line = MagicMock(return_value=True)
            controller.action_history_down = MagicMock()

            event = MagicMock()
            event.key = "down"
            event.stop = MagicMock()

            await controller.on_key(event)

            controller.action_history_down.assert_called_once()
            event.stop.assert_called()


class TestInputControllerUpdateGhostPosition:
    """Test _update_ghost_position method."""

    def test_update_ghost_position_sets_offset(self):
        """_update_ghost_position should set ghost label offset."""
        controller = InputController()
        controller.text = "line1\nline2\nline3 test"
        controller.move_cursor((2, 10))

        controller._update_ghost_position()

        offset = controller.ghost_label.styles.offset
        assert offset[0].value == 11
        assert offset[1].value == 2

    def test_update_ghost_position_handles_exception(self):
        """_update_ghost_position should handle exceptions gracefully."""
        controller = InputController()
        ghost_mock = MagicMock()
        controller.ghost_label = ghost_mock

        def raise_exception():
            raise Exception("test")

        with patch.object(
            type(controller),
            "cursor_location",
            property(lambda self: raise_exception()),
        ):
            pass

        controller._update_ghost_position()


class TestInputControllerSuggestionHandler:
    """Test on_command_suggester_suggestion_ready handler."""

    def test_suggestion_ready_updates_ghost(self):
        """Handler should update ghost label with suggestion remainder."""
        controller = InputController()
        controller.text = "ls "
        ghost_label_mock = MagicMock()
        controller.ghost_label = ghost_label_mock
        controller._update_ghost_position = MagicMock()

        event = MagicMock()
        event.suggestion = "ls -la"

        controller.on_command_suggester_suggestion_ready(event)

        assert controller.current_suggestion == "ls -la"
        ghost_label_mock.update.assert_called_with("-la")
        assert ghost_label_mock.display is True

    def test_suggestion_ready_hides_ghost_when_no_match(self):
        """Handler should hide ghost when suggestion doesn't match."""
        controller = InputController()
        controller.text = "cd "
        ghost_label_mock = MagicMock()
        controller.ghost_label = ghost_label_mock

        event = MagicMock()
        event.suggestion = "ls -la"

        controller.on_command_suggester_suggestion_ready(event)

        assert ghost_label_mock.display is False
        assert controller.current_suggestion == ""

    def test_suggestion_ready_hides_ghost_when_empty(self):
        """Handler should hide ghost when suggestion is empty."""
        controller = InputController()
        controller.text = "ls"
        ghost_label_mock = MagicMock()
        controller.ghost_label = ghost_label_mock

        event = MagicMock()
        event.suggestion = ""

        controller.on_command_suggester_suggestion_ready(event)

        assert ghost_label_mock.display is False

    def test_suggestion_ready_hides_when_same_length(self):
        """Handler should hide ghost when suggestion equals current text."""
        controller = InputController()
        controller.text = "ls -la"
        ghost_label_mock = MagicMock()
        controller.ghost_label = ghost_label_mock

        event = MagicMock()
        event.suggestion = "ls -la"

        controller.on_command_suggester_suggestion_ready(event)

        assert ghost_label_mock.display is False


class TestInputControllerApplyCursorSettings:
    """Test _apply_cursor_settings method."""

    def test_apply_cursor_settings_with_valid_config(self):
        """_apply_cursor_settings should apply settings from config."""
        mock_settings = MagicMock()
        mock_settings.terminal.cursor_blink = False
        mock_settings.terminal.cursor_style = "beam"

        with patch("config.get_settings", return_value=mock_settings):
            controller = InputController()
            controller._apply_cursor_settings()

            assert controller.cursor_blink is False
            assert "cursor-beam" in controller.classes

    def test_apply_cursor_settings_handles_exception(self):
        """_apply_cursor_settings should handle missing config gracefully."""
        with patch("config.get_settings", side_effect=ImportError("No config")):
            controller = InputController()
            controller._apply_cursor_settings()


class TestInputControllerCopyToClipboard:
    """Test _copy_to_clipboard method."""

    @pytest.mark.asyncio
    async def test_copy_to_clipboard_uses_app_method(self):
        """_copy_to_clipboard should use app's copy method."""
        mock_app = MagicMock()

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()

            await controller._copy_to_clipboard("test text")

            mock_app.copy_to_clipboard.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_copy_to_clipboard_uses_pyperclip(self):
        """_copy_to_clipboard should use pyperclip as fallback."""
        mock_app = MagicMock()
        mock_app.copy_to_clipboard.side_effect = Exception("App error")

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()

            with patch("widgets.input.pyperclip") as mock_pyperclip:
                await controller._copy_to_clipboard("test text")

                mock_pyperclip.copy.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_copy_to_clipboard_handles_all_failures(self):
        """_copy_to_clipboard should handle all failures gracefully."""
        mock_app = MagicMock()
        mock_app.copy_to_clipboard.side_effect = Exception("App error")

        with patch.object(
            InputController, "app", new_callable=lambda: property(lambda self: mock_app)
        ):
            controller = InputController()

            with patch("widgets.input.pyperclip") as mock_pyperclip:
                mock_pyperclip.copy.side_effect = Exception("Pyperclip error")

                await controller._copy_to_clipboard("test text")


class TestInputControllerSelectionChanged:
    """Test on_text_area_selection_changed handler."""

    @pytest.mark.asyncio
    async def test_selection_changed_copies_text(self):
        """Selection change should auto-copy selected text."""
        controller = InputController()
        controller.text = "selected text"
        controller.select_all()
        controller._copy_to_clipboard = AsyncMock()

        event = MagicMock()
        event.selection.start = (0, 0)
        event.selection.end = (0, 13)

        await controller.on_text_area_selection_changed(event)

        controller._copy_to_clipboard.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_selection_changed_no_selection(self):
        """Empty selection should not trigger copy."""
        controller = InputController()
        controller.text = "some text"
        controller._copy_to_clipboard = AsyncMock()

        event = MagicMock()
        event.selection.start = (0, 5)
        event.selection.end = (0, 5)

        await controller.on_text_area_selection_changed(event)

        controller._copy_to_clipboard.assert_not_awaited()
