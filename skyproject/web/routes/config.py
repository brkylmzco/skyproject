"""Configuration route."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from skyproject.core.config import Config, PROJECT_ROOT

router = APIRouter()

ENV_FILE = PROJECT_ROOT / ".env"

CONFIG_FIELDS = [
    ("LLM_PROVIDER", "LLM Provider", "text", "openai"),
    ("LLM_MODEL", "LLM Model", "text", "gpt-4o"),
    ("SKY_CYCLE_INTERVAL", "Cycle Interval (seconds)", "number", "30"),
    ("SKY_AUTO_IMPROVE", "Auto Improve", "select:true,false", "true"),
    ("SKY_LOG_LEVEL", "Log Level", "select:DEBUG,INFO,WARNING,ERROR", "INFO"),
    ("SKY_MAX_QUEUE_SIZE", "Max Queue Size", "number", "100"),
    ("SKY_VECTOR_MAX_RESULTS", "Vector Max Results", "number", "10"),
    ("SKY_VECTOR_CONTEXT_TOKENS", "Vector Context Tokens", "number", "3000"),
    ("SELF_IMPROVE_EVERY_N_CYCLES", "Self-Improve Every N Cycles", "number", "5"),
]


def _read_env() -> dict[str, str]:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def _write_env(updates: dict[str, str]) -> None:
    existing_lines = []
    if ENV_FILE.exists():
        existing_lines = ENV_FILE.read_text().splitlines()

    updated_keys = set()
    new_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")


@router.get("/config")
async def config_page(request: Request):
    templates = request.app.state.templates
    env_values = _read_env()

    fields = []
    for key, label, field_type, default in CONFIG_FIELDS:
        current = env_values.get(key, os.getenv(key, default))
        fields.append({
            "key": key,
            "label": label,
            "type": field_type,
            "value": current,
        })

    return templates.TemplateResponse("config.html", {
        "request": request,
        "active": "config",
        "fields": fields,
        "flash_message": request.query_params.get("saved"),
    })


@router.post("/config")
async def config_save(request: Request):
    form = await request.form()
    updates = {}
    for key, _, _, _ in CONFIG_FIELDS:
        val = form.get(key)
        if val is not None:
            updates[key] = str(val)

    _write_env(updates)

    Config.LLM_PROVIDER = updates.get("LLM_PROVIDER", Config.LLM_PROVIDER)
    Config.LLM_MODEL = updates.get("LLM_MODEL", Config.LLM_MODEL)
    Config.CYCLE_INTERVAL = int(updates.get("SKY_CYCLE_INTERVAL", Config.CYCLE_INTERVAL))
    Config.AUTO_IMPROVE = updates.get("SKY_AUTO_IMPROVE", "true").lower() == "true"
    Config.LOG_LEVEL = updates.get("SKY_LOG_LEVEL", Config.LOG_LEVEL)

    return RedirectResponse("/config?saved=Configuration+saved+successfully.", status_code=303)
