"""Tests for the MCP Tools screen."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Any

from screens.tools import ToolsScreen


@dataclass
class MockMCPTool:
    name: str
    description: str | None
    input_schema: dict[str, Any]
    server_name: str


class MockMCPClient:
    def __init__(self, tools: list[MockMCPTool] | None = None):
        self.tools = tools or []
        self._connected = True

    @property
    def is_connected(self) -> bool:
        return self._connected


class MockMCPManager:
    def __init__(self, status: dict[str, Any] | None = None):
        self._status = status or {}
        self.clients: dict[str, MockMCPClient] = {}

    def get_status(self) -> dict[str, Any]:
        return self._status


class TestToolsScreen:
    def test_bindings_defined(self):
        screen = ToolsScreen()
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys

    def test_bindings_escape_action(self):
        screen = ToolsScreen()
        escape_binding = next(b for b in screen.BINDINGS if b.key == "escape")
        assert escape_binding.action == "dismiss"

    def test_bindings_count(self):
        screen = ToolsScreen()
        assert len(screen.BINDINGS) == 1

    def test_button_pressed_dismisses(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once()

    def test_button_pressed_ignores_event_button(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()

        mock_event = MagicMock()
        mock_event.button.id = "some_button"
        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_dismiss(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss()
        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_result(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss(result="test_result")
        screen.dismiss.assert_called_once_with("test_result")

    @pytest.mark.asyncio
    async def test_action_dismiss_with_none_result(self):
        screen = ToolsScreen()
        screen.dismiss = MagicMock()
        await screen.action_dismiss(result=None)
        screen.dismiss.assert_called_once_with(None)


class TestToolsScreenOnMount:
    @pytest.mark.asyncio
    async def test_on_mount_runs_worker(self):
        screen = ToolsScreen()
        screen.run_worker = MagicMock()

        await screen.on_mount()

        screen.run_worker.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_mount_worker_receives_coroutine(self):
        screen = ToolsScreen()
        screen.run_worker = MagicMock()

        await screen.on_mount()

        call_args = screen.run_worker.call_args[0][0]
        assert hasattr(call_args, "__await__")


class TestToolsScreenLoadToolsErrorHandling:
    @pytest.mark.asyncio
    async def test_load_tools_error_handling(self):
        mock_app = MagicMock()
        mock_app.mcp_manager.get_status.side_effect = Exception("Connection error")

        with patch.object(
            ToolsScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ToolsScreen()
            screen.notify = MagicMock()

            await screen._load_tools_refactored()

            screen.notify.assert_called_once()
            call_args = screen.notify.call_args
            assert "Error loading tools" in call_args[0][0]
            assert "Connection error" in call_args[0][0]
            assert call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_load_tools_query_one_error(self):
        mock_app = MagicMock()
        mock_mcp = MockMCPManager(status={})
        mock_app.mcp_manager = mock_mcp

        with patch.object(
            ToolsScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ToolsScreen()
            screen.query_one = MagicMock(side_effect=Exception("Query failed"))
            screen.notify = MagicMock()

            await screen._load_tools_refactored()

            screen.notify.assert_called_once()
            assert "Error loading tools" in screen.notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_load_tools_removes_children_before_error(self):
        mock_app = MagicMock()
        mock_mcp = MockMCPManager(
            status={"server": {"connected": True, "enabled": True}}
        )
        mock_app.mcp_manager = mock_mcp

        mock_container = MagicMock()
        mock_container.remove_children = MagicMock()
        mock_container.mount = MagicMock(side_effect=Exception("Mount failed"))

        with patch.object(
            ToolsScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ToolsScreen()
            screen.query_one = MagicMock(return_value=mock_container)
            screen.notify = MagicMock()

            await screen._load_tools_refactored()

            mock_container.remove_children.assert_called_once()


class TestToolsScreenLoadToolsRefactored:
    @pytest.mark.asyncio
    async def test_load_tools_no_servers_calls_mount_with_label(self):
        mock_app = MagicMock()
        mock_mcp = MockMCPManager(status={})
        mock_app.mcp_manager = mock_mcp

        mock_container = MagicMock()
        mock_container.remove_children = MagicMock()
        mock_container.mount = MagicMock()

        with patch.object(
            ToolsScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ToolsScreen()
            screen.query_one = MagicMock(return_value=mock_container)

            await screen._load_tools_refactored()

            mock_container.remove_children.assert_called_once()
            mock_container.mount.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_tools_calls_get_status(self):
        mock_app = MagicMock()
        mock_mcp = MagicMock()
        mock_mcp.get_status.return_value = {}
        mock_mcp.clients = {}
        mock_app.mcp_manager = mock_mcp

        mock_container = MagicMock()
        mock_container.remove_children = MagicMock()
        mock_container.mount = MagicMock()

        with patch.object(
            ToolsScreen, "app", new_callable=PropertyMock, return_value=mock_app
        ):
            screen = ToolsScreen()
            screen.query_one = MagicMock(return_value=mock_container)

            await screen._load_tools_refactored()

            mock_mcp.get_status.assert_called_once()


class TestMockMCPTool:
    def test_mock_mcp_tool_init(self):
        tool = MockMCPTool(
            name="test",
            description="A test tool",
            input_schema={"type": "object"},
            server_name="server1",
        )
        assert tool.name == "test"
        assert tool.description == "A test tool"
        assert tool.input_schema == {"type": "object"}
        assert tool.server_name == "server1"

    def test_mock_mcp_tool_none_description(self):
        tool = MockMCPTool(
            name="test",
            description=None,
            input_schema={},
            server_name="server1",
        )
        assert tool.description is None


class TestMockMCPClient:
    def test_mock_mcp_client_default(self):
        client = MockMCPClient()
        assert client.tools == []
        assert client.is_connected is True

    def test_mock_mcp_client_with_tools(self):
        tool = MockMCPTool("t", "d", {}, "s")
        client = MockMCPClient(tools=[tool])
        assert len(client.tools) == 1
        assert client.tools[0] == tool

    def test_mock_mcp_client_disconnected(self):
        client = MockMCPClient()
        client._connected = False
        assert client.is_connected is False


class TestMockMCPManager:
    def test_mock_mcp_manager_default(self):
        manager = MockMCPManager()
        assert manager.get_status() == {}
        assert manager.clients == {}

    def test_mock_mcp_manager_with_status(self):
        status = {"server1": {"connected": True}}
        manager = MockMCPManager(status=status)
        assert manager.get_status() == status

    def test_mock_mcp_manager_with_clients(self):
        manager = MockMCPManager()
        client = MockMCPClient()
        manager.clients["test"] = client
        assert "test" in manager.clients
