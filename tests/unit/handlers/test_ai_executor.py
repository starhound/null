import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from handlers.ai_executor import AIExecutor
from models import BlockState, BlockType


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.ai_provider = MagicMock()
    app.ai_provider.model = "test-model"
    app.ai_provider.get_model_info.return_value = MagicMock(context_window=4000)
    app.config.get.return_value = {}
    return app


@pytest.fixture
def ai_executor(mock_app):
    return AIExecutor(mock_app)


@pytest.mark.asyncio
async def test_execute_ai_no_tools(ai_executor, mock_app):
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    mock_app.ai_provider.supports_tools.return_value = False

    with patch("context.ContextManager.build_messages") as mock_build:
        mock_build.return_value = MagicMock(messages=[], truncated=False)

        with patch.object(
            ai_executor, "_execute_without_tools", new_callable=AsyncMock
        ) as mock_exec:
            await ai_executor.execute_ai("hi", block, widget)
            mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_execute_ai_with_tools(ai_executor, mock_app):
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="use tool")
    widget = MagicMock()

    mock_app.ai_provider.supports_tools.return_value = True

    with patch("context.ContextManager.build_messages") as mock_build:
        mock_build.return_value = MagicMock(messages=[], truncated=False)

        with patch.object(
            ai_executor, "_execute_with_tools", new_callable=AsyncMock
        ) as mock_exec:
            await ai_executor.execute_ai("use tool", block, widget)
            mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_execute_without_tools_flow(ai_executor, mock_app):
    mock_app._ai_cancelled = False
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    async def mock_gen(*args, **kwargs):
        yield "response"

    mock_app.ai_provider.generate = mock_gen

    await ai_executor._execute_without_tools("hi", block, widget, [], "", 100)

    assert block.content_output == "response"
    widget.update_output.assert_called_with("response")
