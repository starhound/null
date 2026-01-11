from unittest.mock import AsyncMock, patch

import pytest

from mcp.catalog import (
    CATALOG,
    CatalogEntry,
    _check_npm_package,
    _check_pypi_package,
    _extract_npm_package,
    verify_entry,
)


class TestCatalogEntry:
    def test_dataclass_fields(self):
        entry = CatalogEntry(
            name="test",
            description="Test server",
            command="npx",
            args=["-y", "@test/server"],
            env_keys=["API_KEY"],
            category="utility",
            url="https://example.com",
        )
        assert entry.name == "test"
        assert entry.description == "Test server"
        assert entry.command == "npx"
        assert entry.args == ["-y", "@test/server"]
        assert entry.env_keys == ["API_KEY"]
        assert entry.category == "utility"
        assert entry.url == "https://example.com"


class TestExtractNpmPackage:
    def test_extracts_package_after_y_flag(self):
        result = _extract_npm_package(["-y", "@test/server"])
        assert result == "@test/server"

    def test_extracts_scoped_package(self):
        result = _extract_npm_package(["@modelcontextprotocol/server-brave"])
        assert result == "@modelcontextprotocol/server-brave"

    def test_extracts_regular_package(self):
        result = _extract_npm_package(["mcp-server-test"])
        assert result == "mcp-server-test"

    def test_returns_none_for_empty_args(self):
        result = _extract_npm_package([])
        assert result is None

    def test_handles_y_flag_at_end(self):
        result = _extract_npm_package(["-y"])
        assert result is None


class TestCheckNpmPackage:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _check_npm_package("@test/package")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_not_found(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Not found")
        mock_proc.returncode = 1
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _check_npm_package("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_exception(self):
        with patch(
            "asyncio.create_subprocess_exec", side_effect=Exception("Network error")
        ):
            result = await _check_npm_package("@test/package")
        assert result is True


class TestCheckPypiPackage:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"1.0.0", b"")
        mock_proc.returncode = 0
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _check_pypi_package("requests")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_not_found(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Not found")
        mock_proc.returncode = 1
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await _check_pypi_package("nonexistent-pkg")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_exception(self):
        with patch(
            "asyncio.create_subprocess_exec", side_effect=Exception("pip error")
        ):
            result = await _check_pypi_package("some-package")
        assert result is True


class TestVerifyEntry:
    @pytest.mark.asyncio
    async def test_command_not_found(self):
        entry = CatalogEntry(
            name="test",
            description="Test",
            command="nonexistent-cmd",
            args=[],
            env_keys=[],
            category="test",
            url="https://example.com",
        )
        with patch("shutil.which", return_value=None):
            result = await verify_entry(entry)
        assert result["command_available"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_npx_command_with_package(self):
        entry = CatalogEntry(
            name="test",
            description="Test",
            command="npx",
            args=["-y", "@test/package"],
            env_keys=[],
            category="test",
            url="https://example.com",
        )
        with (
            patch("shutil.which", return_value="/usr/bin/npx"),
            patch(
                "mcp.catalog._check_npm_package", new_callable=AsyncMock
            ) as mock_check,
        ):
            mock_check.return_value = True
            result = await verify_entry(entry)
        assert result["command_available"] is True
        assert result["package_exists"] is True

    @pytest.mark.asyncio
    async def test_npx_package_not_found(self):
        entry = CatalogEntry(
            name="test",
            description="Test",
            command="npx",
            args=["-y", "@test/missing"],
            env_keys=[],
            category="test",
            url="https://example.com",
        )
        with (
            patch("shutil.which", return_value="/usr/bin/npx"),
            patch(
                "mcp.catalog._check_npm_package", new_callable=AsyncMock
            ) as mock_check,
        ):
            mock_check.return_value = False
            result = await verify_entry(entry)
        assert result["command_available"] is True
        assert result["package_exists"] is False
        assert "npm package" in result["error"]

    @pytest.mark.asyncio
    async def test_uvx_command_with_package(self):
        entry = CatalogEntry(
            name="test",
            description="Test",
            command="uvx",
            args=["mcp-server-test"],
            env_keys=[],
            category="test",
            url="https://example.com",
        )
        with (
            patch("shutil.which", return_value="/usr/bin/uvx"),
            patch(
                "mcp.catalog._check_pypi_package", new_callable=AsyncMock
            ) as mock_check,
        ):
            mock_check.return_value = True
            result = await verify_entry(entry)
        assert result["command_available"] is True
        assert result["package_exists"] is True

    @pytest.mark.asyncio
    async def test_uvx_package_not_found(self):
        entry = CatalogEntry(
            name="test",
            description="Test",
            command="uvx",
            args=["missing-package"],
            env_keys=[],
            category="test",
            url="https://example.com",
        )
        with (
            patch("shutil.which", return_value="/usr/bin/uvx"),
            patch(
                "mcp.catalog._check_pypi_package", new_callable=AsyncMock
            ) as mock_check,
        ):
            mock_check.return_value = False
            result = await verify_entry(entry)
        assert result["command_available"] is True
        assert result["package_exists"] is False
        assert "PyPI package" in result["error"]

    @pytest.mark.asyncio
    async def test_other_command_assumes_package_exists(self):
        entry = CatalogEntry(
            name="test",
            description="Test",
            command="some-binary",
            args=["arg1"],
            env_keys=[],
            category="test",
            url="https://example.com",
        )
        with patch("shutil.which", return_value="/usr/bin/some-binary"):
            result = await verify_entry(entry)
        assert result["command_available"] is True
        assert result["package_exists"] is True
        assert result["error"] == ""


class TestCatalog:
    def test_catalog_is_list(self):
        assert isinstance(CATALOG, list)

    def test_catalog_has_entries(self):
        assert len(CATALOG) > 0

    def test_all_entries_have_required_fields(self):
        for entry in CATALOG:
            assert entry.name
            assert entry.description
            assert entry.command
            assert isinstance(entry.args, list)
            assert isinstance(entry.env_keys, list)
            assert entry.category
            assert entry.url

    def test_categories_are_valid(self):
        valid_categories = {
            "filesystem",
            "database",
            "development",
            "sysadmin",
            "cloud",
            "web",
            "search",
            "communication",
            "productivity",
            "memory",
            "finance",
            "social",
            "utility",
            "ai",
            "ecommerce",
            "analytics",
            "crm",
            "iot",
            "news",
            "monitoring",
            "security",
            "datascience",
        }
        for entry in CATALOG:
            assert entry.category in valid_categories, (
                f"Invalid category: {entry.category}"
            )

    def test_common_servers_exist(self):
        names = [e.name for e in CATALOG]
        assert "brave-search" in names
        assert "github" in names
        assert "filesystem" in names
        assert "memory" in names
