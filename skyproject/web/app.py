"""FastAPI application for SkyProject Web UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from skyproject.web.auth import (
    authenticate,
    must_change_password,
    change_password,
    verify_session,
    SESSION_COOKIE,
)

WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


def create_app(orchestrator=None) -> FastAPI:
    app = FastAPI(title="SkyProject", docs_url=None, redoc_url=None)
    app.state.orchestrator = orchestrator
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    # --- Auth routes ---

    @app.get("/login")
    async def login_page(request: Request):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": None,
            "must_change": False,
        })

    @app.post("/login")
    async def login_post(
        request: Request,
        action: str = Form("login"),
        username: str = Form(""),
        password: str = Form(""),
        new_password: str = Form(""),
        confirm_password: str = Form(""),
    ):
        if action == "change_password":
            if new_password != confirm_password:
                return templates.TemplateResponse("login.html", {
                    "request": request,
                    "error": "Passwords do not match.",
                    "must_change": True,
                })
            if len(new_password) < 6:
                return templates.TemplateResponse("login.html", {
                    "request": request,
                    "error": "Password must be at least 6 characters.",
                    "must_change": True,
                })
            change_password(new_password)
            token = authenticate("admin", new_password)
            resp = RedirectResponse("/", status_code=303)
            resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
            return resp

        token = authenticate(username, password)
        if not token:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid username or password.",
                "must_change": False,
            })

        if must_change_password():
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": None,
                "must_change": True,
            })

        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax")
        return resp

    @app.get("/logout")
    async def logout():
        resp = RedirectResponse("/login", status_code=303)
        resp.delete_cookie(SESSION_COOKIE)
        return resp

    # --- Auth middleware ---

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        public = {"/login", "/static"}
        path = request.url.path
        if any(path.startswith(p) for p in public):
            return await call_next(request)
        if not verify_session(request):
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)

    # --- Register route modules ---

    from skyproject.web.routes.dashboard import router as dashboard_router
    from skyproject.web.routes.tasks import router as tasks_router
    from skyproject.web.routes.logs import router as logs_router
    from skyproject.web.routes.config import router as config_router
    from skyproject.web.routes.api_keys import router as keys_router

    app.include_router(dashboard_router)
    app.include_router(tasks_router)
    app.include_router(logs_router)
    app.include_router(config_router)
    app.include_router(keys_router)

    return app
