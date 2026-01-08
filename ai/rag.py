"""RAG (Retrieval-Augmented Generation) System."""

import json
import math
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from config import Config


import asyncio


@dataclass
class DocumentChunk:
    id: str
    content: str
    source: str
    vector: list[float] | None = None


class IndexStats(TypedDict):
    total_documents: int
    total_chunks: int
    total_vectors: int
    index_size_mb: float


class VectorStore:
    """Simple in-memory vector store with JSON persistence."""

    def __init__(self, path: Path):
        self.path = path
        self.chunks: list[DocumentChunk] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            return

        try:
            data = json.loads(self.path.read_text())
            for item in data:
                self.chunks.append(DocumentChunk(**item))
        except Exception:
            pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"id": c.id, "content": c.content, "source": c.source, "vector": c.vector}
            for c in self.chunks
        ]
        self.path.write_text(json.dumps(data))

    def clear(self):
        self.chunks = []
        if self.path.exists():
            self.path.unlink()

    def add(self, chunks: list[DocumentChunk]):
        self.chunks.extend(chunks)
        self.save()

    def search(
        self, query_vector: list[float], limit: int = 5
    ) -> list[tuple[DocumentChunk, float]]:
        """Cosine similarity search."""
        if not self.chunks or not query_vector:
            return []

        results = []

        # Pure Python cosine similarity to avoid heavy dependencies like numpy
        # Optimization: pre-calculate magnitude of query_vector
        q_mag = math.sqrt(sum(x * x for x in query_vector))
        if q_mag == 0:
            return []

        for chunk in self.chunks:
            if not chunk.vector:
                continue

            # Dot product
            dot = sum(a * b for a, b in zip(query_vector, chunk.vector))

            # Magnitude of chunk vector
            c_mag = math.sqrt(sum(x * x for x in chunk.vector))

            if c_mag == 0:
                similarity = 0.0
            else:
                similarity = dot / (q_mag * c_mag)

            results.append((chunk, similarity))

        # Sort by similarity desc
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def stats(self) -> IndexStats:
        size_bytes = self.path.stat().st_size if self.path.exists() else 0
        vectors = sum(1 for c in self.chunks if c.vector)
        unique_docs = len(set(c.source for c in self.chunks))

        return {
            "total_documents": unique_docs,
            "total_chunks": len(self.chunks),
            "total_vectors": vectors,
            "index_size_mb": round(size_bytes / (1024 * 1024), 2),
        }


class Chunker:
    """Simple text chunker."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> list[str]:
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size

            # Try to find a nice break point (newline or space)
            if end < text_len:
                # Look back for newline
                last_newline = text.rfind("\n", start, end)
                if last_newline != -1 and last_newline > start + (
                    self.chunk_size * 0.5
                ):
                    end = last_newline + 1
                else:
                    # Look back for space
                    last_space = text.rfind(" ", start, end)
                    if last_space != -1 and last_space > start + (
                        self.chunk_size * 0.5
                    ):
                        end = last_space + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.overlap
            # Prevent infinite loop if overlap >= chunk_size or no progress
            if start >= end:
                start = end

        return chunks


class RAGManager:
    """Manages indexing and retrieval."""

    def __init__(self):
        self.store = VectorStore(Path.home() / ".null" / "index.json")
        self.chunker = Chunker()
        # Default ignore patterns
        self.ignore_patterns = [
            ".git*",
            "__pycache__*",
            "*.pyc",
            "node_modules*",
            ".venv*",
            "dist*",
            "build*",
            "*.lock",
            "*.png",
            "*.jpg",
            "*.svg",
        ]

    async def index_directory(self, path: Path, provider, status_callback=None) -> int:
        """Index a directory recursively (async non-blocking)."""
        import time

        files_indexed = 0
        chunks_to_add = []
        last_update = 0.0
        embedding_errors = 0

        if not path.exists():
            return 0

        # Collect files in thread to prevent blocking on large trees
        files = await asyncio.to_thread(self._collect_files, path)

        for file_path in files:
            try:
                # Read and chunk in thread
                content = await asyncio.to_thread(file_path.read_text, errors="ignore")
                if not content.strip():
                    continue

                chunks = await asyncio.to_thread(self.chunker.split_text, content)

                for i, chunk_text in enumerate(chunks):
                    vector = await provider.embed_text(chunk_text)
                    if vector:
                        chunks_to_add.append(
                            DocumentChunk(
                                id=f"{file_path.name}:{i}",
                                content=chunk_text,
                                source=str(file_path),
                                vector=vector,
                            )
                        )
                    else:
                        embedding_errors += 1

                    await asyncio.sleep(0.001)

                files_indexed += 1

                # Incrementally save every 10 files to keep status updated
                if len(chunks_to_add) > 50 or files_indexed % 10 == 0:
                    batch = list(chunks_to_add)  # Copy
                    chunks_to_add.clear()
                    await asyncio.to_thread(self.store.add, batch)

                # Throttle updates to once per second
                now = time.time()
                if status_callback and (now - last_update > 1.0):
                    error_msg = (
                        f" ({embedding_errors} errs)" if embedding_errors else ""
                    )
                    status_callback(
                        f"Indexing... {files_indexed}/{len(files)} files{error_msg}"
                    )
                    last_update = now
                    # Force a UI refresh cycle
                    await asyncio.sleep(0.01)

            except Exception:
                continue

        if chunks_to_add:
            await asyncio.to_thread(self.store.add, chunks_to_add)

        if status_callback and embedding_errors > 0:
            status_callback(
                f"Warning: {embedding_errors} embedding failures - check provider supports embeddings"
            )

        return files_indexed

    def _collect_files(self, path: Path) -> list[Path]:
        """Helper to collect files synchronously (run in thread)."""
        files = []
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(fnmatch.fnmatch(file_path.name, p) for p in self.ignore_patterns):
                continue
            # Skip hidden directories (like .git) manually if rglob didn't catch them
            if any(p.startswith(".") for p in file_path.parts):
                continue
            if file_path.stat().st_size > 1_000_000:
                continue
            files.append(file_path)
        return files

    async def search(self, query: str, provider, limit: int = 5) -> list[DocumentChunk]:
        """Search the index."""
        vector = await provider.embed_text(query)
        if not vector:
            return []

        results = self.store.search(vector, limit)
        return [r[0] for r in results]

    def get_stats(self) -> IndexStats:
        return self.store.stats()

    def clear(self):
        self.store.clear()
