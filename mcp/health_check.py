"""MCP Health Check - periodic monitoring of MCP server connections."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import MCPManager


class HealthStatus(Enum):
    """Health status of an MCP server."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"


@dataclass
class ServerHealth:
    """Health information for a single server."""

    name: str
    status: HealthStatus
    last_check: float
    consecutive_failures: int = 0
    last_error: str | None = None


class MCPHealthChecker:
    """Periodic health checker for MCP servers."""

    def __init__(
        self,
        manager: "MCPManager",
        check_interval: float = 30.0,
        on_status_change: Callable[[str, HealthStatus, HealthStatus], None]
        | None = None,
    ):
        self.manager = manager
        self.check_interval = check_interval
        self._on_status_change = on_status_change

        self._health: dict[str, ServerHealth] = {}
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def get_health(self, server_name: str) -> ServerHealth | None:
        """Get health status for a specific server."""
        return self._health.get(server_name)

    def get_all_health(self) -> dict[str, ServerHealth]:
        """Get health status for all monitored servers."""
        return self._health.copy()

    async def start(self):
        """Start the health check loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop())

    async def stop(self):
        """Stop the health check loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def check_now(self) -> dict[str, ServerHealth]:
        """Run an immediate health check on all servers."""
        await self._check_all_servers()
        return self.get_all_health()

    async def _check_loop(self):
        """Background loop for periodic health checks."""
        try:
            while self._running:
                await self._check_all_servers()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            pass

    async def _check_all_servers(self):
        """Check health of all connected servers."""
        import time

        now = time.time()

        for name, client in list(self.manager.clients.items()):
            old_health = self._health.get(name)
            old_status = old_health.status if old_health else None

            new_status, error = await self._ping_server(name)

            if name in self._health:
                health = self._health[name]
                health.last_check = now
                health.last_error = error

                if new_status == HealthStatus.HEALTHY:
                    health.consecutive_failures = 0
                else:
                    health.consecutive_failures += 1

                health.status = new_status
            else:
                self._health[name] = ServerHealth(
                    name=name,
                    status=new_status,
                    last_check=now,
                    consecutive_failures=0 if new_status == HealthStatus.HEALTHY else 1,
                    last_error=error,
                )

            if old_status and old_status != new_status and self._on_status_change:
                self._on_status_change(name, old_status, new_status)

            if new_status == HealthStatus.DISCONNECTED:
                asyncio.create_task(self._attempt_reconnect(name))

        for name in list(self._health.keys()):
            if name not in self.manager.clients:
                del self._health[name]

    async def _ping_server(self, name: str) -> tuple[HealthStatus, str | None]:
        """Ping a server to check its health."""
        client = self.manager.clients.get(name)
        if not client:
            return HealthStatus.DISCONNECTED, "Client not found"

        if not client.is_connected:
            return HealthStatus.DISCONNECTED, "Not connected"

        try:
            await asyncio.wait_for(
                client._send_request("ping", {}),
                timeout=5.0,
            )
            return HealthStatus.HEALTHY, None
        except asyncio.TimeoutError:
            return HealthStatus.DEGRADED, "Ping timeout"
        except Exception:
            try:
                await asyncio.wait_for(
                    client._send_request("tools/list", {}),
                    timeout=5.0,
                )
                return HealthStatus.HEALTHY, None
            except asyncio.TimeoutError:
                return HealthStatus.DEGRADED, "Request timeout"
            except Exception as e2:
                return HealthStatus.DISCONNECTED, str(e2)

    async def _attempt_reconnect(self, name: str):
        """Attempt to reconnect a disconnected server."""
        try:
            success = await self.manager.reconnect_server(name)
            if success:
                health = self._health.get(name)
                if health:
                    old_status = health.status
                    health.status = HealthStatus.HEALTHY
                    health.consecutive_failures = 0
                    health.last_error = None

                    if self._on_status_change:
                        self._on_status_change(name, old_status, HealthStatus.HEALTHY)
        except Exception:
            pass
