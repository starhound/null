import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from handlers.cli_executor import CLIExecutor
from models import BlockState, BlockType


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.process_manager = MagicMock()
    app.config.get.return_value = False
    return app


@pytest.fixture
def cli_executor(mock_app):
    return CLIExecutor(mock_app)


@pytest.mark.asyncio
async def test_execute_cli_basic(cli_executor, mock_app):
    block = BlockState(type=BlockType.COMMAND, content_input="echo hello")
    widget = MagicMock()

    with patch("handlers.cli_executor.ExecutionEngine") as MockEngine:
        engine_instance = MockEngine.return_value
        engine_instance.run_command_and_get_rc = AsyncMock(return_value=0)
        engine_instance.pid = 123
        engine_instance.master_fd = 5

        with patch("asyncio.Event") as MockEvent:
            event = MockEvent.return_value
            event.wait = AsyncMock()

            await cli_executor.execute_cli(block, widget)

            mock_app.process_manager.register.assert_called_once()
            mock_app.process_manager.unregister.assert_called_once()
            if hasattr(widget, "set_exit_code"):
                widget.set_exit_code.assert_called_with(0)


@pytest.mark.asyncio
async def test_execute_cli_append(cli_executor, mock_app):
    block = BlockState(type=BlockType.COMMAND, content_input="initial")
    widget = MagicMock()

    with patch("handlers.cli_executor.ExecutionEngine") as MockEngine:
        engine_instance = MockEngine.return_value
        engine_instance.run_command_and_get_rc = AsyncMock(return_value=1)
        engine_instance.pid = 456

        with patch("asyncio.Event") as MockEvent:
            event = MockEvent.return_value
            event.wait = AsyncMock()

            await cli_executor.execute_cli_append("ls", block, widget)

            # Should append exit code to output, not call set_exit_code
            assert "\n[exit: 1]\n" in block.content_output
            widget.update_output.assert_called()
