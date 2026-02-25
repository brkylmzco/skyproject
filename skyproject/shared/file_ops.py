from __future__ import annotations

import os
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from aiofiles.os import wrap

from skyproject.shared.logging_utils import log_error, log_warning, log_info, ErrorCode

PROJECT_ROOT = Path(__file__).parent.parent.parent

async def read_file(path: str) -> Optional[str]:
    """Read a file's contents with robust error handling and retries."""
    full_path = _resolve_path(path)
    if not full_path.exists():
        log_warning(f"File not found: {full_path}")
        return None
    return await _retry_operation(_read_file, full_path)

async def _read_file(full_path: Path) -> str:
    async with aiofiles.open(full_path, "r") as f:
        return await f.read()

async def write_file(path: str, content: str) -> bool:
    """Write content to a file with robust error handling and retries."""
    full_path = _resolve_path(path)
    full_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if full_path.exists():
        backup_path = full_path.with_suffix(full_path.suffix + ".bak")
        shutil.copy2(full_path, backup_path)

    success = await _retry_operation(_write_file, full_path, content)

    if success and backup_path and backup_path.exists():
        backup_path.unlink()

    return success

async def _write_file(full_path: Path, content: str) -> None:
    async with aiofiles.open(full_path, "w") as f:
        await f.write(content)

async def delete_file(path: str) -> bool:
    """Delete a file with error handling."""
    full_path = _resolve_path(path)
    if full_path.exists():
        try:
            full_path.unlink()
            return True
        except OSError as e:
            log_error(ErrorCode.REQUEST_EXCEPTION, f"Failed to delete file {full_path}: {str(e)}")
            return False
    log_warning(f"File not found for deletion: {full_path}")
    return False

async def list_files(directory: str, pattern: str = "*.py") -> list[str]:
    """List files matching a pattern in a directory with error handling."""
    full_path = _resolve_path(directory)
    if not full_path.exists():
        log_warning(f"Directory not found: {full_path}")
        return []
    try:
        return [
            str(p.relative_to(PROJECT_ROOT))
            for p in full_path.rglob(pattern)
            if not any(part.startswith(".") for part in p.parts)
            and "__pycache__" not in str(p)
        ]
    except OSError as e:
        log_error(ErrorCode.REQUEST_EXCEPTION, f"Failed to list files in {full_path}: {str(e)}")
        return []

async def get_module_source(module_path: str) -> dict[str, str]:
    """Get all Python source files in a module as a dict of path -> content."""
    files = await list_files(module_path, "*.py")
    result = {}
    for f in files:
        content = await read_file(f)
        if content is not None:
            result[f] = content
    return result

async def save_snapshot(module_path: str, label: str) -> str:
    """Save a snapshot of a module for rollback purposes."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = PROJECT_ROOT / "data" / "improvements" / f"{label}_{timestamp}"
    source_dir = _resolve_path(module_path)

    if source_dir.exists():
        try:
            shutil.copytree(source_dir, snapshot_dir, dirs_exist_ok=True)
            log_info(f"Snapshot saved at {snapshot_dir}")
        except OSError as e:
            log_error(ErrorCode.REQUEST_EXCEPTION, f"Failed to save snapshot for {module_path}: {str(e)}")

    return str(snapshot_dir)

async def _retry_operation(func, *args, retries: int = 3, delay: float = 1.0, **kwargs) -> Optional[bool]:
    """Retry a file operation with exponential backoff."""
    attempt = 0
    while attempt < retries:
        try:
            await func(*args, **kwargs)
            return True
        except (OSError, aiofiles.threadpool.errors.ThreadPoolOSError) as e:
            attempt += 1
            log_warning(f"Attempt {attempt}/{retries} failed due to: {str(e)}")
            if attempt < retries:
                await asyncio.sleep(delay * (2 ** (attempt - 1)))
            else:
                log_error(ErrorCode.REQUEST_EXCEPTION, f"Max retries reached for operation: {str(e)}")
                return False


def _resolve_path(path: str) -> Path:
    """Resolve a path relative to project root."""
    p = Path(path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p
