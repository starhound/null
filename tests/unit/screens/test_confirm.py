"""Tests for the confirmation dialog screen."""

import pytest
from unittest.mock import MagicMock

from screens.confirm import ConfirmDialog


class TestConfirmDialog:
    def test_init_default_values(self):
        dialog = ConfirmDialog()
        assert dialog.title_text == "Confirm"
        assert dialog.message_text == "Are you sure?"

    def test_init_custom_values(self):
        dialog = ConfirmDialog(title="Delete File", message="Delete file.txt?")
        assert dialog.title_text == "Delete File"
        assert dialog.message_text == "Delete file.txt?"

    def test_bindings_defined(self):
        dialog = ConfirmDialog()
        binding_keys = [b.key for b in dialog.BINDINGS]
        assert "escape" in binding_keys
        assert "enter" in binding_keys

    def test_action_confirm_dismisses_true(self):
        dialog = ConfirmDialog()
        dialog.dismiss = MagicMock()
        dialog.action_confirm()
        dialog.dismiss.assert_called_once_with(True)

    def test_action_cancel_dismisses_false(self):
        dialog = ConfirmDialog()
        dialog.dismiss = MagicMock()
        dialog.action_cancel()
        dialog.dismiss.assert_called_once_with(False)

    def test_compose_yields_container(self):
        dialog = ConfirmDialog(title="Test", message="Test message")
        widgets = list(dialog.compose())
        assert len(widgets) == 1


class TestConfirmDialogButtonHandling:
    def test_yes_button_dismisses_true(self):
        dialog = ConfirmDialog()
        dialog.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "confirm-yes"
        mock_event = MagicMock()
        mock_event.button = mock_button

        dialog.on_button_pressed(mock_event)
        dialog.dismiss.assert_called_once_with(True)

    def test_no_button_dismisses_false(self):
        dialog = ConfirmDialog()
        dialog.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "confirm-no"
        mock_event = MagicMock()
        mock_event.button = mock_button

        dialog.on_button_pressed(mock_event)
        dialog.dismiss.assert_called_once_with(False)

    def test_unknown_button_dismisses_false(self):
        dialog = ConfirmDialog()
        dialog.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "unknown-button"
        mock_event = MagicMock()
        mock_event.button = mock_button

        dialog.on_button_pressed(mock_event)
        dialog.dismiss.assert_called_once_with(False)
