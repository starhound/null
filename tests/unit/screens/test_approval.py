import pytest
from unittest.mock import MagicMock

from screens.approval import ToolApprovalScreen, ToolPreview


class TestToolPreview:
    def test_init_stores_attributes(self):
        preview = ToolPreview(tool_name="run_command", arguments={"cmd": "ls"})
        assert preview.tool_name == "run_command"
        assert preview.arguments == {"cmd": "ls"}

    def test_init_empty_arguments(self):
        preview = ToolPreview(tool_name="test_tool", arguments={})
        assert preview.arguments == {}

    def test_compose_yields_widgets(self):
        preview = ToolPreview(tool_name="my_tool", arguments={"key": "value"})
        widgets = list(preview.compose())
        assert len(widgets) >= 1


class TestToolApprovalScreen:
    def test_init_stores_tool_calls(self):
        tool_calls = [{"name": "read_file", "arguments": {"path": "/tmp/test"}}]
        screen = ToolApprovalScreen(tool_calls=tool_calls)
        assert screen.tool_calls == tool_calls
        assert screen.iteration_number == 1
        assert screen.result is None

    def test_init_custom_iteration(self):
        screen = ToolApprovalScreen(tool_calls=[], iteration_number=5)
        assert screen.iteration_number == 5

    def test_bindings_defined(self):
        screen = ToolApprovalScreen(tool_calls=[])
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys
        assert "enter" in binding_keys
        assert "a" in binding_keys
        assert "r" in binding_keys

    def test_action_approve(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        screen.action_approve()

        assert screen.result == "approve"
        screen.dismiss.assert_called_once_with("approve")

    def test_action_approve_all(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        screen.action_approve_all()

        assert screen.result == "approve-all"
        screen.dismiss.assert_called_once_with("approve-all")

    def test_action_reject(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        screen.action_reject()

        assert screen.result == "reject"
        screen.dismiss.assert_called_once_with("reject")

    def test_action_cancel(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        screen.action_cancel()

        assert screen.result == "cancel"
        screen.dismiss.assert_called_once_with("cancel")


class TestToolApprovalScreenButtonHandling:
    def test_approve_button(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "approve"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert screen.result == "approve"
        screen.dismiss.assert_called_once_with("approve")

    def test_approve_all_button(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "approve-all"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert screen.result == "approve-all"
        screen.dismiss.assert_called_once_with("approve-all")

    def test_reject_button(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "reject"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert screen.result == "reject"
        screen.dismiss.assert_called_once_with("reject")

    def test_cancel_button(self):
        screen = ToolApprovalScreen(tool_calls=[])
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "cancel"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        assert screen.result == "cancel"
        screen.dismiss.assert_called_once_with("cancel")
