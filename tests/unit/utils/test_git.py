from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.git import GitStatus, get_git_status


class TestGitStatus:
    def test_default_values(self):
        status = GitStatus()
        assert status.branch == ""
        assert status.is_dirty is False
        assert status.is_repo is False

    def test_custom_values(self):
        status = GitStatus(branch="main", is_dirty=True, is_repo=True)
        assert status.branch == "main"
        assert status.is_dirty is True
        assert status.is_repo is True


class TestGetGitStatus:
    @pytest.mark.asyncio
    async def test_no_git_command(self):
        with patch("shutil.which", return_value=None):
            result = await get_git_status()
            assert result.is_repo is False
            assert result.branch == ""

    @pytest.mark.asyncio
    async def test_not_git_repo(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 128
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            result = await get_git_status()
            assert result.is_repo is False

    @pytest.mark.asyncio
    async def test_clean_repo(self):
        check_proc = MagicMock()
        check_proc.returncode = 0
        check_proc.communicate = AsyncMock(return_value=(b"true\n", b""))

        branch_proc = MagicMock()
        branch_proc.returncode = 0
        branch_proc.communicate = AsyncMock(return_value=(b"main\n", b""))

        status_proc = MagicMock()
        status_proc.returncode = 0
        status_proc.communicate = AsyncMock(return_value=(b"", b""))

        call_count = 0

        async def mock_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return check_proc
            elif call_count == 2:
                return branch_proc
            else:
                return status_proc

        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess),
        ):
            result = await get_git_status()
            assert result.is_repo is True
            assert result.branch == "main"
            assert result.is_dirty is False

    @pytest.mark.asyncio
    async def test_dirty_repo(self):
        check_proc = MagicMock()
        check_proc.returncode = 0
        check_proc.communicate = AsyncMock(return_value=(b"true\n", b""))

        branch_proc = MagicMock()
        branch_proc.returncode = 0
        branch_proc.communicate = AsyncMock(return_value=(b"feature/test\n", b""))

        status_proc = MagicMock()
        status_proc.returncode = 0
        status_proc.communicate = AsyncMock(return_value=(b" M file.py\n", b""))

        call_count = 0

        async def mock_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return check_proc
            elif call_count == 2:
                return branch_proc
            else:
                return status_proc

        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess),
        ):
            result = await get_git_status()
            assert result.is_repo is True
            assert result.branch == "feature/test"
            assert result.is_dirty is True

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch("asyncio.create_subprocess_exec", side_effect=Exception("Git error")),
        ):
            result = await get_git_status()
            assert result.is_repo is False
            assert result.branch == ""
