"""Tests for MCP catalog functionality."""

import pytest
from mcp.catalog import (
    CATALOG,
    CATEGORIES,
    CatalogEntry,
    get_by_category,
    get_by_name,
    search,
)


class TestCatalogEntry:
    """Test CatalogEntry dataclass."""

    def test_catalog_entry_creation(self):
        """Test creating a CatalogEntry."""
        entry = CatalogEntry(
            name="test-server",
            description="A test MCP server",
            command="npx",
            args=["-y", "@test/mcp-server"],
            env_keys=["TEST_API_KEY"],
            category="development",
            url="https://github.com/test/mcp-server",
        )

        assert entry.name == "test-server"
        assert entry.description == "A test MCP server"
        assert entry.command == "npx"
        assert entry.args == ["-y", "@test/mcp-server"]
        assert entry.env_keys == ["TEST_API_KEY"]
        assert entry.category == "development"
        assert entry.url == "https://github.com/test/mcp-server"

    def test_catalog_entry_empty_env_keys(self):
        """Test CatalogEntry with no environment keys."""
        entry = CatalogEntry(
            name="simple-server",
            description="No env needed",
            command="uvx",
            args=["mcp-server-simple"],
            env_keys=[],
            category="utility",
            url="https://example.com",
        )

        assert entry.env_keys == []


class TestCatalog:
    """Test the global catalog."""

    def test_catalog_not_empty(self):
        """Test catalog has entries."""
        assert len(CATALOG) > 0
        assert len(CATALOG) >= 100  # We have ~100 entries

    def test_catalog_entries_have_required_fields(self):
        """Test all catalog entries have required fields."""
        for entry in CATALOG:
            assert entry.name, f"Entry missing name"
            assert entry.description, f"Entry {entry.name} missing description"
            assert entry.command, f"Entry {entry.name} missing command"
            assert entry.category, f"Entry {entry.name} missing category"
            assert entry.url, f"Entry {entry.name} missing url"
            assert isinstance(entry.args, list), f"Entry {entry.name} args not list"
            assert isinstance(entry.env_keys, list), (
                f"Entry {entry.name} env_keys not list"
            )

    def test_catalog_categories_valid(self):
        """Test all catalog entries have valid categories."""
        for entry in CATALOG:
            assert entry.category in CATEGORIES, (
                f"Entry {entry.name} has invalid category: {entry.category}"
            )

    def test_catalog_unique_names(self):
        """Test catalog entries have unique names."""
        names = [e.name for e in CATALOG]
        assert len(names) == len(set(names)), "Catalog has duplicate names"

    def test_catalog_commands_valid(self):
        """Test catalog entries use valid commands (npx, uvx, node, python)."""
        valid_commands = {"npx", "uvx", "node", "python", "python3", "docker"}
        for entry in CATALOG:
            assert entry.command in valid_commands, (
                f"Entry {entry.name} has unexpected command: {entry.command}"
            )


class TestCategories:
    """Test category definitions."""

    def test_categories_not_empty(self):
        """Test categories dictionary is not empty."""
        assert len(CATEGORIES) > 0

    def test_categories_have_readable_names(self):
        """Test categories have human-readable display names."""
        for key, name in CATEGORIES.items():
            assert key, "Category key is empty"
            assert name, f"Category {key} has no display name"
            assert key.islower(), f"Category key {key} should be lowercase"

    def test_all_catalog_categories_in_categories(self):
        """Test all categories used in catalog are defined."""
        used_categories = {e.category for e in CATALOG}
        for cat in used_categories:
            assert cat in CATEGORIES, f"Category {cat} used but not defined"


class TestGetByCategory:
    """Test get_by_category function."""

    def test_get_existing_category(self):
        """Test getting entries from an existing category."""
        db_entries = get_by_category("database")
        assert len(db_entries) > 0
        for entry in db_entries:
            assert entry.category == "database"

    def test_get_nonexistent_category(self):
        """Test getting entries from nonexistent category."""
        entries = get_by_category("nonexistent")
        assert entries == []

    def test_all_categories_have_entries(self):
        """Test all defined categories have at least one entry."""
        for cat in CATEGORIES:
            entries = get_by_category(cat)
            assert len(entries) > 0, f"Category {cat} has no entries"


class TestGetByName:
    """Test get_by_name function."""

    def test_get_existing_server(self):
        """Test getting an existing server by name."""
        entry = get_by_name("github")
        assert entry is not None
        assert entry.name == "github"

    def test_get_nonexistent_server(self):
        """Test getting a nonexistent server."""
        entry = get_by_name("nonexistent-server-xyz")
        assert entry is None

    def test_get_known_servers(self):
        """Test getting well-known servers."""
        known = ["filesystem", "sqlite", "github", "slack", "memory"]
        for name in known:
            entry = get_by_name(name)
            assert entry is not None, f"Expected server {name} not found"


class TestSearch:
    """Test search function."""

    def test_search_by_name(self):
        """Test searching by server name."""
        results = search("github")
        assert len(results) > 0
        assert any(e.name == "github" for e in results)

    def test_search_by_description(self):
        """Test searching by description keywords."""
        results = search("database")
        assert len(results) > 0

    def test_search_case_insensitive(self):
        """Test search is case insensitive."""
        results_lower = search("github")
        results_upper = search("GITHUB")
        assert len(results_lower) == len(results_upper)

    def test_search_no_results(self):
        """Test search with no matching results."""
        results = search("xyz-nonexistent-term-abc")
        assert results == []

    def test_search_partial_match(self):
        """Test partial string matching."""
        results = search("post")
        assert len(results) > 0  # Should find postgres, posthog, etc.


class TestCatalogIntegrity:
    """Integration tests for catalog data integrity."""

    def test_npm_packages_have_scope(self):
        """Test npm packages follow expected naming patterns."""
        for entry in CATALOG:
            if entry.command == "npx":
                # Most MCP servers use -y flag and scoped packages
                has_y_flag = "-y" in entry.args
                if has_y_flag and len(entry.args) >= 2:
                    package = entry.args[entry.args.index("-y") + 1]
                    # Package should start with @ or be a valid npm name
                    assert (
                        package.startswith("@") or package.replace("-", "").isalnum()
                    ), f"Invalid npm package format for {entry.name}: {package}"

    def test_uvx_packages_valid(self):
        """Test uvx packages follow expected patterns."""
        for entry in CATALOG:
            if entry.command == "uvx":
                assert len(entry.args) >= 1, f"uvx entry {entry.name} needs package arg"
                package = entry.args[0]
                # Basic validation - should be alphanumeric with dashes
                assert package.replace("-", "").replace(
                    "_", ""
                ).isalnum() or package.startswith("mcp-server"), (
                    f"Invalid uvx package for {entry.name}: {package}"
                )

    def test_env_keys_format(self):
        """Test environment key names follow conventions."""
        for entry in CATALOG:
            for key in entry.env_keys:
                # Env keys should be uppercase with underscores
                assert key.isupper() or "_" in key, (
                    f"Env key {key} for {entry.name} should be uppercase"
                )
                assert " " not in key, f"Env key {key} should not have spaces"

    def test_urls_valid(self):
        """Test URLs are valid format."""
        for entry in CATALOG:
            assert entry.url.startswith("http://") or entry.url.startswith(
                "https://"
            ), f"Invalid URL for {entry.name}: {entry.url}"
