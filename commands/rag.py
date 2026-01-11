"""RAG / Knowledge Base commands."""

from pathlib import Path

from ai.rag import RAGManager
from managers.recall import RecallManager

from .base import CommandMixin


class RAGCommands(CommandMixin):
    """Commands for managing local knowledge base."""

    def __init__(self, app):
        self.app = app
        self.rag = RAGManager()
        self.recall = RecallManager()

    async def cmd_recall(self, args: list[str]):
        """Search interaction history.

        Usage:
            /recall <query>   Search past commands and responses
        """
        if not args:
            self.notify("Usage: /recall <query>", severity="error")
            return

        query = " ".join(args)
        results = await self.recall.search(query)

        if not results:
            self.notify("No matching interactions found.")
            return

        output = ["# Recall Results", ""]
        for i, res in enumerate(results, 1):
            score = res.get("score", 0)
            content = res.get("content", "")
            display_content = content[:500] + "..." if len(content) > 500 else content

            output.append(f"## {i}. Match (Score: {score:.2f})")
            output.append(f"```\n{display_content}\n```")
            output.append("")

        await self.show_output(f"Recall: {query}", "\n".join(output))

    async def cmd_index(self, args: list[str]):
        """Manage knowledge base index.

        Usage:
            /index status       Show index statistics
            /index build [path] Index current or specified directory
            /index search <q>   Test search retrieval
            /index clear        Clear the index
        """
        if not args:
            await self._show_status()
            return

        subcmd = args[0]

        if subcmd == "status":
            await self._show_status()

        elif subcmd == "build":
            path = Path(args[1]) if len(args) > 1 else Path.cwd()
            await self._build_index(path)

        elif subcmd == "search":
            if len(args) < 2:
                self.notify("Usage: /index search <query>", severity="error")
                return
            query = " ".join(args[1:])
            await self._search_index(query)

        elif subcmd == "clear":
            self.rag.clear()
            self.notify("Index cleared")

        else:
            self.notify(f"Unknown subcommand: {subcmd}", severity="error")

    async def _show_status(self):
        stats = self.rag.get_stats()
        output = [
            "# Index Status",
            f"- Documents: {stats['total_documents']}",
            f"- Chunks: {stats['total_chunks']}",
            f"- Vectors: {stats['total_vectors']}",
            f"- Size: {stats['index_size_mb']} MB",
            "",
            "Use `/index build` to index current directory.",
        ]
        await self.show_output("Index Status", "\n".join(output))

    async def _build_index(self, path: Path):
        provider = self.app.ai_provider
        if not provider:
            self.notify("No AI provider connected", severity="error")
            return

        self.notify(f"Indexing {path} in background...")

        async def do_index():
            count = await self.rag.index_directory(
                path, provider, status_callback=lambda msg: self.app.notify(msg)
            )
            stats = self.rag.get_stats()
            if stats["total_chunks"] == 0:
                self.app.notify(
                    "No content indexed - embeddings may have failed",
                    severity="warning",
                )
            else:
                self.app.notify(
                    f"Indexed {count} files, {stats['total_chunks']} chunks."
                )

        self.app.run_worker(do_index())

    async def _search_index(self, query: str):
        provider = self.app.ai_provider
        if not provider:
            self.notify("No AI provider connected", severity="error")
            return

        results = await self.rag.search(query, provider)
        if not results:
            self.notify("No matches found")
            return

        lines = ["# Search Results", ""]
        for i, chunk in enumerate(results, 1):
            lines.append(f"## {i}. {chunk.source}")
            lines.append(f"```\n{chunk.content}\n```")
            lines.append("")

        await self.show_output(f"Search: {query}", "\n".join(lines))
