from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class AIProfile(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_profile(self, args: list[str]):
        """Manage agent profiles. Usage: /profile [list|<name>|create|edit|export|import|delete]"""
        if not args:
            await self._profile_list()
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            await self._profile_list()
        elif subcommand == "create":
            await self._profile_create(args[1:] if len(args) > 1 else [])
        elif subcommand == "edit":
            if len(args) > 1:
                await self._profile_edit(args[1])
            else:
                self.notify("Usage: /profile edit <name>", severity="warning")
        elif subcommand == "export":
            if len(args) > 1:
                await self._profile_export(args[1])
            else:
                self.notify("Usage: /profile export <name>", severity="warning")
        elif subcommand == "import":
            if len(args) > 1:
                await self._profile_import(args[1])
            else:
                self.notify("Usage: /profile import <file>", severity="warning")
        elif subcommand == "delete":
            if len(args) > 1:
                await self._profile_delete(args[1])
            else:
                self.notify("Usage: /profile delete <name>", severity="warning")
        elif subcommand == "active":
            await self._profile_active()
        else:
            await self._profile_activate(subcommand)

    async def _profile_list(self):
        """List all available profiles."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profiles = pm.list_profiles()
        if not profiles:
            await self.show_output("/profile list", "No profiles available.")
            return

        lines = ["Available Agent Profiles:", "=" * 60, ""]

        for profile in profiles:
            source_label = "[builtin]" if profile.source == "builtin" else "[local]"
            active_marker = " ← active" if pm.active_profile_id == profile.id else ""
            lines.append(
                f"{profile.icon} {profile.name:25} {source_label:10}{active_marker}"
            )
            lines.append(f"   ID: {profile.id}")
            lines.append(f"   {profile.description}")
            if profile.tags:
                lines.append(f"   Tags: {', '.join(profile.tags)}")
            lines.append("")

        lines.extend(
            [
                "Commands:",
                "  /profile <name>           - Activate a profile",
                "  /profile create           - Create new profile",
                "  /profile edit <name>      - Edit a profile",
                "  /profile export <name>    - Export profile to YAML",
                "  /profile import <file>    - Import profile from YAML",
                "  /profile delete <name>    - Delete a profile",
                "  /profile active           - Show active profile",
            ]
        )

        await self.show_output("/profile list", "\n".join(lines))

    async def _profile_activate(self, profile_id: str):
        """Activate a profile by ID or name."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profile = pm.get_profile(profile_id)
        if not profile:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        pm.activate(profile_id)
        self.notify(f"Activated profile: {profile.name}")

        lines = [
            f"Profile: {profile.icon} {profile.name}",
            f"Description: {profile.description}",
            "",
            "Configuration:",
            f"  Temperature: {profile.temperature}",
            f"  Max Iterations: {profile.max_iterations}",
            f"  Max Tokens: {profile.max_tokens or 'unlimited'}",
        ]

        if profile.allowed_tools:
            lines.append(f"  Allowed Tools: {', '.join(profile.allowed_tools)}")
        else:
            lines.append("  Allowed Tools: all")

        if profile.blocked_tools:
            lines.append(f"  Blocked Tools: {', '.join(profile.blocked_tools)}")

        if profile.require_approval:
            lines.append(f"  Requires Approval: {', '.join(profile.require_approval)}")

        if profile.auto_include_files:
            lines.append(
                f"  Auto-Include Files: {', '.join(profile.auto_include_files)}"
            )

        await self.show_output(f"/profile {profile_id}", "\n".join(lines))

    async def _profile_active(self):
        """Show the currently active profile."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        if not pm.active_profile:
            self.notify("No active profile. Use /profile <name> to activate one.")
            return

        profile = pm.active_profile
        lines = [
            f"Active Profile: {profile.icon} {profile.name}",
            f"ID: {profile.id}",
            f"Description: {profile.description}",
            "",
            "Configuration:",
            f"  Temperature: {profile.temperature}",
            f"  Max Iterations: {profile.max_iterations}",
            f"  Max Tokens: {profile.max_tokens or 'unlimited'}",
        ]

        if profile.system_prompt:
            lines.extend(["", "System Prompt:", profile.system_prompt[:500]])
            if len(profile.system_prompt) > 500:
                lines.append("... (truncated)")

        await self.show_output("/profile active", "\n".join(lines))

    async def _profile_create(self, args: list[str]):
        """Create a new profile interactively."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        if args and args[0] == "from":
            if len(args) < 2:
                self.notify(
                    "Usage: /profile create from <source_id> <new_id> <new_name>",
                    severity="warning",
                )
                return

            source_id = args[1]
            new_id = args[2] if len(args) > 2 else source_id + "_copy"
            new_name = " ".join(args[3:]) if len(args) > 3 else f"{source_id} (Copy)"

            profile = pm.duplicate_profile(source_id, new_id, new_name)
            if profile:
                self.notify(f"Created profile: {new_id}")
                await self._profile_activate(new_id)
            else:
                self.notify(
                    f"Could not duplicate profile: {source_id}", severity="error"
                )
        else:
            self.notify(
                "Interactive profile creation not yet implemented. Use /profile create from <source_id>"
            )

    async def _profile_edit(self, profile_id: str):
        """Edit a profile."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profile = pm.get_profile(profile_id)
        if not profile:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        if profile.source == "builtin":
            self.notify(
                "Cannot edit builtin profiles. Duplicate and edit the copy.",
                severity="warning",
            )
            return

        self.notify(
            "Profile editing UI not yet implemented. Use /profile export to view/edit YAML."
        )

    async def _profile_export(self, profile_id: str):
        """Export a profile to YAML."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        yaml_content = pm.export_profile(profile_id)
        if not yaml_content:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        await self.show_output(f"/profile export {profile_id}", yaml_content)

    async def _profile_import(self, file_path: str):
        """Import a profile from YAML file."""
        from managers.profiles import ProfileManager
        from pathlib import Path

        try:
            yaml_file = Path(file_path).expanduser()
            if not yaml_file.exists():
                self.notify(f"File not found: {file_path}", severity="error")
                return

            content = yaml_file.read_text(encoding="utf-8")
            pm = ProfileManager()
            pm.initialize()

            profile = pm.import_profile(content)
            if profile:
                self.notify(f"Imported profile: {profile.id}")
                await self._profile_activate(profile.id)
            else:
                self.notify(
                    "Failed to import profile. Check YAML format.", severity="error"
                )
        except Exception as e:
            self.notify(f"Import error: {e}", severity="error")

    async def _profile_delete(self, profile_id: str):
        """Delete a profile."""
        from managers.profiles import ProfileManager

        pm = ProfileManager()
        pm.initialize()

        profile = pm.get_profile(profile_id)
        if not profile:
            self.notify(f"Profile not found: {profile_id}", severity="error")
            return

        if profile.source == "builtin":
            self.notify("Cannot delete builtin profiles.", severity="warning")
            return

        if pm.delete_profile(profile_id):
            self.notify(f"Deleted profile: {profile_id}")
        else:
            self.notify(f"Failed to delete profile: {profile_id}", severity="error")
