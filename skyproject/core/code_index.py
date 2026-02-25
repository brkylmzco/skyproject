"""Code index manager - bridges chunker and vector store for the entire system."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from skyproject.shared.code_chunker import CodeChunker
from skyproject.shared.vector_store import CodeVectorStore, SearchResult

logger = logging.getLogger(__name__)


class CodeIndex:
    """Central code index used by both PM AI and IrgatAI to query the codebase efficiently."""

    def __init__(self, project_root: Optional[Path] = None):
        self.store = CodeVectorStore()
        self.chunker = CodeChunker(project_root=project_root)
        self._indexed = False

    def index_module(self, module_name: str) -> int:
        """Index a single module (pm_ai, irgat_ai, core, shared)."""
        chunks = self.chunker.chunk_module(module_name)
        return self.store.index_chunks(chunks)

    def index_all(self) -> int:
        """Index the entire SkyProject codebase."""
        total = 0
        for module in ("pm_ai", "irgat_ai", "core", "shared"):
            total += self.index_module(module)
        self._indexed = True
        logger.info("Full index complete: %d chunks total in store", self.store.count)
        return total

    def index_directory(self, directory: str) -> int:
        """Index an arbitrary directory (for target project support)."""
        chunks = self.chunker.chunk_directory(directory)
        return self.store.index_chunks(chunks)

    def index_file(self, file_path: str, content: Optional[str] = None) -> int:
        """Re-index a single file after changes."""
        self.store.remove_file(file_path)
        chunks = self.chunker.chunk_file(file_path, content)
        return self.store.index_chunks(chunks)

    def ensure_indexed(self) -> None:
        """Index if not already done."""
        if not self._indexed and self.store.count == 0:
            self.index_all()

    def search(
        self,
        query: str,
        n_results: int = 10,
        module: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search for relevant code chunks."""
        self.ensure_indexed()
        if module:
            return self.store.search_by_module(module, query, n_results)
        return self.store.search(query, n_results)

    def get_context_for_task(self, task_description: str, module: Optional[str] = None, max_tokens: int = 3000) -> str:
        """Build a compact LLM context string from the most relevant chunks.

        Estimates ~4 chars per token and stops adding chunks when the budget is reached.
        """
        self.ensure_indexed()
        results = self.search(task_description, n_results=15, module=module)

        context_parts: list[str] = []
        char_budget = max_tokens * 4
        used = 0

        for r in results:
            entry = f"--- {r.file_path} :: {r.name} (L{r.start_line}-{r.end_line}, relevance={r.relevance_score:.2f}) ---\n{r.content}\n"
            if used + len(entry) > char_budget:
                break
            context_parts.append(entry)
            used += len(entry)

        return "\n".join(context_parts)

    def get_module_summary(self, module: str) -> str:
        """Get a structural summary of a module (classes/functions list)."""
        self.ensure_indexed()
        return self.store.get_module_summary(module)

    def remove_file(self, file_path: str) -> None:
        """Remove a file from the index."""
        self.store.remove_file(file_path)
