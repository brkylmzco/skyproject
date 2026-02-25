import pytest
import asyncio
from pathlib import Path
from skyproject.core.task_store import TaskStore
from skyproject.shared.models import Task, TaskStatus, TaskType, TaskPriority

@pytest.fixture
def task_store(tmp_path: Path) -> TaskStore:
    return TaskStore(store_dir=tmp_path)

@pytest.fixture
def sample_task() -> Task:
    return Task(
        title="Sample Task",
        description="A sample task for testing",
        task_type=TaskType.FEATURE,
        priority=TaskPriority.MEDIUM
    )

@pytest.mark.asyncio
async def test_save_and_load_task(task_store: TaskStore, sample_task: Task):
    await task_store.save(sample_task)
    loaded_task = await task_store.load(sample_task.id)
    assert loaded_task is not None
    assert loaded_task.id == sample_task.id
    assert loaded_task.title == sample_task.title

@pytest.mark.asyncio
async def test_load_task_not_found(task_store: TaskStore):
    loaded_task = await task_store.load("nonexistent")
    assert loaded_task is None

@pytest.mark.asyncio
async def test_get_all_tasks(task_store: TaskStore, sample_task: Task):
    await task_store.save(sample_task)
    tasks = await task_store.get_all()
    assert len(tasks) == 1
    assert tasks[0].id == sample_task.id

@pytest.mark.asyncio
async def test_get_by_status(task_store: TaskStore, sample_task: Task):
    sample_task.status = TaskStatus.IN_PROGRESS
    await task_store.save(sample_task)
    tasks = await task_store.get_by_status(TaskStatus.IN_PROGRESS)
    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.IN_PROGRESS

@pytest.mark.asyncio
async def test_update_status(task_store: TaskStore, sample_task: Task):
    await task_store.save(sample_task)
    await task_store.update_status(sample_task.id, TaskStatus.COMPLETED)
    updated_task = await task_store.load(sample_task.id)
    assert updated_task is not None
    assert updated_task.status == TaskStatus.COMPLETED

@pytest.mark.asyncio
async def test_count_by_status(task_store: TaskStore, sample_task: Task):
    await task_store.save(sample_task)
    counts = await task_store.count_by_status()
    assert counts[TaskStatus.PENDING.value] == 1
    assert counts[TaskStatus.IN_PROGRESS.value] == 0