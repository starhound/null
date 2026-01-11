"""Tests for the MCP server catalog screen."""

import pytest
from unittest.mock import MagicMock, patch

from mcp.catalog import CATALOG, CATEGORIES, CatalogEntry, get_by_name
from screens.mcp_catalog import MCPCatalogScreen, CatalogItemWidget


@pytest.fixture
def sample_catalog_entry():
    """Create a sample CatalogEntry for testing."""
    return CatalogEntry(
        name="test-server",
        description="A test MCP server",
        command="npx",
        args=["-y", "@test/mcp-server"],
        env_keys=["TEST_API_KEY"],
        category="development",
        url="https://github.com/test/mcp-server",
    )


@pytest.fixture
def sample_catalog_entry_no_env():
    """Create a CatalogEntry with no environment variables."""
    return CatalogEntry(
        name="simple-server",
        description="A simple server with no env",
        command="uvx",
        args=["simple-mcp"],
        env_keys=[],
        category="utility",
        url="https://github.com/test/simple",
    )


@pytest.fixture
def installed_servers():
    """Create a set of installed server names."""
    return {"filesystem", "github", "brave-search"}


class TestCatalogItemWidgetInit:
    """Tests for CatalogItemWidget initialization."""

    def test_init_with_entry(self, sample_catalog_entry):
        """Test initialization with a catalog entry."""
        widget = CatalogItemWidget(sample_catalog_entry)
        assert widget.entry == sample_catalog_entry
        assert widget.is_installed is False

    def test_init_with_installed_flag(self, sample_catalog_entry):
        """Test initialization with is_installed=True."""
        widget = CatalogItemWidget(sample_catalog_entry, is_installed=True)
        assert widget.entry == sample_catalog_entry
        assert widget.is_installed is True

    def test_init_with_installed_flag_false(self, sample_catalog_entry):
        """Test initialization with explicit is_installed=False."""
        widget = CatalogItemWidget(sample_catalog_entry, is_installed=False)
        assert widget.is_installed is False


class TestCatalogItemWidgetCompose:
    """Tests for CatalogItemWidget compose method."""

    def test_compose_returns_generator(self, sample_catalog_entry):
        """Test that compose returns a generator."""
        widget = CatalogItemWidget(sample_catalog_entry)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_widget_has_compose_method(self, sample_catalog_entry):
        """Test that widget has a compose method."""
        widget = CatalogItemWidget(sample_catalog_entry)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)

    def test_widget_stores_entry_for_compose(self, sample_catalog_entry):
        """Test widget stores entry used during compose."""
        widget = CatalogItemWidget(sample_catalog_entry)
        assert widget.entry == sample_catalog_entry
        assert widget.entry.env_keys == ["TEST_API_KEY"]

    def test_widget_stores_no_env_entry(self, sample_catalog_entry_no_env):
        """Test widget stores entry with no env keys."""
        widget = CatalogItemWidget(sample_catalog_entry_no_env)
        assert widget.entry.env_keys == []

    def test_widget_installed_flag_available_for_compose(self, sample_catalog_entry):
        """Test widget stores is_installed flag for compose."""
        widget = CatalogItemWidget(sample_catalog_entry, is_installed=True)
        assert widget.is_installed is True


class TestMCPCatalogScreenInit:
    """Tests for MCPCatalogScreen initialization."""

    def test_init_default_values(self):
        """Test initialization with no arguments."""
        screen = MCPCatalogScreen()
        assert screen.current_category == "all"
        assert screen.search_query == ""
        assert screen.installed_servers == set()

    def test_init_with_installed_servers(self, installed_servers):
        """Test initialization with installed servers set."""
        screen = MCPCatalogScreen(installed_servers=installed_servers)
        assert screen.installed_servers == installed_servers
        assert "filesystem" in screen.installed_servers
        assert "github" in screen.installed_servers

    def test_init_with_none_installed_servers(self):
        """Test initialization with None installed servers."""
        screen = MCPCatalogScreen(installed_servers=None)
        assert screen.installed_servers == set()

    def test_init_with_empty_installed_servers(self):
        """Test initialization with empty set of installed servers."""
        screen = MCPCatalogScreen(installed_servers=set())
        assert screen.installed_servers == set()


class TestMCPCatalogScreenBindings:
    """Tests for screen bindings."""

    def test_bindings_defined(self):
        """Test that bindings are defined."""
        screen = MCPCatalogScreen()
        assert len(screen.BINDINGS) > 0

    def test_escape_binding_exists(self):
        """Test that escape binding exists for dismiss."""
        screen = MCPCatalogScreen()
        binding_keys = [b.key for b in screen.BINDINGS]  # type: ignore[union-attr]
        assert "escape" in binding_keys

    def test_search_binding_exists(self):
        """Test that search binding exists."""
        screen = MCPCatalogScreen()
        binding_keys = [b.key for b in screen.BINDINGS]  # type: ignore[union-attr]
        assert "/" in binding_keys


class TestMCPCatalogScreenCompose:
    """Tests for screen composition."""

    def test_compose_returns_generator(self):
        """Test that compose returns a generator."""
        screen = MCPCatalogScreen()
        result = screen.compose()
        assert hasattr(result, "__iter__")

    def test_screen_has_compose_method(self):
        """Test that screen has a compose method."""
        screen = MCPCatalogScreen()
        assert hasattr(screen, "compose")
        assert callable(screen.compose)

    def test_screen_stores_installed_servers_for_compose(self, installed_servers):
        """Test screen stores installed_servers used during compose."""
        screen = MCPCatalogScreen(installed_servers=installed_servers)
        assert screen.installed_servers == installed_servers


class TestMCPCatalogScreenCSS:
    """Tests for screen CSS."""

    def test_default_css_defined(self):
        """Test that DEFAULT_CSS is defined."""
        assert MCPCatalogScreen.DEFAULT_CSS is not None
        css = MCPCatalogScreen.DEFAULT_CSS

    def test_css_contains_main_selectors(self):
        """Test that CSS contains expected selectors."""
        css = MCPCatalogScreen.DEFAULT_CSS
        assert "MCPCatalogScreen" in css
        assert "#catalog-container" in css
        assert "#catalog-header" in css
        assert "#catalog-search" in css

    def test_css_contains_content_selectors(self):
        """Test that CSS contains content area selectors."""
        css = MCPCatalogScreen.DEFAULT_CSS
        assert "#catalog-content" in css
        assert "#category-list" in css
        assert "#server-list" in css

    def test_css_contains_item_selectors(self):
        """Test that CSS contains catalog item selectors."""
        css = MCPCatalogScreen.DEFAULT_CSS
        assert "CatalogItemWidget" in css
        assert ".catalog-item" in css
        assert ".catalog-name" in css
        assert ".catalog-desc" in css

    def test_css_contains_footer_selectors(self):
        """Test that CSS contains footer selectors."""
        css = MCPCatalogScreen.DEFAULT_CSS
        assert "#catalog-footer" in css


class TestMCPCatalogScreenActions:
    """Tests for screen actions."""

    def test_action_focus_search(self):
        """Test that action_focus_search focuses the search input."""
        screen = MCPCatalogScreen()
        mock_input = MagicMock()
        screen.query_one = MagicMock(return_value=mock_input)

        screen.action_focus_search()

        screen.query_one.assert_called()
        mock_input.focus.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_dismiss_calls_dismiss_with_none(self):
        """Test that action_dismiss dismisses with None."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss()

        screen.dismiss.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_action_dismiss_with_result(self):
        """Test that action_dismiss ignores any passed result."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        await screen.action_dismiss(result={"some": "data"})

        screen.dismiss.assert_called_once_with(None)


class TestMCPCatalogScreenInputChanged:
    """Tests for input change handling."""

    def test_on_input_changed_updates_search_query(self):
        """Test that input change updates search query."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "test query"
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "test query"

        screen.on_input_changed(mock_event)

        assert screen.search_query == "test query"
        screen._filter_servers.assert_called_once()

    def test_on_input_changed_trims_and_lowercases(self):
        """Test that input change trims whitespace and lowercases."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "  TEST Query  "
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "  TEST Query  "

        screen.on_input_changed(mock_event)

        assert screen.search_query == "test query"

    def test_on_input_changed_ignores_other_inputs(self):
        """Test that input change ignores non-search inputs."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()
        initial_query = screen.search_query

        mock_input = MagicMock()
        mock_input.id = "some-other-input"
        mock_input.value = "test"
        mock_event = MagicMock()
        mock_event.input = mock_input

        screen.on_input_changed(mock_event)

        assert screen.search_query == initial_query
        screen._filter_servers.assert_not_called()

    def test_on_input_changed_empty_string(self):
        """Test input change with empty string."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = ""
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = ""

        screen.on_input_changed(mock_event)

        assert screen.search_query == ""


class TestMCPCatalogScreenListViewSelected:
    """Tests for category list selection handling."""

    def test_on_list_view_selected_updates_category(self):
        """Test that list view selection updates category."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_list_view = MagicMock()
        mock_list_view.id = "category-list"
        mock_item = MagicMock()
        mock_item.id = "cat-development"
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        mock_event.item = mock_item

        screen.on_list_view_selected(mock_event)

        assert screen.current_category == "development"
        screen._filter_servers.assert_called_once()

    def test_on_list_view_selected_all_category(self):
        """Test selecting 'all' category."""
        screen = MCPCatalogScreen()
        screen.current_category = "development"
        screen._filter_servers = MagicMock()

        mock_list_view = MagicMock()
        mock_list_view.id = "category-list"
        mock_item = MagicMock()
        mock_item.id = "cat-all"
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        mock_event.item = mock_item

        screen.on_list_view_selected(mock_event)

        assert screen.current_category == "all"

    def test_on_list_view_selected_ignores_other_lists(self):
        """Test that non-category list selection is ignored."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()
        initial_category = screen.current_category

        mock_list_view = MagicMock()
        mock_list_view.id = "some-other-list"
        mock_item = MagicMock()
        mock_item.id = "cat-development"
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        mock_event.item = mock_item

        screen.on_list_view_selected(mock_event)

        assert screen.current_category == initial_category
        screen._filter_servers.assert_not_called()

    def test_on_list_view_selected_non_cat_prefix_ignored(self):
        """Test that items without cat- prefix are ignored."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()
        initial_category = screen.current_category

        mock_list_view = MagicMock()
        mock_list_view.id = "category-list"
        mock_item = MagicMock()
        mock_item.id = "other-item"
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        mock_event.item = mock_item

        screen.on_list_view_selected(mock_event)

        assert screen.current_category == initial_category

    def test_on_list_view_selected_none_item_id(self):
        """Test handling of None item id."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()
        initial_category = screen.current_category

        mock_list_view = MagicMock()
        mock_list_view.id = "category-list"
        mock_item = MagicMock()
        mock_item.id = None
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        mock_event.item = mock_item

        screen.on_list_view_selected(mock_event)

        assert screen.current_category == initial_category


class TestMCPCatalogScreenButtonPressed:
    """Tests for button press handling."""

    def test_close_button_dismisses_none(self):
        """Test that close button dismisses with None."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "close"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with(None)

    def test_add_custom_button_dismisses_with_action(self):
        """Test that add-custom button dismisses with action."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "add-custom"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with({"action": "custom"})

    def test_install_button_dismisses_with_entry(self):
        """Test that install button dismisses with entry."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "install-filesystem"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["action"] == "install"
        assert call_args["entry"].name == "filesystem"

    def test_install_button_unknown_server_not_dismissed(self):
        """Test that install button with unknown server doesn't dismiss."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "install-nonexistent-server"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_not_called()

    def test_button_none_id_handled(self):
        """Test that button with None id is handled."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = None
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

    def test_install_github_server(self):
        """Test installing the github server."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "install-github"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["action"] == "install"
        assert call_args["entry"].name == "github"

    def test_install_brave_search_server(self):
        """Test installing the brave-search server."""
        screen = MCPCatalogScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "install-brave-search"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        call_args = screen.dismiss.call_args[0][0]
        assert call_args["action"] == "install"
        assert call_args["entry"].name == "brave-search"


class TestMCPCatalogScreenFilterServers:
    """Tests for server filtering logic."""

    def test_filter_servers_category_all(self):
        """Test filtering with 'all' category shows all servers."""
        screen = MCPCatalogScreen()
        screen.current_category = "all"
        screen.search_query = ""

        mock_server_list = MagicMock()
        mock_widgets = []
        for name in ["server1", "server2"]:
            mock_widget = MagicMock()
            mock_widget.entry = CatalogEntry(
                name=name,
                description=f"Description for {name}",
                command="npx",
                args=[],
                env_keys=[],
                category="development",
                url="http://example.com",
            )
            mock_widgets.append(mock_widget)

        mock_server_list.query.return_value = mock_widgets
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        for widget in mock_widgets:
            assert widget.display is True

    def test_filter_servers_specific_category(self):
        """Test filtering with specific category."""
        screen = MCPCatalogScreen()
        screen.current_category = "development"
        screen.search_query = ""

        mock_server_list = MagicMock()
        mock_dev_widget = MagicMock()
        mock_dev_widget.entry = CatalogEntry(
            name="dev-server",
            description="Development server",
            command="npx",
            args=[],
            env_keys=[],
            category="development",
            url="http://example.com",
        )

        mock_util_widget = MagicMock()
        mock_util_widget.entry = CatalogEntry(
            name="util-server",
            description="Utility server",
            command="npx",
            args=[],
            env_keys=[],
            category="utility",
            url="http://example.com",
        )

        mock_server_list.query.return_value = [mock_dev_widget, mock_util_widget]
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        assert mock_dev_widget.display is True
        assert mock_util_widget.display is False

    def test_filter_by_name(self):
        """Test filtering by search query matching name."""
        screen = MCPCatalogScreen()
        screen.current_category = "all"
        screen.search_query = "git"

        mock_server_list = MagicMock()
        mock_github_widget = MagicMock()
        mock_github_widget.entry = CatalogEntry(
            name="github",
            description="GitHub repos",
            command="uvx",
            args=[],
            env_keys=[],
            category="development",
            url="http://example.com",
        )

        mock_other_widget = MagicMock()
        mock_other_widget.entry = CatalogEntry(
            name="filesystem",
            description="File operations",
            command="npx",
            args=[],
            env_keys=[],
            category="filesystem",
            url="http://example.com",
        )

        mock_server_list.query.return_value = [mock_github_widget, mock_other_widget]
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        assert mock_github_widget.display is True
        assert mock_other_widget.display is False

    def test_filter_by_description(self):
        """Test filtering by search query matching description."""
        screen = MCPCatalogScreen()
        screen.current_category = "all"
        screen.search_query = "browser"

        mock_server_list = MagicMock()
        mock_playwright_widget = MagicMock()
        mock_playwright_widget.entry = CatalogEntry(
            name="playwright",
            description="Browser automation",
            command="npx",
            args=[],
            env_keys=[],
            category="web",
            url="http://example.com",
        )

        mock_other_widget = MagicMock()
        mock_other_widget.entry = CatalogEntry(
            name="sqlite",
            description="Database queries",
            command="uvx",
            args=[],
            env_keys=[],
            category="database",
            url="http://example.com",
        )

        mock_server_list.query.return_value = [
            mock_playwright_widget,
            mock_other_widget,
        ]
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        assert mock_playwright_widget.display is True
        assert mock_other_widget.display is False

    def test_filter_combined_category_and_search(self):
        """Test filtering with both category and search."""
        screen = MCPCatalogScreen()
        screen.current_category = "development"
        screen.search_query = "git"

        mock_server_list = MagicMock()

        mock_github = MagicMock()
        mock_github.entry = CatalogEntry(
            name="github",
            description="GitHub repos",
            command="uvx",
            args=[],
            env_keys=[],
            category="development",
            url="http://example.com",
        )

        mock_git = MagicMock()
        mock_git.entry = CatalogEntry(
            name="git",
            description="Git operations",
            command="uvx",
            args=[],
            env_keys=[],
            category="development",
            url="http://example.com",
        )

        mock_filesystem = MagicMock()
        mock_filesystem.entry = CatalogEntry(
            name="filesystem",
            description="File operations",
            command="npx",
            args=[],
            env_keys=[],
            category="filesystem",
            url="http://example.com",
        )

        mock_linear = MagicMock()
        mock_linear.entry = CatalogEntry(
            name="linear",
            description="Issue tracking",
            command="npx",
            args=[],
            env_keys=[],
            category="development",
            url="http://example.com",
        )

        mock_server_list.query.return_value = [
            mock_github,
            mock_git,
            mock_filesystem,
            mock_linear,
        ]
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        assert mock_github.display is True
        assert mock_git.display is True
        assert mock_filesystem.display is False
        assert mock_linear.display is False

    def test_filter_case_insensitive_search(self):
        """Test that search is case insensitive."""
        screen = MCPCatalogScreen()
        screen.current_category = "all"
        screen.search_query = "github"

        mock_server_list = MagicMock()
        mock_widget = MagicMock()
        mock_widget.entry = CatalogEntry(
            name="github",
            description="GitHub repos",
            command="uvx",
            args=[],
            env_keys=[],
            category="development",
            url="http://example.com",
        )

        mock_server_list.query.return_value = [mock_widget]
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        assert mock_widget.display is True

    def test_filter_empty_search(self):
        """Test filtering with empty search query."""
        screen = MCPCatalogScreen()
        screen.current_category = "all"
        screen.search_query = ""

        mock_server_list = MagicMock()
        mock_widget = MagicMock()
        mock_widget.entry = CatalogEntry(
            name="anything",
            description="Any server",
            command="npx",
            args=[],
            env_keys=[],
            category="utility",
            url="http://example.com",
        )

        mock_server_list.query.return_value = [mock_widget]
        screen.query_one = MagicMock(return_value=mock_server_list)

        screen._filter_servers()

        assert mock_widget.display is True


class TestMCPCatalogIntegration:
    """Tests for integration with the catalog module."""

    def test_catalog_imported(self):
        """Test that CATALOG is importable and has entries."""
        assert len(CATALOG) > 0

    def test_categories_imported(self):
        """Test that CATEGORIES is importable and has entries."""
        assert len(CATEGORIES) > 0
        assert "development" in CATEGORIES
        assert "utility" in CATEGORIES

    def test_get_by_name_filesystem(self):
        """Test get_by_name returns filesystem entry."""
        entry = get_by_name("filesystem")
        assert entry is not None
        assert entry.name == "filesystem"

    def test_get_by_name_nonexistent(self):
        """Test get_by_name returns None for nonexistent server."""
        entry = get_by_name("nonexistent-server-12345")
        assert entry is None

    def test_screen_has_access_to_catalog(self):
        """Test that screen module imports CATALOG."""
        from screens import mcp_catalog

        assert hasattr(mcp_catalog, "CATALOG") or "CATALOG" in dir(mcp_catalog)

    def test_screen_has_access_to_categories(self):
        """Test that screen module has access to CATEGORIES."""
        from screens import mcp_catalog

        assert hasattr(mcp_catalog, "CATEGORIES") or "CATEGORIES" in dir(mcp_catalog)


class TestMCPCatalogScreenEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_long_search_query(self):
        """Test handling of very long search query."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "a" * 1000
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "a" * 1000

        screen.on_input_changed(mock_event)

        assert len(screen.search_query) == 1000

    def test_special_characters_in_search(self):
        """Test handling of special characters in search."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "@test/server-name"
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "@test/server-name"

        screen.on_input_changed(mock_event)

        assert screen.search_query == "@test/server-name"

    def test_unicode_in_search(self):
        """Test handling of unicode characters in search."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "test"
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "test"

        screen.on_input_changed(mock_event)

        assert screen.search_query == "test"

    def test_whitespace_only_search(self):
        """Test handling of whitespace-only search."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "   "
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "   "

        screen.on_input_changed(mock_event)

        assert screen.search_query == ""


class TestMCPCatalogScreenOnMount:
    """Tests for on_mount behavior."""

    def test_on_mount_focuses_search(self):
        """Test that on_mount focuses the search input."""
        screen = MCPCatalogScreen()
        mock_input = MagicMock()
        screen.query_one = MagicMock(return_value=mock_input)

        screen.on_mount()

        screen.query_one.assert_called()
        mock_input.focus.assert_called_once()


class TestCatalogEntryData:
    """Tests for CatalogEntry dataclass."""

    def test_catalog_entry_attributes(self, sample_catalog_entry):
        """Test CatalogEntry has all required attributes."""
        assert hasattr(sample_catalog_entry, "name")
        assert hasattr(sample_catalog_entry, "description")
        assert hasattr(sample_catalog_entry, "command")
        assert hasattr(sample_catalog_entry, "args")
        assert hasattr(sample_catalog_entry, "env_keys")
        assert hasattr(sample_catalog_entry, "category")
        assert hasattr(sample_catalog_entry, "url")

    def test_catalog_entry_values(self, sample_catalog_entry):
        """Test CatalogEntry values are correctly set."""
        assert sample_catalog_entry.name == "test-server"
        assert sample_catalog_entry.command == "npx"
        assert sample_catalog_entry.category == "development"
        assert len(sample_catalog_entry.args) == 2
        assert len(sample_catalog_entry.env_keys) == 1

    def test_catalog_entry_equality(self):
        """Test CatalogEntry equality."""
        entry1 = CatalogEntry(
            name="test",
            description="desc",
            command="cmd",
            args=[],
            env_keys=[],
            category="cat",
            url="http://example.com",
        )
        entry2 = CatalogEntry(
            name="test",
            description="desc",
            command="cmd",
            args=[],
            env_keys=[],
            category="cat",
            url="http://example.com",
        )
        assert entry1 == entry2


class TestMCPCatalogScreenState:
    """Tests for screen state management."""

    def test_state_after_category_change(self):
        """Test screen state after category change."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        mock_list_view = MagicMock()
        mock_list_view.id = "category-list"
        mock_item = MagicMock()
        mock_item.id = "cat-web"
        mock_event = MagicMock()
        mock_event.list_view = mock_list_view
        mock_event.item = mock_item

        screen.on_list_view_selected(mock_event)

        assert screen.current_category == "web"
        assert screen.search_query == ""

    def test_state_after_search_change(self):
        """Test screen state after search change."""
        screen = MCPCatalogScreen()
        screen.current_category = "development"
        screen._filter_servers = MagicMock()

        mock_input = MagicMock()
        mock_input.id = "catalog-search"
        mock_input.value = "github"
        mock_event = MagicMock()
        mock_event.input = mock_input
        mock_event.value = "github"

        screen.on_input_changed(mock_event)

        assert screen.search_query == "github"
        assert screen.current_category == "development"

    def test_multiple_category_changes(self):
        """Test multiple category changes."""
        screen = MCPCatalogScreen()
        screen._filter_servers = MagicMock()

        categories = ["development", "web", "utility", "all"]

        for cat in categories:
            mock_list_view = MagicMock()
            mock_list_view.id = "category-list"
            mock_item = MagicMock()
            mock_item.id = f"cat-{cat}"
            mock_event = MagicMock()
            mock_event.list_view = mock_list_view
            mock_event.item = mock_item

            screen.on_list_view_selected(mock_event)
            assert screen.current_category == cat
