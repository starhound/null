"""Tests for ai/rag_sqlite.py - SQLiteVectorStore and SemanticCache."""

import asyncio
import json

from ai.rag import DocumentChunk
from ai.rag_sqlite import (
    Document,
    SemanticCache,
    SQLiteVectorStore,
    migrate_json_to_sqlite,
)


class TestDocument:
    """Tests for the Document dataclass."""

    def test_default_values(self):
        """Document should have sensible defaults."""
        doc = Document(id="1", source="file.txt", content="test", chunk_index=0)
        assert doc.id == "1"
        assert doc.source == "file.txt"
        assert doc.content == "test"
        assert doc.chunk_index == 0
        assert doc.embedding is None

    def test_with_embedding(self):
        """Document should accept embedding."""
        doc = Document(
            id="1",
            source="file.txt",
            content="test",
            chunk_index=0,
            embedding=[0.1, 0.2, 0.3],
        )
        assert doc.embedding == [0.1, 0.2, 0.3]


class TestSQLiteVectorStoreInitialization:
    """Tests for SQLiteVectorStore initialization and database creation."""

    def test_init_creates_db(self, tmp_path):
        """Should create database file on initialization."""
        db_path = tmp_path / "test.db"
        store = SQLiteVectorStore(db_path)
        assert db_path.exists()
        assert store.db_path == db_path

    def test_init_creates_parent_dirs(self, tmp_path):
        """Should create parent directories if they don't exist."""
        db_path = tmp_path / "nested" / "dirs" / "test.db"
        store = SQLiteVectorStore(db_path)
        assert db_path.exists()
        assert store.db_path == db_path

    def test_init_default_path(self, mock_home):
        """Should use default path ~/.null/rag.db when none provided."""
        store = SQLiteVectorStore()
        expected_path = mock_home / ".null" / "rag.db"
        assert store.db_path == expected_path
        assert expected_path.exists()

    def test_init_creates_tables(self, tmp_path):
        """Should create all required tables."""
        import sqlite3

        db_path = tmp_path / "test.db"
        SQLiteVectorStore(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor}

        assert "documents" in tables
        assert "embeddings" in tables
        assert "query_cache" in tables
        assert "file_index" in tables
        assert "documents_fts" in tables


class TestSQLiteVectorStoreAddDocument:
    """Tests for adding documents to SQLiteVectorStore."""

    def test_add_document(self, tmp_path):
        """Should add a document to the store."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        doc = Document(
            id="doc1", source="file.txt", content="test content", chunk_index=0
        )

        store.add_document(doc)

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, source, content FROM documents WHERE id = ?", ("doc1",)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "doc1"
        assert row[1] == "file.txt"
        assert row[2] == "test content"

    def test_add_document_replaces_existing(self, tmp_path):
        """Should replace document if ID already exists."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        doc1 = Document(id="doc1", source="file.txt", content="original", chunk_index=0)
        doc2 = Document(id="doc1", source="file.txt", content="updated", chunk_index=0)

        store.add_document(doc1)
        store.add_document(doc2)

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE id = ?", ("doc1",)
            )
            count = cursor.fetchone()[0]
            cursor = conn.execute(
                "SELECT content FROM documents WHERE id = ?", ("doc1",)
            )
            content = cursor.fetchone()[0]

        assert count == 1
        assert content == "updated"

    def test_add_via_vectorstore_interface(self, tmp_path):
        """Should add DocumentChunk objects via VectorStore-compatible add method."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        chunk = DocumentChunk(
            id="chunk1", content="test", source="file.txt", vector=[1.0, 0.0]
        )

        store.add([chunk])

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, content FROM documents WHERE id = ?", ("chunk1",)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "chunk1"
        assert row[1] == "test"


class TestSQLiteVectorStoreAddEmbedding:
    """Tests for adding embeddings to SQLiteVectorStore."""

    def test_add_embedding(self, tmp_path):
        """Should add embedding for a document."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        doc = Document(id="doc1", source="file.txt", content="test", chunk_index=0)
        store.add_document(doc)

        vector = [0.1, 0.2, 0.3]
        store.add_embedding("doc1", vector, "test-model")

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute(
                "SELECT vector, model FROM embeddings WHERE doc_id = ?", ("doc1",)
            )
            row = cursor.fetchone()

        assert row is not None
        stored_vector = json.loads(row[0].decode("utf-8"))
        assert stored_vector == vector
        assert row[1] == "test-model"

    def test_add_embedding_replaces_existing(self, tmp_path):
        """Should replace embedding if one already exists for the document."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        doc = Document(id="doc1", source="file.txt", content="test", chunk_index=0)
        store.add_document(doc)

        store.add_embedding("doc1", [0.1, 0.2], "model1")
        store.add_embedding("doc1", [0.3, 0.4], "model2")

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM embeddings WHERE doc_id = ?", ("doc1",)
            )
            count = cursor.fetchone()[0]
            cursor = conn.execute(
                "SELECT model FROM embeddings WHERE doc_id = ?", ("doc1",)
            )
            model = cursor.fetchone()[0]

        assert count == 1
        assert model == "model2"


class TestSQLiteVectorStoreVectorSearch:
    """Tests for vector similarity search."""

    def test_search_vector_empty_store(self, tmp_path):
        """Should return empty list when store is empty."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        results = store.search_vector([1.0, 0.0], limit=5)
        assert results == []

    def test_search_vector_empty_query(self, tmp_path):
        """Should return empty list when query vector is empty."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        doc = Document(id="doc1", source="file.txt", content="test", chunk_index=0)
        store.add_document(doc)
        store.add_embedding("doc1", [1.0, 0.0], "model")

        results = store.search_vector([], limit=5)
        assert results == []

    def test_search_vector_zero_magnitude(self, tmp_path):
        """Should return empty list when query vector has zero magnitude."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        doc = Document(id="doc1", source="file.txt", content="test", chunk_index=0)
        store.add_document(doc)
        store.add_embedding("doc1", [1.0, 0.0], "model")

        results = store.search_vector([0.0, 0.0], limit=5)
        assert results == []

    def test_search_vector_basic(self, tmp_path):
        """Should find similar documents by vector."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        doc1 = Document(
            id="doc1", source="file1.txt", content="python programming", chunk_index=0
        )
        doc2 = Document(
            id="doc2", source="file2.txt", content="javascript coding", chunk_index=0
        )

        store.add_document(doc1)
        store.add_document(doc2)
        store.add_embedding("doc1", [1.0, 0.0, 0.0], "model")
        store.add_embedding("doc2", [0.0, 1.0, 0.0], "model")

        results = store.search_vector([1.0, 0.0, 0.0], limit=2)

        assert len(results) == 2
        assert results[0][0].id == "doc1"
        assert results[0][1] > 0.99

    def test_search_vector_respects_limit(self, tmp_path):
        """Should respect the limit parameter."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        for i in range(10):
            doc = Document(
                id=f"doc{i}",
                source=f"file{i}.txt",
                content=f"content {i}",
                chunk_index=0,
            )
            store.add_document(doc)
            store.add_embedding(f"doc{i}", [float(i), 1.0], "model")

        results = store.search_vector([5.0, 1.0], limit=3)
        assert len(results) == 3

    def test_search_via_vectorstore_interface(self, tmp_path):
        """Should work via VectorStore-compatible search method."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        chunk = DocumentChunk(
            id="chunk1", content="test", source="file.txt", vector=[1.0, 0.0]
        )
        store.add([chunk])

        results = store.search([1.0, 0.0], limit=5)

        assert len(results) == 1
        assert results[0][0].id == "chunk1"
        assert results[0][1] > 0.99


class TestSQLiteVectorStoreFTSSearch:
    """Tests for full-text search."""

    def test_search_fts_empty_store(self, tmp_path):
        """Should return empty list when store is empty."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        results = store.search_fts("python", limit=5)
        assert results == []

    def test_search_fts_basic(self, tmp_path):
        """Should find documents by text content when using integer IDs."""
        import sqlite3

        store = SQLiteVectorStore(tmp_path / "test.db")

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute("SELECT rowid FROM documents")
            initial_count = len(cursor.fetchall())

        doc1 = Document(
            id=str(initial_count + 1),
            source="file1.txt",
            content="python programming language",
            chunk_index=0,
        )
        doc2 = Document(
            id=str(initial_count + 2),
            source="file2.txt",
            content="javascript web development",
            chunk_index=0,
        )

        store.add_document(doc1)
        store.add_document(doc2)

        results = store.search_fts("python", limit=5)

        assert len(results) == 1
        assert results[0].id == str(initial_count + 1)

    def test_search_fts_respects_limit(self, tmp_path):
        """Should respect the limit parameter."""
        import sqlite3

        store = SQLiteVectorStore(tmp_path / "test.db")

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute("SELECT rowid FROM documents")
            initial_count = len(cursor.fetchall())

        for i in range(10):
            doc = Document(
                id=str(initial_count + i + 1),
                source=f"file{i}.txt",
                content=f"common word item {i}",
                chunk_index=0,
            )
            store.add_document(doc)

        results = store.search_fts("common", limit=3)
        assert len(results) == 3


class TestSQLiteVectorStoreHybridSearch:
    """Tests for hybrid (vector + FTS) search."""

    def test_hybrid_search_combines_results(self, tmp_path):
        """Should combine vector and FTS results with weighted scoring."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        doc1 = Document(
            id="doc1",
            source="file1.txt",
            content="python machine learning",
            chunk_index=0,
        )
        doc2 = Document(
            id="doc2",
            source="file2.txt",
            content="javascript web framework",
            chunk_index=0,
        )

        store.add_document(doc1)
        store.add_document(doc2)
        store.add_embedding("doc1", [1.0, 0.0], "model")
        store.add_embedding("doc2", [0.0, 1.0], "model")

        results = store.hybrid_search(
            query="python",
            query_vector=[1.0, 0.0],
            limit=2,
            vector_weight=0.5,
            fts_weight=0.5,
        )

        assert len(results) >= 1
        assert results[0][0].id == "doc1"


class TestSQLiteVectorStoreQueryCache:
    """Tests for query caching."""

    def test_cache_query(self, tmp_path):
        """Should cache query results."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        results = [("doc1", 0.95), ("doc2", 0.80)]
        store.cache_query("test query", results)

        cached = store.get_cached_query("test query")
        assert cached == [["doc1", 0.95], ["doc2", 0.80]]

    def test_get_cached_query_miss(self, tmp_path):
        """Should return None for uncached queries."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        cached = store.get_cached_query("nonexistent query")
        assert cached is None

    def test_cache_hit_increments_count(self, tmp_path):
        """Should increment hit count on cache access."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        store.cache_query("test query", [("doc1", 0.9)])
        store.get_cached_query("test query")
        store.get_cached_query("test query")

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            cursor = conn.execute("SELECT hit_count FROM query_cache")
            hit_count = cursor.fetchone()[0]

        assert hit_count == 2


class TestSQLiteVectorStoreFileIndex:
    """Tests for file indexing tracking."""

    def test_needs_reindex_new_file(self, tmp_path):
        """Should return True for files not yet indexed."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        assert store.needs_reindex(str(test_file)) is True

    def test_needs_reindex_unchanged_file(self, tmp_path):
        """Should return False for unchanged indexed files."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        mtime = test_file.stat().st_mtime
        file_hash = store._hash_file(test_file)
        store.mark_indexed(str(test_file), mtime, file_hash)

        assert store.needs_reindex(str(test_file)) is False

    def test_needs_reindex_modified_file(self, tmp_path):
        """Should return True for modified files."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        mtime = test_file.stat().st_mtime
        file_hash = store._hash_file(test_file)
        store.mark_indexed(str(test_file), mtime, file_hash)

        test_file.write_text("modified content")

        assert store.needs_reindex(str(test_file)) is True

    def test_needs_reindex_nonexistent_file(self, tmp_path):
        """Should return False for nonexistent files."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        assert store.needs_reindex(str(tmp_path / "nonexistent.txt")) is False

    def test_hash_file_error_handling(self, tmp_path):
        """Should return empty string for unreadable files."""
        result = SQLiteVectorStore._hash_file(tmp_path / "nonexistent.txt")
        assert result == ""


class TestSQLiteVectorStoreClear:
    """Tests for clearing the store."""

    def test_clear_removes_all_data(self, tmp_path):
        """Should remove all data from all tables."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        doc = Document(id="doc1", source="file.txt", content="test", chunk_index=0)
        store.add_document(doc)
        store.add_embedding("doc1", [1.0, 0.0], "model")
        store.cache_query("query", [("doc1", 0.9)])

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        store.mark_indexed(str(test_file), test_file.stat().st_mtime, "hash")

        store.clear()

        import sqlite3

        with sqlite3.connect(store.db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM query_cache").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM file_index").fetchone()[0] == 0


class TestSQLiteVectorStoreStats:
    """Tests for store statistics."""

    def test_stats_empty_store(self, tmp_path):
        """Should return zero counts for empty store."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        stats = store.stats()

        assert stats["total_chunks"] == 0
        assert stats["total_vectors"] == 0
        assert stats["total_documents"] == 0
        assert stats["index_size_mb"] >= 0

    def test_stats_with_data(self, tmp_path):
        """Should return correct counts for populated store."""
        store = SQLiteVectorStore(tmp_path / "test.db")

        doc1 = Document(id="doc1", source="file.txt", content="test1", chunk_index=0)
        doc2 = Document(id="doc2", source="file.txt", content="test2", chunk_index=1)
        doc3 = Document(id="doc3", source="other.txt", content="test3", chunk_index=0)

        store.add_document(doc1)
        store.add_document(doc2)
        store.add_document(doc3)
        store.add_embedding("doc1", [1.0], "model")
        store.add_embedding("doc2", [2.0], "model")

        stats = store.stats()

        assert stats["total_chunks"] == 3
        assert stats["total_vectors"] == 2
        assert stats["total_documents"] == 2
        assert stats["index_size_mb"] > 0


class TestSQLiteVectorStorePersistence:
    """Tests for data persistence."""

    def test_data_persists_across_instances(self, tmp_path):
        """Data should persist when creating new store instance."""
        db_path = tmp_path / "test.db"

        store1 = SQLiteVectorStore(db_path)
        doc = Document(
            id="doc1", source="file.txt", content="persistent content", chunk_index=0
        )
        store1.add_document(doc)
        store1.add_embedding("doc1", [1.0, 2.0, 3.0], "test-model")

        store2 = SQLiteVectorStore(db_path)

        results = store2.search_vector([1.0, 2.0, 3.0], limit=1)
        assert len(results) == 1
        assert results[0][0].id == "doc1"
        assert results[0][0].content == "persistent content"


class TestSemanticCache:
    """Tests for SemanticCache."""

    def test_get_exact_match(self, tmp_path):
        """Should return cached results for exact query match."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        cache = SemanticCache(store, threshold=0.9)

        store.cache_query("test query", [("doc1", 0.95)])

        result = asyncio.get_event_loop().run_until_complete(
            cache.get("test query", [1.0, 0.0])
        )

        assert result == [["doc1", 0.95]]

    def test_get_no_match(self, tmp_path):
        """Should return None when no matching query found."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        cache = SemanticCache(store, threshold=0.9)

        result = asyncio.get_event_loop().run_until_complete(
            cache.get("unknown query", [1.0, 0.0])
        )

        assert result is None

    def test_set_caches_results(self, tmp_path):
        """Should cache query results."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        cache = SemanticCache(store, threshold=0.9)

        results = [("doc1", 0.9)]
        asyncio.get_event_loop().run_until_complete(
            cache.set("test query", [1.0, 0.0], results)
        )

        cached = store.get_cached_query("test query")
        assert cached == [["doc1", 0.9]]

    def test_string_similarity(self):
        """Should calculate Jaccard string similarity."""
        similarity = SemanticCache._string_similarity(
            "hello world test", "hello world example"
        )

        assert abs(similarity - 0.5) < 0.01

    def test_string_similarity_identical(self):
        """Should return 1.0 for identical strings."""
        similarity = SemanticCache._string_similarity("hello world", "hello world")
        assert similarity == 1.0

    def test_string_similarity_empty(self):
        """Should return 0.0 for empty strings."""
        assert SemanticCache._string_similarity("", "hello") == 0.0
        assert SemanticCache._string_similarity("hello", "") == 0.0
        assert SemanticCache._string_similarity("", "") == 0.0


class TestMigrateJsonToSqlite:
    """Tests for JSON to SQLite migration."""

    def test_migrate_empty_file(self, tmp_path):
        """Should handle empty JSON file."""
        json_path = tmp_path / "index.json"
        json_path.write_text("[]")

        store = SQLiteVectorStore(tmp_path / "test.db")
        count = migrate_json_to_sqlite(json_path, store)

        assert count == 0

    def test_migrate_nonexistent_file(self, tmp_path):
        """Should return 0 for nonexistent file."""
        store = SQLiteVectorStore(tmp_path / "test.db")
        count = migrate_json_to_sqlite(tmp_path / "nonexistent.json", store)
        assert count == 0

    def test_migrate_with_data(self, tmp_path):
        """Should migrate documents from JSON to SQLite."""
        json_path = tmp_path / "index.json"
        json_data = [
            {
                "id": "doc1",
                "content": "test content",
                "source": "file1.txt",
                "vector": [1.0, 0.0],
            },
            {
                "id": "doc2",
                "content": "more content",
                "source": "file2.txt",
                "vector": [0.0, 1.0],
            },
        ]
        json_path.write_text(json.dumps(json_data))

        store = SQLiteVectorStore(tmp_path / "test.db")
        count = migrate_json_to_sqlite(json_path, store)

        assert count == 2

        results = store.search_vector([1.0, 0.0], limit=2)
        assert len(results) == 2

    def test_migrate_invalid_json(self, tmp_path):
        """Should return 0 for invalid JSON."""
        json_path = tmp_path / "index.json"
        json_path.write_text("not valid json {{{")

        store = SQLiteVectorStore(tmp_path / "test.db")
        count = migrate_json_to_sqlite(json_path, store)

        assert count == 0

    def test_migrate_with_missing_fields(self, tmp_path):
        """Should migrate entries using defaults for missing optional fields."""
        json_path = tmp_path / "index.json"
        json_data = [
            {"id": "doc1", "content": "valid", "source": "file.txt"},
            {"content": "missing id"},
            {"id": "doc2", "content": "also valid", "source": "file2.txt"},
        ]
        json_path.write_text(json.dumps(json_data))

        store = SQLiteVectorStore(tmp_path / "test.db")
        count = migrate_json_to_sqlite(json_path, store)

        assert count == 3
