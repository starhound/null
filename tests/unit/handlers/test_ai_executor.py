from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from handlers.ai_executor import AIExecutor
from models import BlockState, BlockType


@pytest.fixture
def mock_app():
    app = MagicMock()
    mock_provider = MagicMock()
    mock_provider.model = "test-model"
    mock_provider.get_model_info.return_value = MagicMock(context_window=4000)
    mock_provider.supports_tools.return_value = False
    app.ai_manager = MagicMock()
    app.ai_manager.get_provider.return_value = mock_provider
    app.blocks = []
    app._ai_cancelled = False
    return app


@pytest.fixture
def ai_executor(mock_app):
    return AIExecutor(mock_app)


@pytest.mark.asyncio
async def test_execute_ai_no_tools(ai_executor, mock_app):
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    mock_provider = mock_app.ai_manager.get_provider.return_value
    mock_provider.supports_tools.return_value = False

    with (
        patch("config.Config.get", return_value="test-provider"),
        patch("prompts.get_prompt_manager") as mock_pm,
        patch("context.ContextManager.build_messages") as mock_build,
        patch.object(
            ai_executor, "_execute_without_tools", new_callable=AsyncMock
        ) as mock_exec,
    ):
        mock_pm.return_value.get_prompt_content.return_value = "System prompt"
        mock_build.return_value = MagicMock(
            messages=[], truncated=False, estimated_tokens=10, message_count=0
        )
        await ai_executor.execute_ai("hi", block, widget)
        mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_execute_ai_with_tools(ai_executor, mock_app):
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="use tool")
    widget = MagicMock()

    mock_provider = mock_app.ai_manager.get_provider.return_value
    mock_provider.supports_tools.return_value = True

    with (
        patch("config.Config.get", return_value="test-provider"),
        patch("prompts.get_prompt_manager") as mock_pm,
        patch("context.ContextManager.build_messages") as mock_build,
        patch.object(
            ai_executor, "_execute_with_tools", new_callable=AsyncMock
        ) as mock_exec,
    ):
        mock_pm.return_value.get_prompt_content.return_value = "System prompt"
        mock_build.return_value = MagicMock(
            messages=[], truncated=False, estimated_tokens=10, message_count=0
        )
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
