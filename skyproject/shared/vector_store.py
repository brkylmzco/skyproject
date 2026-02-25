"""Vector store for code embeddings - reduces LLM costs by retrieving only relevant code chunks."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from skyproject.core.config import DATA_DIR

logger = logging.getLogger(__name__)

VECTOR_DB_DIR = DATA_DIR / "vector_db"
VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)


class CodeVectorStore:
    """ChromaDB-backed vector store with local embeddings for zero-cost retrieval."""

    def __init__(
        self,
        collection_name: str = "codebase",
        persist_dir: Optional[Path] = None,
    ):
        self._persist_dir = str(persist_dir or VECTOR_DB_DIR)
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._content_hashes: dict[str, str] = {}
        self._load_existing_hashes()

    def _load_existing_hashes(self) -> None:
        """Load content hashes from existing metadata to detect changes."""
        try:
            existing = self._collection.get(include=["metadatas"])
            if existing and existing["metadatas"]:
                for i, meta in enumerate(existing["metadatas"]):
                    if meta and "content_hash" in meta:
                        self._content_hashes[existing["ids"][i]] = meta["content_hash"]
        except Exception as e:
            logger.warning("Could not load existing hashes: %s", e)

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def index_chunks(self, chunks: list[CodeChunk]) -> int:
        """Index code chunks, skipping unchanged ones. Returns count of newly indexed."""
        new_chunks = []
        for chunk in chunks:
            content_hash = self._hash_content(chunk.content)
            if self._content_hashes.get(chunk.chunk_id) == content_hash:
                continue
            new_chunks.append((chunk, content_hash))

        if not new_chunks:
            return 0

        ids = [c.chunk_id for c, _ in new_chunks]
        documents = [c.content for c, _ in new_chunks]
        metadatas = [
            {
                "file_path": c.file_path,
                "chunk_type": c.chunk_type,
                "name": c.name,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content_hash": h,
                "module": c.module,
            }
            for c, h in new_chunks
        ]

        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        for chunk, h in new_chunks:
            self._content_hashes[chunk.chunk_id] = h

        logger.info("Indexed %d code chunks (skipped %d unchanged)", len(new_chunks), len(chunks) - len(new_chunks))
        return len(new_chunks)

    def search(
        self,
        query: str,
        n_results: int = 10,
        module_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search for relevant code chunks by semantic similarity."""
        where_filter = {}
        if module_filter:
            where_filter["module"] = module_filter
        if chunk_type_filter:
            where_filter["chunk_type"] = chunk_type_filter

        kwargs = {
            "query_texts": [query],
            "n_results": min(n_results, self._collection.count() or 1),
        }
        if where_filter:
            if len(where_filter) == 1:
                kwargs["where"] = where_filter
            else:
                kwargs["where"] = {"$and": [{k: v} for k, v in where_filter.items()]}

        try:
            results = self._collection.query(**kwargs)
        except Exception as e:
            logger.error("Vector search failed: %s", e)
            return []

        search_results = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0
                search_results.append(SearchResult(
                    content=doc,
                    file_path=meta.get("file_path", ""),
                    chunk_type=meta.get("chunk_type", ""),
                    name=meta.get("name", ""),
                    start_line=meta.get("start_line", 0),
                    end_line=meta.get("end_line", 0),
                    relevance_score=1.0 - distance,
                    module=meta.get("module", ""),
                ))

        return search_results

    def search_by_module(self, module: str, query: str, n_results: int = 10) -> list[SearchResult]:
        """Search within a specific module."""
        return self.search(query, n_results=n_results, module_filter=module)

    def get_module_summary(self, module: str) -> str:
        """Get a compact summary of a module's structure (class/function names only)."""
        try:
            results = self._collection.get(
                where={"module": module},
                include=["metadatas"],
            )
        except Exception:
            return ""

        if not results or not results["metadatas"]:
            return ""

        lines = []
        by_file: dict[str, list[dict]] = {}
        for meta in results["metadatas"]:
            fp = meta.get("file_path", "unknown")
            by_file.setdefault(fp, []).append(meta)

        for fp, metas in sorted(by_file.items()):
            lines.append(f"\n--- {fp} ---")
            for m in sorted(metas, key=lambda x: x.get("start_line", 0)):
                prefix = "class" if m.get("chunk_type") == "class" else "def"
                lines.append(f"  {prefix} {m.get('name', '?')} (L{m.get('start_line', '?')}-{m.get('end_line', '?')})")

        return "\n".join(lines)

    def remove_file(self, file_path: str) -> None:
        """Remove all chunks for a file (used when file is deleted)."""
        try:
            results = self._collection.get(where={"file_path": file_path})
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
                for cid in results["ids"]:
                    self._content_hashes.pop(cid, None)
        except Exception as e:
            logger.warning("Failed to remove file chunks for %s: %s", file_path, e)

    def clear(self) -> None:
        """Clear all indexed data."""
        try:
            self._client.delete_collection(self._collection.name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection.name,
                metadata={"hnsw:space": "cosine"},
            )
            self._content_hashes.clear()
        except Exception as e:
            logger.error("Failed to clear vector store: %s", e)

    @property
    def count(self) -> int:
        return self._collection.count()


class CodeChunk:
    """Represents a chunk of code (function, class, or module-level block)."""

    __slots__ = ("chunk_id", "file_path", "content", "chunk_type", "name", "start_line", "end_line", "module")

    def __init__(
        self,
        file_path: str,
        content: str,
        chunk_type: str,
        name: str,
        start_line: int,
        end_line: int,
        module: str = "",
    ):
        self.file_path = file_path
        self.content = content
        self.chunk_type = chunk_type
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.module = module or self._detect_module(file_path)
        self.chunk_id = f"{file_path}::{chunk_type}::{name}"

    @staticmethod
    def _detect_module(file_path: str) -> str:
        if "pm_ai" in file_path:
            return "pm_ai"
        if "irgat_ai" in file_path:
            return "irgat_ai"
        if "core" in file_path:
            return "core"
        if "shared" in file_path:
            return "shared"
        return "unknown"


class SearchResult:
    """Result from a vector similarity search."""

    __slots__ = ("content", "file_path", "chunk_type", "name", "start_line", "end_line", "relevance_score", "module")

    def __init__(
        self,
        content: str,
        file_path: str,
        chunk_type: str = "",
        name: str = "",
        start_line: int = 0,
        end_line: int = 0,
        relevance_score: float = 0.0,
        module: str = "",
    ):
        self.content = content
        self.file_path = file_path
        self.chunk_type = chunk_type
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.relevance_score = relevance_score
        self.module = module

    def __repr__(self) -> str:
        return f"SearchResult({self.file_path}::{self.name}, score={self.relevance_score:.3f})"
