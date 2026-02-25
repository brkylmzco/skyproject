"""AST-based code chunker that splits Python files into function/class/module-level chunks."""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Optional

from skyproject.shared.vector_store import CodeChunk

logger = logging.getLogger(__name__)


class CodeChunker:
    """Parses Python source files and produces indexable CodeChunk objects."""

    def __init__(self, project_root: Optional[Path] = None):
        from skyproject.core.config import PROJECT_ROOT
        self.project_root = project_root or PROJECT_ROOT

    def chunk_file(self, file_path: str, content: Optional[str] = None) -> list[CodeChunk]:
        """Parse a single Python file into chunks."""
        if content is None:
            full_path = self.project_root / file_path if not Path(file_path).is_absolute() else Path(file_path)
            try:
                content = full_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Cannot read %s: %s", file_path, e)
                return []

        rel_path = self._relative_path(file_path)

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning("Syntax error in %s: %s", rel_path, e)
            return [CodeChunk(
                file_path=rel_path,
                content=content,
                chunk_type="module",
                name=Path(rel_path).stem,
                start_line=1,
                end_line=content.count("\n") + 1,
            )]

        lines = content.splitlines()
        chunks: list[CodeChunk] = []
        top_level_ranges: list[tuple[int, int]] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                chunk = self._extract_class(node, lines, rel_path)
                chunks.append(chunk)
                top_level_ranges.append((node.lineno, node.end_lineno or node.lineno))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = self._extract_function(node, lines, rel_path)
                chunks.append(chunk)
                top_level_ranges.append((node.lineno, node.end_lineno or node.lineno))

        module_lines = self._get_module_level_lines(lines, top_level_ranges)
        if module_lines.strip():
            chunks.insert(0, CodeChunk(
                file_path=rel_path,
                content=module_lines,
                chunk_type="module_header",
                name=f"{Path(rel_path).stem}::imports",
                start_line=1,
                end_line=len(lines),
            ))

        return chunks

    def chunk_directory(self, directory: str, pattern: str = "*.py") -> list[CodeChunk]:
        """Chunk all Python files in a directory recursively."""
        dir_path = self.project_root / directory if not Path(directory).is_absolute() else Path(directory)
        all_chunks: list[CodeChunk] = []

        if not dir_path.exists():
            logger.warning("Directory not found: %s", dir_path)
            return all_chunks

        for py_file in sorted(dir_path.rglob(pattern)):
            if "__pycache__" in str(py_file) or any(p.startswith(".") for p in py_file.parts):
                continue
            rel = str(py_file.relative_to(self.project_root))
            all_chunks.extend(self.chunk_file(rel))

        logger.info("Chunked %d files from %s -> %d chunks", len(list(dir_path.rglob(pattern))), directory, len(all_chunks))
        return all_chunks

    def chunk_module(self, module_name: str) -> list[CodeChunk]:
        """Chunk a SkyProject module (pm_ai, irgat_ai, core, shared)."""
        return self.chunk_directory(f"skyproject/{module_name}")

    def _extract_class(self, node: ast.ClassDef, lines: list[str], file_path: str) -> CodeChunk:
        end_line = node.end_lineno or node.lineno
        content = "\n".join(lines[node.lineno - 1 : end_line])

        decorators = ""
        if node.decorator_list:
            first_dec_line = node.decorator_list[0].lineno
            decorators = "\n".join(lines[first_dec_line - 1 : node.lineno - 1]) + "\n"
            content = decorators + content

        return CodeChunk(
            file_path=file_path,
            content=content,
            chunk_type="class",
            name=node.name,
            start_line=node.decorator_list[0].lineno if node.decorator_list else node.lineno,
            end_line=end_line,
        )

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, lines: list[str], file_path: str) -> CodeChunk:
        end_line = node.end_lineno or node.lineno
        content = "\n".join(lines[node.lineno - 1 : end_line])

        decorators = ""
        if node.decorator_list:
            first_dec_line = node.decorator_list[0].lineno
            decorators = "\n".join(lines[first_dec_line - 1 : node.lineno - 1]) + "\n"
            content = decorators + content

        return CodeChunk(
            file_path=file_path,
            content=content,
            chunk_type="function",
            name=node.name,
            start_line=node.decorator_list[0].lineno if node.decorator_list else node.lineno,
            end_line=end_line,
        )

    def _get_module_level_lines(self, lines: list[str], class_func_ranges: list[tuple[int, int]]) -> str:
        """Extract imports, constants, and other module-level code outside classes/functions."""
        occupied = set()
        for start, end in class_func_ranges:
            occupied.update(range(start, end + 1))

        module_lines = []
        for i, line in enumerate(lines, 1):
            if i not in occupied:
                module_lines.append(line)

        return "\n".join(module_lines)

    def _relative_path(self, file_path: str) -> str:
        p = Path(file_path)
        if p.is_absolute():
            try:
                return str(p.relative_to(self.project_root))
            except ValueError:
                return str(p)
        return file_path
