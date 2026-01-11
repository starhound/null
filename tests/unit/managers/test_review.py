import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from managers.review import (
    HunkStatus,
    DiffHunk,
    ProposedChange,
    ReviewManager,
)


class TestHunkStatusEnum:
    def test_pending_status(self):
        assert HunkStatus.PENDING.value == "pending"

    def test_accepted_status(self):
        assert HunkStatus.ACCEPTED.value == "accepted"

    def test_rejected_status(self):
        assert HunkStatus.REJECTED.value == "rejected"

    def test_all_statuses_exist(self):
        statuses = [HunkStatus.PENDING, HunkStatus.ACCEPTED, HunkStatus.REJECTED]
        assert len(statuses) == 3


class TestDiffHunk:
    def test_create_basic(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["line1", "line2"],
            proposed=["new1", "new2"],
        )
        assert hunk.start_line == 1
        assert hunk.end_line == 5
        assert hunk.original_lines == ["line1", "line2"]
        assert hunk.proposed_lines == ["new1", "new2"]
        assert hunk.status == HunkStatus.PENDING
        assert hunk.id is not None
        assert len(hunk.id) == 8

    def test_create_with_context(self):
        hunk = DiffHunk.create(
            start_line=10,
            end_line=15,
            original=["old"],
            proposed=["new"],
            context_before=["ctx1", "ctx2"],
            context_after=["ctx3", "ctx4"],
        )
        assert hunk.context_before == ["ctx1", "ctx2"]
        assert hunk.context_after == ["ctx3", "ctx4"]

    def test_create_without_context(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["a"],
            proposed=["b"],
        )
        assert hunk.context_before == []
        assert hunk.context_after == []

    def test_create_empty_original(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=1,
            original=[],
            proposed=["new"],
        )
        assert hunk.original_lines == []
        assert hunk.proposed_lines == ["new"]

    def test_create_empty_proposed(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["old"],
            proposed=[],
        )
        assert hunk.original_lines == ["old"]
        assert hunk.proposed_lines == []

    def test_diff_text_single_line(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["old"],
            proposed=["new"],
        )
        assert hunk.diff_text == "- old\n+ new"

    def test_diff_text_multiple_lines(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=3,
            original=["line1", "line2"],
            proposed=["new1", "new2", "new3"],
        )
        expected = "- line1\n- line2\n+ new1\n+ new2\n+ new3"
        assert hunk.diff_text == expected

    def test_diff_text_empty_original(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=1,
            original=[],
            proposed=["added"],
        )
        assert hunk.diff_text == "+ added"

    def test_diff_text_empty_proposed(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["removed"],
            proposed=[],
        )
        assert hunk.diff_text == "- removed"

    def test_additions_count(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["old"],
            proposed=["new1", "new2", "new3"],
        )
        assert hunk.additions == 3

    def test_additions_empty(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["old"],
            proposed=[],
        )
        assert hunk.additions == 0

    def test_deletions_count(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=4,
            original=["line1", "line2", "line3"],
            proposed=["new"],
        )
        assert hunk.deletions == 3

    def test_deletions_empty(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=1,
            original=[],
            proposed=["new"],
        )
        assert hunk.deletions == 0

    def test_hunk_id_uniqueness(self):
        hunk1 = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["a"],
            proposed=["b"],
        )
        hunk2 = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["a"],
            proposed=["b"],
        )
        assert hunk1.id != hunk2.id


class TestProposedChange:
    def test_from_content_new_file(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="print('hello')",
            rationale="Add greeting",
        )
        assert change.file == "new.py"
        assert change.original is None
        assert change.proposed == "print('hello')"
        assert change.is_new_file is True
        assert change.is_deletion is False
        assert change.rationale == "Add greeting"
        assert change.hunks == []

    def test_from_content_existing_file(self):
        original = "old content"
        proposed = "new content"
        change = ProposedChange.from_content(
            file="existing.py",
            original=original,
            proposed=proposed,
        )
        assert change.file == "existing.py"
        assert change.original == original
        assert change.proposed == proposed
        assert change.is_new_file is False
        assert change.is_deletion is False
        assert len(change.hunks) > 0

    def test_from_content_deletion(self):
        change = ProposedChange.from_content(
            file="delete.py",
            original="content to delete",
            proposed="",
        )
        assert change.file == "delete.py"
        assert change.is_deletion is True
        assert change.is_new_file is False
        assert change.proposed == ""

    def test_from_content_no_rationale(self):
        change = ProposedChange.from_content(
            file="test.py",
            original=None,
            proposed="content",
        )
        assert change.rationale == ""

    def test_compute_hunks_single_line_change(self):
        original = "line1\nline2\nline3"
        proposed = "line1\nmodified\nline3"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) == 1
        assert change.hunks[0].original_lines == ["line2"]
        assert change.hunks[0].proposed_lines == ["modified"]

    def test_compute_hunks_multiple_changes(self):
        original = "a\nb\nc\nd\ne"
        proposed = "a\nX\nc\nY\ne"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) == 2

    def test_compute_hunks_addition(self):
        original = "line1\nline2"
        proposed = "line1\nnew\nline2"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) == 1
        assert "new" in change.hunks[0].proposed_lines

    def test_compute_hunks_deletion(self):
        original = "line1\nremove\nline2"
        proposed = "line1\nline2"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) == 1
        assert "remove" in change.hunks[0].original_lines

    def test_compute_hunks_with_context(self):
        original = "a\nb\nc\nd\ne\nf\ng"
        proposed = "a\nb\nX\nd\ne\nf\ng"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        hunk = change.hunks[0]
        assert len(hunk.context_before) > 0
        assert len(hunk.context_after) > 0

    def test_compute_hunks_empty_original(self):
        change = ProposedChange.from_content(
            file="new.py",
            original="",
            proposed="content",
        )
        assert len(change.hunks) == 1

    def test_compute_hunks_empty_proposed(self):
        change = ProposedChange.from_content(
            file="delete.py",
            original="content",
            proposed="",
        )
        assert len(change.hunks) == 1

    def test_compute_hunks_no_changes(self):
        content = "line1\nline2\nline3"
        change = ProposedChange.from_content(
            file="test.py",
            original=content,
            proposed=content,
        )
        assert len(change.hunks) == 0

    def test_total_additions_new_file(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="line1\nline2\nline3",
        )
        assert change.total_additions == 3

    def test_total_additions_new_file_single_line(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="single line",
        )
        assert change.total_additions == 1

    def test_total_additions_new_file_empty(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="",
        )
        assert change.total_additions == 0

    def test_total_additions_existing_file(self):
        original = "a\nb"
        proposed = "a\nb\nc\nd"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert change.total_additions == 3

    def test_total_deletions_deletion(self):
        change = ProposedChange.from_content(
            file="delete.py",
            original="line1\nline2\nline3",
            proposed="",
        )
        assert change.total_deletions == 3

    def test_total_deletions_deletion_single_line(self):
        change = ProposedChange.from_content(
            file="delete.py",
            original="single",
            proposed="",
        )
        assert change.total_deletions == 1

    def test_total_deletions_existing_file(self):
        original = "a\nb\nc"
        proposed = "a"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert change.total_deletions == 3

    def test_all_accepted_true(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        for hunk in change.hunks:
            hunk.status = HunkStatus.ACCEPTED
        assert change.all_accepted is True

    def test_all_accepted_false_with_pending(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        assert change.all_accepted is False

    def test_all_accepted_false_with_rejected(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        for hunk in change.hunks:
            hunk.status = HunkStatus.REJECTED
        assert change.all_accepted is False

    def test_all_accepted_empty_hunks(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="same",
            proposed="same",
        )
        assert change.all_accepted is True

    def test_all_rejected_true(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        for hunk in change.hunks:
            hunk.status = HunkStatus.REJECTED
        assert change.all_rejected is True

    def test_all_rejected_false_with_pending(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        assert change.all_rejected is False

    def test_all_rejected_false_with_accepted(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        for hunk in change.hunks:
            hunk.status = HunkStatus.ACCEPTED
        assert change.all_rejected is False

    def test_all_rejected_empty_hunks(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="same",
            proposed="same",
        )
        assert change.all_rejected is True

    def test_apply_accepted_new_file_all_accepted(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="content",
        )
        result = change.apply_accepted()
        assert result == "content"

    def test_apply_accepted_new_file_not_accepted(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="content",
        )
        result = change.apply_accepted()
        assert result == "content"

    def test_apply_accepted_single_hunk_accepted(self):
        original = "line1\nline2\nline3"
        proposed = "line1\nmodified\nline3"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        change.hunks[0].status = HunkStatus.ACCEPTED
        result = change.apply_accepted()
        assert "modified" in result
        assert "line1" in result
        assert "line3" in result

    def test_apply_accepted_single_hunk_rejected(self):
        original = "line1\nline2\nline3"
        proposed = "line1\nmodified\nline3"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        change.hunks[0].status = HunkStatus.REJECTED
        result = change.apply_accepted()
        assert "line2" in result
        assert "modified" not in result

    def test_apply_accepted_multiple_hunks_partial(self):
        original = "a\nb\nc\nd\ne"
        proposed = "a\nX\nc\nY\ne"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        if len(change.hunks) >= 2:
            change.hunks[0].status = HunkStatus.ACCEPTED
            change.hunks[1].status = HunkStatus.REJECTED
            result = change.apply_accepted()
            assert "X" in result
            assert "Y" not in result

    def test_apply_accepted_no_original(self):
        change = ProposedChange.from_content(
            file="test.py",
            original=None,
            proposed="content",
        )
        result = change.apply_accepted()
        assert result == "content"

    def test_apply_accepted_preserves_newlines(self):
        original = "line1\nline2\nline3"
        proposed = "line1\nmodified\nline3"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        change.hunks[0].status = HunkStatus.ACCEPTED
        result = change.apply_accepted()
        assert result.endswith("line3")
        assert not result.endswith("\n")


class TestReviewManager:
    def test_init(self):
        manager = ReviewManager()
        assert manager.pending_changes == {}
        assert manager.review_enabled is True

    def test_propose_new_file(self):
        manager = ReviewManager()
        change = manager.propose(
            file="new.py",
            original=None,
            proposed="content",
            rationale="Add new file",
        )
        assert change.file == "new.py"
        assert manager.pending_changes["new.py"] == change

    def test_propose_existing_file(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="old",
            proposed="new",
        )
        assert change.file == "test.py"
        assert manager.pending_changes["test.py"] == change

    def test_propose_overwrites_previous(self):
        manager = ReviewManager()
        change1 = manager.propose(
            file="test.py",
            original=None,
            proposed="v1",
        )
        change2 = manager.propose(
            file="test.py",
            original=None,
            proposed="v2",
        )
        assert manager.pending_changes["test.py"] == change2
        assert manager.pending_changes["test.py"] != change1

    def test_propose_multiple_files(self):
        manager = ReviewManager()
        manager.propose("file1.py", None, "content1")
        manager.propose("file2.py", None, "content2")
        manager.propose("file3.py", None, "content3")
        assert len(manager.pending_changes) == 3

    def test_get_change_exists(self):
        manager = ReviewManager()
        change = manager.propose("test.py", None, "content")
        retrieved = manager.get_change("test.py")
        assert retrieved == change

    def test_get_change_not_exists(self):
        manager = ReviewManager()
        retrieved = manager.get_change("nonexistent.py")
        assert retrieved is None

    def test_accept_hunk_valid(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        hunk_id = change.hunks[0].id
        result = manager.accept_hunk("test.py", hunk_id)
        assert result is True
        assert change.hunks[0].status == HunkStatus.ACCEPTED

    def test_accept_hunk_invalid_file(self):
        manager = ReviewManager()
        result = manager.accept_hunk("nonexistent.py", "hunk123")
        assert result is False

    def test_accept_hunk_invalid_hunk(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")
        result = manager.accept_hunk("test.py", "invalid_hunk_id")
        assert result is False

    def test_accept_hunk_multiple_hunks(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="a\nb\nc\nd\ne",
            proposed="a\nX\nc\nY\ne",
        )
        if len(change.hunks) >= 2:
            hunk_id = change.hunks[0].id
            result = manager.accept_hunk("test.py", hunk_id)
            assert result is True
            assert change.hunks[0].status == HunkStatus.ACCEPTED
            assert change.hunks[1].status == HunkStatus.PENDING

    def test_reject_hunk_valid(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="a\nb",
            proposed="a\nc",
        )
        hunk_id = change.hunks[0].id
        result = manager.reject_hunk("test.py", hunk_id)
        assert result is True
        assert change.hunks[0].status == HunkStatus.REJECTED

    def test_reject_hunk_invalid_file(self):
        manager = ReviewManager()
        result = manager.reject_hunk("nonexistent.py", "hunk123")
        assert result is False

    def test_reject_hunk_invalid_hunk(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")
        result = manager.reject_hunk("test.py", "invalid_hunk_id")
        assert result is False

    def test_accept_file_valid(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="a\nb\nc",
            proposed="a\nX\nY",
        )
        result = manager.accept_file("test.py")
        assert result is True
        for hunk in change.hunks:
            assert hunk.status == HunkStatus.ACCEPTED

    def test_accept_file_invalid(self):
        manager = ReviewManager()
        result = manager.accept_file("nonexistent.py")
        assert result is False

    def test_accept_file_no_hunks(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="same",
            proposed="same",
        )
        result = manager.accept_file("test.py")
        assert result is True

    def test_reject_file_valid(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="a\nb\nc",
            proposed="a\nX\nY",
        )
        result = manager.reject_file("test.py")
        assert result is True
        for hunk in change.hunks:
            assert hunk.status == HunkStatus.REJECTED

    def test_reject_file_invalid(self):
        manager = ReviewManager()
        result = manager.reject_file("nonexistent.py")
        assert result is False

    def test_accept_all_counts_pending_only(self):
        manager = ReviewManager()
        change1 = manager.propose("file1.py", "a\nb", "a\nc")
        change2 = manager.propose("file2.py", "x\ny", "x\nz")

        if len(change1.hunks) > 0:
            change1.hunks[0].status = HunkStatus.ACCEPTED

        count = manager.accept_all()
        assert count >= 1

    def test_accept_all_no_pending(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        for hunk in change.hunks:
            hunk.status = HunkStatus.ACCEPTED
        count = manager.accept_all()
        assert count == 0

    def test_accept_all_multiple_files(self):
        manager = ReviewManager()
        manager.propose("file1.py", "a\nb", "a\nc")
        manager.propose("file2.py", "x\ny", "x\nz")
        manager.propose("file3.py", "p\nq", "p\nr")

        count = manager.accept_all()
        assert count >= 1

        for change in manager.pending_changes.values():
            for hunk in change.hunks:
                assert hunk.status == HunkStatus.ACCEPTED

    def test_reject_all_counts_pending_only(self):
        manager = ReviewManager()
        change1 = manager.propose("file1.py", "a\nb", "a\nc")
        change2 = manager.propose("file2.py", "x\ny", "x\nz")

        if len(change1.hunks) > 0:
            change1.hunks[0].status = HunkStatus.REJECTED

        count = manager.reject_all()
        assert count >= 1

    def test_reject_all_no_pending(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        for hunk in change.hunks:
            hunk.status = HunkStatus.REJECTED
        count = manager.reject_all()
        assert count == 0

    def test_reject_all_multiple_files(self):
        manager = ReviewManager()
        manager.propose("file1.py", "a\nb", "a\nc")
        manager.propose("file2.py", "x\ny", "x\nz")
        manager.propose("file3.py", "p\nq", "p\nr")

        count = manager.reject_all()
        assert count >= 1

        for change in manager.pending_changes.values():
            for hunk in change.hunks:
                assert hunk.status == HunkStatus.REJECTED

    @pytest.mark.asyncio
    async def test_apply_accepted_new_file(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "new.py"
        manager.propose(
            file=str(file_path),
            original=None,
            proposed="print('hello')",
        )
        applied = await manager.apply_accepted()
        assert str(file_path) in applied
        assert file_path.exists()
        assert file_path.read_text() == "print('hello')"

    @pytest.mark.asyncio
    async def test_apply_accepted_existing_file(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "test.py"
        file_path.write_text("line1\nline2\nline3")

        change = manager.propose(
            file=str(file_path),
            original="line1\nline2\nline3",
            proposed="line1\nmodified\nline3",
        )
        change.hunks[0].status = HunkStatus.ACCEPTED

        applied = await manager.apply_accepted()
        assert str(file_path) in applied
        content = file_path.read_text()
        assert "modified" in content

    @pytest.mark.asyncio
    async def test_apply_accepted_deletion(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "delete.py"
        file_path.write_text("content to delete")

        change = manager.propose(
            file=str(file_path),
            original="content to delete",
            proposed="",
        )
        change.hunks[0].status = HunkStatus.ACCEPTED

        applied = await manager.apply_accepted()
        assert str(file_path) in applied
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_apply_accepted_creates_directories(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "subdir" / "nested" / "file.py"
        manager.propose(
            file=str(file_path),
            original=None,
            proposed="content",
        )
        applied = await manager.apply_accepted()
        assert str(file_path) in applied
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_apply_accepted_removes_from_pending(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "test.py"
        manager.propose(
            file=str(file_path),
            original=None,
            proposed="content",
        )
        assert str(file_path) in manager.pending_changes
        await manager.apply_accepted()
        assert str(file_path) not in manager.pending_changes

    @pytest.mark.asyncio
    async def test_apply_accepted_skips_rejected(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "test.py"
        change = manager.propose(
            file=str(file_path),
            original="a\nb",
            proposed="a\nc",
        )
        change.hunks[0].status = HunkStatus.REJECTED
        applied = await manager.apply_accepted()
        assert str(file_path) not in applied

    @pytest.mark.asyncio
    async def test_apply_accepted_multiple_files(self, temp_dir):
        manager = ReviewManager()
        file1 = temp_dir / "file1.py"
        file2 = temp_dir / "file2.py"

        manager.propose(str(file1), None, "content1")
        manager.propose(str(file2), None, "content2")

        applied = await manager.apply_accepted()
        assert len(applied) == 2
        assert file1.exists()
        assert file2.exists()

    @pytest.mark.asyncio
    async def test_apply_accepted_partial_acceptance(self, temp_dir):
        manager = ReviewManager()
        file_path = temp_dir / "test.py"
        file_path.write_text("a\nb\nc\nd\ne")

        change = manager.propose(
            file=str(file_path),
            original="a\nb\nc\nd\ne",
            proposed="a\nX\nc\nY\ne",
        )

        if len(change.hunks) >= 2:
            change.hunks[0].status = HunkStatus.ACCEPTED
            change.hunks[1].status = HunkStatus.REJECTED

            applied = await manager.apply_accepted()
            assert str(file_path) in applied
            content = file_path.read_text()
            assert "X" in content
            assert "Y" not in content

    def test_clear(self):
        manager = ReviewManager()
        manager.propose("file1.py", None, "content1")
        manager.propose("file2.py", None, "content2")
        assert len(manager.pending_changes) == 2
        manager.clear()
        assert len(manager.pending_changes) == 0

    def test_clear_empty(self):
        manager = ReviewManager()
        manager.clear()
        assert len(manager.pending_changes) == 0

    def test_get_summary_no_changes(self):
        manager = ReviewManager()
        summary = manager.get_summary()
        assert "No pending changes" in summary

    def test_get_summary_single_file(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")
        summary = manager.get_summary()
        assert "Pending changes: 1 file(s)" in summary
        assert "test.py" in summary

    def test_get_summary_multiple_files(self):
        manager = ReviewManager()
        manager.propose("file1.py", None, "content1")
        manager.propose("file2.py", None, "content2")
        summary = manager.get_summary()
        assert "Pending changes: 2 file(s)" in summary
        assert "file1.py" in summary
        assert "file2.py" in summary

    def test_get_summary_with_accepted(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        change.hunks[0].status = HunkStatus.ACCEPTED
        summary = manager.get_summary()
        assert "accepted" in summary

    def test_get_summary_with_rejected(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        change.hunks[0].status = HunkStatus.REJECTED
        summary = manager.get_summary()
        assert "rejected" in summary

    def test_get_summary_with_pending(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")
        summary = manager.get_summary()
        assert "pending" in summary

    def test_get_summary_mixed_statuses(self):
        manager = ReviewManager()
        change = manager.propose(
            file="test.py",
            original="a\nb\nc\nd\ne",
            proposed="a\nX\nc\nY\ne",
        )
        if len(change.hunks) >= 2:
            change.hunks[0].status = HunkStatus.ACCEPTED
            change.hunks[1].status = HunkStatus.REJECTED
            summary = manager.get_summary()
            assert "accepted" in summary
            assert "rejected" in summary

    def test_get_summary_shows_additions_deletions(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nb\nc\nd")
        summary = manager.get_summary()
        assert "+" in summary
        assert "-" in summary

    def test_get_summary_new_file(self):
        manager = ReviewManager()
        manager.propose("new.py", None, "line1\nline2\nline3")
        summary = manager.get_summary()
        assert "new.py" in summary
        assert "+3" in summary

    def test_get_summary_deletion(self):
        manager = ReviewManager()
        manager.propose("delete.py", "line1\nline2\nline3", "")
        summary = manager.get_summary()
        assert "delete.py" in summary
        assert "-3" in summary


class TestEdgeCases:
    def test_special_characters_in_content(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="old\n",
            proposed="new with special chars: !@#$%^&*()\n",
        )
        assert len(change.hunks) > 0

    def test_unicode_content(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="hello\n",
            proposed="你好世界\n",
        )
        assert len(change.hunks) > 0

    def test_very_long_lines(self):
        long_line = "x" * 10000
        change = ProposedChange.from_content(
            file="test.py",
            original=long_line,
            proposed=long_line + "y",
        )
        assert len(change.hunks) > 0

    def test_many_small_changes(self):
        original = "\n".join([f"line{i}" for i in range(100)])
        proposed = "\n".join(
            [f"line{i}" if i % 2 == 0 else f"modified{i}" for i in range(100)]
        )
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) > 0

    def test_windows_line_endings(self):
        original = "line1\r\nline2\r\nline3\r\n"
        proposed = "line1\r\nmodified\r\nline3\r\n"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) > 0

    def test_mixed_line_endings(self):
        original = "line1\nline2\r\nline3\n"
        proposed = "line1\nmodified\r\nline3\n"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) > 0

    def test_file_with_no_trailing_newline(self):
        original = "line1\nline2"
        proposed = "line1\nmodified"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) > 0

    def test_empty_string_content(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="",
            proposed="",
        )
        assert len(change.hunks) == 0

    def test_whitespace_only_changes(self):
        original = "line1\nline2"
        proposed = "line1  \nline2"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) > 0

    def test_tab_characters(self):
        original = "def func():\n\tpass"
        proposed = "def func():\n\t\tpass"
        change = ProposedChange.from_content(
            file="test.py",
            original=original,
            proposed=proposed,
        )
        assert len(change.hunks) > 0
