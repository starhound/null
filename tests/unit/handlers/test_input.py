from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handlers.input import InputHandler
from models import BlockState, BlockType


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.query_one = MagicMock()
    app.command_handler = MagicMock()
    app.command_handler.handle = AsyncMock()
    app.execution_handler = MagicMock()
    app.blocks = []
    app.config.get.return_value = {}
    return app


@pytest.fixture
def input_handler(mock_app):
    return InputHandler(mock_app)


@pytest.mark.asyncio
async def test_handle_submission_command(input_handler, mock_app):
    input_ctrl = MagicMock()
    input_ctrl.is_ai_mode = False
    mock_app.query_one.return_value = input_ctrl

    await input_handler.handle_submission("/help")

    mock_app.command_handler.handle.assert_called_with("/help")
    input_ctrl.add_to_history.assert_called_with("/help")


@pytest.mark.asyncio
async def test_handle_submission_ai(input_handler, mock_app):
    input_ctrl = MagicMock()
    input_ctrl.is_ai_mode = True
    mock_app.query_one.return_value = input_ctrl
    mock_app.ai_provider = MagicMock()
    mock_app.ai_provider.supports_tools.return_value = False

    mock_app.run_worker.return_value = MagicMock()

    history_vp = AsyncMock()

    def query_side_effect(selector, type=None):
        if selector == "#input":
            return input_ctrl
        if selector == "#history":
            return history_vp
        return MagicMock()

    mock_app.query_one.side_effect = query_side_effect

    await input_handler.handle_submission("hello ai")

    assert len(mock_app.blocks) == 1
    assert mock_app.blocks[0].content_input == "hello ai"
    assert mock_app.blocks[0].type == BlockType.AI_RESPONSE
    mock_app.run_worker.assert_called_once()


@pytest.mark.asyncio
async def test_handle_submission_cli_new(input_handler, mock_app):
    input_ctrl = MagicMock()
    input_ctrl.is_ai_mode = False
    mock_app.query_one.return_value = input_ctrl
    mock_app.current_cli_block = None

    mock_app.run_worker.return_value = MagicMock()

    history_vp = AsyncMock()

    def query_side_effect(selector, type=None):
        if selector == "#input":
            return input_ctrl
        if selector == "#history":
            return history_vp
        return MagicMock()

    mock_app.query_one.side_effect = query_side_effect

    await input_handler.handle_submission("ls -la")

    assert len(mock_app.blocks) == 1
    assert mock_app.blocks[0].content_input == "ls -la"
    assert mock_app.blocks[0].type == BlockType.COMMAND
    mock_app.run_worker.assert_called_once()


@pytest.mark.asyncio
async def test_handle_submission_cli_append(input_handler, mock_app):
    input_ctrl = MagicMock()
    input_ctrl.is_ai_mode = False
    mock_app.query_one.return_value = input_ctrl

    existing_block = BlockState(
        id="blk1", type=BlockType.COMMAND, content_input="initial cmd"
    )
    existing_widget = MagicMock()
    mock_app.current_cli_block = existing_block
    mock_app.current_cli_widget = existing_widget
    mock_app.process_manager.get.return_value = MagicMock(is_tui=False)
    mock_app.process_manager.is_running.return_value = False

    mock_app.execution_handler.execute_cli_append.side_effect = (
        lambda cmd, b, w: setattr(b, "content_output", b.content_output + cmd)
    )

    await input_handler.handle_submission("grep foo")

    assert len(mock_app.blocks) == 0
    assert "grep foo" in existing_block.content_output
    mock_app.execution_handler.execute_cli_append.assert_called_once()


@pytest.mark.asyncio
async def test_handle_builtin_cd(input_handler, mock_app):
    with patch("os.chdir") as mock_chdir:
        mock_chdir.return_value = None
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                success = await input_handler.handle_builtin("cd /tmp")
                assert success is True
                mock_chdir.assert_called()


@pytest.mark.asyncio
async def test_handle_builtin_pwd(input_handler, mock_app):
    mock_app._show_system_output = AsyncMock()
    success = await input_handler.handle_builtin("pwd")
    assert success is True
    mock_app._show_system_output.assert_called()
