from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import StreamChunk, ToolCallData
from handlers.ai_executor import AIExecutor
from handlers.execution import ExecutionHandler
from models import BlockState, BlockType


@pytest.fixture
def mock_app():
    app = MagicMock()
    mock_provider = MagicMock()
    mock_provider.model = "test-model"
    mock_provider.get_model_info.return_value = MagicMock(context_window=4096)
    mock_provider.supports_tools.return_value = False
    app.ai_manager = MagicMock()
    app.ai_manager.get_provider.return_value = mock_provider
    app._ai_cancelled = False
    app.blocks = []
    return app


@pytest.fixture
def execution_handler(mock_app):
    return ExecutionHandler(mock_app)


@pytest.fixture
def ai_executor(mock_app):
    return AIExecutor(mock_app)


async def async_gen(items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_execute_ai_simple(execution_handler, mock_app):
    prompt = "Hello"
    block_state = BlockState(type=BlockType.AI_RESPONSE, content_input=prompt)
    widget = MagicMock()

    async def mock_execute_ai(prompt, block, widget):
        block.content_output = "Hi there"
        block.is_running = False
        widget.update_output("Hi there")

    with patch.object(
        execution_handler.ai_executor, "execute_ai", side_effect=mock_execute_ai
    ):
        await execution_handler.execute_ai(prompt, block_state, widget)

    assert block_state.content_output == "Hi there"
    assert not block_state.is_running
    widget.update_output.assert_called()


@pytest.mark.asyncio
async def test_execution_handler_delegates_to_ai_executor(execution_handler, mock_app):
    prompt = "Hello"
    block_state = BlockState(type=BlockType.AI_RESPONSE, content_input=prompt)
    widget = MagicMock()

    with patch.object(
        execution_handler.ai_executor, "execute_ai", new_callable=AsyncMock
    ) as mock_execute:
        await execution_handler.execute_ai(prompt, block_state, widget)

        mock_execute.assert_called_once_with(prompt, block_state, widget)


@pytest.mark.asyncio
async def test_execution_handler_delegates_regenerate(execution_handler, mock_app):
    block_state = BlockState(type=BlockType.AI_RESPONSE, content_input="test")
    widget = MagicMock()

    with patch.object(
        execution_handler.ai_executor, "regenerate_ai", new_callable=AsyncMock
    ) as mock_regenerate:
        await execution_handler.regenerate_ai(block_state, widget)

        mock_regenerate.assert_called_once_with(block_state, widget)


@pytest.mark.asyncio
async def test_execution_handler_delegates_cli(execution_handler, mock_app):
    block_state = BlockState(type=BlockType.COMMAND, content_input="ls")
    widget = MagicMock()

    with patch.object(
        execution_handler.cli_executor, "execute_cli", new_callable=AsyncMock
    ) as mock_cli:
        await execution_handler.execute_cli(block_state, widget)

        mock_cli.assert_called_once_with(block_state, widget)
