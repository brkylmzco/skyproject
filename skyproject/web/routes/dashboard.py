"""Dashboard route."""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def dashboard(request: Request):
    templates = request.app.state.templates
    orch = request.app.state.orchestrator

    state = {
        "cycle_count": 0,
        "uptime": "0s",
        "tasks_completed": 0,
        "improvements": 0,
        "last_cycle": "N/A",
    }
    task_counts = {}

    if orch:
        s = orch.state
        state["cycle_count"] = s.cycle_count
        state["tasks_completed"] = s.total_tasks_completed
        state["improvements"] = s.total_improvements
        state["last_cycle"] = s.last_cycle_at.strftime("%H:%M:%S") if s.last_cycle_at else "N/A"

        uptime = s.uptime_seconds
        hours, rem = divmod(int(uptime), 3600)
        minutes, secs = divmod(rem, 60)
        state["uptime"] = f"{hours}h {minutes}m {secs}s" if hours else f"{minutes}m {secs}s"

        try:
            task_counts = await orch.task_store.count_by_status()
        except Exception:
            task_counts = {}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
        "state": state,
        "task_counts": json.dumps(task_counts),
    })
