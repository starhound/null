from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Collapsible,
    Label,
    Markdown,
)

from .base import Binding, ModalScreen


class ToolsScreen(ModalScreen):
    """Screen to list active MCP servers and tools."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Container(id="tools-container"):
            yield Label("MCP Tools", id="tools-title")

            with VerticalScroll(id="tools-list"):
                yield Label("Loading...", id="tools-loading")

            yield Button("Close", variant="default", id="close_btn")

    async def on_mount(self):
        """Load tools on mount."""
        self.run_worker(self._load_tools())

    async def _load_tools(self):
        """Fetch tools from MCP manager."""
        try:
            mcp = self.app.mcp_manager
            status = mcp.get_status()

            container = self.query_one("#tools-list", VerticalScroll)
            loading = self.query_one("#tools-loading", Label)
            loading.remove()

            if not status:
                container.mount(Label("No MCP servers configured."))
                return

            for server_name, info in status.items():
                # Server Header
                conn_status = "🟢" if info["connected"] else "🔴"
                enabled_status = "" if info["enabled"] else "(Disabled)"
                header_text = f"{conn_status} {server_name} {enabled_status}"

                with Vertical(classes="server-block"):
                    yield Label(header_text, classes="server-header")

                    if info["connected"]:
                        client = mcp.clients.get(server_name)
                        if client and client.tools:
                            for tool in client.tools:
                                with Collapsible(title=tool.name):
                                    desc = tool.description or "No description."
                                    yield Markdown(f"**Description:** {desc}")
                                    yield Markdown(f"```json\n{tool.input_schema}\n```")
                        else:
                            yield Label("  No tools available", classes="no-tools")
                    else:
                        yield Label("  Not connected", classes="server-disconnected")

            # Re-mount (since we used yield inside a loop helper which doesn't work directly with container.mount easily
            # unless we restructure. Let's restructure to build widgets then mount.)
            pass  # Placeholder, refactoring below logic

        except Exception as e:
            self.notify(f"Error loading tools: {e}", severity="error")

    async def _load_tools_refactored(self):
        """Fetch tools from MCP manager."""
        try:
            mcp = self.app.mcp_manager
            status = mcp.get_status()

            container = self.query_one("#tools-list", VerticalScroll)
            container.remove_children()

            if not status:
                container.mount(Label("No MCP servers configured."))
                return

            for server_name, info in status.items():
                conn_status = "🟢" if info["connected"] else "🔴"
                enabled_status = "" if info["enabled"] else "(Disabled)"
                header_text = f"{conn_status} {server_name} {enabled_status}"

                # Check for tools if connected
                tools_widgets = []
                if info["connected"]:
                    client = mcp.clients.get(server_name)
                    if client and client.tools:
                        for tool in client.tools:
                            desc = tool.description or "No description."
                            # Create Collapsible for each tool
                            c = Collapsible(title=f"🔧 {tool.name}")
                            c.mount(
                                Markdown(
                                    f"{desc}\n\n**Schema:**\n```json\n{tool.input_schema}\n```"
                                )
                            )
                            tools_widgets.append(c)
                    else:
                        tools_widgets.append(
                            Label("  No tools available", classes="no-tools")
                        )
                else:
                    tools_widgets.append(
                        Label("  Not connected", classes="server-disconnected")
                    )

                # Create a group for this server
                server_group = Vertical(classes="server-block")
                header_lbl = Label(header_text, classes="server-header")
                # Add some color to header based on status
                if info["connected"]:
                    header_lbl.add_class("connected")

                server_group.mount(header_lbl)
                for w in tools_widgets:
                    server_group.mount(w)

                container.mount(server_group)

        except Exception as e:
            self.notify(f"Error loading tools: {e}", severity="error")

    # Override on_mount to call the refactored version
    async def on_mount(self):
        self.run_worker(self._load_tools_refactored())

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss()

    def action_dismiss(self):
        self.dismiss()
