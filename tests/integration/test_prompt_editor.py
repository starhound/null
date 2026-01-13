"""Integration tests for PromptEditorScreen.

Tests verify that the prompt editor screen can be opened and
its core widgets exist and are interactable.
"""

import pytest
from textual.widgets import Button, Input, ListView, TextArea

from app import NullApp
from screens.prompts import PromptEditorScreen


@pytest.fixture
async def prompt_editor_app():
    """Create app with prompt editor screen open."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        app.push_screen(PromptEditorScreen())
        await pilot.pause()
        await pilot.pause()
        yield app, pilot


class TestPromptEditorScreenOpens:
    """Test that the screen can be opened."""

    @pytest.mark.asyncio
    async def test_screen_opens(self, prompt_editor_app):
        """PromptEditorScreen should open successfully."""
        app, pilot = prompt_editor_app
        assert isinstance(app.screen, PromptEditorScreen)


class TestPromptListView:
    """Test the prompts ListView exists."""

    @pytest.mark.asyncio
    async def test_prompt_list_exists(self, prompt_editor_app):
        """ListView for prompts should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        lv = screen.query_one("#prompt-list", ListView)
        assert lv is not None

    @pytest.mark.asyncio
    async def test_prompt_list_focusable(self, prompt_editor_app):
        """ListView should be focusable."""
        app, pilot = prompt_editor_app
        screen = app.screen

        lv = screen.query_one("#prompt-list", ListView)
        assert lv.can_focus


class TestInputFields:
    """Test input fields exist and are interactable."""

    @pytest.mark.asyncio
    async def test_prompt_name_input_exists(self, prompt_editor_app):
        """Prompt name input should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        inp = screen.query_one("#prompt-name-input", Input)
        assert inp is not None

    @pytest.mark.asyncio
    async def test_prompt_desc_input_exists(self, prompt_editor_app):
        """Prompt description input should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        inp = screen.query_one("#prompt-desc-input", Input)
        assert inp is not None

    @pytest.mark.asyncio
    async def test_inputs_focusable(self, prompt_editor_app):
        """All inputs should be focusable."""
        app, pilot = prompt_editor_app
        screen = app.screen

        name_input = screen.query_one("#prompt-name-input", Input)
        desc_input = screen.query_one("#prompt-desc-input", Input)

        assert name_input.can_focus
        assert desc_input.can_focus

    @pytest.mark.asyncio
    async def test_name_input_accepts_text(self, prompt_editor_app):
        """Name input should accept text."""
        app, pilot = prompt_editor_app
        screen = app.screen

        inp = screen.query_one("#prompt-name-input", Input)
        inp.focus()
        await pilot.pause()

        assert inp.has_focus
        await pilot.press("t", "e", "s", "t")
        await pilot.pause()

        assert "test" in inp.value


class TestTextArea:
    """Test the prompt content TextArea."""

    @pytest.mark.asyncio
    async def test_content_textarea_exists(self, prompt_editor_app):
        """TextArea for prompt content should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        ta = screen.query_one("#prompt-content-area", TextArea)
        assert ta is not None

    @pytest.mark.asyncio
    async def test_content_textarea_focusable(self, prompt_editor_app):
        """TextArea should be focusable."""
        app, pilot = prompt_editor_app
        screen = app.screen

        ta = screen.query_one("#prompt-content-area", TextArea)
        ta.focus()
        await pilot.pause()

        assert ta.has_focus


class TestButtons:
    """Test save/delete buttons exist."""

    @pytest.mark.asyncio
    async def test_save_button_exists(self, prompt_editor_app):
        """Save button should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        btn = screen.query_one("#save-btn", Button)
        assert btn is not None
        assert btn.label.plain == "Save"

    @pytest.mark.asyncio
    async def test_delete_button_exists(self, prompt_editor_app):
        """Delete button should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        btn = screen.query_one("#delete-btn", Button)
        assert btn is not None
        assert btn.label.plain == "Delete"

    @pytest.mark.asyncio
    async def test_new_button_exists(self, prompt_editor_app):
        """New button should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        btn = screen.query_one("#new-btn", Button)
        assert btn is not None
        assert btn.label.plain == "New"

    @pytest.mark.asyncio
    async def test_close_button_exists(self, prompt_editor_app):
        """Close button should exist."""
        app, pilot = prompt_editor_app
        screen = app.screen

        btn = screen.query_one("#close-btn", Button)
        assert btn is not None
        assert btn.label.plain == "Close"

    @pytest.mark.asyncio
    async def test_delete_button_initially_disabled(self, prompt_editor_app):
        """Delete button should be disabled initially (no selection)."""
        app, pilot = prompt_editor_app
        screen = app.screen

        btn = screen.query_one("#delete-btn", Button)
        assert btn.disabled
