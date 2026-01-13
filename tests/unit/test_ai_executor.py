import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from handlers.ai_executor import AIExecutor


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.blocks = []
    app.ai_manager = MagicMock()
    app.mcp_manager = MagicMock()
    app.mcp_manager.config.get_active_ai_config.return_value = None
    app.notify = MagicMock()
    app.query_one = MagicMock(side_effect=Exception("Not found"))
    return app


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.model = "test-model"
    provider.supports_tools.return_value = True
    provider.get_model_info.return_value = MagicMock(context_window=4096)
    return provider


@pytest.fixture
def mock_block_state():
    state = MagicMock()
    state.type = MagicMock()
    state.metadata = {}
    return state


@pytest.fixture
def mock_widget():
    widget = MagicMock()
    widget.update_output = MagicMock()
    widget.set_loading = MagicMock()
    widget.update_metadata = MagicMock()
    return widget


class TestAIExecutorInit:
    def test_init_creates_tool_runner(self, mock_app):
        with patch("handlers.ai_executor.ToolRunner") as mock_runner:
            with patch("handlers.ai_executor.AgentLoop"):
                executor = AIExecutor(mock_app)
                mock_runner.assert_called_once_with(mock_app)

    def test_init_creates_agent_loop(self, mock_app):
        with patch("handlers.ai_executor.ToolRunner") as mock_runner:
            with patch("handlers.ai_executor.AgentLoop") as mock_loop:
                executor = AIExecutor(mock_app)
                mock_loop.assert_called_once()


class TestAIExecutorMethods:
    @pytest.fixture
    def executor(self, mock_app):
        with patch("handlers.ai_executor.ToolRunner"):
            with patch("handlers.ai_executor.AgentLoop"):
                return AIExecutor(mock_app)

    def test_get_tool_registry(self, executor):
        executor._tool_runner.get_registry.return_value = MagicMock()
        registry = executor._get_tool_registry()
        executor._tool_runner.get_registry.assert_called_once()

    def test_get_status_bar_not_found(self, executor):
        result = executor._get_status_bar()
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_tool(self, executor):
        executor._tool_runner.cancel_tool = AsyncMock()
        await executor.cancel_tool("tool-123")
        executor._tool_runner.cancel_tool.assert_called_once_with("tool-123")


class TestExecuteAI:
    @pytest.fixture
    def executor(self, mock_app):
        with patch("handlers.ai_executor.ToolRunner"):
            with patch("handlers.ai_executor.AgentLoop"):
                return AIExecutor(mock_app)

    @pytest.mark.asyncio
    async def test_execute_ai_no_provider(
        self, executor, mock_block_state, mock_widget
    ):
        executor.app.ai_manager.get_provider.return_value = None

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get.return_value = "nonexistent"
            await executor.execute_ai("test prompt", mock_block_state, mock_widget)

        mock_widget.update_output.assert_called()
        mock_widget.set_loading.assert_called_with(False)

    @pytest.mark.asyncio
    async def test_execute_ai_with_provider(
        self, executor, mock_provider, mock_block_state, mock_widget
    ):
        executor.app.ai_manager.get_provider.return_value = mock_provider
        executor.app.blocks = []

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get.side_effect = lambda k: {
                "ai.provider": "test",
                "ai.active_prompt": "default",
            }.get(k)

            with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                mock_ctx.build_messages.return_value = MagicMock(
                    messages=[],
                    estimated_tokens=100,
                    message_count=1,
                    summarized=False,
                    truncated=False,
                )

                with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                    mock_pm.return_value.get_prompt_content.return_value = "system"

                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        with patch.object(
                            executor, "_execute_without_tools", new_callable=AsyncMock
                        ):
                            with patch.object(
                                executor, "_execute_with_tools", new_callable=AsyncMock
                            ):
                                await executor.execute_ai(
                                    "test", mock_block_state, mock_widget
                                )

        assert mock_block_state.metadata["provider"] == "test"
        assert mock_block_state.metadata["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_execute_ai_with_mcp_profile(
        self, executor, mock_provider, mock_block_state, mock_widget
    ):
        executor.app.ai_manager.get_provider.return_value = mock_provider
        executor.app.mcp_manager.config.get_active_ai_config.return_value = {
            "provider": "profile-provider",
            "model": "profile-model",
        }

        with patch("handlers.ai_executor.Config") as mock_config:
            mock_config.get.side_effect = lambda k: {
                "ai.provider": "default",
                "ai.active_prompt": "default",
            }.get(k)

            with patch("handlers.ai_executor.ContextManager") as mock_ctx:
                mock_ctx.build_messages.return_value = MagicMock(
                    messages=[],
                    estimated_tokens=100,
                    message_count=1,
                    summarized=False,
                    truncated=False,
                )

                with patch("handlers.ai_executor.get_prompt_manager") as mock_pm:
                    mock_pm.return_value.get_prompt_content.return_value = "system"

                    with patch("handlers.ai_executor.get_settings") as mock_settings:
                        mock_settings.return_value.ai.use_rag = False

                        with patch.object(
                            executor, "_execute_without_tools", new_callable=AsyncMock
                        ):
                            with patch.object(
                                executor, "_execute_with_tools", new_callable=AsyncMock
                            ):
                                await executor.execute_ai(
                                    "test", mock_block_state, mock_widget
                                )

        assert mock_provider.model == "profile-model"


class TestContextHandling:
    @pytest.fixture
    def executor(self, mock_app):
        with patch("handlers.ai_executor.ToolRunner"):
            with patch("handlers.ai_executor.AgentLoop"):
                return AIExecutor(mock_app)

    def test_context_result_attributes(self):
        from unittest.mock import MagicMock

        ctx_result = MagicMock(
            messages=[],
            estimated_tokens=100,
            message_count=5,
            summarized=True,
            truncated=False,
        )
        assert ctx_result.summarized is True
        assert ctx_result.truncated is False

    def test_context_truncated_attributes(self):
        from unittest.mock import MagicMock

        ctx_result = MagicMock(
            messages=[],
            estimated_tokens=100,
            message_count=3,
            original_message_count=10,
            summarized=False,
            truncated=True,
        )
        assert ctx_result.truncated is True
        assert ctx_result.message_count == 3
