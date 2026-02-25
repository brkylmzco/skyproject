from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import aiofiles
from aiofiles.os import wrap

from skyproject.core.config import TASKS_DIR, Config
from skyproject.shared.models import Task, TaskStatus


logger = logging.getLogger(__name__)

async_open = wrap(aiofiles.open)


class TaskStore:
    """File-based task persistence."""

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = store_dir or TASKS_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, task: Task) -> None:
        path = self.store_dir / f"{task.id}.json"
        await self._write_to_file(path, task.model_dump_json(indent=2))

    async def load(self, task_id: str) -> Optional[Task]:
        path = self.store_dir / f"{task_id}.json"
        if not path.exists():
            return None
        return await self._read_from_file(path)

    async def get_all(self) -> list[Task]:
        tasks = []
        for path in sorted(self.store_dir.glob("*.json")):
            task = await self._read_from_file(path)
            if task:
                tasks.append(task)
        return tasks

    async def get_by_status(self, status: TaskStatus) -> list[Task]:
        all_tasks = await self.get_all()
        return [t for t in all_tasks if t.status == status]

    async def get_pending(self) -> list[Task]:
        return await self.get_by_status(TaskStatus.PENDING)

    async def get_in_progress(self) -> list[Task]:
        return await self.get_by_status(TaskStatus.IN_PROGRESS)

    async def get_completed(self) -> list[Task]:
        return await self.get_by_status(TaskStatus.COMPLETED)

    async def update_status(self, task_id: str, status: TaskStatus) -> Optional[Task]:
        task = await self.load(task_id)
        if task:
            task.status = status
            await self.save(task)
        return task

    async def count_by_status(self) -> dict[str, int]:
        all_tasks = await self.get_all()
        counts: dict[str, int] = {}
        for status in TaskStatus:
            counts[status.value] = sum(1 for t in all_tasks if t.status == status)
        return counts

    async def _write_to_file(self, path: Path, data: str) -> None:
        retries = Config.MAX_RETRIES
        while retries > 0:
            try:
                async with async_open(path, "w") as f:
                    await f.write(data)
                return
            except OSError as e:
                logger.error("Failed to save task to %s: %s", path, e)
                retries -= 1
                if retries == 0:
                    raise

    async def _read_from_file(self, path: Path) -> Optional[Task]:
        retries = Config.MAX_RETRIES
        while retries > 0:
            try:
                async with async_open(path, "r") as f:
                    data = json.loads(await f.read())
                return Task(**data)
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to load task from %s: %s", path, e)
                retries -= 1
                if retries == 0:
                    return None
