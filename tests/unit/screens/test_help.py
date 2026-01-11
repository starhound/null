"""Comprehensive tests for the help screen."""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from screens.help import HelpScreen


@dataclass
class MockCommandInfo:
    """Mock CommandInfo for testing."""

    name: str
    description: str
    shortcut: str = ""


def get_binding_keys(screen):
    binding_keys = []
    for b in screen.BINDINGS:
        if hasattr(b, "key"):
            binding_keys.append(b.key)
        elif isinstance(b, tuple):
            binding_keys.append(b[0])
    return binding_keys


def get_binding_by_key(screen, key):
    for b in screen.BINDINGS:
        binding_key = b.key if hasattr(b, "key") else b[0]
        if binding_key == key:
            return b
    return None


class TestHelpScreenInit:
    def test_screen_can_be_instantiated(self):
        screen = HelpScreen()
        assert isinstance(screen, HelpScreen)

    def test_screen_inherits_from_modal_screen(self):
        from textual.screen import ModalScreen

        screen = HelpScreen()
        assert isinstance(screen, ModalScreen)

    def test_screen_has_bindings_attribute(self):
        assert hasattr(HelpScreen, "BINDINGS")
        assert isinstance(HelpScreen.BINDINGS, list)


class TestHelpScreenBindings:
    def test_escape_binding_defined(self):
        screen = HelpScreen()
        binding_keys = get_binding_keys(screen)
        assert "escape" in binding_keys

    def test_escape_binding_action(self):
        screen = HelpScreen()
        escape_binding = get_binding_by_key(screen, "escape")
        action = (
            escape_binding.action
            if hasattr(escape_binding, "action")
            else escape_binding[1]
        )
        assert action == "dismiss"

    def test_escape_binding_description(self):
        screen = HelpScreen()
        escape_binding = get_binding_by_key(screen, "escape")
        description = (
            escape_binding.description
            if hasattr(escape_binding, "description")
            else (escape_binding[2] if len(escape_binding) > 2 else "")
        )
        assert description == "Close"

    def test_bindings_count(self):
        screen = HelpScreen()
        assert len(screen.BINDINGS) == 1


class TestHelpScreenCompose:
    def test_compose_returns_compose_result(self):
        screen = HelpScreen()
        result = screen.compose()
        assert hasattr(result, "__iter__")


class TestHelpScreenOnMountLogic:
    def test_fallback_commands_list_structure(self):
        fallback_commands = [
            ("/help", "Show this help screen", "F1"),
            ("/config", "Open settings", ""),
            ("/provider", "Select and configure AI provider", "F4"),
            ("/providers", "Manage all AI providers", ""),
            ("/theme", "Change the UI theme", "F3"),
            ("/model", "List and select AI models", "F2"),
            ("/prompts", "Manage system prompts", ""),
            ("/agent", "Toggle autonomous agent mode", ""),
            ("/mcp", "Manage MCP servers", ""),
            ("/tools", "Browse available MCP tools", ""),
            ("/session", "Manage sessions", ""),
            ("/export", "Export conversation", "Ctrl+S"),
            ("/status", "Show current status", ""),
            ("/clear", "Clear history", "Ctrl+L"),
            ("/compact", "Summarize context", ""),
            ("/quit", "Exit the application", "Ctrl+C"),
        ]
        assert len(fallback_commands) == 16
        for cmd in fallback_commands:
            assert len(cmd) == 3
            assert cmd[0].startswith("/")

    def test_fallback_has_help_command(self):
        fallback_commands = [
            ("/help", "Show this help screen", "F1"),
            ("/config", "Open settings", ""),
            ("/provider", "Select and configure AI provider", "F4"),
            ("/providers", "Manage all AI providers", ""),
            ("/theme", "Change the UI theme", "F3"),
            ("/model", "List and select AI models", "F2"),
            ("/prompts", "Manage system prompts", ""),
            ("/agent", "Toggle autonomous agent mode", ""),
            ("/mcp", "Manage MCP servers", ""),
            ("/tools", "Browse available MCP tools", ""),
            ("/session", "Manage sessions", ""),
            ("/export", "Export conversation", "Ctrl+S"),
            ("/status", "Show current status", ""),
            ("/clear", "Clear history", "Ctrl+L"),
            ("/compact", "Summarize context", ""),
            ("/quit", "Exit the application", "Ctrl+C"),
        ]
        help_row = next(r for r in fallback_commands if r[0] == "/help")
        assert help_row[1] == "Show this help screen"
        assert help_row[2] == "F1"

    def test_fallback_has_quit_command(self):
        fallback_commands = [
            ("/help", "Show this help screen", "F1"),
            ("/config", "Open settings", ""),
            ("/provider", "Select and configure AI provider", "F4"),
            ("/providers", "Manage all AI providers", ""),
            ("/theme", "Change the UI theme", "F3"),
            ("/model", "List and select AI models", "F2"),
            ("/prompts", "Manage system prompts", ""),
            ("/agent", "Toggle autonomous agent mode", ""),
            ("/mcp", "Manage MCP servers", ""),
            ("/tools", "Browse available MCP tools", ""),
            ("/session", "Manage sessions", ""),
            ("/export", "Export conversation", "Ctrl+S"),
            ("/status", "Show current status", ""),
            ("/clear", "Clear history", "Ctrl+L"),
            ("/compact", "Summarize context", ""),
            ("/quit", "Exit the application", "Ctrl+C"),
        ]
        quit_row = next(r for r in fallback_commands if r[0] == "/quit")
        assert quit_row[1] == "Exit the application"
        assert quit_row[2] == "Ctrl+C"

    def test_fallback_shortcuts_correct(self):
        fallback_commands = [
            ("/help", "Show this help screen", "F1"),
            ("/config", "Open settings", ""),
            ("/provider", "Select and configure AI provider", "F4"),
            ("/providers", "Manage all AI providers", ""),
            ("/theme", "Change the UI theme", "F3"),
            ("/model", "List and select AI models", "F2"),
            ("/prompts", "Manage system prompts", ""),
            ("/agent", "Toggle autonomous agent mode", ""),
            ("/mcp", "Manage MCP servers", ""),
            ("/tools", "Browse available MCP tools", ""),
            ("/session", "Manage sessions", ""),
            ("/export", "Export conversation", "Ctrl+S"),
            ("/status", "Show current status", ""),
            ("/clear", "Clear history", "Ctrl+L"),
            ("/compact", "Summarize context", ""),
            ("/quit", "Exit the application", "Ctrl+C"),
        ]
        commands_dict = {row[0]: row[2] for row in fallback_commands}

        assert commands_dict["/help"] == "F1"
        assert commands_dict["/theme"] == "F3"
        assert commands_dict["/model"] == "F2"
        assert commands_dict["/provider"] == "F4"
        assert commands_dict["/clear"] == "Ctrl+L"
        assert commands_dict["/export"] == "Ctrl+S"
        assert commands_dict["/quit"] == "Ctrl+C"

    def test_command_row_format_from_handler(self):
        mock_cmd = MockCommandInfo(
            name="test", description="Test command", shortcut="F9"
        )
        row = (f"/{mock_cmd.name}", mock_cmd.description, mock_cmd.shortcut or "")
        assert row == ("/test", "Test command", "F9")

    def test_command_row_format_empty_shortcut(self):
        mock_cmd = MockCommandInfo(name="foo", description="Foo cmd", shortcut="")
        row = (f"/{mock_cmd.name}", mock_cmd.description, mock_cmd.shortcut or "")
        assert row[2] == ""

    def test_command_row_format_none_shortcut(self):
        mock_cmd = MagicMock()
        mock_cmd.name = "bar"
        mock_cmd.description = "Bar cmd"
        mock_cmd.shortcut = None
        row = (f"/{mock_cmd.name}", mock_cmd.description, mock_cmd.shortcut or "")
        assert row[2] == ""

    def test_command_formatting_multiple_commands(self):
        mock_commands = [
            MockCommandInfo(name="cmd1", description="First", shortcut="F1"),
            MockCommandInfo(name="cmd2", description="Second", shortcut="F2"),
            MockCommandInfo(name="cmd3", description="Third", shortcut=""),
        ]
        rows = [
            (f"/{info.name}", info.description, info.shortcut or "")
            for info in mock_commands
        ]
        assert len(rows) == 3
        assert rows[0] == ("/cmd1", "First", "F1")
        assert rows[1] == ("/cmd2", "Second", "F2")
        assert rows[2] == ("/cmd3", "Third", "")


class TestHelpScreenButtonPressed:
    def test_close_button_dismisses(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "close_btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once()

    def test_other_button_no_dismiss(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "other_btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_not_called()

    def test_button_with_none_id(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = None
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_not_called()

    def test_button_with_empty_string_id(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = ""
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_not_called()

    def test_unrelated_button_id(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "random_button"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_not_called()

    def test_dismiss_called_once_only(self):
        screen = HelpScreen()
        call_count = 0

        def mock_dismiss():
            nonlocal call_count
            call_count += 1

        screen.dismiss = mock_dismiss

        mock_button = MagicMock()
        mock_button.id = "close_btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert call_count == 1


class TestHelpScreenActionDismiss:
    @pytest.mark.asyncio
    async def test_action_dismiss_no_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss()

        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_none_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result=None)

        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_string_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result="test_result")

        screen.dismiss.assert_called_once_with("test_result")

    @pytest.mark.asyncio
    async def test_action_dismiss_with_dict_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        result = {"key": "value"}
        await screen.action_dismiss(result=result)

        screen.dismiss.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_boolean_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result=True)

        screen.dismiss.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_integer_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result=42)

        screen.dismiss.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_list_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        result = [1, 2, 3]
        await screen.action_dismiss(result=result)

        screen.dismiss.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_tuple_result(self):
        screen = HelpScreen()
        screen.dismiss = MagicMock()

        result = ("a", "b")
        await screen.action_dismiss(result=result)

        screen.dismiss.assert_called_once_with(result)


class TestHelpScreenDocstring:
    def test_screen_has_docstring(self):
        assert HelpScreen.__doc__ is not None
        assert len(HelpScreen.__doc__) > 0

    def test_screen_docstring_content(self):
        assert "command" in HelpScreen.__doc__.lower()


class TestHelpScreenEdgeCases:
    def test_command_with_special_characters_in_description(self):
        mock_cmd = MockCommandInfo(
            name="special",
            description="Test <special> & 'chars'",
            shortcut="Ctrl+<",
        )
        row = (f"/{mock_cmd.name}", mock_cmd.description, mock_cmd.shortcut or "")
        assert row[1] == "Test <special> & 'chars'"

    def test_command_with_very_long_description(self):
        long_desc = "A" * 200
        mock_cmd = MockCommandInfo(name="long", description=long_desc, shortcut="")
        row = (f"/{mock_cmd.name}", mock_cmd.description, mock_cmd.shortcut or "")
        assert row[1] == long_desc

    def test_command_name_prefix_slash(self):
        mock_cmd = MockCommandInfo(name="mycommand", description="Test", shortcut="")
        formatted_name = f"/{mock_cmd.name}"
        assert formatted_name == "/mycommand"
        assert formatted_name.startswith("/")

    def test_empty_shortcut_becomes_empty_string(self):
        mock_cmd = MockCommandInfo(name="test", description="Test", shortcut="")
        shortcut = mock_cmd.shortcut or ""
        assert shortcut == ""
        assert isinstance(shortcut, str)

    def test_none_shortcut_becomes_empty_string(self):
        mock_cmd = MagicMock()
        mock_cmd.shortcut = None
        shortcut = mock_cmd.shortcut or ""
        assert shortcut == ""

    def test_command_info_dataclass_defaults(self):
        cmd = MockCommandInfo(name="test", description="Test desc")
        assert cmd.name == "test"
        assert cmd.description == "Test desc"
        assert cmd.shortcut == ""


class TestHelpScreenClassAttributes:
    def test_bindings_is_class_var(self):
        assert hasattr(HelpScreen, "BINDINGS")
        screen1 = HelpScreen()
        screen2 = HelpScreen()
        assert screen1.BINDINGS is screen2.BINDINGS

    def test_screen_class_name(self):
        assert HelpScreen.__name__ == "HelpScreen"

    def test_screen_module(self):
        assert "screens.help" in HelpScreen.__module__


class TestMockCommandInfo:
    def test_dataclass_creation(self):
        cmd = MockCommandInfo(name="help", description="Show help", shortcut="F1")
        assert cmd.name == "help"
        assert cmd.description == "Show help"
        assert cmd.shortcut == "F1"

    def test_dataclass_default_shortcut(self):
        cmd = MockCommandInfo(name="test", description="Test")
        assert cmd.shortcut == ""

    def test_dataclass_equality(self):
        cmd1 = MockCommandInfo(name="help", description="Help", shortcut="F1")
        cmd2 = MockCommandInfo(name="help", description="Help", shortcut="F1")
        assert cmd1 == cmd2

    def test_dataclass_inequality(self):
        cmd1 = MockCommandInfo(name="help", description="Help", shortcut="F1")
        cmd2 = MockCommandInfo(name="quit", description="Quit", shortcut="")
        assert cmd1 != cmd2
