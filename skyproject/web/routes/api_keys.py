"""API Keys management route."""
from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from skyproject.core.config import PROJECT_ROOT

router = APIRouter()

ENV_FILE = PROJECT_ROOT / ".env"

KEY_FIELDS = [
    ("OPENAI_API_KEY", "OpenAI API Key"),
    ("ANTHROPIC_API_KEY", "Anthropic API Key"),
    ("TELEGRAM_BOT_TOKEN", "Telegram Bot Token"),
    ("TELEGRAM_CHAT_ID", "Telegram Chat ID"),
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


def _mask(value: str) -> str:
    if not value or len(value) < 8 or value.startswith("your-"):
        return ""
    return "*" * (len(value) - 4) + value[-4:]


@router.get("/settings/keys")
async def keys_page(request: Request):
    templates = request.app.state.templates
    env_values = _read_env()

    keys = []
    for key, label in KEY_FIELDS:
        raw = env_values.get(key, os.getenv(key, ""))
        keys.append({
            "key": key,
            "label": label,
            "masked": _mask(raw),
            "has_value": bool(raw and not raw.startswith("your-")),
        })

    return templates.TemplateResponse("api_keys.html", {
        "request": request,
        "active": "keys",
        "keys": keys,
        "flash_message": request.query_params.get("saved"),
    })


@router.post("/settings/keys")
async def keys_save(request: Request):
    form = await request.form()
    updates = {}

    for key, _ in KEY_FIELDS:
        val = form.get(key, "").strip()
        if val and not val.startswith("*"):
            updates[key] = val

    if updates:
        _write_env(updates)

    return RedirectResponse("/settings/keys?saved=API+keys+updated+successfully.", status_code=303)
