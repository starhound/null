"""Integration tests for SelectionListScreen."""

import pytest
from textual.widgets import ListView, Label, Button

from app import NullApp
from screens.selection import SelectionListScreen


@pytest.fixture
async def selection_app(mock_home, mock_storage):
    """Fixture that creates app with SelectionListScreen pushed."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        options = ["Option 1", "Option 2", "Option 3"]
        screen = SelectionListScreen(title="Select One", items=options)
        app.push_screen(screen)
        await pilot.pause()
        yield app, pilot, screen


@pytest.mark.asyncio
async def test_selection_screen_displays_options(selection_app):
    """Test that SelectionScreen displays with options."""
    app, pilot, screen = selection_app

    list_view = screen.query_one(ListView)
    assert list_view is not None

    items = list(list_view.query("ListItem"))
    assert len(items) == 3

    labels = list(screen.query(Label))
    title_found = any("Select One" in lbl.render().plain for lbl in labels)
    assert title_found


@pytest.mark.asyncio
async def test_selection_screen_select_with_enter(selection_app):
    """Test selecting an option with Enter returns correct value."""
    app, pilot, screen = selection_app

    result_holder = {"value": None}

    def capture_result(result):
        result_holder["value"] = result

    screen.dismiss = capture_result

    list_view = screen.query_one(ListView)
    list_view.focus()
    await pilot.pause()

    await pilot.press("enter")
    await pilot.pause()

    assert result_holder["value"] == "Option 1"


@pytest.mark.asyncio
async def test_selection_screen_keyboard_navigation(selection_app):
    """Test keyboard navigation with up/down arrows."""
    app, pilot, screen = selection_app

    list_view = screen.query_one(ListView)
    list_view.focus()
    await pilot.pause()

    assert list_view.index == 0

    await pilot.press("down")
    await pilot.pause()
    assert list_view.index == 1

    await pilot.press("down")
    await pilot.pause()
    assert list_view.index == 2

    await pilot.press("up")
    await pilot.pause()
    assert list_view.index == 1


@pytest.mark.asyncio
async def test_selection_screen_escape_cancels(selection_app):
    """Test pressing Escape cancels selection and returns None."""
    app, pilot, screen = selection_app

    result_holder = {"value": "not_set"}

    def capture_result(result):
        result_holder["value"] = result

    screen.dismiss = capture_result

    await pilot.press("escape")
    await pilot.pause()

    assert result_holder["value"] is None


@pytest.mark.asyncio
async def test_selection_screen_cancel_button(selection_app):
    """Test cancel button dismisses with None."""
    app, pilot, screen = selection_app

    result_holder = {"value": "not_set"}

    def capture_result(result):
        result_holder["value"] = result

    screen.dismiss = capture_result

    cancel_btn = screen.query_one("#cancel_btn", Button)
    cancel_btn.press()
    await pilot.pause()

    assert result_holder["value"] is None


@pytest.mark.asyncio
async def test_selection_screen_empty_items(mock_home, mock_storage):
    """Test SelectionScreen with empty items list."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        screen = SelectionListScreen(title="Empty List", items=[])
        app.push_screen(screen)
        await pilot.pause()

        labels = list(screen.query(Label))
        label_texts = [lbl.render().plain for lbl in labels]
        assert any("No items found" in text for text in label_texts)


@pytest.mark.asyncio
async def test_selection_screen_select_middle_item(selection_app):
    """Test selecting middle item after navigation."""
    app, pilot, screen = selection_app

    result_holder = {"value": None}

    def capture_result(result):
        result_holder["value"] = result

    screen.dismiss = capture_result

    list_view = screen.query_one(ListView)
    list_view.focus()
    await pilot.pause()

    await pilot.press("down")
    await pilot.pause()
    await pilot.press("enter")
    await pilot.pause()

    assert result_holder["value"] == "Option 2"
