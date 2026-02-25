"""Authentication for SkyProject Web UI."""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import RedirectResponse

from skyproject.core.config import DATA_DIR

AUTH_FILE = DATA_DIR / "auth.json"
SESSION_COOKIE = "sky_session"


def _hash_password(password: str, salt: str = "") -> str:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def _verify_password(password: str, stored: str) -> bool:
    salt = stored.split(":")[0]
    return _hash_password(password, salt) == stored


def _load_auth() -> dict:
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    default = {
        "username": "admin",
        "password_hash": _hash_password("admin"),
        "must_change": True,
        "session_secret": secrets.token_hex(32),
    }
    _save_auth(default)
    return default


def _save_auth(data: dict) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(data, indent=2))


def get_session_secret() -> str:
    auth = _load_auth()
    return auth.get("session_secret", secrets.token_hex(32))


def authenticate(username: str, password: str) -> Optional[str]:
    """Authenticate and return a session token, or None."""
    auth = _load_auth()
    if username != auth["username"]:
        return None
    if not _verify_password(password, auth["password_hash"]):
        return None
    token = secrets.token_hex(32)
    auth["active_session"] = token
    _save_auth(auth)
    return token


def must_change_password() -> bool:
    return _load_auth().get("must_change", True)


def change_password(new_password: str) -> None:
    auth = _load_auth()
    auth["password_hash"] = _hash_password(new_password)
    auth["must_change"] = False
    auth["active_session"] = secrets.token_hex(32)
    _save_auth(auth)


def verify_session(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return False
    auth = _load_auth()
    return auth.get("active_session") == token


def require_auth(request: Request):
    """Middleware-style check. Returns RedirectResponse if not authenticated."""
    if not verify_session(request):
        return RedirectResponse("/login", status_code=303)
    return None
