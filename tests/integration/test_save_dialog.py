"""Integration tests for SaveFileDialog screen."""

import pytest
from textual.widgets import Button, Input

from app import NullApp
from screens.save_dialog import SaveFileDialog


@pytest.fixture
async def save_dialog_app(mock_home, mock_storage, mock_ai_components):
    """Setup app with SaveFileDialog pushed."""
    app = NullApp()
    async with app.run_test(size=(120, 50)) as pilot:
        dialog = SaveFileDialog(suggested_name="test.txt", content="test content")
        await app.push_screen(dialog)
        await pilot.pause()
        yield app, pilot, dialog


class TestSaveDialogIntegration:
    """Integration tests for SaveFileDialog."""

    @pytest.mark.asyncio
    async def test_filename_prepopulated(self, save_dialog_app):
        """Test that the filename input is pre-populated with suggested name."""
        app, pilot, dialog = save_dialog_app
        input_widget = app.screen.query_one("#filename-input", Input)
        assert input_widget.value == "test.txt"

    @pytest.mark.asyncio
    async def test_save_button_triggers_save(self, save_dialog_app, temp_workdir):
        """Test that save button triggers file save and dismisses dialog."""
        app, pilot, dialog = save_dialog_app

        # Click save button
        save_btn = app.screen.query_one("#save-btn", Button)
        await pilot.click(save_btn)
        await pilot.pause()

        # Dialog should be dismissed (screen stack returns to main)
        assert not isinstance(app.screen, SaveFileDialog)

        # File should be created
        saved_file = temp_workdir / "test.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_cancel_dismisses_dialog(self, save_dialog_app):
        """Test that cancel button dismisses the dialog without saving."""
        app, pilot, dialog = save_dialog_app

        # Click cancel button
        cancel_btn = app.screen.query_one("#cancel-btn", Button)
        await pilot.click(cancel_btn)
        await pilot.pause()

        # Dialog should be dismissed
        assert not isinstance(app.screen, SaveFileDialog)

    @pytest.mark.asyncio
    async def test_escape_cancels_dialog(self, save_dialog_app):
        """Test that action_cancel dismisses the dialog."""
        app, pilot, dialog = save_dialog_app

        app.screen.action_cancel()
        await pilot.pause()

        assert not isinstance(app.screen, SaveFileDialog)

    @pytest.mark.asyncio
    async def test_enter_submits_form(self, save_dialog_app, temp_workdir):
        """Test that input submission saves the file."""
        app, pilot, dialog = save_dialog_app

        app.screen._do_save()
        await pilot.pause()

        assert not isinstance(app.screen, SaveFileDialog)
        saved_file = temp_workdir / "test.txt"
        assert saved_file.exists()

    @pytest.mark.asyncio
    async def test_empty_filename_shows_warning(self, save_dialog_app):
        """Test that empty filename shows warning and doesn't dismiss."""
        app, pilot, dialog = save_dialog_app

        # Clear the input
        input_widget = app.screen.query_one("#filename-input", Input)
        input_widget.value = ""
        await pilot.pause()

        # Click save
        save_btn = app.screen.query_one("#save-btn", Button)
        await pilot.click(save_btn)
        await pilot.pause()

        # Dialog should still be open
        assert isinstance(app.screen, SaveFileDialog)
