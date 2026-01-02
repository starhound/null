"""Configuration commands: config, settings, theme."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from .base import CommandMixin
from config import Config


class ConfigCommands(CommandMixin):
    """Configuration-related commands."""

    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_config(self, args: list[str]):
        """Open settings screen."""
        from screens import ConfigScreen

        def on_settings_saved(result):
            if result:
                new_theme = result.appearance.theme
                if new_theme and new_theme in self.app.available_themes:
                    self.app.theme = new_theme

                self.notify("Settings saved")
                self.app._update_status_bar()

        self.app.push_screen(ConfigScreen(), on_settings_saved)

    async def cmd_settings(self, args: list[str]):
        """Open settings screen (alias)."""
        await self.cmd_config(args)

    async def cmd_theme(self, args: list[str]):
        """Set theme."""
        if not args:
            self.app.action_select_theme()
            return

        theme_name = args[0]
        if theme_name in self.app.available_themes:
            Config.update_key(["theme"], theme_name)
            self.app.theme = theme_name
            self.notify(f"Theme set to {theme_name}")
        else:
            self.notify(f"Unknown theme: {theme_name}", severity="error")
