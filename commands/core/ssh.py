from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import NullApp

from ..base import CommandMixin


class SSHCommands(CommandMixin):
    def __init__(self, app: "NullApp"):
        self.app = app

    async def cmd_ssh(self, args: list[str]):
        """Connect to SSH host."""
        if not args:
            self.notify("Usage: /ssh <alias_or_host>", severity="warning")
            return

        target = args[0]
        # Implementation needed for actual SSH connection logic which involves widgets/ssh_terminal.py
        self.notify(f"Connecting to {target}...")
        # Logic to launch SSH terminal block

    async def cmd_ssh_add(self, args: list[str]):
        """Add SSH host."""
        from screens.ssh_add import SSHAddScreen

        self.app.push_screen(SSHAddScreen())

    async def cmd_ssh_list(self, args: list[str]):
        """List SSH hosts."""
        from config import Config

        storage = Config._get_storage()
        hosts = storage.list_ssh_hosts()

        if not hosts:
            self.notify("No SSH hosts saved.")
            return

        lines = ["Saved SSH Hosts:", "=" * 20, ""]
        for h in hosts:
            lines.append(f"{h['alias']:15} {h['username']}@{h['hostname']}:{h['port']}")

        await self.show_output("/ssh-list", "\n".join(lines))

    async def cmd_ssh_del(self, args: list[str]):
        """Delete SSH host."""
        if not args:
            self.notify("Usage: /ssh-del <alias>", severity="warning")
            return

        alias = args[0]
        from config import Config

        storage = Config._get_storage()
        storage.delete_ssh_host(alias)
        self.notify(f"Deleted SSH host: {alias}")
