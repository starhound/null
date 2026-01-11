"""Tests for widgets/blocks/commit_block.py - CommitBlockWidget."""

import pytest
from datetime import datetime
import inspect

from textual.widgets import Static
from textual.message import Message

from managers.git import GitCommit, GitDiff
from widgets.blocks.commit_block import CommitBlockWidget, CommitRevertRequested


@pytest.fixture
def sample_commit():
    return GitCommit(
        sha="abc1234567890",
        message="Fix bug in authentication",
        author="John Doe",
        date=datetime(2025, 1, 10, 14, 30, 0),
        files=["src/auth.py", "tests/test_auth.py"],
        is_ai_generated=False,
    )


@pytest.fixture
def ai_commit():
    return GitCommit(
        sha="def9876543210",
        message="Refactor database connection",
        author="AI Assistant",
        date=datetime(2025, 1, 10, 15, 0, 0),
        files=["src/db.py"],
        is_ai_generated=True,
    )


@pytest.fixture
def sample_diff():
    return GitDiff(
        file="src/auth.py",
        additions=10,
        deletions=5,
        content="@@ -1,5 +1,10 @@\n+added line\n-removed line",
        is_new=False,
        is_deleted=False,
    )


@pytest.fixture
def new_file_diff():
    return GitDiff(
        file="src/new_feature.py",
        additions=50,
        deletions=0,
        content="+new content",
        is_new=True,
        is_deleted=False,
    )


@pytest.fixture
def deleted_file_diff():
    return GitDiff(
        file="src/deprecated.py",
        additions=0,
        deletions=30,
        content="-old content",
        is_new=False,
        is_deleted=True,
    )


@pytest.fixture
def multiple_diffs(sample_diff, new_file_diff, deleted_file_diff):
    return [sample_diff, new_file_diff, deleted_file_diff]


class TestCommitRevertRequestedMessage:
    def test_message_is_importable(self):
        from widgets.blocks.commit_block import CommitRevertRequested

        assert CommitRevertRequested is not None

    def test_message_can_be_instantiated(self):
        msg = CommitRevertRequested(commit_sha="abc123")
        assert msg is not None

    def test_message_inherits_from_message(self):
        msg = CommitRevertRequested(commit_sha="abc123")
        assert isinstance(msg, Message)

    def test_message_stores_commit_sha(self):
        msg = CommitRevertRequested(commit_sha="abc1234567890")
        assert msg.commit_sha == "abc1234567890"

    def test_message_with_short_sha(self):
        msg = CommitRevertRequested(commit_sha="abc123")
        assert msg.commit_sha == "abc123"

    def test_message_with_full_sha(self):
        full_sha = "abc1234567890def1234567890abc1234567890ab"
        msg = CommitRevertRequested(commit_sha=full_sha)
        assert msg.commit_sha == full_sha

    def test_multiple_messages_are_independent(self):
        msg1 = CommitRevertRequested(commit_sha="sha1")
        msg2 = CommitRevertRequested(commit_sha="sha2")
        assert msg1 is not msg2
        assert msg1.commit_sha != msg2.commit_sha


class TestCommitBlockWidgetInit:
    def test_init_stores_commit(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit is sample_commit

    def test_init_stores_commit_sha(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.sha == "abc1234567890"

    def test_init_stores_commit_message(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.message == "Fix bug in authentication"

    def test_init_stores_commit_author(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.author == "John Doe"

    def test_init_stores_commit_date(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.date == datetime(2025, 1, 10, 14, 30, 0)

    def test_init_stores_commit_files(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.files == ["src/auth.py", "tests/test_auth.py"]

    def test_init_default_diffs_empty(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.diffs == []

    def test_init_with_diffs(self, sample_commit, sample_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[sample_diff])
        assert len(widget.diffs) == 1
        assert widget.diffs[0] is sample_diff

    def test_init_with_multiple_diffs(self, sample_commit, multiple_diffs):
        widget = CommitBlockWidget(commit=sample_commit, diffs=multiple_diffs)
        assert len(widget.diffs) == 3

    def test_init_with_none_diffs(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit, diffs=None)
        assert widget.diffs == []

    def test_init_accepts_kwargs(self, sample_commit):
        widget = CommitBlockWidget(
            commit=sample_commit, id="my-commit", classes="custom-class"
        )
        assert widget.id == "my-commit"
        assert "custom-class" in widget.classes

    def test_init_ai_generated_commit(self, ai_commit):
        widget = CommitBlockWidget(commit=ai_commit)
        assert widget.commit.is_ai_generated is True

    def test_init_non_ai_generated_commit(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.is_ai_generated is False


class TestCommitBlockWidgetCSS:
    def test_default_css_contains_widget_selector(self):
        assert "CommitBlockWidget" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_contains_commit_header(self):
        assert ".commit-header" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_contains_commit_file(self):
        assert ".commit-file" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_contains_added_class(self):
        assert ".added" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_contains_modified_class(self):
        assert ".modified" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_contains_deleted_class(self):
        assert ".deleted" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_uses_success_variable(self):
        assert "$success" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_uses_warning_variable(self):
        assert "$warning" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_uses_error_variable(self):
        assert "$error" in CommitBlockWidget.DEFAULT_CSS

    def test_default_css_uses_text_muted_variable(self):
        assert "$text-muted" in CommitBlockWidget.DEFAULT_CSS


class TestCommitBlockWidgetCompose:
    def test_compose_returns_generator(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_exists(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert hasattr(widget, "compose")
        assert callable(widget.compose)

    def test_compose_method_is_generator_function(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert inspect.isgeneratorfunction(widget.compose) or hasattr(
            widget.compose(), "__iter__"
        )

    def test_widget_has_default_css(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.DEFAULT_CSS is not None
        assert len(widget.DEFAULT_CSS) > 0


class TestCommitBlockWidgetInheritance:
    def test_inherits_from_static(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert isinstance(widget, Static)

    def test_has_standard_widget_attributes(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert hasattr(widget, "compose")
        assert hasattr(widget, "render")
        assert hasattr(widget, "styles")

    def test_has_default_css(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.DEFAULT_CSS is not None
        assert len(widget.DEFAULT_CSS) > 0


class TestCommitBlockWidgetEdgeCases:
    def test_commit_with_empty_message(self):
        commit = GitCommit(
            sha="abc123",
            message="",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert widget.commit.message == ""

    def test_commit_with_long_message(self):
        long_message = "Fix " + "x" * 500
        commit = GitCommit(
            sha="abc123",
            message=long_message,
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert len(widget.commit.message) > 100

    def test_commit_with_unicode_message(self):
        commit = GitCommit(
            sha="abc123",
            message="修复认证中的错误",
            author="开发者",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert "修复" in widget.commit.message

    def test_commit_with_special_characters_in_message(self):
        commit = GitCommit(
            sha="abc123",
            message="Fix <script>alert('xss')</script> & \"quotes\"",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert "<script>" in widget.commit.message

    def test_commit_with_multiline_message(self):
        commit = GitCommit(
            sha="abc123",
            message="Fix bug\n\nThis is a detailed description\nwith multiple lines",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert "\n" in widget.commit.message

    def test_commit_with_empty_sha(self):
        commit = GitCommit(
            sha="",
            message="Message",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert widget.commit.sha == ""

    def test_diff_with_zero_changes(self, sample_commit):
        diff = GitDiff(
            file="unchanged.py",
            additions=0,
            deletions=0,
            content="",
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert len(widget.diffs) == 1

    def test_diff_with_large_changes(self, sample_commit):
        diff = GitDiff(
            file="big_change.py",
            additions=10000,
            deletions=5000,
            content="+x\n" * 10000,
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].additions == 10000

    def test_diff_with_unicode_filename(self, sample_commit):
        diff = GitDiff(
            file="src/日本語/ファイル.py",
            additions=5,
            deletions=2,
            content="+日本語",
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert "日本語" in widget.diffs[0].file

    def test_diff_with_spaces_in_filename(self, sample_commit):
        diff = GitDiff(
            file="src/my file with spaces.py",
            additions=1,
            deletions=0,
            content="+new line",
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert "my file with spaces" in widget.diffs[0].file


class TestCommitBlockWidgetDiffStatus:
    def test_new_file_is_classified_correctly(self, sample_commit):
        diff = GitDiff(
            file="new.py",
            additions=10,
            deletions=0,
            content="+",
            is_new=True,
            is_deleted=False,
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].is_new is True

    def test_deleted_file_is_classified_correctly(self, sample_commit):
        diff = GitDiff(
            file="deleted.py",
            additions=0,
            deletions=10,
            content="-",
            is_new=False,
            is_deleted=True,
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].is_deleted is True

    def test_modified_file_is_classified_correctly(self, sample_commit):
        diff = GitDiff(
            file="modified.py",
            additions=5,
            deletions=3,
            content="+\n-",
            is_new=False,
            is_deleted=False,
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].is_new is False
        assert widget.diffs[0].is_deleted is False

    def test_renamed_file_diff(self, sample_commit):
        diff = GitDiff(
            file="new_name.py",
            additions=0,
            deletions=0,
            content="",
            is_new=False,
            is_deleted=False,
            is_renamed=True,
            old_path="old_name.py",
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].is_renamed is True
        assert widget.diffs[0].old_path == "old_name.py"


class TestCommitBlockWidgetCommitFields:
    def test_all_commit_fields_accessible(self):
        commit = GitCommit(
            sha="abc1234567890",
            message="Test message",
            author="Test Author",
            date=datetime(2025, 1, 10, 12, 0, 0),
            files=["file1.py", "file2.py"],
            is_ai_generated=True,
        )
        widget = CommitBlockWidget(commit=commit)

        assert widget.commit.sha == "abc1234567890"
        assert widget.commit.message == "Test message"
        assert widget.commit.author == "Test Author"
        assert widget.commit.date == datetime(2025, 1, 10, 12, 0, 0)
        assert widget.commit.files == ["file1.py", "file2.py"]
        assert widget.commit.is_ai_generated is True

    def test_commit_files_default_empty(self):
        commit = GitCommit(
            sha="abc123",
            message="Message",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert widget.commit.files == []


class TestCommitBlockWidgetMultipleDiffs:
    def test_handles_empty_diffs_list(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[])
        assert widget.diffs == []

    def test_handles_single_diff(self, sample_commit, sample_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[sample_diff])
        assert len(widget.diffs) == 1

    def test_handles_many_diffs(self, sample_commit):
        diffs = [
            GitDiff(file=f"file{i}.py", additions=i, deletions=0, content=f"+{i}")
            for i in range(20)
        ]
        widget = CommitBlockWidget(commit=sample_commit, diffs=diffs)
        assert len(widget.diffs) == 20

    def test_preserves_diff_order(self, sample_commit):
        diffs = [
            GitDiff(file="first.py", additions=1, deletions=0, content="+"),
            GitDiff(file="second.py", additions=2, deletions=0, content="+"),
            GitDiff(file="third.py", additions=3, deletions=0, content="+"),
        ]
        widget = CommitBlockWidget(commit=sample_commit, diffs=diffs)
        assert widget.diffs[0].file == "first.py"
        assert widget.diffs[1].file == "second.py"
        assert widget.diffs[2].file == "third.py"


class TestCommitBlockWidgetGitDiffFields:
    def test_diff_file_field(self, sample_commit, sample_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[sample_diff])
        assert widget.diffs[0].file == "src/auth.py"

    def test_diff_additions_field(self, sample_commit, sample_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[sample_diff])
        assert widget.diffs[0].additions == 10

    def test_diff_deletions_field(self, sample_commit, sample_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[sample_diff])
        assert widget.diffs[0].deletions == 5

    def test_diff_content_field(self, sample_commit, sample_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[sample_diff])
        assert "@@ -1,5 +1,10 @@" in widget.diffs[0].content

    def test_diff_is_new_field(self, sample_commit, new_file_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[new_file_diff])
        assert widget.diffs[0].is_new is True

    def test_diff_is_deleted_field(self, sample_commit, deleted_file_diff):
        widget = CommitBlockWidget(commit=sample_commit, diffs=[deleted_file_diff])
        assert widget.diffs[0].is_deleted is True


class TestCommitBlockWidgetGitCommitDate:
    def test_commit_date_is_datetime(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert isinstance(widget.commit.date, datetime)

    def test_commit_date_year(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.date.year == 2025

    def test_commit_date_month(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.date.month == 1

    def test_commit_date_day(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.date.day == 10

    def test_commit_date_hour(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.date.hour == 14

    def test_commit_date_minute(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.date.minute == 30


class TestCommitBlockWidgetSHAFormat:
    def test_sha_is_string(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert isinstance(widget.commit.sha, str)

    def test_sha_can_be_sliced(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        short_sha = widget.commit.sha[:7]
        assert short_sha == "abc1234"

    def test_short_sha_length(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert len(widget.commit.sha[:7]) == 7

    def test_full_sha_length(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert len(widget.commit.sha) == 13

    def test_sha_with_only_hex_chars(self):
        commit = GitCommit(
            sha="abcdef1234567890",
            message="Msg",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert all(c in "0123456789abcdef" for c in widget.commit.sha)


class TestCommitBlockWidgetAuthorField:
    def test_author_is_string(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert isinstance(widget.commit.author, str)

    def test_author_value(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.author == "John Doe"

    def test_author_with_email(self):
        commit = GitCommit(
            sha="abc123",
            message="Msg",
            author="John Doe <john@example.com>",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert "john@example.com" in widget.commit.author

    def test_author_with_unicode(self):
        commit = GitCommit(
            sha="abc123",
            message="Msg",
            author="山田太郎",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert widget.commit.author == "山田太郎"


class TestCommitBlockWidgetAIGenerated:
    def test_ai_generated_true(self, ai_commit):
        widget = CommitBlockWidget(commit=ai_commit)
        assert widget.commit.is_ai_generated is True

    def test_ai_generated_false(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert widget.commit.is_ai_generated is False

    def test_ai_generated_default_false(self):
        commit = GitCommit(
            sha="abc123",
            message="Msg",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert widget.commit.is_ai_generated is False


class TestCommitBlockWidgetFilesField:
    def test_files_is_list(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert isinstance(widget.commit.files, list)

    def test_files_count(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert len(widget.commit.files) == 2

    def test_files_contains_expected_files(self, sample_commit):
        widget = CommitBlockWidget(commit=sample_commit)
        assert "src/auth.py" in widget.commit.files
        assert "tests/test_auth.py" in widget.commit.files

    def test_files_empty_by_default(self):
        commit = GitCommit(
            sha="abc123",
            message="Msg",
            author="Author",
            date=datetime.now(),
        )
        widget = CommitBlockWidget(commit=commit)
        assert widget.commit.files == []


class TestCommitBlockWidgetDiffContentFormats:
    def test_diff_with_unified_format(self, sample_commit):
        diff = GitDiff(
            file="test.py",
            additions=2,
            deletions=1,
            content="@@ -1,3 +1,4 @@\n context\n-removed\n+added1\n+added2",
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert "@@" in widget.diffs[0].content

    def test_diff_with_only_additions(self, sample_commit):
        diff = GitDiff(
            file="new.py",
            additions=3,
            deletions=0,
            content="+line1\n+line2\n+line3",
            is_new=True,
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].content.count("+") == 3

    def test_diff_with_only_deletions(self, sample_commit):
        diff = GitDiff(
            file="old.py",
            additions=0,
            deletions=3,
            content="-line1\n-line2\n-line3",
            is_deleted=True,
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert widget.diffs[0].content.count("-") == 3

    def test_diff_with_context_lines(self, sample_commit):
        diff = GitDiff(
            file="test.py",
            additions=1,
            deletions=0,
            content=" context\n+added\n context",
        )
        widget = CommitBlockWidget(commit=sample_commit, diffs=[diff])
        assert " context" in widget.diffs[0].content
