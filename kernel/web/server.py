# kernel/web/server.py
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer, BadSignature

_HERE = Path(__file__).parent
_KL = timezone(timedelta(hours=8))
_COOKIE = "vspr_session"
_GREEN_MINUTES = 35
_YELLOW_MINUTES = 70


def _signer(password: str) -> URLSafeSerializer:
    return URLSafeSerializer(password, salt="vesper-dashboard")


def _is_authed(request: Request, password: str) -> bool:
    token = request.cookies.get(_COOKIE, "")
    try:
        _signer(password).loads(token)
        return True
    except BadSignature:
        return False


def read_deadlines(data_dir: Path) -> list[dict]:
    path = data_dir / "deadlines.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def read_heartbeat_status(data_dir: Path) -> dict:
    path = data_dir / "heartbeat-status.json"
    if not path.exists():
        return {"last_tick": None, "next_tick_eta": None, "errors": [], "health": "unknown"}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"last_tick": None, "next_tick_eta": None, "errors": [], "health": "unknown"}

    last_tick_str = raw.get("last_tick")
    errors = raw.get("errors", [])
    health = "unknown"
    if last_tick_str:
        try:
            last_tick = datetime.fromisoformat(last_tick_str)
            minutes_ago = (datetime.now(_KL) - last_tick).total_seconds() / 60
            if errors:
                health = "red"
            elif minutes_ago <= _GREEN_MINUTES:
                health = "green"
            elif minutes_ago <= _YELLOW_MINUTES:
                health = "yellow"
            else:
                health = "red"
        except ValueError:
            health = "unknown"

    return {
        "last_tick": last_tick_str,
        "next_tick_eta": raw.get("next_tick_eta"),
        "errors": errors,
        "health": health,
    }


def read_budget(data_dir: Path) -> list[dict]:
    path = data_dir / "finance.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def read_schedule(vault_dir: Path) -> str:
    today = datetime.now(_KL).strftime("%Y-%m-%d")
    note = vault_dir / "daily" / f"{today}.md"
    if not note.exists():
        return ""
    try:
        return note.read_text(encoding="utf-8")
    except OSError:
        return ""


def create_app(data_dir: Path, vault_dir: Path, password: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_HERE / "templates"))
    static_dir = _HERE / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: str = ""):
        return templates.TemplateResponse(request, "login.html", {"error": error})

    @app.post("/login", response_class=HTMLResponse)
    async def login_submit(request: Request, password_input: str = Form(alias="password")):
        if password_input != password:
            return templates.TemplateResponse(
                request, "login.html", {"error": "Invalid password"}, status_code=200
            )
        token = _signer(password).dumps("ok")
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie(_COOKIE, token, httponly=True, samesite="lax")
        return resp

    @app.get("/logout")
    async def logout():
        resp = RedirectResponse("/login", status_code=302)
        resp.delete_cookie(_COOKIE)
        return resp

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        if not _is_authed(request, password):
            return RedirectResponse("/login", status_code=302)
        return templates.TemplateResponse(request, "dashboard.html", {
            "deadlines": read_deadlines(data_dir),
            "heartbeat": read_heartbeat_status(data_dir),
            "budget": read_budget(data_dir),
            "schedule": read_schedule(vault_dir),
        })

    return app
