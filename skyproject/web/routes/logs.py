"""Logs route with SSE streaming."""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from skyproject.core.config import LOGS_DIR

router = APIRouter()

LOG_FILE = LOGS_DIR / "skyproject.log"


def _read_tail(path: Path, lines: int = 500) -> list[str]:
    if not path.exists():
        return []
    try:
        text = path.read_text(errors="replace")
        return text.strip().splitlines()[-lines:]
    except OSError:
        return []


@router.get("/logs")
async def logs_page(request: Request):
    templates = request.app.state.templates
    log_lines = _read_tail(LOG_FILE, 500)
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "active": "logs",
        "log_lines": log_lines,
    })


async def _log_event_generator():
    """Tail the log file and yield SSE events."""
    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.touch()

    last_size = LOG_FILE.stat().st_size

    while True:
        await asyncio.sleep(1)
        try:
            current_size = LOG_FILE.stat().st_size
            if current_size > last_size:
                with open(LOG_FILE, "r", errors="replace") as f:
                    f.seek(last_size)
                    new_data = f.read()
                last_size = current_size
                for line in new_data.strip().splitlines():
                    yield f"data: {line}\n\n"
            elif current_size < last_size:
                last_size = 0
        except OSError:
            await asyncio.sleep(2)


@router.get("/api/logs/stream")
async def log_stream():
    return StreamingResponse(
        _log_event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
