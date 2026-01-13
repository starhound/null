"""Integration tests for ReviewScreen modal."""

import pytest
from unittest.mock import MagicMock, patch

from textual.widgets import Label

from managers.review import DiffHunk, HunkStatus, ProposedChange, ReviewManager
from screens.review import FileChangeWidget, HunkWidget, ReviewScreen


@pytest.fixture
def mock_review_manager():
    """Create a ReviewManager with test data."""
    manager = ReviewManager()

    # Create a sample proposed change with hunks
    hunk1 = DiffHunk.create(
        start_line=10,
        end_line=12,
        original=["old line 1", "old line 2"],
        proposed=["new line 1", "new line 2", "new line 3"],
        context_before=["context before"],
        context_after=["context after"],
    )
    hunk2 = DiffHunk.create(
        start_line=20,
        end_line=21,
        original=["another old line"],
        proposed=["another new line"],
        context_before=["more context"],
        context_after=[],
    )

    change = ProposedChange(
        file="test_file.py",
        original="old content",
        proposed="new content",
        hunks=[hunk1, hunk2],
        rationale="Test rationale for changes",
    )

    manager.pending_changes["test_file.py"] = change
    return manager


@pytest.fixture
def mock_review_manager_multiple_files():
    """Create a ReviewManager with multiple files."""
    manager = ReviewManager()

    # File 1
    hunk1 = DiffHunk.create(
        start_line=5,
        end_line=6,
        original=["def old_func():"],
        proposed=["def new_func():"],
    )
    change1 = ProposedChange(
        file="file1.py",
        original="original",
        proposed="modified",
        hunks=[hunk1],
        rationale="Renamed function",
    )
    manager.pending_changes["file1.py"] = change1

    # File 2
    hunk2 = DiffHunk.create(
        start_line=1,
        end_line=2,
        original=["import old"],
        proposed=["import new"],
    )
    change2 = ProposedChange(
        file="file2.py",
        original="original",
        proposed="modified",
        hunks=[hunk2],
    )
    manager.pending_changes["file2.py"] = change2

    return manager


@pytest.fixture
async def review_app(temp_home, mock_storage, mock_ai_components, mock_review_manager):
    """Create app with ReviewScreen pushed."""
    from app import NullApp

    with patch("app.Config._get_storage", return_value=mock_storage):
        with patch("handlers.input.Config._get_storage", return_value=mock_storage):
            app = NullApp()
            async with app.run_test(size=(120, 50)) as pilot:
                screen = ReviewScreen(mock_review_manager)
                app.push_screen(screen)
                await pilot.pause()
                yield app, pilot, screen, mock_review_manager


@pytest.mark.asyncio
async def test_review_screen_displays(review_app):
    """Test that ReviewScreen displays correctly."""
    app, pilot, screen, manager = review_app

    assert screen.is_mounted

    title = screen.query_one("#review-title", Label)
    assert "Code Review" in str(title.content)

    summary = screen.query_one("#review-summary", Label)
    assert "1 file(s)" in str(summary.content)


@pytest.mark.asyncio
async def test_file_changes_shown(review_app):
    """Test that file changes are displayed."""
    app, pilot, screen, manager = review_app

    file_widgets = screen.query(FileChangeWidget)
    assert len(file_widgets) == 1

    file_widget = file_widgets.first()
    file_path_label = file_widget.query_one(".file-path", Label)
    assert "test_file.py" in str(file_path_label.content)

    hunk_widgets = screen.query(HunkWidget)
    assert len(hunk_widgets) == 2


@pytest.mark.asyncio
async def test_accept_hunk(review_app):
    """Test accepting a single hunk via button click."""
    app, pilot, screen, manager = review_app

    hunk_widgets = list(screen.query(HunkWidget))
    assert len(hunk_widgets) >= 1

    first_hunk = hunk_widgets[0]
    hunk_id = first_hunk.hunk.id

    accept_btn = first_hunk.query_one("#accept")
    accept_btn.press()
    await pilot.pause()

    change = manager.pending_changes["test_file.py"]
    target_hunk = next(h for h in change.hunks if h.id == hunk_id)
    assert target_hunk.status == HunkStatus.ACCEPTED


@pytest.mark.asyncio
async def test_reject_hunk(review_app):
    """Test rejecting a single hunk via button click."""
    app, pilot, screen, manager = review_app

    hunk_widgets = list(screen.query(HunkWidget))
    assert len(hunk_widgets) >= 1

    first_hunk = hunk_widgets[0]
    hunk_id = first_hunk.hunk.id

    reject_btn = first_hunk.query_one("#reject")
    reject_btn.press()
    await pilot.pause()

    change = manager.pending_changes["test_file.py"]
    target_hunk = next(h for h in change.hunks if h.id == hunk_id)
    assert target_hunk.status == HunkStatus.REJECTED


@pytest.mark.asyncio
async def test_accept_all_hunks_keyboard(review_app):
    """Test accepting all hunks with 'a' key."""
    app, pilot, screen, manager = review_app

    # Press 'a' to accept all
    await pilot.press("a")
    await pilot.pause()

    # Verify all hunks are accepted
    change = manager.pending_changes["test_file.py"]
    for hunk in change.hunks:
        assert hunk.status == HunkStatus.ACCEPTED


@pytest.mark.asyncio
async def test_reject_all_hunks_keyboard(review_app):
    """Test rejecting all hunks with 'r' key."""
    app, pilot, screen, manager = review_app

    # Press 'r' to reject all
    await pilot.press("r")
    await pilot.pause()

    # Verify all hunks are rejected
    change = manager.pending_changes["test_file.py"]
    for hunk in change.hunks:
        assert hunk.status == HunkStatus.REJECTED


@pytest.mark.asyncio
async def test_cancel_dismisses_screen(review_app):
    """Test that cancel button dismisses screen with False."""
    app, pilot, screen, manager = review_app

    # Click cancel button
    cancel_btn = screen.query_one("#cancel")

    # Track dismiss result
    dismiss_result = None
    original_dismiss = screen.dismiss

    def track_dismiss(result=None):
        nonlocal dismiss_result
        dismiss_result = result
        return original_dismiss(result)

    screen.dismiss = track_dismiss

    await pilot.click(cancel_btn)
    await pilot.pause()

    assert dismiss_result is False


@pytest.mark.asyncio
async def test_apply_dismisses_screen(review_app):
    """Test that apply button dismisses screen with True."""
    app, pilot, screen, manager = review_app

    # Click apply button
    apply_btn = screen.query_one("#apply")

    # Track dismiss result
    dismiss_result = None
    original_dismiss = screen.dismiss

    def track_dismiss(result=None):
        nonlocal dismiss_result
        dismiss_result = result
        return original_dismiss(result)

    screen.dismiss = track_dismiss

    await pilot.click(apply_btn)
    await pilot.pause()

    assert dismiss_result is True


@pytest.mark.asyncio
async def test_escape_cancels_screen(review_app):
    """Test that escape key cancels the screen."""
    app, pilot, screen, manager = review_app

    dismiss_result = None
    original_dismiss = screen.dismiss

    def track_dismiss(result=None):
        nonlocal dismiss_result
        dismiss_result = result
        return original_dismiss(result)

    screen.dismiss = track_dismiss

    await pilot.press("escape")
    await pilot.pause()

    assert dismiss_result is False


@pytest.mark.asyncio
async def test_diff_lines_displayed(review_app):
    """Test that diff lines (additions/deletions) are properly displayed."""
    app, pilot, screen, manager = review_app

    # Check for diff line classes
    del_lines = screen.query(".diff-line-del")
    add_lines = screen.query(".diff-line-add")

    # Our test data has deletions and additions
    assert len(del_lines) > 0
    assert len(add_lines) > 0


@pytest.mark.asyncio
async def test_hunk_status_label_displayed(review_app):
    """Test that hunk status labels are shown."""
    app, pilot, screen, manager = review_app

    status_labels = list(screen.query(".hunk-status"))
    assert len(status_labels) == 2

    for label in status_labels:
        assert "PENDING" in str(label.content)


@pytest.mark.asyncio
async def test_file_rationale_displayed(review_app):
    """Test that file rationale is displayed when present."""
    app, pilot, screen, manager = review_app

    rationale_labels = list(screen.query(".file-rationale"))
    assert len(rationale_labels) == 1

    rationale = rationale_labels[0]
    assert "Test rationale" in str(rationale.content)


@pytest.mark.asyncio
async def test_multiple_files_displayed(
    temp_home, mock_storage, mock_ai_components, mock_review_manager_multiple_files
):
    """Test that multiple files are displayed correctly."""
    from app import NullApp

    manager = mock_review_manager_multiple_files

    with patch("app.Config._get_storage", return_value=mock_storage):
        with patch("handlers.input.Config._get_storage", return_value=mock_storage):
            app = NullApp()
            async with app.run_test(size=(120, 50)) as pilot:
                screen = ReviewScreen(manager)
                app.push_screen(screen)
                await pilot.pause()

                summary = screen.query_one("#review-summary", Label)
                assert "2 file(s)" in str(summary.content)

                file_widgets = screen.query(FileChangeWidget)
                assert len(file_widgets) == 2


@pytest.mark.asyncio
async def test_accept_all_button_for_file(review_app):
    """Test Accept All button for a specific file."""
    app, pilot, screen, manager = review_app

    file_widget = screen.query_one(FileChangeWidget)
    accept_all_btn = file_widget.query_one("#accept-all")

    accept_all_btn.press()
    await pilot.pause()

    change = manager.pending_changes["test_file.py"]
    for hunk in change.hunks:
        assert hunk.status == HunkStatus.ACCEPTED


@pytest.mark.asyncio
async def test_reject_all_button_for_file(review_app):
    """Test Reject All button for a specific file."""
    app, pilot, screen, manager = review_app

    file_widget = screen.query_one(FileChangeWidget)
    reject_all_btn = file_widget.query_one("#reject-all")

    reject_all_btn.press()
    await pilot.pause()

    change = manager.pending_changes["test_file.py"]
    for hunk in change.hunks:
        assert hunk.status == HunkStatus.REJECTED
