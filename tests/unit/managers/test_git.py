"""Unit tests for GitManager."""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.git import (
    CommitResult,
    GitCommit,
    GitDiff,
    GitManager,
    get_git_manager,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def git_manager(temp_dir):
    """Create a GitManager with a temp working directory."""
    return GitManager(working_dir=temp_dir)


@pytest.fixture
def git_manager_no_git():
    """Create a GitManager with no git binary available."""
    manager = GitManager()
    manager._has_git = False
    return manager


def create_mock_process(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Helper to create a mock subprocess."""
    mock_proc = MagicMock()
    mock_proc.returncode = returncode
    mock_proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    return mock_proc


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestGitDiff:
    """Tests for GitDiff dataclass."""

    def test_default_values(self):
        """Test GitDiff with required fields only."""
        diff = GitDiff(file="test.py", additions=10, deletions=5, content="diff")
        assert diff.file == "test.py"
        assert diff.additions == 10
        assert diff.deletions == 5
        assert diff.content == "diff"
        assert diff.is_new is False
        assert diff.is_deleted is False
        assert diff.is_renamed is False
        assert diff.old_path is None

    def test_all_values(self):
        """Test GitDiff with all fields."""
        diff = GitDiff(
            file="new.py",
            additions=100,
            deletions=0,
            content="new file",
            is_new=True,
            is_deleted=False,
            is_renamed=True,
            old_path="old.py",
        )
        assert diff.file == "new.py"
        assert diff.is_new is True
        assert diff.is_renamed is True
        assert diff.old_path == "old.py"

    def test_deleted_file(self):
        """Test GitDiff for a deleted file."""
        diff = GitDiff(
            file="deleted.py",
            additions=0,
            deletions=50,
            content="deleted",
            is_deleted=True,
        )
        assert diff.is_deleted is True
        assert diff.deletions == 50


class TestGitCommit:
    """Tests for GitCommit dataclass."""

    def test_default_values(self):
        """Test GitCommit with required fields only."""
        date = datetime.now()
        commit = GitCommit(sha="abc123", message="Initial", author="Test", date=date)
        assert commit.sha == "abc123"
        assert commit.message == "Initial"
        assert commit.author == "Test"
        assert commit.date == date
        assert commit.files == []
        assert commit.is_ai_generated is False

    def test_all_values(self):
        """Test GitCommit with all fields."""
        date = datetime.now()
        commit = GitCommit(
            sha="def456",
            message="[AI] Auto commit",
            author="AI",
            date=date,
            files=["a.py", "b.py"],
            is_ai_generated=True,
        )
        assert commit.files == ["a.py", "b.py"]
        assert commit.is_ai_generated is True


class TestCommitResult:
    """Tests for CommitResult dataclass."""

    def test_success_result(self):
        """Test successful CommitResult."""
        result = CommitResult(
            success=True,
            sha="abc123",
            message="feat: add feature",
            files_committed=["a.py"],
        )
        assert result.success is True
        assert result.sha == "abc123"
        assert result.error is None

    def test_failure_result(self):
        """Test failed CommitResult."""
        result = CommitResult(success=False, error="Nothing to commit")
        assert result.success is False
        assert result.error == "Nothing to commit"
        assert result.sha is None

    def test_default_values(self):
        """Test CommitResult default values."""
        result = CommitResult(success=True)
        assert result.sha is None
        assert result.message is None
        assert result.error is None
        assert result.files_committed == []


# ============================================================================
# GitManager Initialization Tests
# ============================================================================


class TestGitManagerInit:
    """Tests for GitManager initialization."""

    def test_default_working_dir(self):
        """Test default working directory is cwd."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            manager = GitManager()
            assert manager.working_dir == Path.cwd()

    def test_custom_working_dir(self, temp_dir):
        """Test custom working directory."""
        manager = GitManager(working_dir=temp_dir)
        assert manager.working_dir == temp_dir

    def test_has_git_when_available(self):
        """Test _has_git is True when git is available."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            manager = GitManager()
            assert manager._has_git is True

    def test_has_git_when_unavailable(self):
        """Test _has_git is False when git is not available."""
        with patch("shutil.which", return_value=None):
            manager = GitManager()
            assert manager._has_git is False


# ============================================================================
# _run_git Tests
# ============================================================================


class TestRunGit:
    """Tests for GitManager._run_git method."""

    @pytest.mark.asyncio
    async def test_run_git_no_git_binary(self, git_manager_no_git):
        """Test _run_git when git is not installed."""
        stdout, stderr, rc = await git_manager_no_git._run_git("status")
        assert stdout == ""
        assert stderr == "git not found"
        assert rc == 1

    @pytest.mark.asyncio
    async def test_run_git_success(self, git_manager):
        """Test _run_git with successful command."""
        mock_proc = create_mock_process(stdout="on branch main", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            stdout, stderr, rc = await git_manager._run_git("status")
            assert stdout == "on branch main"
            assert rc == 0

    @pytest.mark.asyncio
    async def test_run_git_failure(self, git_manager):
        """Test _run_git with failed command."""
        mock_proc = create_mock_process(stderr="fatal: not a repo", returncode=128)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            stdout, stderr, rc = await git_manager._run_git("status")
            assert stderr == "fatal: not a repo"
            assert rc == 128

    @pytest.mark.asyncio
    async def test_run_git_uses_working_dir(self, git_manager, temp_dir):
        """Test _run_git uses the correct working directory."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            await git_manager._run_git("status")
            mock_exec.assert_called_once()
            # Check that cwd is set correctly
            call_kwargs = mock_exec.call_args.kwargs
            assert call_kwargs["cwd"] == str(temp_dir)

    @pytest.mark.asyncio
    async def test_run_git_handles_unicode(self, git_manager):
        """Test _run_git handles unicode output correctly."""
        mock_proc = create_mock_process(stdout="file_\u00e9.py", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            stdout, _, _ = await git_manager._run_git("status")
            assert "file_\u00e9.py" in stdout


# ============================================================================
# Repository State Tests
# ============================================================================


class TestIsRepo:
    """Tests for GitManager.is_repo method."""

    @pytest.mark.asyncio
    async def test_is_repo_true(self, git_manager):
        """Test is_repo returns True for valid repo."""
        mock_proc = create_mock_process(stdout="true", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.is_repo() is True

    @pytest.mark.asyncio
    async def test_is_repo_false(self, git_manager):
        """Test is_repo returns False for non-repo."""
        mock_proc = create_mock_process(returncode=128)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.is_repo() is False

    @pytest.mark.asyncio
    async def test_is_repo_no_git(self, git_manager_no_git):
        """Test is_repo returns False when git is not installed."""
        assert await git_manager_no_git.is_repo() is False


class TestGetBranch:
    """Tests for GitManager.get_branch method."""

    @pytest.mark.asyncio
    async def test_get_branch_main(self, git_manager):
        """Test get_branch returns branch name."""
        mock_proc = create_mock_process(stdout="main\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.get_branch() == "main"

    @pytest.mark.asyncio
    async def test_get_branch_feature(self, git_manager):
        """Test get_branch returns feature branch."""
        mock_proc = create_mock_process(stdout="feature/new-ui\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.get_branch() == "feature/new-ui"

    @pytest.mark.asyncio
    async def test_get_branch_failure(self, git_manager):
        """Test get_branch returns empty string on failure."""
        mock_proc = create_mock_process(returncode=128)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.get_branch() == ""

    @pytest.mark.asyncio
    async def test_get_branch_no_git(self, git_manager_no_git):
        """Test get_branch returns empty string when git unavailable."""
        assert await git_manager_no_git.get_branch() == ""


class TestIsDirty:
    """Tests for GitManager.is_dirty method."""

    @pytest.mark.asyncio
    async def test_is_dirty_clean_repo(self, git_manager):
        """Test is_dirty returns False for clean repo."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.is_dirty() is False

    @pytest.mark.asyncio
    async def test_is_dirty_modified_files(self, git_manager):
        """Test is_dirty returns True for modified files."""
        mock_proc = create_mock_process(stdout=" M file.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.is_dirty() is True

    @pytest.mark.asyncio
    async def test_is_dirty_untracked_files(self, git_manager):
        """Test is_dirty returns True for untracked files."""
        mock_proc = create_mock_process(stdout="?? new_file.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.is_dirty() is True

    @pytest.mark.asyncio
    async def test_is_dirty_staged_files(self, git_manager):
        """Test is_dirty returns True for staged files."""
        mock_proc = create_mock_process(stdout="A  staged.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            assert await git_manager.is_dirty() is True


# ============================================================================
# File Status Tests
# ============================================================================


class TestGetStagedFiles:
    """Tests for GitManager.get_staged_files method."""

    @pytest.mark.asyncio
    async def test_get_staged_files_none(self, git_manager):
        """Test get_staged_files returns empty list when none staged."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_staged_files()
            assert files == []

    @pytest.mark.asyncio
    async def test_get_staged_files_single(self, git_manager):
        """Test get_staged_files returns single file."""
        mock_proc = create_mock_process(stdout="file.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_staged_files()
            assert files == ["file.py"]

    @pytest.mark.asyncio
    async def test_get_staged_files_multiple(self, git_manager):
        """Test get_staged_files returns multiple files."""
        mock_proc = create_mock_process(stdout="a.py\nb.py\nc.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_staged_files()
            assert files == ["a.py", "b.py", "c.py"]

    @pytest.mark.asyncio
    async def test_get_staged_files_failure(self, git_manager):
        """Test get_staged_files returns empty list on failure."""
        mock_proc = create_mock_process(returncode=128)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_staged_files()
            assert files == []


class TestGetUnstagedFiles:
    """Tests for GitManager.get_unstaged_files method."""

    @pytest.mark.asyncio
    async def test_get_unstaged_files_none(self, git_manager):
        """Test get_unstaged_files returns empty list when none."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_unstaged_files()
            assert files == []

    @pytest.mark.asyncio
    async def test_get_unstaged_files_multiple(self, git_manager):
        """Test get_unstaged_files returns multiple files."""
        mock_proc = create_mock_process(stdout="x.py\ny.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_unstaged_files()
            assert files == ["x.py", "y.py"]

    @pytest.mark.asyncio
    async def test_get_unstaged_files_failure(self, git_manager):
        """Test get_unstaged_files returns empty list on failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_unstaged_files()
            assert files == []


class TestGetUntrackedFiles:
    """Tests for GitManager.get_untracked_files method."""

    @pytest.mark.asyncio
    async def test_get_untracked_files_none(self, git_manager):
        """Test get_untracked_files returns empty list when none."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_untracked_files()
            assert files == []

    @pytest.mark.asyncio
    async def test_get_untracked_files_multiple(self, git_manager):
        """Test get_untracked_files returns multiple files."""
        mock_proc = create_mock_process(stdout="new1.py\nnew2.py\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_untracked_files()
            assert files == ["new1.py", "new2.py"]

    @pytest.mark.asyncio
    async def test_get_untracked_files_failure(self, git_manager):
        """Test get_untracked_files returns empty list on failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_untracked_files()
            assert files == []


# ============================================================================
# Diff Tests
# ============================================================================


class TestGetDiff:
    """Tests for GitManager.get_diff method."""

    @pytest.mark.asyncio
    async def test_get_diff_unstaged(self, git_manager):
        """Test get_diff for unstaged changes."""
        diff_content = "diff --git a/file.py\n+new line"
        mock_proc = create_mock_process(stdout=diff_content, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            diff = await git_manager.get_diff(staged=False)
            assert diff == diff_content

    @pytest.mark.asyncio
    async def test_get_diff_staged(self, git_manager):
        """Test get_diff for staged changes."""
        diff_content = "diff --git a/staged.py\n+staged change"
        mock_proc = create_mock_process(stdout=diff_content, returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            diff = await git_manager.get_diff(staged=True)
            assert diff == diff_content
            # Verify --cached was passed
            call_args = mock_exec.call_args[0]
            assert "--cached" in call_args

    @pytest.mark.asyncio
    async def test_get_diff_specific_file(self, git_manager):
        """Test get_diff for a specific file."""
        mock_proc = create_mock_process(stdout="file diff", returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            await git_manager.get_diff(file="specific.py")
            call_args = mock_exec.call_args[0]
            assert "--" in call_args
            assert "specific.py" in call_args

    @pytest.mark.asyncio
    async def test_get_diff_empty(self, git_manager):
        """Test get_diff returns empty string when no diff."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            diff = await git_manager.get_diff()
            assert diff == ""


class TestGetDiffStat:
    """Tests for GitManager.get_diff_stat method."""

    @pytest.mark.asyncio
    async def test_get_diff_stat_empty(self, git_manager):
        """Test get_diff_stat returns empty list when no changes."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            diffs = await git_manager.get_diff_stat()
            assert diffs == []

    @pytest.mark.asyncio
    async def test_get_diff_stat_failure(self, git_manager):
        """Test get_diff_stat returns empty list on failure."""
        mock_proc = create_mock_process(returncode=128)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            diffs = await git_manager.get_diff_stat()
            assert diffs == []

    @pytest.mark.asyncio
    async def test_get_diff_stat_single_file(self, git_manager):
        """Test get_diff_stat with single file."""
        numstat_output = "10\t5\tfile.py\n"
        stat_proc = create_mock_process(stdout=numstat_output, returncode=0)
        diff_proc = create_mock_process(stdout="diff content", returncode=0)

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return stat_proc
            return diff_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            diffs = await git_manager.get_diff_stat()
            assert len(diffs) == 1
            assert diffs[0].file == "file.py"
            assert diffs[0].additions == 10
            assert diffs[0].deletions == 5

    @pytest.mark.asyncio
    async def test_get_diff_stat_multiple_files(self, git_manager):
        """Test get_diff_stat with multiple files."""
        numstat_output = "10\t5\ta.py\n20\t0\tb.py\n0\t15\tc.py\n"
        stat_proc = create_mock_process(stdout=numstat_output, returncode=0)
        diff_proc = create_mock_process(stdout="diff", returncode=0)

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return stat_proc
            return diff_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            diffs = await git_manager.get_diff_stat()
            assert len(diffs) == 3
            assert diffs[1].additions == 20
            assert diffs[1].deletions == 0
            assert diffs[2].deletions == 15

    @pytest.mark.asyncio
    async def test_get_diff_stat_binary_file(self, git_manager):
        """Test get_diff_stat with binary file (- for stats)."""
        numstat_output = "-\t-\timage.png\n"
        stat_proc = create_mock_process(stdout=numstat_output, returncode=0)
        diff_proc = create_mock_process(stdout="Binary file", returncode=0)

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return stat_proc
            return diff_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            diffs = await git_manager.get_diff_stat()
            assert len(diffs) == 1
            assert diffs[0].file == "image.png"
            assert diffs[0].additions == 0
            assert diffs[0].deletions == 0


# ============================================================================
# Staging Tests
# ============================================================================


class TestStageFile:
    """Tests for GitManager.stage_file method."""

    @pytest.mark.asyncio
    async def test_stage_file_success(self, git_manager):
        """Test stage_file returns True on success."""
        mock_proc = create_mock_process(returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.stage_file("test.py")
            assert result is True

    @pytest.mark.asyncio
    async def test_stage_file_failure(self, git_manager):
        """Test stage_file returns False on failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.stage_file("nonexistent.py")
            assert result is False


class TestStageAll:
    """Tests for GitManager.stage_all method."""

    @pytest.mark.asyncio
    async def test_stage_all_success(self, git_manager):
        """Test stage_all returns True on success."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await git_manager.stage_all()
            assert result is True
            call_args = mock_exec.call_args[0]
            assert "-A" in call_args

    @pytest.mark.asyncio
    async def test_stage_all_failure(self, git_manager):
        """Test stage_all returns False on failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.stage_all()
            assert result is False


class TestUnstageFile:
    """Tests for GitManager.unstage_file method."""

    @pytest.mark.asyncio
    async def test_unstage_file_success(self, git_manager):
        """Test unstage_file returns True on success."""
        mock_proc = create_mock_process(returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.unstage_file("test.py")
            assert result is True

    @pytest.mark.asyncio
    async def test_unstage_file_failure(self, git_manager):
        """Test unstage_file returns False on failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.unstage_file("test.py")
            assert result is False


# ============================================================================
# Commit Tests
# ============================================================================


class TestCommit:
    """Tests for GitManager.commit method."""

    @pytest.mark.asyncio
    async def test_commit_success(self, git_manager):
        """Test successful commit."""
        staged_proc = create_mock_process(stdout="file.py\n", returncode=0)
        commit_proc = create_mock_process(
            stdout="[main abc1234] feat: add feature\n", returncode=0
        )

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "diff" in args:
                return staged_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.commit("feat: add feature")
            assert result.success is True
            assert result.sha == "abc1234"
            assert result.message == "feat: add feature"
            assert "file.py" in result.files_committed

    @pytest.mark.asyncio
    async def test_commit_nothing_staged(self, git_manager):
        """Test commit fails when nothing staged."""
        staged_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=staged_proc):
            result = await git_manager.commit("message")
            assert result.success is False
            assert result.error == "Nothing to commit"

    @pytest.mark.asyncio
    async def test_commit_failure(self, git_manager):
        """Test commit failure."""
        staged_proc = create_mock_process(stdout="file.py\n", returncode=0)
        commit_proc = create_mock_process(stderr="error: commit failed", returncode=1)

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "diff" in args:
                return staged_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.commit("message")
            assert result.success is False
            assert "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_commit_with_files(self, git_manager):
        """Test commit with specific files to stage."""
        stage_proc = create_mock_process(returncode=0)
        staged_proc = create_mock_process(stdout="a.py\nb.py\n", returncode=0)
        commit_proc = create_mock_process(
            stdout="[main def5678] message\n", returncode=0
        )

        async def mock_exec(*args, **kwargs):
            if "add" in args:
                return stage_proc
            if "diff" in args:
                return staged_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.commit("message", files=["a.py", "b.py"])
            assert result.success is True
            assert result.sha == "def5678"

    @pytest.mark.asyncio
    async def test_commit_sha_extraction(self, git_manager):
        """Test SHA extraction from various commit output formats."""
        staged_proc = create_mock_process(stdout="file.py\n", returncode=0)

        test_cases = [
            ("[main abc1234] message\n", "abc1234"),
            ("[feature/test 1234567890] long sha\n", "1234567890"),
            ("[HEAD (root-commit) abcdef0] initial\n", "abcdef0"),
        ]

        for output, expected_sha in test_cases:
            commit_proc = create_mock_process(stdout=output, returncode=0)

            call_count = 0

            async def mock_exec(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if "diff" in args:
                    return staged_proc
                return commit_proc

            with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
                result = await git_manager.commit("message")
                assert result.sha == expected_sha, f"Failed for output: {output}"


# ============================================================================
# Undo/Discard Tests
# ============================================================================


class TestUndoLastCommit:
    """Tests for GitManager.undo_last_commit method."""

    @pytest.mark.asyncio
    async def test_undo_soft(self, git_manager):
        """Test undo with soft reset (keep changes)."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await git_manager.undo_last_commit(keep_changes=True)
            assert result is True
            call_args = mock_exec.call_args[0]
            assert "--soft" in call_args

    @pytest.mark.asyncio
    async def test_undo_hard(self, git_manager):
        """Test undo with hard reset (discard changes)."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await git_manager.undo_last_commit(keep_changes=False)
            assert result is True
            call_args = mock_exec.call_args[0]
            assert "--hard" in call_args

    @pytest.mark.asyncio
    async def test_undo_failure(self, git_manager):
        """Test undo failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.undo_last_commit()
            assert result is False


class TestDiscardFile:
    """Tests for GitManager.discard_file method."""

    @pytest.mark.asyncio
    async def test_discard_success(self, git_manager):
        """Test discard_file returns True on success."""
        mock_proc = create_mock_process(returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.discard_file("test.py")
            assert result is True

    @pytest.mark.asyncio
    async def test_discard_failure(self, git_manager):
        """Test discard_file returns False on failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.discard_file("test.py")
            assert result is False


# ============================================================================
# Stash Tests
# ============================================================================


class TestStash:
    """Tests for GitManager.stash method."""

    @pytest.mark.asyncio
    async def test_stash_without_message(self, git_manager):
        """Test stash without message."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await git_manager.stash()
            assert result is True
            call_args = mock_exec.call_args[0]
            assert "stash" in call_args
            assert "push" in call_args

    @pytest.mark.asyncio
    async def test_stash_with_message(self, git_manager):
        """Test stash with message."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            result = await git_manager.stash(message="WIP: feature")
            assert result is True
            call_args = mock_exec.call_args[0]
            assert "-m" in call_args
            assert "WIP: feature" in call_args

    @pytest.mark.asyncio
    async def test_stash_failure(self, git_manager):
        """Test stash failure."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.stash()
            assert result is False


class TestStashPop:
    """Tests for GitManager.stash_pop method."""

    @pytest.mark.asyncio
    async def test_stash_pop_success(self, git_manager):
        """Test stash_pop success."""
        mock_proc = create_mock_process(returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.stash_pop()
            assert result is True

    @pytest.mark.asyncio
    async def test_stash_pop_failure(self, git_manager):
        """Test stash_pop failure (no stash)."""
        mock_proc = create_mock_process(returncode=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await git_manager.stash_pop()
            assert result is False


# ============================================================================
# Recent Commits Tests
# ============================================================================


class TestGetRecentCommits:
    """Tests for GitManager.get_recent_commits method."""

    @pytest.mark.asyncio
    async def test_get_recent_commits_empty(self, git_manager):
        """Test get_recent_commits returns empty list when no commits."""
        mock_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            commits = await git_manager.get_recent_commits()
            assert commits == []

    @pytest.mark.asyncio
    async def test_get_recent_commits_failure(self, git_manager):
        """Test get_recent_commits returns empty list on failure."""
        mock_proc = create_mock_process(returncode=128)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            commits = await git_manager.get_recent_commits()
            assert commits == []

    @pytest.mark.asyncio
    async def test_get_recent_commits_single(self, git_manager):
        """Test get_recent_commits with single commit."""
        log_output = "abc123|Initial commit|John Doe|2024-01-01T12:00:00+00:00\n"
        mock_proc = create_mock_process(stdout=log_output, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            commits = await git_manager.get_recent_commits()
            assert len(commits) == 1
            assert commits[0].sha == "abc123"
            assert commits[0].message == "Initial commit"
            assert commits[0].author == "John Doe"
            assert commits[0].is_ai_generated is False

    @pytest.mark.asyncio
    async def test_get_recent_commits_multiple(self, git_manager):
        """Test get_recent_commits with multiple commits."""
        log_output = (
            "abc123|First|Alice|2024-01-01T12:00:00+00:00\n"
            "def456|Second|Bob|2024-01-02T12:00:00+00:00\n"
            "ghi789|Third|Charlie|2024-01-03T12:00:00+00:00\n"
        )
        mock_proc = create_mock_process(stdout=log_output, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            commits = await git_manager.get_recent_commits()
            assert len(commits) == 3
            assert commits[0].sha == "abc123"
            assert commits[1].sha == "def456"
            assert commits[2].sha == "ghi789"

    @pytest.mark.asyncio
    async def test_get_recent_commits_ai_generated(self, git_manager):
        """Test get_recent_commits detects AI-generated commits."""
        log_output = (
            "abc123|[AI] Auto commit|Bot|2024-01-01T12:00:00+00:00\n"
            "def456|[null] Generated|Bot|2024-01-02T12:00:00+00:00\n"
            "ghi789|Normal commit|Human|2024-01-03T12:00:00+00:00\n"
        )
        mock_proc = create_mock_process(stdout=log_output, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            commits = await git_manager.get_recent_commits()
            assert commits[0].is_ai_generated is True
            assert commits[1].is_ai_generated is True
            assert commits[2].is_ai_generated is False

    @pytest.mark.asyncio
    async def test_get_recent_commits_custom_limit(self, git_manager):
        """Test get_recent_commits with custom limit."""
        mock_proc = create_mock_process(returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_proc
        ) as mock_exec:
            await git_manager.get_recent_commits(limit=5)
            call_args = mock_exec.call_args[0]
            assert "-5" in call_args


# ============================================================================
# AI Integration Tests
# ============================================================================


class TestGenerateCommitMessage:
    """Tests for GitManager.generate_commit_message method."""

    @pytest.mark.asyncio
    async def test_generate_message_with_staged_diff(self, git_manager):
        """Test generate_commit_message uses staged diff."""
        staged_diff_proc = create_mock_process(stdout="+new code", returncode=0)

        async def mock_generate(*args, **kwargs):
            yield "feat: add new feature"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        with patch("asyncio.create_subprocess_exec", return_value=staged_diff_proc):
            message = await git_manager.generate_commit_message(mock_provider)
            assert message == "feat: add new feature"

    @pytest.mark.asyncio
    async def test_generate_message_falls_back_to_unstaged(self, git_manager):
        """Test generate_commit_message falls back to unstaged diff."""
        empty_proc = create_mock_process(stdout="", returncode=0)
        unstaged_proc = create_mock_process(stdout="+unstaged", returncode=0)

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call is for staged
                return empty_proc
            return unstaged_proc  # Second call is for unstaged

        async def mock_generate(*args, **kwargs):
            yield "fix: bug fix"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            message = await git_manager.generate_commit_message(mock_provider)
            assert message == "fix: bug fix"

    @pytest.mark.asyncio
    async def test_generate_message_default_when_no_diff(self, git_manager):
        """Test generate_commit_message returns default when no diff."""
        empty_proc = create_mock_process(stdout="", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=empty_proc):
            mock_provider = MagicMock()
            message = await git_manager.generate_commit_message(mock_provider)
            assert message == "chore: update files"

    @pytest.mark.asyncio
    async def test_generate_message_strips_quotes(self, git_manager):
        """Test generate_commit_message strips surrounding quotes."""
        diff_proc = create_mock_process(stdout="+code", returncode=0)

        async def mock_generate(*args, **kwargs):
            yield '"feat: with quotes"'

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        with patch("asyncio.create_subprocess_exec", return_value=diff_proc):
            message = await git_manager.generate_commit_message(mock_provider)
            assert message == "feat: with quotes"

    @pytest.mark.asyncio
    async def test_generate_message_with_context(self, git_manager):
        """Test generate_commit_message includes context in prompt."""
        diff_proc = create_mock_process(stdout="+code", returncode=0)

        captured_prompt = None

        async def mock_generate(prompt, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            yield "feat: context feature"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        with patch("asyncio.create_subprocess_exec", return_value=diff_proc):
            await git_manager.generate_commit_message(
                mock_provider, context="Adding user auth"
            )
            assert "Adding user auth" in captured_prompt

    @pytest.mark.asyncio
    async def test_generate_message_default_on_empty_response(self, git_manager):
        """Test generate_commit_message returns default on empty AI response."""
        diff_proc = create_mock_process(stdout="+code", returncode=0)

        async def mock_generate(*args, **kwargs):
            yield ""

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        with patch("asyncio.create_subprocess_exec", return_value=diff_proc):
            message = await git_manager.generate_commit_message(mock_provider)
            assert message == "chore: update files"


class TestAutoCommit:
    """Tests for GitManager.auto_commit method."""

    @pytest.mark.asyncio
    async def test_auto_commit_stages_all_when_no_files(self, git_manager):
        """Test auto_commit stages all changes when no files specified."""
        stage_all_proc = create_mock_process(returncode=0)
        staged_proc = create_mock_process(stdout="file.py\n", returncode=0)
        diff_proc = create_mock_process(stdout="+code", returncode=0)
        commit_proc = create_mock_process(
            stdout="[main abc123] generated\n", returncode=0
        )

        async def mock_generate(*args, **kwargs):
            yield "feat: auto"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        commands_called = []

        async def mock_exec(*args, **kwargs):
            commands_called.append(args)
            if "add" in args and "-A" in args:
                return stage_all_proc
            if "diff" in args and "--cached" in args and "--name-only" in args:
                return staged_proc
            if "diff" in args:
                return diff_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.auto_commit(mock_provider)
            assert result.success is True
            # Check that git add -A was called
            assert any("-A" in cmd for cmd in commands_called)

    @pytest.mark.asyncio
    async def test_auto_commit_stages_specific_files(self, git_manager):
        """Test auto_commit stages specific files when provided."""
        stage_proc = create_mock_process(returncode=0)
        staged_proc = create_mock_process(stdout="a.py\nb.py\n", returncode=0)
        diff_proc = create_mock_process(stdout="+code", returncode=0)
        commit_proc = create_mock_process(
            stdout="[main def456] generated\n", returncode=0
        )

        async def mock_generate(*args, **kwargs):
            yield "feat: specific files"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        files_staged = []

        async def mock_exec(*args, **kwargs):
            if "add" in args and "-A" not in args:
                # Capture which files were staged
                for arg in args:
                    if arg.endswith(".py"):
                        files_staged.append(arg)
                return stage_proc
            if "diff" in args and "--cached" in args and "--name-only" in args:
                return staged_proc
            if "diff" in args:
                return diff_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.auto_commit(
                mock_provider, files=["a.py", "b.py"]
            )
            assert result.success is True
            assert "a.py" in files_staged
            assert "b.py" in files_staged

    @pytest.mark.asyncio
    async def test_auto_commit_nothing_to_commit(self, git_manager):
        """Test auto_commit returns error when nothing to commit."""
        stage_all_proc = create_mock_process(returncode=0)
        staged_proc = create_mock_process(stdout="", returncode=0)

        async def mock_exec(*args, **kwargs):
            if "add" in args:
                return stage_all_proc
            return staged_proc

        mock_provider = MagicMock()

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.auto_commit(mock_provider)
            assert result.success is False
            assert result.error == "Nothing to commit"

    @pytest.mark.asyncio
    async def test_auto_commit_with_context(self, git_manager):
        """Test auto_commit passes context to message generation."""
        stage_all_proc = create_mock_process(returncode=0)
        staged_proc = create_mock_process(stdout="file.py\n", returncode=0)
        diff_proc = create_mock_process(stdout="+code", returncode=0)
        commit_proc = create_mock_process(
            stdout="[main abc123] context commit\n", returncode=0
        )

        captured_context = None

        async def mock_generate(prompt, *args, **kwargs):
            nonlocal captured_context
            if "Adding auth" in prompt:
                captured_context = "Adding auth"
            yield "feat: auth"

        mock_provider = MagicMock()
        mock_provider.generate = mock_generate

        async def mock_exec(*args, **kwargs):
            if "add" in args:
                return stage_all_proc
            if "diff" in args and "--cached" in args and "--name-only" in args:
                return staged_proc
            if "diff" in args:
                return diff_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            await git_manager.auto_commit(mock_provider, context="Adding auth")
            assert captured_context == "Adding auth"


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestGetGitManager:
    """Tests for get_git_manager factory function."""

    @pytest.mark.asyncio
    async def test_get_git_manager_default(self):
        """Test get_git_manager with default path."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            manager = await get_git_manager()
            assert manager.working_dir == Path.cwd()

    @pytest.mark.asyncio
    async def test_get_git_manager_custom_path(self, temp_dir):
        """Test get_git_manager with custom path."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            manager = await get_git_manager(temp_dir)
            assert manager.working_dir == temp_dir

    @pytest.mark.asyncio
    async def test_get_git_manager_returns_gitmanager_instance(self):
        """Test get_git_manager returns GitManager instance."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            manager = await get_git_manager()
            assert isinstance(manager, GitManager)


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Edge case and integration tests."""

    @pytest.mark.asyncio
    async def test_whitespace_in_file_paths(self, git_manager):
        """Test handling of whitespace in file paths."""
        mock_proc = create_mock_process(
            stdout="path with spaces/file.py\n", returncode=0
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_staged_files()
            assert files == ["path with spaces/file.py"]

    @pytest.mark.asyncio
    async def test_special_characters_in_branch_name(self, git_manager):
        """Test handling of special characters in branch names."""
        mock_proc = create_mock_process(stdout="feature/user@123-fix\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            branch = await git_manager.get_branch()
            assert branch == "feature/user@123-fix"

    @pytest.mark.asyncio
    async def test_concurrent_git_operations(self, git_manager):
        """Test concurrent git operations don't interfere."""
        mock_proc = create_mock_process(stdout="main\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            # Run multiple operations concurrently
            results = await asyncio.gather(
                git_manager.get_branch(),
                git_manager.is_repo(),
                git_manager.is_dirty(),
            )
            assert results[0] == "main"
            assert results[1] is True
            # is_dirty checks porcelain output which is empty here

    @pytest.mark.asyncio
    async def test_empty_lines_in_file_list(self, git_manager):
        """Test that empty lines are filtered from file lists."""
        mock_proc = create_mock_process(stdout="file1.py\n\nfile2.py\n\n", returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            files = await git_manager.get_staged_files()
            assert files == ["file1.py", "file2.py"]
            assert "" not in files

    @pytest.mark.asyncio
    async def test_commit_message_with_special_chars(self, git_manager):
        """Test commit with special characters in message."""
        staged_proc = create_mock_process(stdout="file.py\n", returncode=0)
        commit_proc = create_mock_process(
            stdout='[main abc123] fix: handle "quotes" & <special>\n', returncode=0
        )

        async def mock_exec(*args, **kwargs):
            if "diff" in args:
                return staged_proc
            return commit_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_exec):
            result = await git_manager.commit('fix: handle "quotes" & <special>')
            assert result.success is True

    @pytest.mark.asyncio
    async def test_malformed_log_output(self, git_manager):
        """Test handling of malformed git log output."""
        # Missing parts in the log output
        log_output = "abc123|Only two parts|Author\n"
        mock_proc = create_mock_process(stdout=log_output, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            commits = await git_manager.get_recent_commits()
            # Should skip malformed entries
            assert commits == []

    @pytest.mark.asyncio
    async def test_numstat_with_incomplete_parts(self, git_manager):
        """Test get_diff_stat with incomplete numstat output."""
        # Only two parts instead of three
        numstat_output = "10\t5\n"
        stat_proc = create_mock_process(stdout=numstat_output, returncode=0)

        with patch("asyncio.create_subprocess_exec", return_value=stat_proc):
            diffs = await git_manager.get_diff_stat()
            # Should skip incomplete entries
            assert diffs == []
