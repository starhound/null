"""Tests for the review screen."""

from unittest.mock import MagicMock

from managers.review import DiffHunk, HunkStatus, ProposedChange, ReviewManager
from screens.review import FileChangeWidget, HunkWidget, ReviewScreen


class TestHunkWidgetMessages:
    """Test HunkWidget message classes."""

    def test_accepted_message_stores_hunk_id(self):
        msg = HunkWidget.Accepted(hunk_id="abc123")
        assert msg.hunk_id == "abc123"

    def test_rejected_message_stores_hunk_id(self):
        msg = HunkWidget.Rejected(hunk_id="def456")
        assert msg.hunk_id == "def456"

    def test_accepted_message_empty_id(self):
        msg = HunkWidget.Accepted(hunk_id="")
        assert msg.hunk_id == ""

    def test_rejected_message_empty_id(self):
        msg = HunkWidget.Rejected(hunk_id="")
        assert msg.hunk_id == ""


class TestHunkWidget:
    """Test HunkWidget initialization and behavior."""

    def test_init_stores_hunk(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old line"],
            proposed=["new line"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk == hunk

    def test_init_with_context(self):
        hunk = DiffHunk.create(
            start_line=10,
            end_line=15,
            original=["old"],
            proposed=["new"],
            context_before=["ctx1", "ctx2"],
            context_after=["ctx3"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.context_before == ["ctx1", "ctx2"]
        assert widget.hunk.context_after == ["ctx3"]

    def test_hunk_status_pending_by_default(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.status == HunkStatus.PENDING

    def test_hunk_status_can_be_changed_to_accepted(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        hunk.status = HunkStatus.ACCEPTED
        widget = HunkWidget(hunk)
        assert widget.hunk.status == HunkStatus.ACCEPTED

    def test_hunk_status_can_be_changed_to_rejected(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        hunk.status = HunkStatus.REJECTED
        widget = HunkWidget(hunk)
        assert widget.hunk.status == HunkStatus.REJECTED

    def test_on_mount_adds_status_class(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        widget = HunkWidget(hunk)
        # Mock set_class
        widget.set_class = MagicMock()
        widget.on_mount()
        widget.set_class.assert_called_once_with(True, "pending")

    def test_on_mount_adds_accepted_class(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        hunk.status = HunkStatus.ACCEPTED
        widget = HunkWidget(hunk)
        widget.set_class = MagicMock()
        widget.on_mount()
        widget.set_class.assert_called_once_with(True, "accepted")

    def test_on_mount_adds_rejected_class(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        hunk.status = HunkStatus.REJECTED
        widget = HunkWidget(hunk)
        widget.set_class = MagicMock()
        widget.on_mount()
        widget.set_class.assert_called_once_with(True, "rejected")

    def test_on_button_pressed_accept(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        widget = HunkWidget(hunk)
        widget.post_message = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "accept"
        mock_event = MagicMock()
        mock_event.button = mock_button

        widget.on_button_pressed(mock_event)

        assert widget.post_message.called
        posted_msg = widget.post_message.call_args[0][0]
        assert isinstance(posted_msg, HunkWidget.Accepted)
        assert posted_msg.hunk_id == hunk.id

    def test_on_button_pressed_reject(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        widget = HunkWidget(hunk)
        widget.post_message = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "reject"
        mock_event = MagicMock()
        mock_event.button = mock_button

        widget.on_button_pressed(mock_event)

        assert widget.post_message.called
        posted_msg = widget.post_message.call_args[0][0]
        assert isinstance(posted_msg, HunkWidget.Rejected)
        assert posted_msg.hunk_id == hunk.id

    def test_on_button_pressed_unknown_does_nothing(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["old"],
            proposed=["new"],
        )
        widget = HunkWidget(hunk)
        widget.post_message = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "unknown"
        mock_event = MagicMock()
        mock_event.button = mock_button

        widget.on_button_pressed(mock_event)

        widget.post_message.assert_not_called()


class TestHunkWidgetWithMultipleLines:
    """Test HunkWidget with various line configurations."""

    def test_multiple_original_lines(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=10,
            original=["line1", "line2", "line3", "line4", "line5"],
            proposed=["new1"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.original_lines == [
            "line1",
            "line2",
            "line3",
            "line4",
            "line5",
        ]

    def test_multiple_proposed_lines(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=2,
            original=["old"],
            proposed=["new1", "new2", "new3", "new4"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.proposed_lines == ["new1", "new2", "new3", "new4"]

    def test_empty_original_lines(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=1,
            original=[],
            proposed=["new line"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.original_lines == []

    def test_empty_proposed_lines(self):
        hunk = DiffHunk.create(
            start_line=1,
            end_line=5,
            original=["deleted"],
            proposed=[],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.proposed_lines == []


class TestFileChangeWidget:
    """Test FileChangeWidget initialization and behavior."""

    def test_init_stores_file_and_change(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="old content",
            proposed="new content",
        )
        widget = FileChangeWidget("test.py", change)
        assert widget.file == "test.py"
        assert widget.change == change

    def test_init_with_new_file(self):
        change = ProposedChange.from_content(
            file="new.py",
            original=None,
            proposed="print('hello')",
        )
        widget = FileChangeWidget("new.py", change)
        assert widget.change.is_new_file is True

    def test_init_with_deletion(self):
        change = ProposedChange.from_content(
            file="delete.py",
            original="content",
            proposed="",
        )
        widget = FileChangeWidget("delete.py", change)
        assert widget.change.is_deletion is True

    def test_init_with_rationale(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="old",
            proposed="new",
            rationale="Refactoring for clarity",
        )
        widget = FileChangeWidget("test.py", change)
        assert widget.change.rationale == "Refactoring for clarity"

    def test_file_change_stores_hunks(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="old\nline",
            proposed="new\nline",
        )
        widget = FileChangeWidget("test.py", change)
        assert len(widget.change.hunks) > 0

    def test_file_change_with_no_rationale(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="old",
            proposed="new",
        )
        widget = FileChangeWidget("test.py", change)
        assert widget.change.rationale == ""

    def test_file_change_with_empty_hunks(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="same",
            proposed="same",
        )
        widget = FileChangeWidget("test.py", change)
        assert len(widget.change.hunks) == 0


class TestFileChangeWidgetProperties:
    """Test FileChangeWidget computed properties."""

    def test_total_additions_displayed(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb",
            proposed="a\nb\nc\nd\ne",
        )
        widget = FileChangeWidget("test.py", change)
        assert widget.change.total_additions > 0

    def test_total_deletions_displayed(self):
        change = ProposedChange.from_content(
            file="test.py",
            original="a\nb\nc\nd",
            proposed="a",
        )
        widget = FileChangeWidget("test.py", change)
        assert widget.change.total_deletions > 0


class TestReviewScreen:
    """Test ReviewScreen initialization and behavior."""

    def test_init_stores_manager(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        assert screen.manager == manager

    def test_bindings_defined(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys
        assert "enter" in binding_keys
        assert "a" in binding_keys
        assert "r" in binding_keys

    def test_manager_has_pending_changes(self):
        manager = ReviewManager()
        manager.propose("test.py", "old", "new")
        screen = ReviewScreen(manager)
        assert len(screen.manager.pending_changes) == 1

    def test_manager_with_no_changes(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        assert len(screen.manager.pending_changes) == 0

    def test_manager_with_multiple_files(self):
        manager = ReviewManager()
        manager.propose("file1.py", "a", "b")
        manager.propose("file2.py", "c", "d")
        manager.propose("file3.py", "e", "f")
        screen = ReviewScreen(manager)
        assert len(screen.manager.pending_changes) == 3


class TestReviewScreenActions:
    """Test ReviewScreen action methods."""

    def test_action_cancel_dismisses_false(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()

        screen.action_cancel()

        screen.dismiss.assert_called_once_with(False)

    def test_action_apply_dismisses_true(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()

        screen.action_apply()

        screen.dismiss.assert_called_once_with(True)

    def test_action_accept_all(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        screen.action_accept_all()

        for hunk in change.hunks:
            assert hunk.status == HunkStatus.ACCEPTED

    def test_action_reject_all(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        screen.action_reject_all()

        for hunk in change.hunks:
            assert hunk.status == HunkStatus.REJECTED

    def test_action_accept_all_multiple_files(self):
        manager = ReviewManager()
        change1 = manager.propose("file1.py", "a\nb", "a\nc")
        change2 = manager.propose("file2.py", "x\ny", "x\nz")
        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        screen.action_accept_all()

        for hunk in change1.hunks:
            assert hunk.status == HunkStatus.ACCEPTED
        for hunk in change2.hunks:
            assert hunk.status == HunkStatus.ACCEPTED

    def test_action_reject_all_multiple_files(self):
        manager = ReviewManager()
        change1 = manager.propose("file1.py", "a\nb", "a\nc")
        change2 = manager.propose("file2.py", "x\ny", "x\nz")
        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        screen.action_reject_all()

        for hunk in change1.hunks:
            assert hunk.status == HunkStatus.REJECTED
        for hunk in change2.hunks:
            assert hunk.status == HunkStatus.REJECTED


class TestReviewScreenButtonHandling:
    """Test ReviewScreen button press handling."""

    def test_cancel_button_dismisses_false(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "cancel"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with(False)

    def test_apply_button_dismisses_true(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "apply"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)

        screen.dismiss.assert_called_once_with(True)

    def test_accept_all_button_on_file_widget(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)

        # Create mock parent hierarchy
        file_widget = MagicMock(spec=FileChangeWidget)
        file_widget.file = "test.py"

        mock_button = MagicMock()
        mock_button.id = "accept-all"
        mock_button.parent = file_widget
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen._refresh_file = MagicMock()
        screen.on_button_pressed(mock_event)

        for hunk in change.hunks:
            assert hunk.status == HunkStatus.ACCEPTED

    def test_reject_all_button_on_file_widget(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)

        # Create mock parent hierarchy
        file_widget = MagicMock(spec=FileChangeWidget)
        file_widget.file = "test.py"

        mock_button = MagicMock()
        mock_button.id = "reject-all"
        mock_button.parent = file_widget
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen._refresh_file = MagicMock()
        screen.on_button_pressed(mock_event)

        for hunk in change.hunks:
            assert hunk.status == HunkStatus.REJECTED

    def test_accept_all_button_traverses_parent_hierarchy(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)

        # Create mock parent hierarchy with intermediate widget
        file_widget = MagicMock(spec=FileChangeWidget)
        file_widget.file = "test.py"

        intermediate = MagicMock()
        intermediate.parent = file_widget

        mock_button = MagicMock()
        mock_button.id = "accept-all"
        mock_button.parent = intermediate
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen._refresh_file = MagicMock()
        screen.on_button_pressed(mock_event)

        for hunk in change.hunks:
            assert hunk.status == HunkStatus.ACCEPTED

    def test_reject_all_button_traverses_parent_hierarchy(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)

        # Create mock parent hierarchy with intermediate widget
        file_widget = MagicMock(spec=FileChangeWidget)
        file_widget.file = "test.py"

        intermediate = MagicMock()
        intermediate.parent = file_widget

        mock_button = MagicMock()
        mock_button.id = "reject-all"
        mock_button.parent = intermediate
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen._refresh_file = MagicMock()
        screen.on_button_pressed(mock_event)

        for hunk in change.hunks:
            assert hunk.status == HunkStatus.REJECTED

    def test_accept_all_no_parent_file_widget(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)

        # Mock parent chain without FileChangeWidget
        mock_parent = MagicMock()
        mock_parent.parent = None

        mock_button = MagicMock()
        mock_button.id = "accept-all"
        mock_button.parent = mock_parent
        mock_event = MagicMock()
        mock_event.button = mock_button

        # Should not raise - gracefully handles missing parent
        screen.on_button_pressed(mock_event)


class TestReviewScreenHunkEvents:
    """Test ReviewScreen hunk acceptance/rejection event handling."""

    def test_on_hunk_widget_accepted(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        hunk_id = change.hunks[0].id

        screen = ReviewScreen(manager)
        screen._refresh_hunk = MagicMock()

        event = HunkWidget.Accepted(hunk_id=hunk_id)
        screen.on_hunk_widget_accepted(event)

        assert change.hunks[0].status == HunkStatus.ACCEPTED

    def test_on_hunk_widget_rejected(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        hunk_id = change.hunks[0].id

        screen = ReviewScreen(manager)
        screen._refresh_hunk = MagicMock()

        event = HunkWidget.Rejected(hunk_id=hunk_id)
        screen.on_hunk_widget_rejected(event)

        assert change.hunks[0].status == HunkStatus.REJECTED

    def test_on_hunk_widget_accepted_invalid_id(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")

        screen = ReviewScreen(manager)
        screen._refresh_hunk = MagicMock()

        event = HunkWidget.Accepted(hunk_id="invalid_id")
        # Should not raise - gracefully handles invalid ID
        screen.on_hunk_widget_accepted(event)
        screen._refresh_hunk.assert_not_called()

    def test_on_hunk_widget_rejected_invalid_id(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")

        screen = ReviewScreen(manager)
        screen._refresh_hunk = MagicMock()

        event = HunkWidget.Rejected(hunk_id="invalid_id")
        # Should not raise - gracefully handles invalid ID
        screen.on_hunk_widget_rejected(event)
        screen._refresh_hunk.assert_not_called()

    def test_on_hunk_widget_accepted_multiple_files(self):
        manager = ReviewManager()
        change1 = manager.propose("file1.py", "a\nb", "a\nc")
        change2 = manager.propose("file2.py", "x\ny", "x\nz")
        hunk_id = change2.hunks[0].id

        screen = ReviewScreen(manager)
        screen._refresh_hunk = MagicMock()

        event = HunkWidget.Accepted(hunk_id=hunk_id)
        screen.on_hunk_widget_accepted(event)

        # First file should be unchanged
        assert change1.hunks[0].status == HunkStatus.PENDING
        # Second file should be accepted
        assert change2.hunks[0].status == HunkStatus.ACCEPTED

    def test_on_hunk_widget_rejected_multiple_files(self):
        manager = ReviewManager()
        change1 = manager.propose("file1.py", "a\nb", "a\nc")
        change2 = manager.propose("file2.py", "x\ny", "x\nz")
        hunk_id = change1.hunks[0].id

        screen = ReviewScreen(manager)
        screen._refresh_hunk = MagicMock()

        event = HunkWidget.Rejected(hunk_id=hunk_id)
        screen.on_hunk_widget_rejected(event)

        # First file should be rejected
        assert change1.hunks[0].status == HunkStatus.REJECTED
        # Second file should be unchanged
        assert change2.hunks[0].status == HunkStatus.PENDING


class TestReviewScreenRefreshMethods:
    """Test ReviewScreen refresh helper methods."""

    def test_refresh_hunk_updates_widget_classes(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        hunk_id = change.hunks[0].id
        change.hunks[0].status = HunkStatus.ACCEPTED

        screen = ReviewScreen(manager)

        # Create mock HunkWidget
        mock_hunk_widget = MagicMock()
        mock_hunk_widget.hunk.id = hunk_id
        mock_hunk_widget.hunk.status = MagicMock()
        mock_hunk_widget.hunk.status.value = "accepted"

        screen.query = MagicMock(return_value=[mock_hunk_widget])

        screen._refresh_hunk(hunk_id)

        mock_hunk_widget.remove_class.assert_called_once_with(
            "pending", "accepted", "rejected"
        )
        mock_hunk_widget.add_class.assert_called_once_with("accepted")
        mock_hunk_widget.refresh.assert_called_once()

    def test_refresh_hunk_nonexistent_id(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")

        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        # Should not raise - gracefully handles missing widget
        screen._refresh_hunk("nonexistent_id")

    def test_refresh_file_updates_all_hunk_widgets(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb\nc\nd\ne", "a\nX\nc\nY\ne")
        change.hunks[0].status = HunkStatus.ACCEPTED
        if len(change.hunks) > 1:
            change.hunks[1].status = HunkStatus.REJECTED

        screen = ReviewScreen(manager)

        # Create mock FileChangeWidget with HunkWidgets
        mock_hunk1 = MagicMock()
        mock_hunk1.hunk.status.value = "accepted"
        mock_hunk2 = MagicMock()
        mock_hunk2.hunk.status.value = "rejected"

        mock_file_widget = MagicMock()
        mock_file_widget.file = "test.py"
        mock_file_widget.query = MagicMock(return_value=[mock_hunk1, mock_hunk2])

        screen.query = MagicMock(return_value=[mock_file_widget])

        screen._refresh_file("test.py")

        # Verify each hunk widget was updated
        for mock_hunk in [mock_hunk1, mock_hunk2]:
            mock_hunk.remove_class.assert_called_once_with(
                "pending", "accepted", "rejected"
            )
            mock_hunk.add_class.assert_called_once()
            mock_hunk.refresh.assert_called_once()

    def test_refresh_file_nonexistent_file(self):
        manager = ReviewManager()
        manager.propose("test.py", "a\nb", "a\nc")

        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        # Should not raise - gracefully handles missing file
        screen._refresh_file("nonexistent.py")


class TestReviewScreenWithEmptyManager:
    def test_empty_manager_has_no_changes(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        assert len(screen.manager.pending_changes) == 0

    def test_action_accept_all_with_empty_manager(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        # Should not raise
        screen.action_accept_all()

    def test_action_reject_all_with_empty_manager(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.query = MagicMock(return_value=[])

        # Should not raise
        screen.action_reject_all()


class TestReviewScreenCSS:
    """Test that CSS classes are properly defined."""

    def test_hunk_widget_has_default_css(self):
        assert HunkWidget.DEFAULT_CSS is not None
        assert len(HunkWidget.DEFAULT_CSS) > 0

    def test_hunk_widget_css_contains_status_classes(self):
        css = HunkWidget.DEFAULT_CSS
        assert ".pending" in css or "HunkWidget.pending" in css
        assert ".accepted" in css or "HunkWidget.accepted" in css
        assert ".rejected" in css or "HunkWidget.rejected" in css

    def test_file_change_widget_has_default_css(self):
        assert FileChangeWidget.DEFAULT_CSS is not None
        assert len(FileChangeWidget.DEFAULT_CSS) > 0

    def test_review_screen_has_default_css(self):
        manager = ReviewManager()
        ReviewScreen(manager)
        assert ReviewScreen.DEFAULT_CSS is not None
        assert len(ReviewScreen.DEFAULT_CSS) > 0


class TestReviewScreenWithNewFile:
    def test_new_file_is_marked_as_new(self):
        manager = ReviewManager()
        manager.propose("new.py", None, "print('hello')")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("new.py")
        assert change.is_new_file is True

    def test_new_file_has_no_hunks(self):
        manager = ReviewManager()
        change = manager.propose("new.py", None, "print('hello')")
        assert len(change.hunks) == 0
        screen = ReviewScreen(manager)
        assert len(screen.manager.get_change("new.py").hunks) == 0

    def test_new_file_proposed_content(self):
        manager = ReviewManager()
        manager.propose("new.py", None, "print('hello')")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("new.py")
        assert change.proposed == "print('hello')"


class TestReviewScreenWithDeletion:
    def test_deletion_is_marked_as_deletion(self):
        manager = ReviewManager()
        manager.propose("delete.py", "content to delete", "")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("delete.py")
        assert change.is_deletion is True

    def test_deletion_proposed_content_is_empty(self):
        manager = ReviewManager()
        manager.propose("delete.py", "content to delete", "")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("delete.py")
        assert change.proposed == ""

    def test_deletion_has_hunks(self):
        manager = ReviewManager()
        manager.propose("delete.py", "content to delete", "")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("delete.py")
        assert len(change.hunks) > 0


class TestReviewScreenSummaryCount:
    """Test that summary counts are accurate."""

    def test_single_file_count(self):
        manager = ReviewManager()
        manager.propose("test.py", "a", "b")
        ReviewScreen(manager)
        assert len(manager.pending_changes) == 1

    def test_multiple_file_count(self):
        manager = ReviewManager()
        manager.propose("file1.py", "a", "b")
        manager.propose("file2.py", "c", "d")
        manager.propose("file3.py", "e", "f")
        ReviewScreen(manager)
        assert len(manager.pending_changes) == 3


class TestHunkWidgetLineDisplay:
    """Test HunkWidget line number and content display."""

    def test_line_range_display(self):
        hunk = DiffHunk.create(
            start_line=10,
            end_line=20,
            original=["old"],
            proposed=["new"],
        )
        widget = HunkWidget(hunk)
        assert widget.hunk.start_line == 10
        assert widget.hunk.end_line == 20

    def test_context_lines(self):
        hunk = DiffHunk.create(
            start_line=5,
            end_line=7,
            original=["old"],
            proposed=["new"],
            context_before=["before1", "before2", "before3"],
            context_after=["after1", "after2"],
        )
        widget = HunkWidget(hunk)
        assert len(widget.hunk.context_before) == 3
        assert len(widget.hunk.context_after) == 2


class TestEdgeCasesReviewScreen:
    def test_unicode_content_in_manager(self):
        manager = ReviewManager()
        manager.propose("test.py", "hello", "")
        screen = ReviewScreen(manager)
        assert "test.py" in screen.manager.pending_changes

    def test_very_long_file_path_in_manager(self):
        manager = ReviewManager()
        long_path = "a" * 200 + "/test.py"
        manager.propose(long_path, "old", "new")
        screen = ReviewScreen(manager)
        assert long_path in screen.manager.pending_changes

    def test_special_characters_in_content(self):
        manager = ReviewManager()
        manager.propose("test.py", "old\n", "new !@#$%^&*()\n")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("test.py")
        assert "!@#$%^&*()" in change.proposed

    def test_whitespace_only_change_creates_hunks(self):
        manager = ReviewManager()
        manager.propose("test.py", "line1\nline2", "line1  \nline2")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("test.py")
        assert len(change.hunks) > 0

    def test_manager_review_enabled_by_default(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        assert screen.manager.review_enabled is True

    def test_manager_clear_removes_all_changes(self):
        manager = ReviewManager()
        manager.propose("file1.py", "a", "b")
        manager.propose("file2.py", "c", "d")
        screen = ReviewScreen(manager)
        screen.manager.clear()
        assert len(screen.manager.pending_changes) == 0


class TestReviewScreenModalBehavior:
    def test_is_modal_screen(self):
        from textual.screen import ModalScreen

        manager = ReviewManager()
        screen = ReviewScreen(manager)
        assert isinstance(screen, ModalScreen)

    def test_apply_dismisses_with_true(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()
        screen.action_apply()
        screen.dismiss.assert_called_with(True)

    def test_cancel_dismisses_with_false(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()
        screen.action_cancel()
        screen.dismiss.assert_called_with(False)


class TestReviewScreenBindingActions:
    def test_escape_binding_exists(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        bindings = {b.key: b for b in screen.BINDINGS}
        assert "escape" in bindings
        assert bindings["escape"].action == "cancel"

    def test_enter_binding_exists(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        bindings = {b.key: b for b in screen.BINDINGS}
        assert "enter" in bindings
        assert bindings["enter"].action == "apply"

    def test_a_binding_for_accept_all(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        bindings = {b.key: b for b in screen.BINDINGS}
        assert "a" in bindings
        assert bindings["a"].action == "accept_all"

    def test_r_binding_for_reject_all(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        bindings = {b.key: b for b in screen.BINDINGS}
        assert "r" in bindings
        assert bindings["r"].action == "reject_all"


class TestHunkWidgetAcceptedMessage:
    def test_accepted_inherits_from_message(self):
        from textual.message import Message

        msg = HunkWidget.Accepted(hunk_id="test")
        assert isinstance(msg, Message)

    def test_accepted_with_special_chars_id(self):
        msg = HunkWidget.Accepted(hunk_id="!@#$%^&*()")
        assert msg.hunk_id == "!@#$%^&*()"

    def test_accepted_with_unicode_id(self):
        msg = HunkWidget.Accepted(hunk_id="")
        assert msg.hunk_id == ""


class TestHunkWidgetRejectedMessage:
    def test_rejected_inherits_from_message(self):
        from textual.message import Message

        msg = HunkWidget.Rejected(hunk_id="test")
        assert isinstance(msg, Message)

    def test_rejected_with_special_chars_id(self):
        msg = HunkWidget.Rejected(hunk_id="!@#$%^&*()")
        assert msg.hunk_id == "!@#$%^&*()"

    def test_rejected_with_unicode_id(self):
        msg = HunkWidget.Rejected(hunk_id="")
        assert msg.hunk_id == ""


class TestReviewScreenManagerInteraction:
    def test_accept_file_via_manager(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)
        screen.manager.accept_file("test.py")
        assert all(h.status == HunkStatus.ACCEPTED for h in change.hunks)

    def test_reject_file_via_manager(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)
        screen.manager.reject_file("test.py")
        assert all(h.status == HunkStatus.REJECTED for h in change.hunks)

    def test_get_change_via_screen(self):
        manager = ReviewManager()
        manager.propose("test.py", "old", "new")
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("test.py")
        assert change is not None
        assert change.file == "test.py"

    def test_get_nonexistent_change_returns_none(self):
        manager = ReviewManager()
        screen = ReviewScreen(manager)
        change = screen.manager.get_change("nonexistent.py")
        assert change is None


class TestFileChangeWidgetAttributes:
    def test_widget_stores_file_path(self):
        change = ProposedChange.from_content("path/to/file.py", "old", "new")
        widget = FileChangeWidget("path/to/file.py", change)
        assert widget.file == "path/to/file.py"

    def test_widget_stores_change_object(self):
        change = ProposedChange.from_content("test.py", "old", "new")
        widget = FileChangeWidget("test.py", change)
        assert widget.change is change

    def test_widget_change_additions(self):
        change = ProposedChange.from_content("test.py", "a", "a\nb\nc")
        widget = FileChangeWidget("test.py", change)
        assert widget.change.total_additions >= 2

    def test_widget_change_deletions(self):
        change = ProposedChange.from_content("test.py", "a\nb\nc", "a")
        widget = FileChangeWidget("test.py", change)
        assert widget.change.total_deletions >= 2


class TestReviewScreenUnknownButton:
    def test_unknown_button_id_does_nothing(self):
        manager = ReviewManager()
        change = manager.propose("test.py", "a\nb", "a\nc")
        screen = ReviewScreen(manager)
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "unknown-button-id"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_not_called()
        assert change.hunks[0].status == HunkStatus.PENDING
