import asyncio
import pytest
from pathlib import Path

from skyproject.core.task_store import TaskStore
from skyproject.shared.models import Task, TaskStatus, TaskPriority, TaskType


@pytest.fixture
async def task_store(tmp_path: Path):
    store = TaskStore(store_dir=tmp_path)
    yield store


@pytest.fixture
def sample_task():
    return Task(
        title="Sample Task",
        description="This is a sample task",
        task_type=TaskType.FEATURE,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.PENDING
    )


@pytest.mark.asyncio
async def test_save_and_load_task(task_store, sample_task):
    await task_store.save(sample_task)
    loaded_task = await task_store.load(sample_task.id)
    assert loaded_task is not None
    assert loaded_task.id == sample_task.id
    assert loaded_task.title == sample_task.title


@pytest.mark.asyncio
async def test_load_nonexistent_task(task_store):
    loaded_task = await task_store.load("nonexistent")
    assert loaded_task is None


@pytest.mark.asyncio
async def test_get_all_tasks(task_store, sample_task):
    await task_store.save(sample_task)
    tasks = await task_store.get_all()
    assert len(tasks) == 1
    assert tasks[0].id == sample_task.id


@pytest.mark.asyncio
async def test_get_by_status(task_store, sample_task):
    await task_store.save(sample_task)
    tasks_pending = await task_store.get_pending()
    assert len(tasks_pending) == 1
    assert tasks_pending[0].id == sample_task.id

    sample_task.status = TaskStatus.COMPLETED
    await task_store.save(sample_task)
    tasks_completed = await task_store.get_completed()
    assert len(tasks_completed) == 1
    assert tasks_completed[0].id == sample_task.id


@pytest.mark.asyncio
async def test_update_status(task_store, sample_task):
    await task_store.save(sample_task)
    updated_task = await task_store.update_status(sample_task.id, TaskStatus.IN_PROGRESS)
    assert updated_task is not None
    assert updated_task.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_count_by_status(task_store, sample_task):
    await task_store.save(sample_task)
    counts = await task_store.count_by_status()
    assert counts[TaskStatus.PENDING.value] == 1
    assert counts[TaskStatus.IN_PROGRESS.value] == 0
    assert counts[TaskStatus.COMPLETED.value] == 0

    sample_task.status = TaskStatus.COMPLETED
    await task_store.save(sample_task)
    counts = await task_store.count_by_status()
    assert counts[TaskStatus.COMPLETED.value] == 1
