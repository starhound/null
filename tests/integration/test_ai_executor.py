"""Integration tests for AIExecutor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.base import StreamChunk, TokenUsage, ToolCallData
from handlers.ai_executor import AIExecutor
from models import BlockState, BlockType


@pytest.fixture
def mock_app(temp_home, mock_storage):
    """Create a mock NullApp instance for AIExecutor tests."""
    app = MagicMock()
    app.blocks = []
    app._ai_cancelled = False
    app._active_worker = None
    app.notify = MagicMock()
    app.log = MagicMock()
    app._auto_save = MagicMock()
    app.set_interval = MagicMock()
    app.query_one = MagicMock(side_effect=Exception("NoMatches"))
    app.run_worker = MagicMock(return_value=MagicMock())

    # Mock AIManager
    app.ai_manager = MagicMock()
    app.ai_manager.get_provider = MagicMock(return_value=None)

    # Mock MCPManager
    app.mcp_manager = MagicMock()
    app.mcp_manager.config = MagicMock()
    app.mcp_manager.config.get_active_ai_config = MagicMock(return_value=None)

    return app


@pytest.fixture
def mock_provider():
    """Create a mock AI provider."""
    provider = MagicMock()
    provider.model = "test-model"
    provider.supports_tools = MagicMock(return_value=False)
    provider.get_model_info = MagicMock(return_value=MagicMock(context_window=4096))
    return provider


@pytest.fixture
def mock_widget():
    """Create a mock block widget."""
    widget = MagicMock()
    widget.update_output = MagicMock()
    widget.update_metadata = MagicMock()
    widget.set_loading = MagicMock()
    return widget


@pytest.fixture
def sample_block():
    """Create a sample AI block state."""
    return BlockState(
        type=BlockType.AI_RESPONSE,
        content_input="Hello, AI!",
        content_output="",
        is_running=True,
    )


class TestAIExecutorStreaming:
    """Test streaming response handling."""

    @pytest.mark.asyncio
    async def test_streaming_without_tools(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test streaming AI response without tool support."""

        # Setup streaming generator
        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Hello ")
            yield StreamChunk(text="World!")
            yield StreamChunk(text="", is_complete=True)

        mock_provider.generate = mock_generate
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System prompt"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=False,
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Hello", sample_block, mock_widget)

        # Verify streaming occurred
        assert mock_widget.update_output.called
        assert mock_widget.set_loading.called

    @pytest.mark.asyncio
    async def test_streaming_with_token_usage(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test streaming with token usage tracking."""
        usage = TokenUsage(input_tokens=10, output_tokens=5)

        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Response")
            yield StreamChunk(text="", is_complete=True, usage=usage)

        mock_provider.generate = mock_generate
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=False,
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Test", sample_block, mock_widget)

        assert sample_block.is_running is False


class TestAIExecutorToolCalls:
    """Test tool calling functionality."""

    @pytest.mark.asyncio
    async def test_execute_with_tools(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test AI execution with tool support."""
        mock_provider.supports_tools = MagicMock(return_value=True)

        tool_call = ToolCallData(
            id="call_123",
            name="test_tool",
            arguments={"arg": "value"},
        )

        async def mock_generate_with_tools(*args, **kwargs):
            yield StreamChunk(text="I'll use a tool.")
            yield StreamChunk(tool_calls=[tool_call])
            yield StreamChunk(text="", is_complete=True)

        mock_provider.generate_with_tools = mock_generate_with_tools
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        # Mock tool runner to return empty results (stops iteration)
        executor._tool_runner.process_chat_tools = AsyncMock(return_value=[])

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=False,
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Use tool", sample_block, mock_widget)

        assert mock_widget.update_output.called

    @pytest.mark.asyncio
    async def test_cancel_tool(self, mock_app):
        """Test tool cancellation."""
        executor = AIExecutor(mock_app)
        executor._tool_runner.cancel_tool = AsyncMock()

        await executor.cancel_tool("tool_123")

        executor._tool_runner.cancel_tool.assert_called_once_with("tool_123")


class TestAIExecutorErrorHandling:
    """Test error handling for failed AI calls."""

    @pytest.mark.asyncio
    async def test_provider_not_configured(self, mock_app, mock_widget, sample_block):
        """Test handling when AI provider is not configured."""
        mock_app.ai_manager.get_provider = MagicMock(return_value=None)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="nonexistent")
            with patch("handlers.ai_executor.get_prompt_manager"):
                await executor.execute_ai("Test", sample_block, mock_widget)

        mock_widget.update_output.assert_called()
        mock_widget.set_loading.assert_called_with(False)

    @pytest.mark.asyncio
    async def test_generation_error(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test handling of generation errors."""

        async def mock_generate_error(*args, **kwargs):
            raise RuntimeError("API Error")
            yield  # Make it a generator

        mock_provider.generate = mock_generate_error
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=False,
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Test", sample_block, mock_widget)

        # Should have error message in output
        assert "Error" in sample_block.content_output
        assert sample_block.is_running is False
        mock_widget.set_loading.assert_called_with(False)


class TestAIExecutorCancellation:
    """Test cancellation of running AI tasks."""

    @pytest.mark.asyncio
    async def test_cancellation_during_streaming(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test cancellation during streaming response."""

        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Start ")
            mock_app._ai_cancelled = True
            yield StreamChunk(text="More ")
            yield StreamChunk(text="", is_complete=True)

        mock_provider.generate = mock_generate
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=False,
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Test", sample_block, mock_widget)

        assert "[Cancelled]" in sample_block.content_output

    @pytest.mark.asyncio
    async def test_asyncio_cancelled_error(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test handling of asyncio.CancelledError."""

        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Start")
            raise asyncio.CancelledError()

        mock_provider.generate = mock_generate
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=False,
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Test", sample_block, mock_widget)

        assert "[Cancelled]" in sample_block.content_output
        assert sample_block.is_running is False


class TestAIExecutorContextManagement:
    """Test context management (adding messages)."""

    @pytest.mark.asyncio
    async def test_context_building(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test context is built from existing blocks."""
        # Add previous blocks to app
        prev_block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Previous question",
            content_output="Previous answer",
            is_running=False,
        )
        mock_app.blocks = [prev_block, sample_block]

        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Response")
            yield StreamChunk(text="", is_complete=True)

        mock_provider.generate = mock_generate
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[
                                {"role": "user", "content": "Previous question"},
                                {"role": "assistant", "content": "Previous answer"},
                            ],
                            estimated_tokens=200,
                            truncated=False,
                            message_count=2,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai(
                            "New question", sample_block, mock_widget
                        )

                    # Verify context manager was called with previous blocks
                    mock_ctx.build_messages.assert_called_once()
                    call_args = mock_ctx.build_messages.call_args
                    # First arg should be blocks[:-1] (excluding current block)
                    assert len(call_args[0][0]) == 1

    @pytest.mark.asyncio
    async def test_context_truncation_warning(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test warning when context is truncated."""

        async def mock_generate(*args, **kwargs):
            yield StreamChunk(text="Response")
            yield StreamChunk(text="", is_complete=True)

        mock_provider.generate = mock_generate
        mock_app.ai_provider = mock_provider
        mock_app.ai_manager.get_provider = MagicMock(return_value=mock_provider)

        executor = AIExecutor(mock_app)

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get = MagicMock(return_value="test")
            with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                mock_pm.return_value.get_prompt_content = MagicMock(
                    return_value="System"
                )
                with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                    mock_ctx.build_messages = MagicMock(
                        return_value=MagicMock(
                            messages=[],
                            estimated_tokens=100,
                            truncated=True,  # Context was truncated
                            message_count=0,
                        )
                    )
                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        await executor.execute_ai("Test", sample_block, mock_widget)

        # Should notify about truncation
        mock_app.notify.assert_called()


class TestAIExecutorRegenerate:
    """Test regeneration functionality."""

    @pytest.mark.asyncio
    async def test_regenerate_ai_no_provider(self, mock_app, mock_widget, sample_block):
        """Test regenerate when no AI provider configured."""
        mock_app.ai_provider = None

        executor = AIExecutor(mock_app)
        await executor.regenerate_ai(sample_block, mock_widget)

        mock_app.notify.assert_called_with(
            "AI Provider not configured", severity="error"
        )

    @pytest.mark.asyncio
    async def test_regenerate_ai_resets_state(
        self, mock_app, mock_provider, mock_widget, sample_block
    ):
        """Test regenerate resets block state."""
        sample_block.content_output = "Old response"
        sample_block.is_running = False

        mock_app.ai_provider = mock_provider

        executor = AIExecutor(mock_app)
        await executor.regenerate_ai(sample_block, mock_widget)

        assert sample_block.content_output == ""
        assert sample_block.is_running is True
        mock_widget.set_loading.assert_called_with(True)
        mock_app.run_worker.assert_called()
