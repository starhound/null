from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import StreamChunk, TokenUsage, ToolCallData
from handlers.ai_executor import AIExecutor
from models import BlockState, BlockType
from tools import ToolResult


@pytest.fixture
def mock_app():
    app = MagicMock()
    mock_provider = MagicMock()
    mock_provider.model = "test-model"
    mock_provider.get_model_info.return_value = MagicMock(context_window=4000)
    mock_provider.supports_tools.return_value = False
    app.ai_manager = MagicMock()
    app.ai_manager.get_provider.return_value = mock_provider
    app.ai_provider = mock_provider
    app.blocks = []
    app._ai_cancelled = False
    app._active_worker = None
    app.mcp_manager = MagicMock()
    app.mcp_manager.config.get_active_ai_config.return_value = None
    app.config = MagicMock()
    app.config.get.return_value = {}
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
        patch("handlers.ai_executor.Config.get", return_value="test-provider"),
        patch("handlers.ai_executor.get_settings") as mock_settings,
        patch("prompts.get_prompt_manager") as mock_pm,
        patch("context.ContextManager.build_messages") as mock_build,
        patch.object(
            ai_executor, "_execute_without_tools", new_callable=AsyncMock
        ) as mock_exec,
    ):
        # Configure mock settings with use_rag=False
        mock_settings.return_value.ai.use_rag = False
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
        patch("handlers.ai_executor.Config.get", return_value="test-provider"),
        patch("handlers.ai_executor.get_settings") as mock_settings,
        patch("prompts.get_prompt_manager") as mock_pm,
        patch("context.ContextManager.build_messages") as mock_build,
        patch.object(
            ai_executor, "_execute_with_tools", new_callable=AsyncMock
        ) as mock_exec,
    ):
        mock_settings.return_value.ai.use_rag = False
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
        yield StreamChunk(text="response")

    mock_app.ai_provider.generate = mock_gen

    await ai_executor._execute_without_tools("hi", block, widget, [], "", 100)

    assert block.content_output == "response"
    widget.update_output.assert_called_with("response")


@pytest.mark.asyncio
async def test_execute_without_tools_cancelled(ai_executor, mock_app):
    mock_app._ai_cancelled = False
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    call_count = 0

    async def mock_gen(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield StreamChunk(text="first")
        mock_app._ai_cancelled = True
        yield StreamChunk(text="second")

    mock_app.ai_provider.generate = mock_gen

    await ai_executor._execute_without_tools("hi", block, widget, [], "", 100)

    assert "[Cancelled]" in block.content_output


@pytest.mark.asyncio
async def test_execute_ai_handles_exception(ai_executor, mock_app):
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    with (
        patch("handlers.ai_executor.Config.get", return_value="test-provider"),
        patch("handlers.ai_executor.get_settings"),
        patch("prompts.get_prompt_manager") as mock_pm,
        patch("context.ContextManager.build_messages") as mock_build,
    ):
        mock_pm.return_value.get_prompt_content.return_value = "System prompt"
        mock_build.side_effect = Exception("Build failed")

        await ai_executor.execute_ai("hi", block, widget)

    assert "Error" in block.content_output
    assert not block.is_running


@pytest.mark.asyncio
async def test_execute_ai_handles_cancelled_error(ai_executor, mock_app):
    import asyncio

    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    with (
        patch("handlers.ai_executor.Config.get", return_value="test-provider"),
        patch("handlers.ai_executor.get_settings"),
        patch("context.ContextManager.build_messages") as mock_build,
        patch("prompts.get_prompt_manager") as mock_pm,
    ):
        mock_pm.return_value.get_prompt_content.return_value = "System prompt"
        mock_build.side_effect = asyncio.CancelledError()

        await ai_executor.execute_ai("hi", block, widget)

    assert "[Cancelled]" in block.content_output
    assert not block.is_running


@pytest.mark.asyncio
async def test_execute_ai_no_provider(ai_executor, mock_app):
    block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
    widget = MagicMock()

    mock_app.ai_manager.get_provider.return_value = None

    with patch("handlers.ai_executor.Config.get", return_value="missing-provider"):
        await ai_executor.execute_ai("hi", block, widget)

    widget.update_output.assert_called()
    assert "not configured" in widget.update_output.call_args[0][0]


class TestAIExecutorToolRegistry:
    def test_get_tool_registry_creates_once(self, ai_executor):
        registry1 = ai_executor._get_tool_registry()
        registry2 = ai_executor._get_tool_registry()
        assert registry1 is registry2

    def test_get_tool_registry_with_mcp_manager(self, mock_app):
        mock_mcp = MagicMock()
        mock_app.mcp_manager = mock_mcp
        executor = AIExecutor(mock_app)

        with patch("handlers.ai.tool_runner.ToolRegistry") as mock_registry:
            executor._get_tool_registry()
            mock_registry.assert_called_once_with(mcp_manager=mock_mcp)


class TestAIExecutorCancelTool:
    @pytest.mark.asyncio
    async def test_cancel_tool_calls_cancel_on_active(self, ai_executor):
        from handlers.ai.tool_runner import ToolRunner

        mock_streaming = MagicMock()
        ToolRunner._active_streaming_calls["tool_123"] = mock_streaming

        await ai_executor.cancel_tool("tool_123")

        mock_streaming.cancel.assert_called_once()
        del ToolRunner._active_streaming_calls["tool_123"]

    @pytest.mark.asyncio
    async def test_cancel_tool_ignores_unknown(self, ai_executor):
        await ai_executor.cancel_tool("unknown_tool")


class TestAIExecutorWithTools:
    @pytest.mark.asyncio
    async def test_execute_with_tools_text_only(self, ai_executor, mock_app):
        mock_app._ai_cancelled = False
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
        widget = MagicMock()

        async def mock_gen_with_tools(*args, **kwargs):
            yield StreamChunk(text="Hello ")
            yield StreamChunk(text="world")
            yield StreamChunk(
                text="",
                is_complete=True,
                usage=TokenUsage(input_tokens=10, output_tokens=5),
            )

        mock_app.ai_provider.generate_with_tools = mock_gen_with_tools

        with patch.object(ai_executor, "_get_tool_registry") as mock_reg:
            mock_reg.return_value.get_all_tools_schema.return_value = []
            await ai_executor._execute_with_tools("hi", block, widget, [], "", 100)

        assert "Hello world" in block.content_output

    @pytest.mark.asyncio
    async def test_execute_with_tools_processes_tool_calls(self, ai_executor, mock_app):
        mock_app._ai_cancelled = False
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="search")
        widget = MagicMock()

        tool_call = ToolCallData(id="call_1", name="search", arguments={"q": "test"})

        call_count = 0

        async def mock_gen_with_tools(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                yield StreamChunk(text="Let me search...")
                yield StreamChunk(
                    text="",
                    tool_calls=[tool_call],
                    is_complete=True,
                    usage=TokenUsage(input_tokens=10, output_tokens=5),
                )

        mock_app.ai_provider.generate_with_tools = mock_gen_with_tools

        mock_result = ToolResult(
            tool_call_id="call_1",
            content="Search results",
            is_error=False,
        )

        with (
            patch.object(ai_executor, "_get_tool_registry") as mock_reg,
            patch.object(
                ai_executor._tool_runner,
                "process_chat_tools",
                new_callable=AsyncMock,
                return_value=[mock_result],
            ) as mock_process,
        ):
            mock_reg.return_value.get_all_tools_schema.return_value = []
            await ai_executor._execute_with_tools("search", block, widget, [], "", 100)

        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_tools_cancelled(self, ai_executor, mock_app):
        block = BlockState(type=BlockType.AI_RESPONSE, content_input="hi")
        widget = MagicMock()

        async def mock_gen_with_tools(*args, **kwargs):
            mock_app._ai_cancelled = True
            yield StreamChunk(text="Starting...")
            yield StreamChunk(text="", is_complete=True)

        mock_app.ai_provider.generate_with_tools = mock_gen_with_tools

        with patch.object(ai_executor, "_get_tool_registry") as mock_reg:
            mock_reg.return_value.get_all_tools_schema.return_value = []
            await ai_executor._execute_with_tools("hi", block, widget, [], "", 100)

        assert "[Cancelled]" in block.content_output


class TestAIExecutorAgentMode:
    @pytest.mark.asyncio
    async def test_execute_agent_mode_uses_agent_prompt(self, ai_executor, mock_app):
        block = BlockState(type=BlockType.AGENT_RESPONSE, content_input="task")
        widget = MagicMock()
        mock_app._ai_cancelled = False
        mock_app.agent_manager = MagicMock()
        mock_app.agent_manager.should_cancel.return_value = True

        async def mock_gen(*args, **kwargs):
            yield StreamChunk(text="Done", is_complete=True)

        mock_app.ai_provider.generate_with_tools = mock_gen

        with (
            patch("handlers.ai_executor.Config.get", return_value="test-provider"),
            patch.object(ai_executor, "_get_tool_registry") as mock_reg,
            patch("ai.thinking.get_thinking_strategy") as mock_strategy,
        ):
            mock_reg.return_value.get_all_tools_schema.return_value = []
            mock_strategy.return_value.requires_prompting = False

            await ai_executor._agent_loop.run_loop(
                "task", block, widget, [], "System", 100, ai_executor._finalize_response
            )

        mock_app.agent_manager.start_session.assert_called_once()


class TestToolRunnerSessionApproval:
    def test_reset_session_approvals(self, ai_executor):
        tool_runner = ai_executor._tool_runner
        tool_runner._session_approved_tools.add("read_file")
        tool_runner._session_approved_tools.add("write_file")

        tool_runner.reset_session_approvals()

        assert len(tool_runner._session_approved_tools) == 0

    def test_is_tool_session_approved(self, ai_executor):
        tool_runner = ai_executor._tool_runner
        tool_runner._session_approved_tools.add("read_file")

        assert tool_runner.is_tool_session_approved("read_file") is True
        assert tool_runner.is_tool_session_approved("write_file") is False

    def test_add_session_approved_tools(self, ai_executor):
        tool_runner = ai_executor._tool_runner

        tool_runner.add_session_approved_tools(["read_file", "write_file"])

        assert tool_runner.is_tool_session_approved("read_file") is True
        assert tool_runner.is_tool_session_approved("write_file") is True
        assert tool_runner.is_tool_session_approved("run_command") is False

    @pytest.mark.asyncio
    async def test_request_approval_skips_session_approved(self, ai_executor, mock_app):
        tool_runner = ai_executor._tool_runner
        tool_runner.add_session_approved_tools(["read_file"])

        mock_tool_call = MagicMock()
        mock_tool_call.name = "read_file"
        mock_tool_call.arguments = {"path": "/tmp/test.txt"}

        result = await tool_runner.request_approval(
            [mock_tool_call], iteration_number=1
        )

        assert result == "approve"

    @pytest.mark.asyncio
    async def test_request_approval_shows_screen_for_unapproved(
        self, ai_executor, mock_app
    ):
        tool_runner = ai_executor._tool_runner
        tool_runner.reset_session_approvals()

        mock_tool_call = MagicMock()
        mock_tool_call.name = "write_file"
        mock_tool_call.arguments = {"path": "/tmp/test.txt"}

        mock_app.config.get.return_value = {"agent_approval_timeout": 60}
        mock_app.push_screen_wait = AsyncMock(return_value="approve")

        result = await tool_runner.request_approval(
            [mock_tool_call], iteration_number=1
        )

        assert result == "approve"
        mock_app.push_screen_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_approval_timeout_returns_reject(self, ai_executor, mock_app):
        tool_runner = ai_executor._tool_runner
        tool_runner.reset_session_approvals()

        mock_tool_call = MagicMock()
        mock_tool_call.name = "run_command"
        mock_tool_call.arguments = {"cmd": "ls"}

        mock_app.config.get.return_value = {"agent_approval_timeout": 60}
        mock_app.push_screen_wait = AsyncMock(return_value="timeout")
        mock_app.notify = MagicMock()

        result = await tool_runner.request_approval(
            [mock_tool_call], iteration_number=1
        )

        assert result == "reject"
        mock_app.notify.assert_called_once()
        assert "timed out" in mock_app.notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_request_approval_session_adds_tools(self, ai_executor, mock_app):
        tool_runner = ai_executor._tool_runner
        tool_runner.reset_session_approvals()

        mock_tool_call = MagicMock()
        mock_tool_call.name = "read_file"
        mock_tool_call.arguments = {"path": "/tmp/test.txt"}

        mock_app.config.get.return_value = {"agent_approval_timeout": 60}
        mock_app.push_screen_wait = AsyncMock(return_value="approve-session")

        result = await tool_runner.request_approval(
            [mock_tool_call], iteration_number=1
        )

        assert result == "approve"
        assert tool_runner.is_tool_session_approved("read_file") is True
