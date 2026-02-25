"""Tasks routes."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/tasks")
async def task_list(request: Request):
    templates = request.app.state.templates
    orch = request.app.state.orchestrator

    tasks = []
    status_filter = request.query_params.get("status", "")

    if orch:
        try:
            all_tasks = await orch.task_store.get_all()
            if status_filter:
                tasks = [t for t in all_tasks if t.status.value == status_filter]
            else:
                tasks = all_tasks
            tasks.sort(key=lambda t: t.created_at, reverse=True)
        except Exception:
            tasks = []

    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "active": "tasks",
        "tasks": tasks,
        "status_filter": status_filter,
    })


@router.get("/tasks/{task_id}")
async def task_detail(request: Request, task_id: str):
    templates = request.app.state.templates
    orch = request.app.state.orchestrator

    task = None
    if orch:
        try:
            task = await orch.task_store.load(task_id)
        except Exception:
            pass

    if not task:
        return templates.TemplateResponse("task_detail.html", {
            "request": request,
            "active": "tasks",
            "task": None,
            "error": "Task not found.",
        })

    return templates.TemplateResponse("task_detail.html", {
        "request": request,
        "active": "tasks",
        "task": task,
        "error": None,
    })
