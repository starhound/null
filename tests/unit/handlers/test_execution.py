from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import StreamChunk, ToolCallData
from handlers.ai_executor import AIExecutor
from handlers.execution import ExecutionHandler
from models import BlockState, BlockType


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.ai_provider = MagicMock()
    app.ai_provider.model = "test-model"
    app.ai_provider.get_model_info.return_value = MagicMock(context_window=4096)
    app.ai_provider.supports_tools.return_value = False
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
    # Setup
    prompt = "Hello"
    block_state = BlockState(type=BlockType.AI_RESPONSE, content_input=prompt)
    widget = MagicMock()

    # Mock generation
    mock_app.ai_provider.generate.return_value = async_gen(["Hi", " there"])

    # Execute
    with (
        patch("config.Config.get", return_value="test-provider"),
        patch("prompts.get_prompt_manager") as mock_pm,
        patch("context.ContextManager.build_messages") as mock_build,
    ):
        mock_pm.return_value.get_prompt_content.return_value = "System prompt"
        mock_build.return_value = MagicMock(
            truncated=False, messages=[], estimated_tokens=10, message_count=0
        )

        await execution_handler.execute_ai(prompt, block_state, widget)

    # Verify
    assert block_state.content_output == "Hi there"
    assert not block_state.is_running
    widget.update_output.assert_called()


@pytest.mark.asyncio
async def test_execute_ai_with_tools_approval(ai_executor, mock_app):
    mock_app.ai_provider.supports_tools.return_value = True
    prompt = "Run command"
    block_state = BlockState(type=BlockType.AI_RESPONSE, content_input=prompt)
    widget = MagicMock()

    tool_call = ToolCallData(id="tc-1", name="run_command", arguments={"command": "ls"})
    chunk = StreamChunk(text="", tool_calls=[tool_call], is_complete=True)

    mock_app.ai_provider.generate_with_tools.side_effect = [
        async_gen([chunk]),
        async_gen([StreamChunk(text="Done", is_complete=True)]),
    ]

    mock_registry = MagicMock()
    mock_registry.requires_approval.return_value = True
    mock_registry.execute_tool = AsyncMock(
        return_value=MagicMock(content="output", is_error=False, tool_call_id="tc-1")
    )
    mock_registry.get_all_tools_schema.return_value = []
    ai_executor._get_tool_registry = MagicMock(return_value=mock_registry)

    with patch.object(
        ai_executor, "_request_tool_approval", new_callable=AsyncMock
    ) as mock_approval:
        mock_approval.return_value = "approve"

        with (
            patch("config.Config.get", return_value="test-provider"),
            patch("prompts.get_prompt_manager") as mock_pm,
            patch("context.ContextManager.build_messages") as mock_build,
        ):
            mock_pm.return_value.get_prompt_content.return_value = "System prompt"
            mock_build.return_value = MagicMock(
                truncated=False, messages=[], estimated_tokens=10, message_count=0
            )

            await ai_executor.execute_ai(prompt, block_state, widget)

        mock_approval.assert_called()
        mock_registry.execute_tool.assert_called()
