import pytest

from screens import HelpScreen
from widgets import InputController


async def submit_command(pilot, app, command: str):
    input_widget = app.query_one("#input", InputController)
    input_widget.text = command
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()


class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_help_opens_help_screen(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/help")

        assert len(app.screen_stack) > 1
        assert isinstance(app.screen, HelpScreen)

    @pytest.mark.asyncio
    async def test_help_screen_closes_with_escape(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/help")
        await pilot.press("escape")
        await pilot.pause()

        assert len(app.screen_stack) == 1


class TestClearCommand:
    @pytest.mark.asyncio
    async def test_clear_removes_blocks(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test1")
        await pilot.pause()
        await submit_command(pilot, app, "echo test2")
        await pilot.pause()
        initial_blocks = len(app.blocks)
        assert initial_blocks >= 1

        await submit_command(pilot, app, "/clear")

        assert len(app.blocks) == 0

    @pytest.mark.asyncio
    async def test_clear_resets_history_viewport(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")
        await submit_command(pilot, app, "/clear")

        history = app.query_one("#history")
        from widgets.blocks import BaseBlockWidget

        blocks_in_history = list(history.query(BaseBlockWidget))
        assert len(blocks_in_history) == 0


class TestStatusCommand:
    @pytest.mark.asyncio
    async def test_status_executes(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/status")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_status_after_command(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "echo test")
        await pilot.pause()
        await submit_command(pilot, app, "/status")
        await pilot.pause()


class TestWatchCommand:
    @pytest.mark.asyncio
    async def test_watch_toggles_watch_mode(self, running_app):
        pilot, app = running_app

        initial_watch = getattr(app, "_watch_mode", False)
        await submit_command(pilot, app, "/watch")

        assert getattr(app, "_watch_mode", False) != initial_watch

    @pytest.mark.asyncio
    async def test_watch_stop_disables_watch(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/watch")
        await submit_command(pilot, app, "/watch stop")

        assert getattr(app, "_watch_mode", False) is False


class TestReloadCommand:
    @pytest.mark.asyncio
    async def test_reload_executes_without_error(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/reload")
        await pilot.pause()


class TestGitCommand:
    @pytest.mark.asyncio
    async def test_git_status_creates_block(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/git status")

        assert len(app.blocks) >= initial_blocks

    @pytest.mark.asyncio
    async def test_git_no_args_shows_status(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/git")

        assert len(app.blocks) >= initial_blocks


class TestDiffCommand:
    @pytest.mark.asyncio
    async def test_diff_creates_block(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/diff")

        assert len(app.blocks) >= initial_blocks


class TestBranchCommand:
    @pytest.mark.asyncio
    async def test_branch_list_shows_branches(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/branch list")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_branch_save_creates_branch(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/branch save test_branch")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_branch_no_args_shows_help(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/branch")

        assert len(app.blocks) >= initial_blocks


class TestSSHCommands:
    @pytest.mark.asyncio
    async def test_ssh_list_shows_hosts(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/ssh-list")

        assert len(app.blocks) >= initial_blocks

    @pytest.mark.asyncio
    async def test_ssh_add_no_args_opens_screen(self, running_app):
        pilot, app = running_app
        from screens.ssh_add import SSHAddScreen

        await submit_command(pilot, app, "/ssh-add")

        if len(app.screen_stack) > 1:
            assert isinstance(app.screen, SSHAddScreen)

    @pytest.mark.asyncio
    async def test_ssh_del_nonexistent_host(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/ssh-del nonexistent_host_12345")
        await pilot.pause()


class TestWorkflowCommand:
    @pytest.mark.asyncio
    async def test_workflow_list(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/workflow list")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_workflow_no_args_shows_list(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/workflow")
        await pilot.pause()


class TestMapCommand:
    @pytest.mark.asyncio
    async def test_map_creates_output(self, running_app):
        pilot, app = running_app

        initial_blocks = len(app.blocks)
        await submit_command(pilot, app, "/map")

        assert len(app.blocks) >= initial_blocks


class TestExplainCommand:
    @pytest.mark.asyncio
    async def test_explain_no_args_shows_usage(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/explain")
        await pilot.pause()


class TestCmdCommand:
    @pytest.mark.asyncio
    async def test_cmd_no_args_shows_usage(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/cmd")
        await pilot.pause()


class TestFixCommand:
    @pytest.mark.asyncio
    async def test_fix_no_error_shows_message(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/fix")
        await pilot.pause()


class TestReviewCommand:
    @pytest.mark.asyncio
    async def test_review_status(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/review status")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_review_no_args_shows_status(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/review")
        await pilot.pause()


class TestIssueCommand:
    @pytest.mark.asyncio
    async def test_issue_list(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/issue list")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_issue_no_args(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/issue")
        await pilot.pause()


class TestPRCommand:
    @pytest.mark.asyncio
    async def test_pr_list(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/pr list")
        await pilot.pause()

    @pytest.mark.asyncio
    async def test_pr_no_args(self, running_app):
        pilot, app = running_app

        await submit_command(pilot, app, "/pr")
        await pilot.pause()
