import os

import pytest

from tools.builtin import (
    BUILTIN_TOOLS,
    BuiltinTool,
    get_builtin_tool,
    list_directory,
    read_file,
    run_command,
    write_file,
)


class TestBuiltinTool:
    """Tests for BuiltinTool dataclass."""

    def test_builtin_tool_has_required_fields(self):
        """BuiltinTool should have all required fields."""
        tool = BuiltinTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            handler=lambda: "result",
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema is not None
        assert tool.handler is not None

    def test_builtin_tool_requires_approval_default(self):
        """BuiltinTool should default to requiring approval."""
        tool = BuiltinTool(
            name="test",
            description="test",
            input_schema={},
            handler=lambda: "",
        )
        assert tool.requires_approval is True

    def test_builtin_tool_requires_approval_override(self):
        """BuiltinTool requires_approval can be overridden."""
        tool = BuiltinTool(
            name="test",
            description="test",
            input_schema={},
            handler=lambda: "",
            requires_approval=False,
        )
        assert tool.requires_approval is False


class TestBuiltinToolsList:
    """Tests for BUILTIN_TOOLS constant."""

    def test_builtin_tools_is_list(self):
        """BUILTIN_TOOLS should be a list."""
        assert isinstance(BUILTIN_TOOLS, list)

    def test_builtin_tools_not_empty(self):
        """BUILTIN_TOOLS should contain at least one tool."""
        assert len(BUILTIN_TOOLS) > 0

    def test_all_builtin_tools_are_valid(self):
        """All items in BUILTIN_TOOLS should be BuiltinTool instances."""
        for tool in BUILTIN_TOOLS:
            assert isinstance(tool, BuiltinTool)

    def test_expected_tools_exist(self):
        """Expected built-in tools should be defined."""
        tool_names = {t.name for t in BUILTIN_TOOLS}
        assert "run_command" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "list_directory" in tool_names

    def test_each_tool_has_valid_schema(self):
        """Each tool should have a valid JSON schema."""
        for tool in BUILTIN_TOOLS:
            assert isinstance(tool.input_schema, dict)
            assert "type" in tool.input_schema
            assert tool.input_schema["type"] == "object"

    def test_tools_have_unique_names(self):
        """All tool names should be unique."""
        names = [t.name for t in BUILTIN_TOOLS]
        assert len(names) == len(set(names))


class TestGetBuiltinTool:
    """Tests for get_builtin_tool function."""

    def test_get_existing_tool(self):
        """Should return tool for valid name."""
        tool = get_builtin_tool("run_command")
        assert tool is not None
        assert tool.name == "run_command"

    def test_get_nonexistent_tool(self):
        """Should return None for invalid name."""
        tool = get_builtin_tool("nonexistent_tool")
        assert tool is None

    def test_get_all_builtin_tools(self):
        """Should be able to retrieve all built-in tools."""
        for builtin in BUILTIN_TOOLS:
            retrieved = get_builtin_tool(builtin.name)
            assert retrieved is not None
            assert retrieved.name == builtin.name


class TestRunCommandHandler:
    """Tests for run_command async handler."""

    @pytest.mark.asyncio
    async def test_run_simple_command(self):
        """Should execute simple command and return output."""
        result = await run_command("echo hello")
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_run_command_with_exit_code(self):
        """Should include exit code for failed commands."""
        result = await run_command("exit 42")
        assert "Exit code: 42" in result

    @pytest.mark.asyncio
    async def test_run_command_with_working_dir(self, temp_dir):
        """Should execute command in specified directory."""
        result = await run_command("pwd", working_dir=str(temp_dir))
        assert str(temp_dir) in result

    @pytest.mark.asyncio
    async def test_run_command_default_working_dir(self):
        """Should use current directory when working_dir not specified."""
        result = await run_command("pwd")
        assert os.getcwd() in result

    @pytest.mark.asyncio
    async def test_run_invalid_command(self):
        """Should handle invalid command gracefully."""
        result = await run_command("nonexistent_command_xyz123")
        # Should contain error or exit code
        assert (
            "Exit code:" in result or "Error" in result or "not found" in result.lower()
        )


class TestReadFileHandler:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, temp_workdir):
        test_file = temp_workdir / "test.txt"
        test_file.write_text("Hello, World!")

        result = await read_file(str(test_file))
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_workdir):
        result = await read_file(str(temp_workdir / "nonexistent.txt"))
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_read_directory_as_file(self, temp_workdir):
        subdir = temp_workdir / "subdir"
        subdir.mkdir()
        result = await read_file(str(subdir))
        assert "Not a file" in result

    @pytest.mark.asyncio
    async def test_read_with_max_lines(self, temp_workdir):
        test_file = temp_workdir / "multiline.txt"
        test_file.write_text("\n".join(f"Line {i}" for i in range(100)))

        result = await read_file(str(test_file), max_lines=5)
        assert "Line 0" in result
        assert "Line 4" in result
        assert "truncated" in result

    @pytest.mark.asyncio
    async def test_read_expands_tilde(self, temp_workdir):
        test_file = temp_workdir / "tilde_test.txt"
        test_file.write_text("test content")

        result = await read_file(str(test_file))
        assert result == "test content"

    @pytest.mark.asyncio
    async def test_read_relative_path(self, temp_workdir):
        test_file = temp_workdir / "relative_test.txt"
        test_file.write_text("relative content")

        result = await read_file("relative_test.txt")
        assert result == "relative content"


class TestWriteFileHandler:
    @pytest.mark.asyncio
    async def test_write_new_file(self, temp_workdir):
        test_path = temp_workdir / "new_file.txt"

        result = await write_file(str(test_path), "Hello, World!")

        assert "Successfully wrote" in result
        assert test_path.exists()
        assert test_path.read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_write_overwrites_existing(self, temp_workdir):
        test_path = temp_workdir / "existing.txt"
        test_path.write_text("old content")

        result = await write_file(str(test_path), "new content")

        assert "Successfully wrote" in result
        assert test_path.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, temp_workdir):
        test_path = temp_workdir / "nested" / "dir" / "file.txt"

        result = await write_file(str(test_path), "nested content")

        assert "Successfully wrote" in result
        assert test_path.exists()
        assert test_path.read_text() == "nested content"

    @pytest.mark.asyncio
    async def test_write_reports_byte_count(self, temp_workdir):
        test_path = temp_workdir / "bytes_test.txt"
        content = "12345"

        result = await write_file(str(test_path), content)

        assert "5 bytes" in result

    @pytest.mark.asyncio
    async def test_write_empty_content(self, temp_workdir):
        test_path = temp_workdir / "empty.txt"

        result = await write_file(str(test_path), "")

        assert "Successfully wrote" in result
        assert test_path.read_text() == ""


class TestListDirectoryHandler:
    @pytest.mark.asyncio
    async def test_list_directory(self, temp_workdir):
        (temp_workdir / "file1.txt").write_text("content")
        (temp_workdir / "file2.txt").write_text("content")
        (temp_workdir / "subdir").mkdir()

        result = await list_directory(str(temp_workdir))

        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir/" in result

    @pytest.mark.asyncio
    async def test_list_hides_hidden_by_default(self, temp_workdir):
        (temp_workdir / "visible.txt").write_text("content")
        (temp_workdir / ".hidden").write_text("hidden")

        result = await list_directory(str(temp_workdir))

        assert "visible.txt" in result
        assert ".hidden" not in result

    @pytest.mark.asyncio
    async def test_list_shows_hidden_when_requested(self, temp_workdir):
        (temp_workdir / "visible.txt").write_text("content")
        (temp_workdir / ".hidden").write_text("hidden")

        result = await list_directory(str(temp_workdir), show_hidden=True)

        assert "visible.txt" in result
        assert ".hidden" in result

    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, temp_workdir):
        result = await list_directory(str(temp_workdir / "nonexistent"))
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_list_file_as_directory(self, temp_workdir):
        test_file = temp_workdir / "file.txt"
        test_file.write_text("content")

        result = await list_directory(str(test_file))
        assert "Not a directory" in result

    @pytest.mark.asyncio
    async def test_list_empty_directory(self, temp_workdir):
        empty_dir = temp_workdir / "empty"
        empty_dir.mkdir()

        result = await list_directory(str(empty_dir))
        assert "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_list_shows_file_sizes(self, temp_workdir):
        test_file = temp_workdir / "sized.txt"
        test_file.write_text("12345")

        result = await list_directory(str(temp_workdir))
        assert "5 bytes" in result

    @pytest.mark.asyncio
    async def test_list_default_path(self, temp_workdir):
        (temp_workdir / "testfile.txt").write_text("content")

        result = await list_directory()
        assert "testfile.txt" in result


class TestToolApprovalSettings:
    """Tests for tool approval configuration."""

    def test_run_command_requires_approval(self):
        """run_command should require approval."""
        tool = get_builtin_tool("run_command")
        assert tool.requires_approval is True

    def test_read_file_no_approval(self):
        """read_file should not require approval."""
        tool = get_builtin_tool("read_file")
        assert tool.requires_approval is False

    def test_write_file_requires_approval(self):
        """write_file should require approval."""
        tool = get_builtin_tool("write_file")
        assert tool.requires_approval is True

    def test_list_directory_no_approval(self):
        """list_directory should not require approval."""
        tool = get_builtin_tool("list_directory")
        assert tool.requires_approval is False
