"""Tests for tools/registry.py - ToolRegistry, ToolCall, and ToolResult."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tools.builtin import BUILTIN_TOOLS
from tools.registry import ToolCall, ToolRegistry, ToolResult


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_tool_call_creation(self):
        """Should create ToolCall with required fields."""
        call = ToolCall(
            id="call_123",
            name="test_tool",
            arguments={"arg1": "value1"},
        )
        assert call.id == "call_123"
        assert call.name == "test_tool"
        assert call.arguments == {"arg1": "value1"}

    def test_tool_call_empty_arguments(self):
        """Should accept empty arguments dict."""
        call = ToolCall(id="call_1", name="no_args", arguments={})
        assert call.arguments == {}

    def test_tool_call_complex_arguments(self):
        """Should accept complex nested arguments."""
        call = ToolCall(
            id="call_complex",
            name="complex_tool",
            arguments={
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "number": 42,
            },
        )
        assert call.arguments["nested"]["key"] == "value"
        assert call.arguments["list"] == [1, 2, 3]
        assert call.arguments["number"] == 42


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_tool_result_success(self):
        """Should create successful result."""
        result = ToolResult(
            tool_call_id="call_123",
            content="Success message",
        )
        assert result.tool_call_id == "call_123"
        assert result.content == "Success message"
        assert result.is_error is False

    def test_tool_result_error(self):
        """Should create error result."""
        result = ToolResult(
            tool_call_id="call_456",
            content="Error occurred",
            is_error=True,
        )
        assert result.is_error is True
        assert "Error" in result.content

    def test_tool_result_default_not_error(self):
        """is_error should default to False."""
        result = ToolResult(tool_call_id="test", content="output")
        assert result.is_error is False


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_registry_initialization(self):
        """Should initialize with built-in tools."""
        registry = ToolRegistry()
        assert registry.mcp_manager is None
        assert len(registry._builtin_tools) == len(BUILTIN_TOOLS)

    def test_registry_with_mcp_manager(self):
        """Should accept MCP manager."""
        mock_mcp = MagicMock()
        registry = ToolRegistry(mcp_manager=mock_mcp)
        assert registry.mcp_manager is mock_mcp

    def test_get_tool_existing(self):
        """Should return existing tool by name."""
        registry = ToolRegistry()
        tool = registry.get_tool("run_command")
        assert tool is not None
        assert tool.name == "run_command"

    def test_get_tool_nonexistent(self):
        """Should return None for non-existent tool."""
        registry = ToolRegistry()
        tool = registry.get_tool("nonexistent")
        assert tool is None

    def test_is_mcp_tool_true(self):
        """Should identify MCP tools by prefix."""
        registry = ToolRegistry()
        assert registry.is_mcp_tool("mcp_some_tool") is True
        assert registry.is_mcp_tool("mcp_") is True

    def test_is_mcp_tool_false(self):
        """Should not identify regular tools as MCP."""
        registry = ToolRegistry()
        assert registry.is_mcp_tool("run_command") is False
        assert registry.is_mcp_tool("some_mcp") is False
        assert registry.is_mcp_tool("") is False


class TestToolRegistryApproval:
    """Tests for tool approval checking."""

    def test_requires_approval_builtin(self):
        """Should check built-in tool approval setting."""
        registry = ToolRegistry()

        # run_command requires approval
        assert registry.requires_approval("run_command") is True

        # read_file does not require approval
        assert registry.requires_approval("read_file") is False

    def test_requires_approval_mcp_always_true(self):
        """MCP tools should always require approval."""
        registry = ToolRegistry()
        assert registry.requires_approval("mcp_any_tool") is True
        assert registry.requires_approval("mcp_safe_tool") is True

    def test_requires_approval_unknown_tool(self):
        """Unknown tools should require approval."""
        registry = ToolRegistry()
        assert registry.requires_approval("unknown_tool") is True


class TestToolRegistrySchema:
    """Tests for tool schema generation."""

    def test_get_all_tools_schema_format(self):
        """Should return OpenAI-compatible format."""
        registry = ToolRegistry()
        tools = registry.get_all_tools_schema()

        assert isinstance(tools, list)
        assert len(tools) >= len(BUILTIN_TOOLS)

        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_get_all_tools_schema_includes_builtins(self):
        """Should include all built-in tools."""
        registry = ToolRegistry()
        tools = registry.get_all_tools_schema()

        tool_names = {t["function"]["name"] for t in tools}
        for builtin in BUILTIN_TOOLS:
            assert builtin.name in tool_names

    def test_get_ollama_tools_schema_format(self):
        """Should return Ollama-compatible format."""
        registry = ToolRegistry()
        tools = registry.get_ollama_tools_schema()

        assert isinstance(tools, list)
        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool

    def test_schema_with_mcp_tools(self):
        """Should include MCP tools with prefix."""
        mock_mcp = MagicMock()
        mock_tool = MagicMock()
        mock_tool.name = "fetch_data"
        mock_tool.description = "Fetches data from API"
        mock_tool.input_schema = {"type": "object", "properties": {}}
        mock_tool.server_name = "test_server"
        mock_mcp.get_all_tools.return_value = [mock_tool]

        registry = ToolRegistry(mcp_manager=mock_mcp)
        tools = registry.get_all_tools_schema()

        # Find MCP tool
        mcp_tools = [t for t in tools if t["function"]["name"].startswith("mcp_")]
        assert len(mcp_tools) == 1
        assert mcp_tools[0]["function"]["name"] == "mcp_fetch_data"
        assert "[MCP: test_server]" in mcp_tools[0]["function"]["description"]


class TestToolRegistryExecution:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_execute_builtin_tool(self, temp_dir):
        """Should execute built-in tool."""
        registry = ToolRegistry()
        call = ToolCall(
            id="call_1",
            name="list_directory",
            arguments={"path": str(temp_dir)},
        )

        result = await registry.execute_tool(call)

        assert result.tool_call_id == "call_1"
        assert result.is_error is False

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Should return error for unknown tool."""
        registry = ToolRegistry()
        call = ToolCall(
            id="call_unknown",
            name="nonexistent_tool",
            arguments={},
        )

        result = await registry.execute_tool(call)

        assert result.is_error is True
        assert "Unknown tool" in result.content

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_no_manager(self):
        """Should return error when MCP manager not available."""
        registry = ToolRegistry(mcp_manager=None)
        call = ToolCall(
            id="call_mcp",
            name="mcp_some_tool",
            arguments={},
        )

        result = await registry.execute_tool(call)

        assert result.is_error is True
        assert "MCP not available" in result.content

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_with_manager(self):
        """Should call MCP manager for MCP tools."""
        mock_mcp = MagicMock()
        mock_mcp.call_tool = AsyncMock(return_value="MCP result")

        registry = ToolRegistry(mcp_manager=mock_mcp)
        call = ToolCall(
            id="call_mcp",
            name="mcp_fetch",
            arguments={"url": "http://example.com"},
        )

        result = await registry.execute_tool(call)

        mock_mcp.call_tool.assert_called_once_with("fetch", {"url": "http://example.com"})
        assert result.is_error is False
        assert result.content == "MCP result"

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self):
        """Should handle exceptions gracefully."""
        registry = ToolRegistry()

        # Create a tool call that will cause an error
        call = ToolCall(
            id="call_error",
            name="read_file",
            arguments={},  # Missing required 'path' argument
        )

        result = await registry.execute_tool(call)

        assert result.is_error is True
        assert "Error executing tool" in result.content


class TestExtractMCPContent:
    """Tests for MCP content extraction."""

    def test_extract_string_content(self):
        """Should return string content directly."""
        registry = ToolRegistry()
        result = registry._extract_mcp_content("Hello, World!")
        assert result == "Hello, World!"

    def test_extract_dict_with_text_content(self):
        """Should extract text from MCP format."""
        registry = ToolRegistry()
        mcp_result = {
            "content": [
                {"type": "text", "text": "First line"},
                {"type": "text", "text": "Second line"},
            ]
        }

        result = registry._extract_mcp_content(mcp_result)
        assert "First line" in result
        assert "Second line" in result

    def test_extract_dict_with_string_items(self):
        """Should handle string items in content list."""
        registry = ToolRegistry()
        mcp_result = {"content": ["Line 1", "Line 2"]}

        result = registry._extract_mcp_content(mcp_result)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_extract_empty_content(self):
        """Should fall back to str() for empty content list."""
        registry = ToolRegistry()
        mcp_result = {"content": []}

        result = registry._extract_mcp_content(mcp_result)
        # Empty list is falsy, so falls through to str(result)
        assert result == str(mcp_result)

    def test_extract_non_text_content(self):
        """Should ignore non-text content types."""
        registry = ToolRegistry()
        mcp_result = {
            "content": [
                {"type": "image", "data": "..."},
                {"type": "text", "text": "Visible"},
            ]
        }

        result = registry._extract_mcp_content(mcp_result)
        assert "Visible" in result

    def test_extract_fallback_to_str(self):
        """Should fall back to str() for unexpected types."""
        registry = ToolRegistry()

        result = registry._extract_mcp_content(12345)
        assert result == "12345"

        result = registry._extract_mcp_content(["a", "b"])
        assert "a" in result
