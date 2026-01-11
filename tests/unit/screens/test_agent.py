import pytest
from unittest.mock import MagicMock

from screens.agent import AgentScreen


class TestAgentScreen:
    def test_bindings_defined(self):
        screen = AgentScreen()
        # BINDINGS can be Binding objects or tuples (key, action, description)
        binding_keys = []
        for b in screen.BINDINGS:
            if hasattr(b, "key"):
                binding_keys.append(b.key)
            elif isinstance(b, tuple):
                binding_keys.append(b[0])
        assert "escape" in binding_keys
        assert "c" in binding_keys
        assert "s" in binding_keys

    def test_action_dismiss(self):
        screen = AgentScreen()
        screen.dismiss = MagicMock()
        screen.action_dismiss()
        screen.dismiss.assert_called_once()


class TestAgentScreenUpdateStatus:
    def test_update_status_idle(self):
        screen = AgentScreen()
        mock_display = MagicMock()
        screen.query_one = MagicMock(return_value=mock_display)

        screen._update_status({"state": "idle"})

        mock_display.update.assert_called_once()
        call_arg = mock_display.update.call_args[0][0]
        assert "IDLE" in call_arg

    def test_update_status_with_session(self):
        screen = AgentScreen()
        mock_display = MagicMock()
        screen.query_one = MagicMock(return_value=mock_display)

        status = {
            "state": "executing",
            "current_session": {
                "id": "sess_123",
                "task": "Test task",
                "iterations": 5,
                "tool_calls": 10,
                "duration": 30.5,
            },
        }

        screen._update_status(status)

        mock_display.update.assert_called_once()
        call_arg = mock_display.update.call_args[0][0]
        assert "EXECUTING" in call_arg
        assert "sess_123" in call_arg


class TestAgentScreenUpdateStats:
    def test_update_stats_no_sessions(self):
        screen = AgentScreen()
        mock_display = MagicMock()
        screen.query_one = MagicMock(return_value=mock_display)

        screen._update_stats({"total_sessions": 0})

        mock_display.update.assert_called_once()
        call_arg = mock_display.update.call_args[0][0]
        assert "No sessions" in call_arg

    def test_update_stats_with_sessions(self):
        screen = AgentScreen()
        mock_display = MagicMock()
        screen.query_one = MagicMock(return_value=mock_display)

        stats = {
            "total_sessions": 5,
            "total_iterations": 25,
            "total_tool_calls": 50,
            "total_tokens": 10000,
            "total_duration": 120.5,
            "error_count": 2,
            "avg_iterations_per_session": 5.0,
            "avg_tools_per_session": 10.0,
        }

        screen._update_stats(stats)

        mock_display.update.assert_called_once()
        call_arg = mock_display.update.call_args[0][0]
        assert "Total Sessions: 5" in call_arg
        assert "Total Iterations: 25" in call_arg


class TestAgentScreenUpdateToolTable:
    def test_update_tool_table_empty(self):
        screen = AgentScreen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        screen._update_tool_table({})

        mock_table.clear.assert_called_once()
        mock_table.add_row.assert_not_called()

    def test_update_tool_table_with_tools(self):
        screen = AgentScreen()
        mock_table = MagicMock()
        screen.query_one = MagicMock(return_value=mock_table)

        tool_usage = {"read_file": 10, "write_file": 5, "run_command": 15}

        screen._update_tool_table(tool_usage)

        mock_table.clear.assert_called_once()
        assert mock_table.add_row.call_count == 3


class TestAgentScreenButtonHandling:
    def test_close_button(self):
        screen = AgentScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "close-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once()

    def test_stop_button(self):
        screen = AgentScreen()
        screen.action_stop_agent = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "stop-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.action_stop_agent.assert_called_once()

    def test_clear_button(self):
        screen = AgentScreen()
        screen.action_clear_history = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "clear-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.action_clear_history.assert_called_once()
