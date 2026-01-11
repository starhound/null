"""Test RAG system."""

from unittest.mock import AsyncMock

import pytest

from ai.rag import Chunker, DocumentChunk, RAGManager, VectorStore


def test_chunker():
    chunker = Chunker(chunk_size=10, overlap=2)
    text = "Hello world this is a test"
    chunks = chunker.split_text(text)
    assert len(chunks) > 1
    assert "Hello" in chunks[0]


def test_vector_store(tmp_path):
    store = VectorStore(tmp_path / "index.json")

    chunk = DocumentChunk(id="1", content="test", source="file.txt", vector=[1.0, 0.0])
    store.add([chunk])

    assert len(store.chunks) == 1

    # Reload
    store2 = VectorStore(tmp_path / "index.json")
    assert len(store2.chunks) == 1

    # Search
    results = store.search([1.0, 0.0])
    assert len(results) == 1
    assert results[0][0].id == "1"
    assert results[0][1] > 0.9  # Similarity should be close to 1.0


@pytest.mark.asyncio
async def test_rag_manager(tmp_path):
    # Mock home path for index.json
    with pytest.MonkeyPatch.context() as m:
        m.setattr("pathlib.Path.home", lambda: tmp_path)

        rag = RAGManager()

        # Create dummy file
        d = tmp_path / "test_dir"
        d.mkdir()
        (d / "doc.txt").write_text("This is some content for RAG.")

        # Mock provider
        provider = AsyncMock()
        provider.embed_text.return_value = [0.1, 0.2]

        count = await rag.index_directory(d, provider)
        assert count == 1

        stats = rag.get_stats()
        assert stats["total_documents"] == 1

        results = await rag.search("query", provider)
        assert len(results) == 1
        assert "content" in results[0].content
