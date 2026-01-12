"""Unit tests for RecallManager - semantic recall of past interactions."""

import json
from datetime import datetime
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from managers.recall import RecallManager


class MockBlockType(Enum):
    """Mock BlockType enum matching the real BlockType."""

    COMMAND = "command"
    AI_RESPONSE = "ai"
    AGENT_RESPONSE = "agent"
    AI_QUERY = "ai_query"
    SYSTEM_MSG = "system"
    TOOL_CALL = "tool_call"


class MockBlock:
    """Mock block that matches the interface RecallManager.index_interaction expects."""

    def __init__(
        self,
        type: str = "command",
        content_input: str = "",
        content_output: str = "",
        is_running: bool = False,
        exit_code: int | None = None,
        model: str | None = None,
        timestamp: datetime | None = None,
    ):
        type_map = {
            "command": MockBlockType.COMMAND,
            "ai": MockBlockType.AI_RESPONSE,
            "ai_response": MockBlockType.AI_RESPONSE,
            "agent": MockBlockType.AGENT_RESPONSE,
        }
        self.type = type_map.get(type, MockBlockType.COMMAND)
        self.content_input = content_input
        self.content_output = content_output
        self.is_running = is_running
        self.exit_code = exit_code
        self.metadata = {"model": model} if model else {}
        self.timestamp = timestamp or datetime.now()


class TestRecallManagerInit:
    def test_init_creates_storage_manager(self, mock_home):
        manager = RecallManager()
        assert manager.storage is not None

    def test_init_creates_ai_factory(self, mock_home):
        manager = RecallManager()
        assert manager.ai_factory is not None

    def test_init_creates_vector_store(self, mock_home):
        manager = RecallManager()
        assert manager.vector_store is not None

    def test_vector_store_path_is_in_null_dir(self, mock_home):
        manager = RecallManager()
        expected_path = mock_home / ".null" / "history_index.json"
        assert manager.vector_store.path == expected_path


class TestIndexInteraction:
    @pytest.mark.asyncio
    async def test_index_interaction_skips_empty_content(self, mock_home):
        manager = RecallManager()
        block = MockBlock(content_input="", is_running=False)

        await manager.index_interaction(block)

    @pytest.mark.asyncio
    async def test_index_interaction_skips_incomplete_blocks(self, mock_home):
        manager = RecallManager()
        block = MockBlock(content_input="ls -la", is_running=True)

        await manager.index_interaction(block)

    @pytest.mark.asyncio
    async def test_index_interaction_command_block(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input="ls -la",
            content_output="file1.txt\nfile2.txt",
            is_running=False,
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("ls -la")
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_index_interaction_ai_response_block(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="ai_response",
            content_input="Python is a programming language.",
            is_running=False,
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("Python")
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_index_interaction_with_embedding_provider(
        self, mock_home, mock_storage
    ):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input="git status",
            content_output="On branch main",
            is_running=False,
        )

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            await manager.index_interaction(block)

            mock_provider.embed_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_interaction_embedding_failure_graceful(
        self, mock_home, mock_storage
    ):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input="test command",
            content_output="test output",
            is_running=False,
        )

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(side_effect=Exception("Embedding failed"))

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            await manager.index_interaction(block)

    @pytest.mark.asyncio
    async def test_index_interaction_stores_metadata(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        now = datetime.now()
        block = MockBlock(
            type="command",
            content_input="test command",
            content_output="test output",
            is_running=False,
            exit_code=0,
            timestamp=now,
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("test command")
            assert len(results) > 0
            if results[0].get("metadata"):
                metadata = json.loads(results[0]["metadata"])
                assert "exit_code" in metadata or "timestamp" in metadata

    @pytest.mark.asyncio
    async def test_index_interaction_adds_to_vector_store(
        self, mock_home, mock_storage
    ):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input="ls",
            content_output="files",
            is_running=False,
        )

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=[0.5, 0.5, 0.5])

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            initial_chunks = len(manager.vector_store.chunks)
            await manager.index_interaction(block)

            assert len(manager.vector_store.chunks) > initial_chunks


class TestGetEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_get_embedding_provider_returns_none_on_error(self, mock_home):
        manager = RecallManager()

        with patch(
            "managers.recall.AIFactory.get_provider", side_effect=Exception("Error")
        ):
            provider = await manager._get_embedding_provider()
            assert provider is None

    @pytest.mark.asyncio
    async def test_get_embedding_provider_uses_profile_config(self, mock_home):
        manager = RecallManager()

        mock_mcp_config = MagicMock()
        mock_mcp_config.get_active_ai_config.return_value = {
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-small",
            "embedding_endpoint": "https://api.openai.com/v1",
        }

        with (
            patch("mcp.config.MCPConfig", return_value=mock_mcp_config),
            patch("config.Config") as mock_config,
            patch("ai.factory.AIFactory.get_provider") as mock_get_provider,
        ):
            mock_config.get.return_value = None
            mock_get_provider.return_value = MagicMock()

            await manager._get_embedding_provider()

            mock_get_provider.assert_called_once()
            call_args = mock_get_provider.call_args[0][0]
            assert call_args["provider"] == "openai"
            assert call_args["model"] == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_get_embedding_provider_falls_back_to_defaults(self, mock_home):
        manager = RecallManager()

        mock_mcp_config = MagicMock()
        mock_mcp_config.get_active_ai_config.return_value = None

        with (
            patch("mcp.config.MCPConfig", return_value=mock_mcp_config),
            patch("config.Config") as mock_config,
            patch("ai.factory.AIFactory.get_provider") as mock_get_provider,
        ):
            mock_config.get.side_effect = lambda key, default=None: {
                "ai.embedding_provider": "ollama",
                "ai.embedding.ollama.model": "nomic-embed-text",
                "ai.embedding.ollama.endpoint": "http://localhost:11434",
                "ai.embedding.ollama.api_key": "",
                "ai.ollama.api_key": "",
            }.get(key, default)
            mock_get_provider.return_value = MagicMock()

            await manager._get_embedding_provider()

            mock_get_provider.assert_called_once()
            call_args = mock_get_provider.call_args[0][0]
            assert call_args["provider"] == "ollama"


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_without_provider_uses_text_search(
        self, mock_home, mock_storage
    ):
        manager = RecallManager()
        manager.storage = mock_storage

        mock_storage.add_interaction(
            type="command",
            input_text="git status",
            output_text="On branch main",
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            results = await manager.search("git")

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_provider_uses_vector_search(
        self, mock_home, mock_storage
    ):
        manager = RecallManager()
        manager.storage = mock_storage

        from ai.rag import DocumentChunk

        chunk = DocumentChunk(
            id="1",
            content="git status output",
            source="history",
            vector=[0.1, 0.2, 0.3],
        )
        manager.vector_store.add([chunk])

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            results = await manager.search("git")

            assert isinstance(results, list)
            if results:
                assert "source" in results[0]

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        for i in range(10):
            mock_storage.add_interaction(
                type="command",
                input_text=f"command {i}",
                output_text=f"output {i}",
            )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            results = await manager.search("command", limit=3)

            assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_empty_query_vector(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        mock_storage.add_interaction(
            type="command",
            input_text="test",
            output_text="output",
        )

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=None)

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            results = await manager.search("test")
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_returns_scores_for_vector_results(self, mock_home):
        manager = RecallManager()

        from ai.rag import DocumentChunk

        chunk = DocumentChunk(
            id="1",
            content="test content",
            source="history",
            vector=[1.0, 0.0, 0.0],
        )
        manager.vector_store.add([chunk])

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=[1.0, 0.0, 0.0])

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            results = await manager.search("test")

            if results:
                assert "score" in results[0]
                assert results[0]["source"] == "vector"

    @pytest.mark.asyncio
    async def test_search_default_limit(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        for i in range(20):
            mock_storage.add_interaction(
                type="command",
                input_text=f"cmd {i}",
                output_text=f"out {i}",
            )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            results = await manager.search("cmd")

            assert len(results) <= 5


class TestVectorStoreIntegration:
    def test_vector_store_persists_to_disk(self, mock_home):
        manager = RecallManager()

        from ai.rag import DocumentChunk

        chunk = DocumentChunk(
            id="test",
            content="test content",
            source="test",
            vector=[0.1, 0.2, 0.3],
        )
        manager.vector_store.add([chunk])

        assert manager.vector_store.path.exists()

    def test_vector_store_loads_existing_data(self, mock_home):
        manager1 = RecallManager()

        from ai.rag import DocumentChunk

        chunk = DocumentChunk(
            id="persistent",
            content="persistent content",
            source="test",
            vector=[0.5, 0.5, 0.5],
        )
        manager1.vector_store.add([chunk])

        manager2 = RecallManager()
        assert len(manager2.vector_store.chunks) == 1
        assert manager2.vector_store.chunks[0].id == "persistent"

    def test_vector_store_search_returns_ranked_results(self, mock_home):
        manager = RecallManager()

        from ai.rag import DocumentChunk

        chunk1 = DocumentChunk(
            id="1",
            content="very similar",
            source="test",
            vector=[1.0, 0.0, 0.0],
        )
        chunk2 = DocumentChunk(
            id="2",
            content="less similar",
            source="test",
            vector=[0.5, 0.5, 0.5],
        )
        manager.vector_store.add([chunk1, chunk2])

        results = manager.vector_store.search([1.0, 0.0, 0.0], limit=2)

        assert len(results) == 2
        assert results[0][1] >= results[1][1]


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_index_interaction_empty_output(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input="clear",
            content_output="",
            is_running=False,
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("clear")
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_index_interaction_special_characters(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input='echo "hello\nworld" | grep -E "[a-z]+"',
            content_output="hello\nworld",
            is_running=False,
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("grep")
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_special_characters(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        mock_storage.add_interaction(
            type="command",
            input_text="echo $HOME",
            output_text="/home/user",
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            results = await manager.search("$HOME")
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_index_very_long_content(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        long_output = "x" * 10000
        block = MockBlock(
            type="command",
            content_input="cat large_file.txt",
            content_output=long_output,
            is_running=False,
        )

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("large_file")
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_concurrent_index_operations(self, mock_home, mock_storage):
        import asyncio

        manager = RecallManager()
        manager.storage = mock_storage

        blocks = [
            MockBlock(
                type="command",
                content_input=f"cmd{i}",
                content_output=f"out{i}",
                is_running=False,
            )
            for i in range(5)
        ]

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = None

            await asyncio.gather(*[manager.index_interaction(b) for b in blocks])

            all_results = mock_storage.search_interactions("cmd", limit=10)
            assert len(all_results) >= 5

    @pytest.mark.asyncio
    async def test_search_empty_vector_store(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            results = await manager.search("anything")

            assert results == []

    @pytest.mark.asyncio
    async def test_null_vector_from_provider(self, mock_home, mock_storage):
        manager = RecallManager()
        manager.storage = mock_storage

        block = MockBlock(
            type="command",
            content_input="test",
            content_output="output",
            is_running=False,
        )

        mock_provider = AsyncMock()
        mock_provider.embed_text = AsyncMock(return_value=None)

        with patch.object(
            manager, "_get_embedding_provider", new_callable=AsyncMock
        ) as mock_get_provider:
            mock_get_provider.return_value = mock_provider

            await manager.index_interaction(block)

            results = mock_storage.search_interactions("test")
            assert len(results) > 0
