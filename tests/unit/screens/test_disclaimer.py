"""Tests for the disclaimer screen."""

from unittest.mock import MagicMock

from screens.disclaimer import DISCLAIMER_TEXT, DisclaimerScreen


class TestDisclaimerScreen:
    def test_disclaimer_text_exists(self):
        assert DISCLAIMER_TEXT
        assert "AI models can produce incorrect" in DISCLAIMER_TEXT
        assert "risk" in DISCLAIMER_TEXT.lower()

    def test_bindings_defined(self):
        screen = DisclaimerScreen()
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "enter" in binding_keys

    def test_action_accept_dismisses_true(self):
        screen = DisclaimerScreen()
        screen.dismiss = MagicMock()
        screen.action_accept()
        screen.dismiss.assert_called_once_with(True)

    def test_button_pressed_confirm_yes(self):
        screen = DisclaimerScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "confirm-yes"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_called_once_with(True)

    def test_button_pressed_other_button_no_dismiss(self):
        screen = DisclaimerScreen()
        screen.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "other-button"
        mock_event = MagicMock()
        mock_event.button = mock_button

        screen.on_button_pressed(mock_event)
        screen.dismiss.assert_not_called()
