"""Tests for commands/rag.py - RAG / Knowledge Base commands."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from commands.rag import RAGCommands


@pytest.fixture
def mock_app():
    app = MagicMock()
    app.ai_provider = MagicMock()
    app.ai_provider.model = "test-model"
    app.run_worker = MagicMock()
    app.notify = MagicMock()
    app._show_system_output = AsyncMock()
    return app


@pytest.fixture
def mock_rag_manager():
    rag = MagicMock()
    rag.get_stats.return_value = {
        "total_documents": 10,
        "total_chunks": 50,
        "total_vectors": 50,
        "index_size_mb": 1.5,
    }
    rag.clear = MagicMock()
    rag.index_directory = AsyncMock(return_value=5)
    rag.search = AsyncMock(return_value=[])
    return rag


@pytest.fixture
def mock_recall_manager():
    recall = MagicMock()
    recall.search = AsyncMock(return_value=[])
    return recall


@pytest.fixture
def rag_commands(mock_app, mock_rag_manager, mock_recall_manager):
    with (
        patch("commands.rag.RAGManager", return_value=mock_rag_manager),
        patch("commands.rag.RecallManager", return_value=mock_recall_manager),
    ):
        commands = RAGCommands(mock_app)
    commands.rag = mock_rag_manager
    commands.recall = mock_recall_manager
    return commands


class TestRecallCommand:
    """Tests for /recall command."""

    @pytest.mark.asyncio
    async def test_cmd_recall_no_args_shows_error(self, rag_commands, mock_app):
        """Should show usage error when no query provided."""
        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands.cmd_recall([])

        mock_notify.assert_called_once()
        assert "Usage" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_cmd_recall_no_results(self, rag_commands, mock_recall_manager):
        """Should notify when no results found."""
        mock_recall_manager.search.return_value = []

        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands.cmd_recall(["test", "query"])

        mock_recall_manager.search.assert_called_once_with("test query")
        mock_notify.assert_called_once()
        assert "No matching" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_cmd_recall_displays_results(self, rag_commands, mock_recall_manager):
        """Should display results with scores."""
        mock_recall_manager.search.return_value = [
            {"score": 0.95, "content": "First result content"},
            {"score": 0.80, "content": "Second result content"},
        ]

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands.cmd_recall(["test", "query"])

        mock_show.assert_called_once()
        title = mock_show.call_args[0][0]
        output = mock_show.call_args[0][1]

        assert "Recall: test query" in title
        assert "Recall Results" in output
        assert "0.95" in output
        assert "First result content" in output
        assert "0.80" in output

    @pytest.mark.asyncio
    async def test_cmd_recall_truncates_long_content(
        self, rag_commands, mock_recall_manager
    ):
        """Should truncate content longer than 500 chars."""
        long_content = "x" * 600
        mock_recall_manager.search.return_value = [
            {"score": 0.9, "content": long_content},
        ]

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands.cmd_recall(["query"])

        output = mock_show.call_args[0][1]
        assert "..." in output
        assert "x" * 500 in output
        assert "x" * 600 not in output

    @pytest.mark.asyncio
    async def test_cmd_recall_handles_missing_score(
        self, rag_commands, mock_recall_manager
    ):
        """Should handle results without score field."""
        mock_recall_manager.search.return_value = [
            {"content": "Content without score"},
        ]

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands.cmd_recall(["query"])

        output = mock_show.call_args[0][1]
        assert "0.00" in output  # Default score
        assert "Content without score" in output

    @pytest.mark.asyncio
    async def test_cmd_recall_handles_missing_content(
        self, rag_commands, mock_recall_manager
    ):
        """Should handle results without content field."""
        mock_recall_manager.search.return_value = [
            {"score": 0.5},
        ]

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands.cmd_recall(["query"])

        mock_show.assert_called_once()


class TestIndexCommand:
    """Tests for /index command."""

    @pytest.mark.asyncio
    async def test_cmd_index_no_args_shows_status(self, rag_commands):
        """Should show status when no args provided."""
        with patch.object(
            rag_commands, "_show_status", new_callable=AsyncMock
        ) as mock_status:
            await rag_commands.cmd_index([])

        mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_index_status_subcommand(self, rag_commands):
        """Should show status with 'status' subcommand."""
        with patch.object(
            rag_commands, "_show_status", new_callable=AsyncMock
        ) as mock_status:
            await rag_commands.cmd_index(["status"])

        mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_index_build_default_path(self, rag_commands):
        """Should build index with current directory when no path specified."""
        with patch.object(
            rag_commands, "_build_index", new_callable=AsyncMock
        ) as mock_build:
            await rag_commands.cmd_index(["build"])

        mock_build.assert_called_once()
        called_path = mock_build.call_args[0][0]
        assert called_path == Path.cwd()

    @pytest.mark.asyncio
    async def test_cmd_index_build_with_path(self, rag_commands):
        """Should build index with specified path."""
        with patch.object(
            rag_commands, "_build_index", new_callable=AsyncMock
        ) as mock_build:
            await rag_commands.cmd_index(["build", "/some/path"])

        mock_build.assert_called_once()
        called_path = mock_build.call_args[0][0]
        assert called_path == Path("/some/path")

    @pytest.mark.asyncio
    async def test_cmd_index_search_no_query(self, rag_commands):
        """Should show error when search has no query."""
        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands.cmd_index(["search"])

        mock_notify.assert_called_once()
        assert "Usage" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_cmd_index_search_with_query(self, rag_commands):
        """Should search index with provided query."""
        with patch.object(
            rag_commands, "_search_index", new_callable=AsyncMock
        ) as mock_search:
            await rag_commands.cmd_index(["search", "test", "query"])

        mock_search.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_cmd_index_clear(self, rag_commands, mock_rag_manager):
        """Should clear the index."""
        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands.cmd_index(["clear"])

        mock_rag_manager.clear.assert_called_once()
        mock_notify.assert_called_with("Index cleared")

    @pytest.mark.asyncio
    async def test_cmd_index_unknown_subcommand(self, rag_commands):
        """Should show error for unknown subcommand."""
        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands.cmd_index(["unknown"])

        mock_notify.assert_called_once()
        assert "Unknown subcommand" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"


class TestShowStatus:
    """Tests for _show_status helper."""

    @pytest.mark.asyncio
    async def test_show_status_displays_stats(self, rag_commands, mock_rag_manager):
        """Should display index statistics."""
        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands._show_status()

        mock_rag_manager.get_stats.assert_called_once()
        mock_show.assert_called_once()

        title = mock_show.call_args[0][0]
        output = mock_show.call_args[0][1]

        assert "Index Status" in title
        assert "Documents: 10" in output
        assert "Chunks: 50" in output
        assert "Vectors: 50" in output
        assert "1.5 MB" in output

    @pytest.mark.asyncio
    async def test_show_status_includes_build_hint(
        self, rag_commands, mock_rag_manager
    ):
        """Should include build hint in status output."""
        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands._show_status()

        output = mock_show.call_args[0][1]
        assert "/index build" in output


class TestBuildIndex:
    """Tests for _build_index helper."""

    @pytest.mark.asyncio
    async def test_build_index_no_provider(self, rag_commands, mock_app):
        """Should show error when no AI provider is connected."""
        mock_app.ai_provider = None

        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands._build_index(Path("/test"))

        mock_notify.assert_called_once()
        assert "No AI provider" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_build_index_notifies_start(self, rag_commands, mock_app):
        """Should notify that indexing is starting."""
        test_path = Path("/test/path")

        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands._build_index(test_path)

        mock_notify.assert_called_once()
        assert "Indexing" in mock_notify.call_args[0][0]
        assert "/test/path" in mock_notify.call_args[0][0]
        assert "background" in mock_notify.call_args[0][0]

    @pytest.mark.asyncio
    async def test_build_index_starts_worker(self, rag_commands, mock_app):
        """Should start a background worker for indexing."""
        await rag_commands._build_index(Path("/test"))

        mock_app.run_worker.assert_called_once()


class TestSearchIndex:
    """Tests for _search_index helper."""

    @pytest.mark.asyncio
    async def test_search_index_no_provider(self, rag_commands, mock_app):
        """Should show error when no AI provider is connected."""
        mock_app.ai_provider = None

        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands._search_index("test query")

        mock_notify.assert_called_once()
        assert "No AI provider" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_search_index_no_results(self, rag_commands, mock_rag_manager):
        """Should notify when no matches found."""
        mock_rag_manager.search.return_value = []

        with patch.object(rag_commands, "notify") as mock_notify:
            await rag_commands._search_index("test query")

        mock_rag_manager.search.assert_called_once()
        mock_notify.assert_called_with("No matches found")

    @pytest.mark.asyncio
    async def test_search_index_displays_results(self, rag_commands, mock_rag_manager):
        """Should display search results."""
        from ai.rag import DocumentChunk

        mock_chunks = [
            DocumentChunk(id="1", content="First result", source="file1.py"),
            DocumentChunk(id="2", content="Second result", source="file2.py"),
        ]
        mock_rag_manager.search.return_value = mock_chunks

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands._search_index("test query")

        mock_show.assert_called_once()

        title = mock_show.call_args[0][0]
        output = mock_show.call_args[0][1]

        assert "Search: test query" in title
        assert "Search Results" in output
        assert "file1.py" in output
        assert "First result" in output
        assert "file2.py" in output

    @pytest.mark.asyncio
    async def test_search_index_passes_provider(
        self, rag_commands, mock_app, mock_rag_manager
    ):
        """Should pass AI provider to search."""
        mock_rag_manager.search.return_value = []

        await rag_commands._search_index("query")

        mock_rag_manager.search.assert_called_once_with("query", mock_app.ai_provider)


class TestRAGCommandsInitialization:
    """Tests for RAGCommands initialization."""

    def test_init_creates_managers(self, mock_app):
        """Should create RAG and Recall managers."""
        with (
            patch("commands.rag.RAGManager") as mock_rag_class,
            patch("commands.rag.RecallManager") as mock_recall_class,
        ):
            commands = RAGCommands(mock_app)

        mock_rag_class.assert_called_once()
        mock_recall_class.assert_called_once()
        assert commands.app is mock_app

    def test_init_stores_app_reference(self, mock_app):
        """Should store app reference."""
        with (
            patch("commands.rag.RAGManager"),
            patch("commands.rag.RecallManager"),
        ):
            commands = RAGCommands(mock_app)

        assert commands.app is mock_app


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_recall_single_word_query(self, rag_commands, mock_recall_manager):
        """Should handle single word queries."""
        mock_recall_manager.search.return_value = []

        with patch.object(rag_commands, "notify"):
            await rag_commands.cmd_recall(["python"])

        mock_recall_manager.search.assert_called_once_with("python")

    @pytest.mark.asyncio
    async def test_recall_multi_word_query(self, rag_commands, mock_recall_manager):
        """Should join multiple words into query."""
        mock_recall_manager.search.return_value = []

        with patch.object(rag_commands, "notify"):
            await rag_commands.cmd_recall(["how", "to", "fix", "error"])

        mock_recall_manager.search.assert_called_once_with("how to fix error")

    @pytest.mark.asyncio
    async def test_search_single_word_query(self, rag_commands, mock_rag_manager):
        """Should handle single word search queries."""
        mock_rag_manager.search.return_value = []

        with patch.object(rag_commands, "notify"):
            await rag_commands.cmd_index(["search", "function"])

        # Verify _search_index was effectively called
        # via checking rag.search was called

    @pytest.mark.asyncio
    async def test_index_build_relative_path(self, rag_commands):
        """Should handle relative paths for build."""
        with patch.object(
            rag_commands, "_build_index", new_callable=AsyncMock
        ) as mock_build:
            await rag_commands.cmd_index(["build", "relative/path"])

        called_path = mock_build.call_args[0][0]
        assert called_path == Path("relative/path")

    @pytest.mark.asyncio
    async def test_recall_result_numbering(self, rag_commands, mock_recall_manager):
        """Should number results starting from 1."""
        mock_recall_manager.search.return_value = [
            {"score": 0.9, "content": "Result A"},
            {"score": 0.8, "content": "Result B"},
            {"score": 0.7, "content": "Result C"},
        ]

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands.cmd_recall(["query"])

        output = mock_show.call_args[0][1]
        assert "## 1." in output
        assert "## 2." in output
        assert "## 3." in output

    @pytest.mark.asyncio
    async def test_search_result_numbering(self, rag_commands, mock_rag_manager):
        """Should number search results starting from 1."""
        from ai.rag import DocumentChunk

        mock_rag_manager.search.return_value = [
            DocumentChunk(id="1", content="A", source="a.py"),
            DocumentChunk(id="2", content="B", source="b.py"),
        ]

        with patch.object(
            rag_commands, "show_output", new_callable=AsyncMock
        ) as mock_show:
            await rag_commands._search_index("query")

        output = mock_show.call_args[0][1]
        assert "## 1." in output
        assert "## 2." in output


class TestIntegrationWithMixin:
    """Tests verifying CommandMixin integration."""

    @pytest.mark.asyncio
    async def test_notify_calls_app_notify(self, rag_commands, mock_app):
        """Should delegate notify to app."""
        await rag_commands.cmd_recall([])

        mock_app.notify.assert_called()

    @pytest.mark.asyncio
    async def test_show_output_calls_app_method(
        self, rag_commands, mock_app, mock_recall_manager
    ):
        """Should delegate show_output to app."""
        mock_recall_manager.search.return_value = [
            {"score": 0.9, "content": "Result"},
        ]

        await rag_commands.cmd_recall(["query"])

        mock_app._show_system_output.assert_called()
