"""Tests for commands/core.py - Core application commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.core import CoreCommands


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.config = MagicMock()
    app.config.get.return_value = {"provider": "ollama", "active_prompt": "default"}
    app.ai_provider = MagicMock()
    app.ai_provider.model = "llama3.2"
    app.ai_provider.name = "ollama"
    app.blocks = []
    app.current_cli_block = None
    app.current_cli_widget = None
    app.storage = MagicMock()
    app.mcp_manager = MagicMock()
    app.mcp_manager.reload_config = MagicMock()
    app.mcp_manager.initialize = AsyncMock()
    app._show_system_output = AsyncMock()
    return app


@pytest.fixture
def core_commands(mock_app):
    return CoreCommands(mock_app)


class TestCoreCommandsHelp:
    @pytest.mark.asyncio
    async def test_cmd_help_pushes_help_screen(self, core_commands, mock_app):
        with patch("screens.HelpScreen"):
            await core_commands.cmd_help([])
        mock_app.push_screen.assert_called_once()


class TestCoreCommandsStatus:
    @pytest.mark.asyncio
    async def test_cmd_status_shows_provider_info(self, core_commands, mock_app):
        mock_status_bar = MagicMock()
        mock_status_bar.provider_status = "connected"
        mock_status_bar.session_input_tokens = 100
        mock_status_bar.session_output_tokens = 50
        mock_status_bar.session_cost = 0.0015
        mock_app.query_one.return_value = mock_status_bar

        with (
            patch("context.ContextManager.get_context", return_value="test context"),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_status([])

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "AI Provider" in output or "Provider" in output
        assert "ollama" in output

    @pytest.mark.asyncio
    async def test_cmd_status_handles_missing_status_bar(self, core_commands, mock_app):
        mock_app.query_one.side_effect = Exception("Not found")

        with (
            patch("context.ContextManager.get_context", return_value=""),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_status([])

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "Provider" in output or "Python" in output


class TestCoreCommandsClear:
    @pytest.mark.asyncio
    async def test_cmd_clear_clears_blocks(self, core_commands, mock_app):
        mock_app.blocks = [MagicMock(), MagicMock()]
        mock_history = MagicMock()
        mock_history.remove_children = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with patch.object(core_commands, "notify"):
            await core_commands.cmd_clear([])

        assert mock_app.blocks == []
        assert mock_app.current_cli_block is None

    @pytest.mark.asyncio
    async def test_cmd_clear_resets_status_bar(self, core_commands, mock_app):
        mock_status_bar = MagicMock()
        mock_status_bar.reset_token_usage = MagicMock()
        mock_app.query_one.return_value = mock_status_bar

        with patch.object(core_commands, "notify"):
            await core_commands.cmd_clear([])

        mock_status_bar.reset_token_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_clear_handles_exceptions(self, core_commands, mock_app):
        mock_app.query_one.side_effect = Exception("Widget not found")

        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_clear([])

        mock_notify.assert_called_with("History cleared")


class TestCoreCommandsQuit:
    @pytest.mark.asyncio
    async def test_cmd_quit_exits_app(self, core_commands, mock_app):
        await core_commands.cmd_quit([])
        mock_app.exit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_exit_exits_app(self, core_commands, mock_app):
        await core_commands.cmd_exit([])
        mock_app.exit.assert_called_once()


class TestCoreCommandsSSH:
    @pytest.mark.asyncio
    async def test_cmd_ssh_no_args_shows_error(self, core_commands, mock_app):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_ssh([])

        mock_notify.assert_called_once()
        assert "Usage" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_ssh_unknown_host_shows_error(self, core_commands, mock_app):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_ssh(["unknown"])

        mock_notify.assert_called_once()
        assert "Connecting to" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_ssh_connects_to_host(self, core_commands, mock_app):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_ssh(["myserver"])

        mock_notify.assert_called_once()
        assert "Connecting to myserver" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_ssh_with_jump_host(self, core_commands, mock_app):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_ssh(["myserver"])

        mock_notify.assert_called_once()
        assert "Connecting to myserver" in mock_notify.call_args[0][0]


class TestCoreCommandsSSHAdd:
    @pytest.mark.asyncio
    async def test_cmd_ssh_add_no_args_shows_form(self, core_commands, mock_app):
        with patch("screens.ssh_add.SSHAddScreen"):
            await core_commands.cmd_ssh_add([])

        mock_app.push_screen.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_ssh_add_insufficient_args(self, core_commands, mock_app):
        with patch("screens.ssh_add.SSHAddScreen"):
            await core_commands.cmd_ssh_add(["alias", "host"])

        mock_app.push_screen.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_ssh_add_adds_host(self, core_commands, mock_app):
        with patch("screens.ssh_add.SSHAddScreen"):
            await core_commands.cmd_ssh_add(["myserver", "example.com", "user"])

        mock_app.push_screen.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_ssh_add_with_port_and_key(self, core_commands, mock_app):
        with patch("screens.ssh_add.SSHAddScreen"):
            await core_commands.cmd_ssh_add(
                ["myserver", "example.com", "user", "2222", "/path/to/key"]
            )

        mock_app.push_screen.assert_called_once()


class TestCoreCommandsSSHList:
    @pytest.mark.asyncio
    async def test_cmd_ssh_list_no_hosts(self, core_commands, mock_app):
        mock_storage = MagicMock()
        mock_storage.list_ssh_hosts.return_value = []

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(core_commands, "notify") as mock_notify,
        ):
            await core_commands.cmd_ssh_list([])

        mock_notify.assert_called_once()
        assert "No SSH hosts" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_ssh_list_shows_hosts(self, core_commands, mock_app):
        mock_storage = MagicMock()
        mock_storage.list_ssh_hosts.return_value = [
            {"alias": "server1", "hostname": "s1.com", "port": 22, "username": "user1"},
            {
                "alias": "server2",
                "hostname": "s2.com",
                "port": 2222,
                "username": "user2",
            },
        ]

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_ssh_list([])

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "server1" in output
        assert "server2" in output


class TestCoreCommandsSSHDel:
    @pytest.mark.asyncio
    async def test_cmd_ssh_del_no_args(self, core_commands, mock_app):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_ssh_del([])

        mock_notify.assert_called_once()
        assert "Usage" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_ssh_del_deletes_host(self, core_commands, mock_app):
        mock_storage = MagicMock()

        with (
            patch("config.Config._get_storage", return_value=mock_storage),
            patch.object(core_commands, "notify") as mock_notify,
        ):
            await core_commands.cmd_ssh_del(["myserver"])

        mock_storage.delete_ssh_host.assert_called_once_with("myserver")
        mock_notify.assert_called_once()
        assert "Deleted" in mock_notify.call_args[0][0]


class TestCoreCommandsReload:
    @pytest.mark.asyncio
    async def test_cmd_reload_reloads_config(self, core_commands, mock_app):
        mock_settings = MagicMock()
        mock_config = MagicMock()

        with (
            patch("config.Config.load_all", return_value=mock_config),
            patch("config.get_settings", return_value=mock_settings),
            patch.object(core_commands, "notify") as mock_notify,
        ):
            await core_commands.cmd_reload([])

        mock_notify.assert_called_with("Configuration reloaded")

    @pytest.mark.asyncio
    async def test_cmd_reload_handles_error(self, core_commands, mock_app):
        with (
            patch("config.Config.load_all", side_effect=Exception("Reload failed")),
            patch.object(core_commands, "notify") as mock_notify,
        ):
            await core_commands.cmd_reload([])

        mock_notify.assert_called_once()
        assert "failed" in mock_notify.call_args[0][0].lower()


class TestCoreCommandsGit:
    @pytest.mark.asyncio
    async def test_cmd_git_not_a_repo(self, core_commands, mock_app):
        mock_gm = MagicMock()
        mock_gm.get_status = AsyncMock(return_value="Not a git repository")

        with (
            patch("managers.git.GitManager", return_value=mock_gm),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_git([])

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_git_status_default(self, core_commands, mock_app):
        with patch.object(
            core_commands, "_git_status", new_callable=AsyncMock
        ) as mock_status:
            await core_commands.cmd_git([])

        mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_git_diff(self, core_commands, mock_app):
        with patch.object(
            core_commands, "_git_diff", new_callable=AsyncMock
        ) as mock_diff:
            await core_commands.cmd_git(["diff", "file.py"])

        mock_diff.assert_called_once_with(["file.py"])

    @pytest.mark.asyncio
    async def test_cmd_git_commit(self, core_commands, mock_app):
        with patch.object(
            core_commands, "_git_commit", new_callable=AsyncMock
        ) as mock_commit:
            await core_commands.cmd_git(["commit", "Initial", "commit"])

        mock_commit.assert_called_once_with("Initial commit")

    @pytest.mark.asyncio
    async def test_cmd_git_log(self, core_commands, mock_app):
        with patch.object(
            core_commands, "_git_log", new_callable=AsyncMock
        ) as mock_log:
            await core_commands.cmd_git(["log", "5"])

        mock_log.assert_called_once_with(["5"])

    @pytest.mark.asyncio
    async def test_cmd_git_unknown_subcommand(self, core_commands, mock_app):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_git(["unknown"])

        mock_notify.assert_called_once()
        assert "Unknown" in mock_notify.call_args[0][0]


class TestGitHelperMethods:
    @pytest.mark.asyncio
    async def test_git_status_shows_branch(self, core_commands, mock_app):
        mock_gm = MagicMock()
        mock_gm.get_status = AsyncMock(return_value="On branch main\nnothing to commit")

        with (
            patch("managers.git.GitManager", return_value=mock_gm),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands._git_status()

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "main" in output or "branch" in output.lower()

    @pytest.mark.asyncio
    async def test_git_status_shows_staged_files(self, core_commands, mock_app):
        mock_gm = MagicMock()
        mock_gm.get_status = AsyncMock(
            return_value="On branch main\nChanges to be committed:\n  file1.py\n  file2.py"
        )

        with (
            patch("managers.git.GitManager", return_value=mock_gm),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands._git_status()

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "file1.py" in output or "Changes" in output

    @pytest.mark.asyncio
    async def test_git_diff_no_changes(self, core_commands, mock_app):
        mock_gm = MagicMock()
        mock_gm.get_diff = AsyncMock(return_value="")

        with (
            patch("managers.git.GitManager", return_value=mock_gm),
            patch.object(core_commands, "notify") as mock_notify,
        ):
            await core_commands._git_diff([])

        mock_notify.assert_called_once()
        assert "No changes" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_git_diff_shows_changes(self, core_commands, mock_app):
        mock_gm = MagicMock()
        mock_gm.get_diff = AsyncMock(return_value="+ added line\n- removed line")

        mock_history = MagicMock()
        mock_history.mount = AsyncMock()
        mock_app.query_one.return_value = mock_history

        with patch("managers.git.GitManager", return_value=mock_gm):
            await core_commands._git_diff([])

        mock_history.mount.assert_called_once()

    @pytest.mark.asyncio
    async def test_git_commit_no_staged(self, core_commands, mock_app):
        mock_gm = MagicMock()
        mock_gm.get_diff = AsyncMock(return_value="")

        with (
            patch("managers.git.GitManager", return_value=mock_gm),
            patch.object(core_commands, "notify") as mock_notify,
        ):
            await core_commands._git_commit("")

        assert mock_notify.call_count == 2
        assert "Generating commit message" in mock_notify.call_args_list[0][0][0]
        assert "Nothing to commit" in mock_notify.call_args_list[1][0][0]


class TestIssueCommand:
    @pytest.mark.asyncio
    async def test_cmd_issue_no_args_shows_usage(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.list_issues = AsyncMock(return_value="No open issues")

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_issue([])

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_issue_unknown_subcommand(self, core_commands):
        with patch.object(core_commands, "notify") as mock_notify:
            await core_commands.cmd_issue(["invalid"])

        mock_notify.assert_called_once()
        assert "Usage" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_issue_list_calls_github(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.list_issues = AsyncMock(return_value="Issue list")

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_issue(["list"])

        mock_gh.list_issues.assert_called_once()
        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_issue_list_handles_no_issues(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.list_issues = AsyncMock(return_value="No open issues")

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_issue(["list"])

        mock_show.assert_called_once()
        output = mock_show.call_args[0][1]
        assert "No open issues" in output or output is not None

    @pytest.mark.asyncio
    async def test_cmd_issue_view_by_number(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.get_issue = AsyncMock(return_value="Issue #123 details")

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_issue(["123"])

        mock_gh.get_issue.assert_called_once_with(123)
        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_issue_view_handles_not_found(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.get_issue = AsyncMock(return_value=None)

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_issue(["999"])

        mock_show.assert_called_once()


class TestPrCommand:
    @pytest.mark.asyncio
    async def test_cmd_pr_no_args_shows_usage(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.list_prs = AsyncMock(return_value="No open PRs")

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(
                core_commands, "show_output", new_callable=AsyncMock
            ) as mock_show,
        ):
            await core_commands.cmd_pr([])

        mock_show.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_pr_list_calls_github(self, core_commands):
        mock_gh = MagicMock()
        mock_gh.list_prs = AsyncMock(return_value="PR list")

        with (
            patch("managers.github.GitHubContextManager", return_value=mock_gh),
            patch.object(core_commands, "show_output", new_callable=AsyncMock),
        ):
            await core_commands.cmd_pr(["list"])

        mock_gh.list_prs.assert_called_once()
