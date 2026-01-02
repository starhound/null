"""Tool registry combining built-in and MCP tools."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .builtin import BUILTIN_TOOLS, BuiltinTool, get_builtin_tool

if TYPE_CHECKING:
    from mcp.manager import MCPManager


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_call_id: str
    content: str
    is_error: bool = False


class ToolRegistry:
    """Registry that combines built-in tools with MCP tools."""

    def __init__(self, mcp_manager: Optional["MCPManager"] = None):
        self.mcp_manager = mcp_manager
        self._builtin_tools = {t.name: t for t in BUILTIN_TOOLS}

    def get_all_tools_schema(self) -> List[Dict[str, Any]]:
        """Get all tool schemas in OpenAI-compatible format."""
        tools = []

        # Add built-in tools
        for tool in BUILTIN_TOOLS:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            })

        # Add MCP tools
        if self.mcp_manager:
            for mcp_tool in self.mcp_manager.get_all_tools():
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"mcp_{mcp_tool.name}",  # Prefix to avoid conflicts
                        "description": f"[MCP: {mcp_tool.server_name}] {mcp_tool.description}",
                        "parameters": mcp_tool.input_schema
                    }
                })

        return tools

    def get_ollama_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tool schemas in Ollama format."""
        tools = []

        for tool in BUILTIN_TOOLS:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            })

        if self.mcp_manager:
            for mcp_tool in self.mcp_manager.get_all_tools():
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"mcp_{mcp_tool.name}",
                        "description": f"[MCP: {mcp_tool.server_name}] {mcp_tool.description}",
                        "parameters": mcp_tool.input_schema
                    }
                })

        return tools

    def get_tool(self, name: str) -> Optional[BuiltinTool]:
        """Get a built-in tool by name."""
        return self._builtin_tools.get(name)

    def is_mcp_tool(self, name: str) -> bool:
        """Check if a tool name is an MCP tool."""
        return name.startswith("mcp_")

    def requires_approval(self, name: str) -> bool:
        """Check if a tool requires user approval before execution."""
        if self.is_mcp_tool(name):
            # MCP tools always require approval for safety
            return True

        tool = self.get_tool(name)
        return tool.requires_approval if tool else True

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool and return the result."""
        name = tool_call.name
        args = tool_call.arguments

        try:
            if self.is_mcp_tool(name):
                # Remove mcp_ prefix and call via MCP manager
                mcp_name = name[4:]  # Remove "mcp_" prefix
                if not self.mcp_manager:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        content="MCP not available",
                        is_error=True
                    )

                result = await self.mcp_manager.call_tool(mcp_name, args)
                # Extract text content from MCP result
                content = self._extract_mcp_content(result)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=content
                )

            else:
                # Built-in tool
                tool = self.get_tool(name)
                if not tool:
                    return ToolResult(
                        tool_call_id=tool_call.id,
                        content=f"Unknown tool: {name}",
                        is_error=True
                    )

                result = await tool.handler(**args)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=result
                )

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Error executing tool: {str(e)}",
                is_error=True
            )

    def _extract_mcp_content(self, result: Any) -> str:
        """Extract text content from MCP tool result."""
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # MCP returns {content: [{type: "text", text: "..."}]}
            contents = result.get("content", [])
            if contents:
                texts = []
                for item in contents:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        texts.append(item)
                return "\n".join(texts)

        return str(result)
