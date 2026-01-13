"""Configuration commands: config, settings, theme."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from config import Config

from .base import CommandMixin


class ConfigCommands(CommandMixin):
    """Configuration-related commands."""

    def __init__(self, app: NullApp):
        self.app = app

    async def cmd_config(self, args: list[str]):
        """Open settings screen."""
        from screens import ConfigScreen

        def on_settings_saved(result):
            if result:
                # Apply theme
                new_theme = result.appearance.theme
                if new_theme and new_theme in self.app.available_themes:
                    self.app.theme = new_theme
                    # Also save to SQLite config for persistence
                    Config.set("theme", new_theme)

                # Sync AI provider to SQLite config
                Config.set("ai.provider", result.ai.provider)

                self.notify("Settings saved")
                self.app._update_status_bar()

        self.app.push_screen(ConfigScreen(), on_settings_saved)

    async def cmd_settings(self, args: list[str]):
        """Open settings screen (alias)."""
        await self.cmd_config(args)

    async def cmd_theme(self, args: list[str]):
        """Set theme or open editor."""
        if not args:
            self.app.action_select_theme()
            return

        arg = args[0]
        arg_lower = arg.lower()

        if arg_lower == "edit":
            base_theme = args[1] if len(args) > 1 else self.app.theme
            self._open_theme_editor(base_theme)
        elif arg_lower == "new":
            self._open_theme_editor(None)
        elif arg_lower == "list":
            self._list_themes()
        elif arg in self.app.available_themes:
            Config.update_key(["theme"], arg)
            self.app.theme = arg
            self.notify(f"Theme set to {arg}")
        else:
            self.notify(f"Unknown theme: {arg}", severity="error")

    def _open_theme_editor(self, base_theme: str | None) -> None:
        from screens import ThemeEditorScreen

        def on_editor_result(result: str | None) -> None:
            if result:
                from themes import get_all_themes

                for theme in get_all_themes().values():
                    self.app.register_theme(theme)

                if result in self.app.available_themes:
                    self.app.theme = result
                    Config.update_key(["theme"], result)
                self.notify(f"Theme '{result}' saved and applied")

        self.app.push_screen(ThemeEditorScreen(base_theme), on_editor_result)

    def _list_themes(self) -> None:
        from themes import get_all_themes, is_custom_theme

        themes = get_all_themes()
        lines = ["Available Themes:", ""]

        builtin = []
        custom = []
        for name in sorted(themes.keys()):
            marker = "*" if name == self.app.theme else " "
            if is_custom_theme(name):
                custom.append(f"  {marker} {name} (custom)")
            else:
                builtin.append(f"  {marker} {name}")

        if builtin:
            lines.append("Built-in:")
            lines.extend(builtin)
        if custom:
            lines.append("")
            lines.append("Custom:")
            lines.extend(custom)

        lines.append("")
        lines.append("Commands: /theme <name>, /theme edit, /theme new")
        self.show_output("\n".join(lines))
