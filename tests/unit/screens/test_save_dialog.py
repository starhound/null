import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from screens.save_dialog import SaveFileDialog


class TestSaveFileDialog:
    def test_init_default_values(self):
        dialog = SaveFileDialog()
        assert dialog.suggested_name == "code.txt"
        assert dialog.content == ""

    def test_init_custom_values(self):
        dialog = SaveFileDialog(suggested_name="script.py", content="print('hello')")
        assert dialog.suggested_name == "script.py"
        assert dialog.content == "print('hello')"

    def test_bindings_defined(self):
        dialog = SaveFileDialog()
        binding_keys = [b.key for b in dialog.BINDINGS]
        assert "escape" in binding_keys

    def test_action_cancel_dismisses_none(self):
        dialog = SaveFileDialog()
        dialog.dismiss = MagicMock()
        dialog.action_cancel()
        dialog.dismiss.assert_called_once_with(None)


class TestSaveFileDialogButtonHandling:
    def test_cancel_button(self):
        dialog = SaveFileDialog()
        dialog.dismiss = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "cancel-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        dialog.on_button_pressed(mock_event)
        dialog.dismiss.assert_called_once_with(None)

    def test_save_button_calls_do_save(self):
        dialog = SaveFileDialog()
        dialog._do_save = MagicMock()

        mock_button = MagicMock()
        mock_button.id = "save-btn"
        mock_event = MagicMock()
        mock_event.button = mock_button

        dialog.on_button_pressed(mock_event)
        dialog._do_save.assert_called_once()


class TestSaveFileDialogDoSave:
    def test_empty_filename_notifies_warning(self):
        dialog = SaveFileDialog()
        dialog.notify = MagicMock()
        dialog.dismiss = MagicMock()

        mock_input = MagicMock()
        mock_input.value = "   "
        dialog.query_one = MagicMock(return_value=mock_input)

        dialog._do_save()

        dialog.notify.assert_called_once()
        assert "filename" in dialog.notify.call_args[0][0].lower()
        dialog.dismiss.assert_not_called()

    @patch("pathlib.Path")
    def test_successful_save(self, mock_path_class):
        dialog = SaveFileDialog(content="test content")
        dialog.notify = MagicMock()
        dialog.dismiss = MagicMock()

        mock_input = MagicMock()
        mock_input.value = "output.txt"
        dialog.query_one = MagicMock(return_value=mock_input)

        mock_filepath = MagicMock()
        mock_filepath.parent.mkdir = MagicMock()
        mock_filepath.write_text = MagicMock()
        mock_path_class.cwd.return_value.__truediv__ = MagicMock(
            return_value=mock_filepath
        )

        dialog._do_save()

        mock_filepath.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_filepath.write_text.assert_called_once_with(
            "test content", encoding="utf-8"
        )
        dialog.dismiss.assert_called_once()

    @patch("pathlib.Path")
    def test_save_failure_notifies_error(self, mock_path_class):
        dialog = SaveFileDialog(content="test")
        dialog.notify = MagicMock()
        dialog.dismiss = MagicMock()

        mock_input = MagicMock()
        mock_input.value = "test.txt"
        dialog.query_one = MagicMock(return_value=mock_input)

        mock_filepath = MagicMock()
        mock_filepath.parent.mkdir = MagicMock(side_effect=PermissionError("denied"))
        mock_path_class.cwd.return_value.__truediv__ = MagicMock(
            return_value=mock_filepath
        )

        dialog._do_save()

        dialog.notify.assert_called()
        assert "error" in str(dialog.notify.call_args).lower()
        dialog.dismiss.assert_not_called()


class TestSaveFileDialogInputSubmitted:
    def test_input_submitted_calls_do_save(self):
        dialog = SaveFileDialog()
        dialog._do_save = MagicMock()

        mock_event = MagicMock()
        dialog.on_input_submitted(mock_event)

        dialog._do_save.assert_called_once()
