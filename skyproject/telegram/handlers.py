"""Telegram command handlers for SkyProject."""
from __future__ import annotations

import logging
from pathlib import Path

from skyproject.core.config import LOGS_DIR, Config

logger = logging.getLogger(__name__)


async def handle_command(text: str, orchestrator) -> str:
    """Dispatch a command and return the response text."""
    parts = text.split()
    cmd = parts[0].lower()

    handlers = {
        "/status": _cmd_status,
        "/tasks": _cmd_tasks,
        "/task": _cmd_task_detail,
        "/logs": _cmd_logs,
        "/pause": _cmd_pause,
        "/resume": _cmd_resume,
        "/config": _cmd_config,
        "/report": _cmd_report,
        "/help": _cmd_help,
        "/start": _cmd_help,
    }

    handler = handlers.get(cmd)
    if not handler:
        return f"Unknown command: {cmd}\nType /help for available commands."

    try:
        return await handler(parts, orchestrator)
    except Exception as e:
        logger.error("Command %s error: %s", cmd, e)
        return f"Error: {e}"


async def _cmd_help(parts: list[str], orch) -> str:
    return (
        "<b>SkyProject Bot Commands</b>\n\n"
        "/status — System status\n"
        "/tasks — Last 10 tasks\n"
        "/task &lt;id&gt; — Task detail\n"
        "/logs — Last 20 log lines\n"
        "/pause — Pause orchestrator\n"
        "/resume — Resume orchestrator\n"
        "/config — Current configuration\n"
        "/report — Full status report\n"
    )


async def _cmd_status(parts: list[str], orch) -> str:
    if not orch:
        return "Orchestrator not connected."
    s = orch.state
    paused = getattr(orch, "_paused", False)
    return (
        "<b>SkyProject Status</b>\n\n"
        f"State: {'PAUSED' if paused else 'RUNNING'}\n"
        f"Cycle: {s.cycle_count}\n"
        f"Uptime: {int(s.uptime_seconds)}s\n"
        f"Tasks completed: {s.total_tasks_completed}\n"
        f"Improvements: {s.total_improvements}\n"
        f"Last cycle: {s.last_cycle_at.strftime('%H:%M:%S') if s.last_cycle_at else 'N/A'}\n"
    )


async def _cmd_tasks(parts: list[str], orch) -> str:
    if not orch:
        return "Orchestrator not connected."
    try:
        tasks = await orch.task_store.get_all()
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        tasks = tasks[:10]
    except Exception:
        return "Failed to load tasks."

    if not tasks:
        return "No tasks found."

    lines = ["<b>Recent Tasks</b>\n"]
    for t in tasks:
        lines.append(f"<code>{t.id}</code> [{t.status.value}] {t.title[:40]}")
    return "\n".join(lines)


async def _cmd_task_detail(parts: list[str], orch) -> str:
    if not orch:
        return "Orchestrator not connected."
    if len(parts) < 2:
        return "Usage: /task &lt;id&gt;"
    task_id = parts[1]
    try:
        task = await orch.task_store.load(task_id)
    except Exception:
        return "Failed to load task."

    if not task:
        return f"Task {task_id} not found."

    return (
        f"<b>{task.title}</b>\n\n"
        f"ID: <code>{task.id}</code>\n"
        f"Status: {task.status.value}\n"
        f"Type: {task.task_type.value}\n"
        f"Priority: {task.priority.value}\n"
        f"Module: {task.target_module}\n"
        f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{task.description[:500]}"
    )


async def _cmd_logs(parts: list[str], orch) -> str:
    log_file = LOGS_DIR / "skyproject.log"
    if not log_file.exists():
        return "No log file found."
    try:
        lines = log_file.read_text(errors="replace").strip().splitlines()[-20:]
        return "<b>Recent Logs</b>\n\n<pre>" + "\n".join(lines) + "</pre>"
    except OSError:
        return "Failed to read logs."


async def _cmd_pause(parts: list[str], orch) -> str:
    if not orch:
        return "Orchestrator not connected."
    if hasattr(orch, "pause"):
        orch.pause()
        return "Orchestrator PAUSED."
    return "Pause not supported."


async def _cmd_resume(parts: list[str], orch) -> str:
    if not orch:
        return "Orchestrator not connected."
    if hasattr(orch, "resume"):
        orch.resume()
        return "Orchestrator RESUMED."
    return "Resume not supported."


async def _cmd_config(parts: list[str], orch) -> str:
    return (
        "<b>Configuration</b>\n\n"
        f"Provider: {Config.LLM_PROVIDER}\n"
        f"Model: {Config.LLM_MODEL}\n"
        f"Cycle Interval: {Config.CYCLE_INTERVAL}s\n"
        f"Auto Improve: {Config.AUTO_IMPROVE}\n"
        f"Self-Improve Every: {Config.SELF_IMPROVE_EVERY_N_CYCLES} cycles\n"
        f"Log Level: {Config.LOG_LEVEL}\n"
    )


async def _cmd_report(parts: list[str], orch) -> str:
    status = await _cmd_status(parts, orch)
    tasks = await _cmd_tasks(parts, orch)
    config = await _cmd_config(parts, orch)
    return f"{status}\n---\n{tasks}\n---\n{config}"
