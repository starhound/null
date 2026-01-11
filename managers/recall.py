import json
from pathlib import Path
from typing import Any

from ai.factory import AIFactory
from ai.rag import DocumentChunk, VectorStore
from config.storage import StorageManager
from models import BlockState


class RecallManager:
    """Manages semantic recall of past interactions."""

    def __init__(self):
        self.storage = StorageManager()
        self.ai_factory = AIFactory()
        self.vector_store = VectorStore(Path.home() / ".null" / "history_index.json")

    async def index_interaction(self, block: BlockState):
        """Index a completed block interaction."""
        if not block.content or not block.is_complete:
            return

        input_text = ""
        output_text = ""

        if block.type == "command":
            input_text = block.content
            output_text = block.content_output or ""
        elif block.type == "ai_response":
            output_text = block.content
            input_text = "AI Response"

        full_text = f"Input: {input_text}\nOutput: {output_text}".strip()
        if not full_text:
            return

        metadata = {
            "exit_code": block.exit_code,
            "model": block.model,
            "timestamp": block.timestamp.isoformat() if block.timestamp else None,
        }

        interaction_id = self.storage.add_interaction(
            type=block.type,
            input_text=input_text,
            output_text=output_text,
            metadata=json.dumps(metadata),
        )

        provider = await self._get_embedding_provider()
        if provider:
            try:
                vector = await provider.embed_text(full_text)
                if vector:
                    chunk = DocumentChunk(
                        id=str(interaction_id),
                        content=full_text,
                        source="history",
                        vector=vector,
                    )
                    self.vector_store.add([chunk])
            except Exception:
                pass

    async def _get_embedding_provider(self):
        """Get a provider capable of embeddings."""
        try:
            from ai.factory import AIFactory
            from config import Config
            from mcp.config import MCPConfig

            mcp_config = MCPConfig()
            profile_ai = mcp_config.get_active_ai_config()

            provider_name = None
            if profile_ai:
                provider_name = profile_ai.get("embedding_provider")

            if not provider_name:
                provider_name = Config.get("ai.embedding_provider", "ollama")

            model = None
            endpoint = None
            api_key = None

            if profile_ai and provider_name == profile_ai.get("embedding_provider"):
                model = profile_ai.get("embedding_model")
                endpoint = profile_ai.get("embedding_endpoint")

            if not model:
                model = Config.get(
                    f"ai.embedding.{provider_name}.model", "nomic-embed-text"
                )
            if not endpoint:
                endpoint = Config.get(
                    f"ai.embedding.{provider_name}.endpoint", "http://localhost:11434"
                )
            if not api_key:
                api_key = Config.get(
                    f"ai.embedding.{provider_name}.api_key"
                ) or Config.get(f"ai.{provider_name}.api_key", "")

            config = {
                "provider": provider_name,
                "model": model,
                "endpoint": endpoint,
                "api_key": api_key,
            }

            return AIFactory.get_provider(config)
        except Exception:
            return None

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search history using vector similarity."""
        results = []

        provider = await self._get_embedding_provider()
        if not provider:
            return self.storage.search_interactions(query, limit)

        query_vector = await provider.embed_text(query)
        if not query_vector:
            return self.storage.search_interactions(query, limit)

        vector_results = self.vector_store.search(query_vector, limit)

        for chunk, score in vector_results:
            results.append(
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "score": score,
                    "source": "vector",
                }
            )

        return results
