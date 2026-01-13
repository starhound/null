from typing import ClassVar

from textual.binding import BindingType
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, ListItem, ListView, Static

from mcp.catalog import CATALOG, CATEGORIES, CatalogEntry, get_by_name

from .base import Binding, ComposeResult, ModalScreen


class CatalogItemWidget(Static):
    def __init__(self, entry: CatalogEntry, is_installed: bool = False):
        super().__init__()
        self.entry = entry
        self.is_installed = is_installed

    def compose(self) -> ComposeResult:
        with Horizontal(classes="catalog-item"):
            with Vertical(classes="catalog-item-info"):
                name_label = f"[bold]{self.entry.name}[/bold]"
                if self.is_installed:
                    name_label += " [green][Installed][/green]"
                yield Label(name_label, classes="catalog-name")
                yield Label(self.entry.description, classes="catalog-desc")
                env_text = (
                    ", ".join(self.entry.env_keys) if self.entry.env_keys else "None"
                )
                yield Label(f"[dim]Env: {env_text}[/dim]", classes="catalog-env")

            button_label = "Configure" if self.is_installed else "Install"
            yield Button(
                button_label,
                id=f"install-{self.entry.name}",
                classes="catalog-install-btn",
            )


class MCPCatalogScreen(ModalScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("/", "focus_search", "Search"),
    ]

    def __init__(self, installed_servers: set[str] | None = None):
        super().__init__()
        self.current_category = "all"
        self.search_query = ""
        self.installed_servers = installed_servers or set()

    def compose(self) -> ComposeResult:
        with Container(id="catalog-container"):
            with Vertical(id="catalog-header"):
                yield Label("MCP Server Catalog", id="catalog-title")
                yield Input(placeholder="Search servers...", id="catalog-search")

            with Horizontal(id="catalog-content"):
                with ListView(id="category-list"):
                    yield ListItem(Label("All"), id="cat-all")
                    for cat_id, cat_name in CATEGORIES.items():
                        yield ListItem(Label(cat_name), id=f"cat-{cat_id}")

                with VerticalScroll(id="server-list"):
                    for entry in CATALOG:
                        is_installed = entry.name in self.installed_servers
                        yield CatalogItemWidget(entry, is_installed=is_installed)

            with Horizontal(id="catalog-footer"):
                yield Button("Add Custom", id="add-custom")
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        self.query_one("#catalog-search", Input).focus()

    def action_focus_search(self) -> None:
        self.query_one("#catalog-search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "catalog-search":
            self.search_query = event.value.strip().lower()
            self._filter_servers()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "category-list":
            item_id = event.item.id or ""
            if item_id.startswith("cat-"):
                self.current_category = item_id[4:]
                self._filter_servers()

    def _filter_servers(self) -> None:
        server_list = self.query_one("#server-list", VerticalScroll)

        for widget in server_list.query(CatalogItemWidget):
            entry = widget.entry

            cat_match = (
                self.current_category == "all"
                or entry.category == self.current_category
            )

            if self.search_query:
                search_match = (
                    self.search_query in entry.name.lower()
                    or self.search_query in entry.description.lower()
                )
            else:
                search_match = True

            widget.display = cat_match and search_match

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""

        if button_id == "close":
            self.dismiss(None)
        elif button_id == "add-custom":
            self.dismiss({"action": "custom"})
        elif button_id.startswith("install-"):
            server_name = button_id[8:]
            entry = get_by_name(server_name)
            if entry:
                self.dismiss(
                    {
                        "action": "install",
                        "entry": entry,
                    }
                )

    async def action_dismiss(self, result: object = None) -> None:
        self.dismiss(None)
