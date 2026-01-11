"""Tests for managers/nl2shell.py - NL2Shell command translation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.nl2shell import CommandSuggestion, NL2Shell, ShellContext


class TestShellContext:
    def test_default_values(self):
        ctx = ShellContext()
        assert ctx.cwd == ""
        assert ctx.git_branch == ""
        assert ctx.os_info == ""
        assert ctx.recent_commands == []
        assert ctx.environment == {}
        assert ctx.available_tools == []


class TestCommandSuggestion:
    def test_default_values(self):
        suggestion = CommandSuggestion(command="ls", explanation="List files")
        assert suggestion.command == "ls"
        assert suggestion.explanation == "List files"
        assert suggestion.confidence == 0.8
        assert suggestion.alternatives == []
        assert suggestion.warnings == []
        assert suggestion.requires_sudo is False


class TestNL2ShellGetContext:
    @pytest.mark.asyncio
    async def test_get_context_returns_shell_context(self):
        nl2shell = NL2Shell()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"main\n", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            context = await nl2shell.get_context()

        assert isinstance(context, ShellContext)
        assert context.cwd != ""

    @pytest.mark.asyncio
    async def test_get_context_captures_git_branch(self):
        nl2shell = NL2Shell()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"feature-branch\n", b""))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            context = await nl2shell.get_context()

        assert context.git_branch == "feature-branch"

    @pytest.mark.asyncio
    async def test_get_context_handles_git_not_found(self):
        nl2shell = NL2Shell()
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            context = await nl2shell.get_context()

        assert context.git_branch == ""

    @pytest.mark.asyncio
    async def test_get_context_handles_git_timeout(self):
        nl2shell = NL2Shell()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_exec.return_value = mock_proc

            context = await nl2shell.get_context()

        assert context.git_branch == ""

    @pytest.mark.asyncio
    async def test_get_context_handles_not_git_repo(self):
        nl2shell = NL2Shell()
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b"not a git repo"))
            mock_proc.returncode = 128
            mock_exec.return_value = mock_proc

            context = await nl2shell.get_context()

        assert context.git_branch == ""


class TestNL2ShellPatternMatch:
    def test_pattern_match_disk_usage(self):
        nl2shell = NL2Shell()
        result = nl2shell._try_pattern_match("disk usage")
        assert result is not None
        assert result.command == "du -sh *"

    def test_pattern_match_memory_usage(self):
        nl2shell = NL2Shell()
        result = nl2shell._try_pattern_match("memory usage")
        assert result is not None
        assert "free" in result.command

    def test_pattern_match_find_large_files_with_size(self):
        nl2shell = NL2Shell()
        result = nl2shell._try_pattern_match("find files larger than 50m")
        assert result is not None
        assert "50" in result.command

    def test_pattern_match_returns_none_for_unknown(self):
        nl2shell = NL2Shell()
        result = nl2shell._try_pattern_match("do something completely unique xyz123")
        assert result is None

    def test_pattern_match_returns_none_when_placeholder_needed(self):
        nl2shell = NL2Shell()
        result = nl2shell._try_pattern_match("search for text")
        assert result is None


class TestNL2ShellParseResponse:
    def test_parse_response_full_format(self):
        nl2shell = NL2Shell()
        response = """COMMAND: ls -la
EXPLANATION: List all files including hidden
ALTERNATIVES: ls -lah, dir
WARNINGS: none
REQUIRES_SUDO: no
CONFIDENCE: 0.95"""

        result = nl2shell._parse_response(response)

        assert result.command == "ls -la"
        assert result.explanation == "List all files including hidden"
        assert "ls -lah" in result.alternatives
        assert result.warnings == []
        assert result.requires_sudo is False
        assert result.confidence == 0.95

    def test_parse_response_with_warnings(self):
        nl2shell = NL2Shell()
        response = """COMMAND: rm -rf /tmp/test
EXPLANATION: Remove directory
ALTERNATIVES: none
WARNINGS: This is destructive
REQUIRES_SUDO: no
CONFIDENCE: 0.8"""

        result = nl2shell._parse_response(response)

        assert "This is destructive" in result.warnings

    def test_parse_response_requires_sudo(self):
        nl2shell = NL2Shell()
        response = """COMMAND: apt install vim
EXPLANATION: Install vim
REQUIRES_SUDO: yes"""

        result = nl2shell._parse_response(response)

        assert result.requires_sudo is True

    def test_parse_response_extracts_command_from_backticks(self):
        nl2shell = NL2Shell()
        response = "`ls -la`"

        result = nl2shell._parse_response(response)

        assert result.command == "ls -la"

    def test_parse_response_extracts_command_from_dollar_prefix(self):
        nl2shell = NL2Shell()
        response = "$ pwd"

        result = nl2shell._parse_response(response)

        assert result.command == "pwd"

    def test_parse_response_handles_malformed_input(self):
        nl2shell = NL2Shell()
        response = "just some random text"

        result = nl2shell._parse_response(response)

        assert result.command == "just some random text"
        assert result.explanation == "AI-generated command"


class TestNL2ShellTranslate:
    @pytest.mark.asyncio
    async def test_translate_uses_pattern_match_first(self):
        nl2shell = NL2Shell()
        mock_provider = MagicMock()

        result = await nl2shell.translate("disk usage", mock_provider)

        assert result.command == "du -sh *"
        mock_provider.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_translate_falls_back_to_ai(self):
        nl2shell = NL2Shell()

        async def mock_generate(*args, **kwargs):
            yield "COMMAND: custom-command\nEXPLANATION: Does something"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        with patch.object(nl2shell, "get_context", new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ShellContext(cwd="/tmp", os_info="Linux")
            result = await nl2shell.translate("do something unique", mock_provider)

        assert result.command == "custom-command"


class TestNL2ShellExplain:
    @pytest.mark.asyncio
    async def test_explain_calls_provider(self):
        nl2shell = NL2Shell()

        async def mock_generate(*args, **kwargs):
            yield "This command lists files in long format"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        result = await nl2shell.explain("ls -la", mock_provider)

        assert "lists files" in result

    @pytest.mark.asyncio
    async def test_explain_strips_whitespace(self):
        nl2shell = NL2Shell()

        async def mock_generate(*args, **kwargs):
            yield "  explanation with whitespace  \n\n"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        result = await nl2shell.explain("pwd", mock_provider)

        assert result == "explanation with whitespace"
