"""SQLite-based RAG storage with FTS5 and vector search."""

import asyncio
import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.rag import DocumentChunk


@dataclass
class Document:
    """Document representation for SQLite storage."""

    id: str
    source: str
    content: str
    chunk_index: int
    embedding: list[float] | None = None


class SQLiteVectorStore:
    """SQLite-based vector store with FTS5 for hybrid search."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        content TEXT NOT NULL,
        chunk_index INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS embeddings (
        doc_id TEXT PRIMARY KEY REFERENCES documents(id),
        vector BLOB NOT NULL,
        model TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
        content,
        content='documents',
        content_rowid='rowid'
    );

    CREATE TABLE IF NOT EXISTS query_cache (
        query_hash TEXT PRIMARY KEY,
        query_text TEXT,
        results TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        hit_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS file_index (
        path TEXT PRIMARY KEY,
        mtime REAL,
        hash TEXT
    );
    """

    def __init__(self, db_path: Path | None = None):
        """Initialize SQLite vector store.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.null/rag.db
        """
        self.db_path = db_path or Path.home() / ".null" / "rag.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    def add(self, chunks: list) -> None:
        """Add DocumentChunk objects to the store (VectorStore compatibility).

        Args:
            chunks: List of DocumentChunk objects
        """
        for chunk in chunks:
            doc = Document(
                id=chunk.id,
                source=chunk.source,
                content=chunk.content,
                chunk_index=0,
                embedding=chunk.vector,
            )
            self.add_document(doc)
            if chunk.vector:
                self.add_embedding(chunk.id, chunk.vector, "unknown")

    def add_document(self, doc: Document) -> None:
        """Add or update a document in the store.

        Args:
            doc: Document to add
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (id, source, content, chunk_index)
                VALUES (?, ?, ?, ?)
                """,
                (doc.id, doc.source, doc.content, doc.chunk_index),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO documents_fts (rowid, content)
                SELECT rowid, content FROM documents WHERE id = ?
                """,
                (doc.id,),
            )
            conn.commit()

    def add_embedding(self, doc_id: str, vector: list[float], model: str) -> None:
        """Add or update embedding for a document.

        Args:
            doc_id: Document ID
            vector: Embedding vector as list of floats
            model: Model name used to generate embedding
        """
        # Convert vector to binary blob
        vector_bytes = json.dumps(vector).encode("utf-8")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings (doc_id, vector, model)
                VALUES (?, ?, ?)
                """,
                (doc_id, vector_bytes, model),
            )
            conn.commit()

    def search_fts(self, query: str, limit: int = 10) -> list[Document]:
        """Full-text search using FTS5.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching documents
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT d.id, d.source, d.content, d.chunk_index
                FROM documents d
                WHERE d.id IN (
                    SELECT rowid FROM documents_fts WHERE documents_fts MATCH ?
                )
                LIMIT ?
                """,
                (query, limit),
            )
            results = []
            for row in cursor:
                doc = Document(
                    id=row[0],
                    source=row[1],
                    content=row[2],
                    chunk_index=row[3],
                )
                results.append(doc)
            return results

    def _doc_to_chunk(self, doc: Document):
        """Convert Document to DocumentChunk for compatibility."""

        return DocumentChunk(
            id=doc.id,
            content=doc.content,
            source=doc.source,
            vector=doc.embedding,
        )

    def search(self, query_vector: list[float], limit: int = 5) -> list[tuple]:
        """Vector similarity search (VectorStore compatibility).

        Args:
            query_vector: Query embedding vector
            limit: Maximum results to return

        Returns:
            List of (DocumentChunk-like, similarity_score) tuples
        """
        results = self.search_vector(query_vector, limit)
        return [(self._doc_to_chunk(doc), score) for doc, score in results]

    def search_vector(
        self, query_vector: list[float], limit: int = 10
    ) -> list[tuple[Document, float]]:
        """Vector similarity search using cosine similarity.

        Args:
            query_vector: Query embedding vector
            limit: Maximum results to return

        Returns:
            List of (Document, similarity_score) tuples
        """
        if not query_vector:
            return []

        # Pre-calculate query magnitude
        q_mag = math.sqrt(sum(x * x for x in query_vector))
        if q_mag == 0:
            return []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT d.id, d.source, d.content, d.chunk_index, e.vector
                FROM documents d
                LEFT JOIN embeddings e ON d.id = e.doc_id
                WHERE e.vector IS NOT NULL
                """
            )

            results = []
            for row in cursor:
                doc_id, source, content, chunk_index, vector_bytes = row
                try:
                    vector = json.loads(vector_bytes.decode("utf-8"))
                except (json.JSONDecodeError, AttributeError):
                    continue

                # Cosine similarity
                dot = sum(a * b for a, b in zip(query_vector, vector, strict=False))
                c_mag = math.sqrt(sum(x * x for x in vector))

                if c_mag == 0:
                    similarity = 0.0
                else:
                    similarity = dot / (q_mag * c_mag)

                doc = Document(
                    id=doc_id,
                    source=source,
                    content=content,
                    chunk_index=chunk_index,
                    embedding=vector,
                )
                results.append((doc, similarity))

            # Sort by similarity descending
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        limit: int = 10,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
    ) -> list[tuple[Document, float]]:
        """Combined vector + FTS search with weighted scoring.

        Args:
            query: Text query for FTS
            query_vector: Embedding vector for semantic search
            limit: Maximum results to return
            vector_weight: Weight for vector similarity (0-1)
            fts_weight: Weight for FTS relevance (0-1)

        Returns:
            List of (Document, combined_score) tuples
        """
        # Get results from both searches
        fts_results = self.search_fts(query, limit * 2)
        vector_results = self.search_vector(query_vector, limit * 2)

        # Create score maps
        fts_scores = {
            doc.id: (1.0 - i / len(fts_results)) for i, doc in enumerate(fts_results)
        }
        vector_scores = {doc.id: score for doc, score in vector_results}

        # Combine results
        combined = {}
        for doc in fts_results:
            combined[doc.id] = doc

        for doc, _ in vector_results:
            if doc.id not in combined:
                combined[doc.id] = doc

        # Calculate combined scores
        results = []
        for doc_id, doc in combined.items():
            fts_score = fts_scores.get(doc_id, 0.0)
            vector_score = vector_scores.get(doc_id, 0.0)
            combined_score = (vector_score * vector_weight) + (fts_score * fts_weight)
            results.append((doc, combined_score))

        # Sort by combined score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_cached_query(self, query: str) -> list[tuple[str, float]] | None:
        """Check query cache for results.

        Args:
            query: Query string

        Returns:
            Cached results as list of (doc_id, score) tuples, or None if not cached
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT results FROM query_cache WHERE query_hash = ?
                """,
                (query_hash,),
            )
            row = cursor.fetchone()
            if row:
                # Update hit count
                conn.execute(
                    """
                    UPDATE query_cache SET hit_count = hit_count + 1
                    WHERE query_hash = ?
                    """,
                    (query_hash,),
                )
                conn.commit()

                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return None

        return None

    def cache_query(self, query: str, results: list[tuple[str, float]]) -> None:
        """Cache query results.

        Args:
            query: Query string
            results: List of (doc_id, score) tuples
        """
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        results_json = json.dumps(results)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_cache (query_hash, query_text, results)
                VALUES (?, ?, ?)
                """,
                (query_hash, query, results_json),
            )
            conn.commit()

    def needs_reindex(self, path: str) -> bool:
        """Check if file needs reindexing based on mtime/hash.

        Args:
            path: File path

        Returns:
            True if file needs reindexing, False otherwise
        """
        file_path = Path(path)
        if not file_path.exists():
            return False

        current_mtime = file_path.stat().st_mtime
        current_hash = self._hash_file(file_path)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT mtime, hash FROM file_index WHERE path = ?
                """,
                (path,),
            )
            row = cursor.fetchone()

            if not row:
                return True

            stored_mtime, stored_hash = row
            return current_mtime != stored_mtime or current_hash != stored_hash

    def mark_indexed(self, path: str, mtime: float, file_hash: str) -> None:
        """Mark file as indexed.

        Args:
            path: File path
            mtime: File modification time
            file_hash: File content hash
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_index (path, mtime, hash)
                VALUES (?, ?, ?)
                """,
                (path, mtime, file_hash),
            )
            conn.commit()

    @staticmethod
    def _hash_file(path: Path, chunk_size: int = 8192) -> str:
        """Calculate SHA256 hash of file.

        Args:
            path: File path
            chunk_size: Chunk size for reading

        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
        except OSError:
            return ""
        return hasher.hexdigest()

    def clear(self) -> None:
        """Clear all data from the store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM embeddings")
            conn.execute("DELETE FROM query_cache")
            conn.execute("DELETE FROM file_index")
            conn.commit()

    def stats(self) -> dict[str, Any]:
        """Get store statistics.

        Returns:
            Dictionary with store statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            chunk_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            vector_count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            unique_sources = conn.execute(
                "SELECT COUNT(DISTINCT source) FROM documents"
            ).fetchone()[0]

        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_documents": unique_sources,
            "total_chunks": chunk_count,
            "total_vectors": vector_count,
            "index_size_mb": round(size_bytes / (1024 * 1024), 2),
        }


class SemanticCache:
    """Cache that uses semantic similarity to match queries."""

    def __init__(self, store: SQLiteVectorStore, threshold: float = 0.92):
        """Initialize semantic cache.

        Args:
            store: SQLiteVectorStore instance
            threshold: Similarity threshold for cache hits (0-1)
        """
        self.store = store
        self.threshold = threshold

    async def get(
        self, query: str, query_vector: list[float]
    ) -> list[tuple[str, float]] | None:
        """Find semantically similar cached query.

        Args:
            query: Query string
            query_vector: Query embedding vector

        Returns:
            Cached results if similar query found, None otherwise
        """
        # Run in thread to avoid blocking
        return await asyncio.to_thread(self._get_sync, query, query_vector)

    def _get_sync(
        self, query: str, query_vector: list[float]
    ) -> list[tuple[str, float]] | None:
        """Synchronous implementation of get.

        Args:
            query: Query string
            query_vector: Query embedding vector

        Returns:
            Cached results if similar query found, None otherwise
        """
        # First try exact match
        cached = self.store.get_cached_query(query)
        if cached:
            return cached

        # Then try semantic similarity on cached queries
        with sqlite3.connect(self.store.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT query_text, results FROM query_cache
                ORDER BY hit_count DESC
                LIMIT 100
                """
            )

            q_mag = math.sqrt(sum(x * x for x in query_vector))
            if q_mag == 0:
                return None

            for row in cursor:
                cached_query, results_json = row
                try:
                    # Try to embed cached query (would need provider)
                    # For now, just do string similarity as fallback
                    if self._string_similarity(query, cached_query) > self.threshold:
                        return json.loads(results_json)
                except (json.JSONDecodeError, AttributeError):
                    continue

        return None

    async def set(
        self, query: str, query_vector: list[float], results: list[tuple[str, float]]
    ) -> None:
        """Cache query results.

        Args:
            query: Query string
            query_vector: Query embedding vector
            results: List of (doc_id, score) tuples
        """
        # Run in thread to avoid blocking
        await asyncio.to_thread(self.store.cache_query, query, results)

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate simple string similarity (Jaccard).

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (0-1)
        """
        set1 = set(s1.lower().split())
        set2 = set(s2.lower().split())

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0


def migrate_json_to_sqlite(json_path: Path, sqlite_store: SQLiteVectorStore) -> int:
    """Migrate documents from JSON VectorStore to SQLite.

    Args:
        json_path: Path to JSON index file
        sqlite_store: Target SQLiteVectorStore instance

    Returns:
        Number of documents migrated
    """
    if not json_path.exists():
        return 0

    try:
        data = json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError):
        return 0

    migrated = 0
    for item in data:
        try:
            # Convert DocumentChunk format to Document format
            doc = Document(
                id=item.get("id", ""),
                source=item.get("source", ""),
                content=item.get("content", ""),
                chunk_index=0,
                embedding=item.get("vector"),
            )

            sqlite_store.add_document(doc)

            if doc.embedding:
                sqlite_store.add_embedding(doc.id, doc.embedding, "unknown")

            migrated += 1
        except (KeyError, TypeError, ValueError):
            continue

    return migrated
