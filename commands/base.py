"""Base command utilities."""

from __future__ import annotations
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app import NullApp


class CommandMixin:
    """Mixin class providing common command utilities."""

    app: "NullApp"

    async def show_output(self, title: str, content: str):
        """Display system output in a block."""
        await self.app._show_system_output(title, content)

    def notify(self, message: str, severity: str = "information"):
        """Show a notification."""
        self.app.notify(message, severity=severity)
