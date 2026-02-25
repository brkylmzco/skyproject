import pytest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path

from skyproject.core.task_store import TaskStore
from skyproject.shared.models import Task, TaskStatus
from skyproject.core.config import Config

@pytest.fixture
async def task_store(tmp_path):
    return TaskStore(store_dir=tmp_path)

@pytest.fixture
async def sample_task():
    return Task(id="1", title="Sample Task", description="This is a sample task.", status=TaskStatus.PENDING)

@pytest.mark.asyncio
async def test_save_task(task_store, sample_task):
    await task_store.save(sample_task)
    path = task_store.store_dir / f"{sample_task.id}.json"
    assert path.exists()

@pytest.mark.asyncio
async def test_load_task(task_store, sample_task):
    await task_store.save(sample_task)
    loaded_task = await task_store.load(sample_task.id)
    assert loaded_task == sample_task

@pytest.mark.asyncio
async def test_load_nonexistent_task(task_store):
    loaded_task = await task_store.load("nonexistent")
    assert loaded_task is None

@pytest.mark.asyncio
async def test_get_all_tasks(task_store, sample_task):
    await task_store.save(sample_task)
    tasks = await task_store.get_all()
    assert len(tasks) == 1
    assert tasks[0] == sample_task

@pytest.mark.asyncio
async def test_get_by_status(task_store, sample_task):
    await task_store.save(sample_task)
    pending_tasks = await task_store.get_by_status(TaskStatus.PENDING)
    assert len(pending_tasks) == 1
    assert pending_tasks[0] == sample_task

@pytest.mark.asyncio
async def test_update_status(task_store, sample_task):
    await task_store.save(sample_task)
    await task_store.update_status(sample_task.id, TaskStatus.COMPLETED)
    updated_task = await task_store.load(sample_task.id)
    assert updated_task.status == TaskStatus.COMPLETED

@pytest.mark.asyncio
async def test_count_by_status(task_store, sample_task):
    await task_store.save(sample_task)
    counts = await task_store.count_by_status()
    assert counts[TaskStatus.PENDING.value] == 1
    assert counts[TaskStatus.COMPLETED.value] == 0

@pytest.mark.asyncio
async def test_save_task_retry_logic(task_store, sample_task):
    with patch('aiofiles.open', side_effect=OSError("Mocked error")) as mock_open:
        with pytest.raises(OSError):
            await task_store.save(sample_task)
        assert mock_open.call_count == Config.MAX_RETRIES

@pytest.mark.asyncio
async def test_load_task_retry_logic(task_store, sample_task):
    await task_store.save(sample_task)
    with patch('aiofiles.open', side_effect=[OSError("Mocked error"), MagicMock()]) as mock_open:
        loaded_task = await task_store.load(sample_task.id)
        assert loaded_task == sample_task
        assert mock_open.call_count == 2
