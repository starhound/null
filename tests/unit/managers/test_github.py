import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.github import (
    GitHubComment,
    GitHubContextManager,
    GitHubIssue,
    GitHubPR,
)


class TestGitHubDataClasses:
    def test_github_comment_creation(self):
        comment = GitHubComment(
            author="testuser",
            body="This is a test comment",
            created_at="2025-01-10T10:00:00Z",
        )
        assert comment.author == "testuser"
        assert comment.body == "This is a test comment"
        assert comment.created_at == "2025-01-10T10:00:00Z"

    def test_github_issue_creation(self):
        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="Issue body",
            state="open",
            labels=["bug", "priority"],
            comments=[],
        )
        assert issue.number == 123
        assert issue.title == "Test Issue"
        assert issue.state == "open"
        assert "bug" in issue.labels

    def test_github_issue_defaults(self):
        issue = GitHubIssue(
            number=1,
            title="Title",
            body="Body",
            state="open",
        )
        assert issue.labels == []
        assert issue.comments == []
        assert issue.linked_prs == []

    def test_github_pr_creation(self):
        pr = GitHubPR(
            number=456,
            title="Test PR",
            body="PR body",
            state="open",
            base_branch="main",
            head_branch="feature/test",
            files_changed=["file1.py", "file2.py"],
        )
        assert pr.number == 456
        assert pr.title == "Test PR"
        assert pr.base_branch == "main"
        assert pr.head_branch == "feature/test"
        assert len(pr.files_changed) == 2

    def test_github_pr_defaults(self):
        pr = GitHubPR(
            number=1,
            title="Title",
            body="Body",
            state="open",
            base_branch="main",
            head_branch="feature",
        )
        assert pr.diff == ""
        assert pr.files_changed == []
        assert pr.comments == []
        assert pr.checks == []


class TestGitHubContextManager:
    @pytest.fixture
    def manager(self):
        return GitHubContextManager()

    @pytest.mark.asyncio
    async def test_run_gh_handles_missing_cli(self, manager):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            output, rc = await manager._run_gh("repo", "view")
            assert rc == 1
            assert "gh CLI not installed" in output

    @pytest.mark.asyncio
    async def test_detect_repo_success(self, manager):
        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ("owner/repo\n", 0)
            result = await manager.detect_repo()
            assert result == "owner/repo"
            mock_run.assert_called_once_with(
                "repo", "view", "--json", "nameWithOwner", "-q", "nameWithOwner"
            )

    @pytest.mark.asyncio
    async def test_detect_repo_failure(self, manager):
        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ("", 1)
            result = await manager.detect_repo()
            assert result is None

    @pytest.mark.asyncio
    async def test_detect_repo_cached(self, manager):
        manager._repo = "cached/repo"
        result = await manager.detect_repo()
        assert result == "cached/repo"

    @pytest.mark.asyncio
    async def test_get_issue_success(self, manager):
        issue_data = {
            "number": 123,
            "title": "Test Issue",
            "body": "Issue body",
            "state": "OPEN",
            "labels": [{"name": "bug"}],
        }
        comments_data = {
            "comments": [
                {
                    "author": {"login": "user1"},
                    "body": "Comment 1",
                    "createdAt": "2025-01-10T10:00:00Z",
                }
            ]
        }

        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                ("owner/repo", 0),
                (json.dumps(issue_data), 0),
                (json.dumps(comments_data), 0),
            ]

            result = await manager.get_issue(123)

            assert result is not None
            assert result.number == 123
            assert result.title == "Test Issue"
            assert "bug" in result.labels
            assert len(result.comments) == 1
            assert result.comments[0].author == "user1"

    @pytest.mark.asyncio
    async def test_get_issue_no_repo(self, manager):
        with patch.object(
            manager, "detect_repo", new_callable=AsyncMock
        ) as mock_detect:
            mock_detect.return_value = None
            result = await manager.get_issue(123)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_pr_success(self, manager):
        pr_data = {
            "number": 456,
            "title": "Test PR",
            "body": "PR body",
            "state": "OPEN",
            "baseRefName": "main",
            "headRefName": "feature",
            "files": [{"path": "file1.py"}],
        }
        comments_data = {"comments": []}
        checks_data = {"statusCheckRollup": []}

        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                ("owner/repo", 0),
                (json.dumps(pr_data), 0),
                (json.dumps(comments_data), 0),
                (json.dumps(checks_data), 0),
            ]

            result = await manager.get_pr(456)

            assert result is not None
            assert result.number == 456
            assert result.title == "Test PR"
            assert result.base_branch == "main"
            assert result.head_branch == "feature"
            assert "file1.py" in result.files_changed

    @pytest.mark.asyncio
    async def test_get_pr_diff(self, manager):
        manager._repo = "owner/repo"

        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = ("+ added line\n- removed line", 0)
            result = await manager.get_pr_diff(123)
            assert "+ added line" in result
            assert "- removed line" in result

    @pytest.mark.asyncio
    async def test_list_issues(self, manager):
        issues_data = [
            {"number": 1, "title": "Issue 1", "state": "OPEN", "labels": []},
            {"number": 2, "title": "Issue 2", "state": "OPEN", "labels": []},
        ]

        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                ("owner/repo", 0),
                (json.dumps(issues_data), 0),
            ]

            result = await manager.list_issues()

            assert len(result) == 2
            assert result[0].number == 1
            assert result[1].number == 2

    @pytest.mark.asyncio
    async def test_list_prs(self, manager):
        prs_data = [
            {
                "number": 10,
                "title": "PR 1",
                "state": "OPEN",
                "baseRefName": "main",
                "headRefName": "feature1",
            },
        ]

        with patch.object(manager, "_run_gh", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                ("owner/repo", 0),
                (json.dumps(prs_data), 0),
            ]

            result = await manager.list_prs()

            assert len(result) == 1
            assert result[0].number == 10


class TestFormatMethods:
    def test_format_issue_context(self):
        manager = GitHubContextManager()
        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="This is the body",
            state="open",
            labels=["bug", "priority"],
            comments=[
                GitHubComment(
                    author="user1",
                    body="First comment",
                    created_at="2025-01-10",
                )
            ],
        )

        result = manager.format_issue_context(issue)

        assert "# Issue #123: Test Issue" in result
        assert "**State:** open" in result
        assert "bug, priority" in result
        assert "This is the body" in result
        assert "@user1" in result
        assert "First comment" in result

    def test_format_pr_context(self):
        manager = GitHubContextManager()
        pr = GitHubPR(
            number=456,
            title="Test PR",
            body="PR description",
            state="open",
            base_branch="main",
            head_branch="feature",
            files_changed=["file1.py", "file2.py"],
            checks=[{"name": "CI", "status": "success"}],
        )

        result = manager.format_pr_context(pr)

        assert "# PR #456: Test PR" in result
        assert "**State:** open" in result
        assert "**Base:** main" in result
        assert "**Head:** feature" in result
        assert "file1.py" in result
        assert "CI: success" in result
