"""MCP client for communicating with MCP servers."""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from .config import MCPServerConfig


@dataclass
class MCPTool:
    """Represents an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str


@dataclass
class MCPResource:
    """Represents an MCP resource."""

    uri: str
    name: str
    description: str
    mime_type: str
    server_name: str


class MCPClient:
    """Client for communicating with a single MCP server via stdio."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: asyncio.subprocess.Process | None = None
        self.tools: list[MCPTool] = []
        self.resources: list[MCPResource] = []
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._read_task: asyncio.Task | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.process is not None

    async def connect(self) -> bool:
        """Start the MCP server process and initialize."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.config.env)

            # Start the process
            self.process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Start reading responses
            self._read_task = asyncio.create_task(self._read_loop())

            # Initialize the connection
            result = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}},
                    "clientInfo": {"name": "null-terminal", "version": "1.0.0"},
                },
            )

            if result:
                # Send initialized notification
                await self._send_notification("notifications/initialized", {})

                # Discover tools
                await self._discover_tools()
                await self._discover_resources()

                self._connected = True
                return True

        except Exception as e:
            print(f"MCP connect error ({self.config.name}): {e}")
            await self.disconnect()

        return False

    async def disconnect(self):
        """Disconnect from the MCP server."""
        self._connected = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except TimeoutError:
                self.process.kill()
            except Exception:
                pass
            self.process = None

        self.tools = []
        self.resources = []
        self._pending_requests.clear()

    async def _read_loop(self):
        """Read responses from the server."""
        try:
            while self.process and self.process.stdout:
                line = await self.process.stdout.readline()
                if not line:
                    break

                try:
                    message = json.loads(line.decode("utf-8"))
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    continue

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"MCP read error ({self.config.name}): {e}")

    async def _handle_message(self, message: dict[str, Any]):
        """Handle incoming message from server."""
        if "id" in message:
            # Response to a request
            request_id = message["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if "error" in message:
                    future.set_exception(
                        Exception(message["error"].get("message", "Unknown error"))
                    )
                else:
                    future.set_result(message.get("result"))

    async def _send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Send a request and wait for response."""
        if not self.process or not self.process.stdin:
            raise Exception("Not connected")

        self._request_id += 1
        request_id = self._request_id

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        data = json.dumps(message) + "\n"
        self.process.stdin.write(data.encode("utf-8"))
        await self.process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except TimeoutError as e:
            self._pending_requests.pop(request_id, None)
            raise Exception(f"Request timeout: {method}") from e

    async def _send_notification(self, method: str, params: dict[str, Any]):
        """Send a notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return

        message = {"jsonrpc": "2.0", "method": method, "params": params}

        data = json.dumps(message) + "\n"
        self.process.stdin.write(data.encode("utf-8"))
        await self.process.stdin.drain()

    async def _discover_tools(self):
        """Discover available tools from the server."""
        try:
            result = await self._send_request("tools/list", {})
            self.tools = []
            for tool_data in result.get("tools", []):
                self.tools.append(
                    MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=self.config.name,
                    )
                )
        except Exception as e:
            print(f"Error discovering tools ({self.config.name}): {e}")

    async def _discover_resources(self):
        """Discover available resources from the server."""
        try:
            result = await self._send_request("resources/list", {})
            self.resources = []
            for res_data in result.get("resources", []):
                self.resources.append(
                    MCPResource(
                        uri=res_data["uri"],
                        name=res_data.get("name", res_data["uri"]),
                        description=res_data.get("description", ""),
                        mime_type=res_data.get("mimeType", "text/plain"),
                        server_name=self.config.name,
                    )
                )
        except Exception:
            # Resources are optional, don't error
            pass

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the server."""
        if not self.is_connected:
            raise Exception("Not connected")

        result = await self._send_request(
            "tools/call", {"name": name, "arguments": arguments}
        )

        return result

    async def read_resource(self, uri: str) -> str:
        """Read a resource from the server."""
        if not self.is_connected:
            raise Exception("Not connected")

        result = await self._send_request("resources/read", {"uri": uri})

        contents = result.get("contents", [])
        if contents:
            text: str = contents[0].get("text", "")
            return text
        return ""
