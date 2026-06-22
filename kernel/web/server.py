# kernel/web/server.py
from __future__ import annotations

import json
import re
from datetime import datetime, date, timezone, timedelta
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


_DEADLINE_RE = re.compile(r"^-\s+(\d{4}-\d{2}-\d{2})\s+—\s+(.+?)\s+—\s+(.+)$")
_ACTIVE_SECTION = "## Active"


def read_deadlines(vault_dir: Path) -> list[dict]:
    path = vault_dir / "DEADLINES.md"
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    if _ACTIVE_SECTION not in text:
        return []
    section = text[text.index(_ACTIVE_SECTION) + len(_ACTIVE_SECTION):]
    next_h2 = re.search(r"\n## ", section)
    if next_h2:
        section = section[: next_h2.start()]
    today = date.today()
    result = []
    for line in section.splitlines():
        m = _DEADLINE_RE.match(line.strip())
        if not m:
            continue
        due_str, _course, title = m.group(1), m.group(2), m.group(3)
        try:
            due_date = date.fromisoformat(due_str)
        except ValueError:
            continue
        days_remaining = (due_date - today).days
        result.append({
            "title": title.strip(),
            "due": due_str,
            "overdue": days_remaining < 0,
            "days_remaining": days_remaining,
        })
    result.sort(key=lambda d: d["due"])
    return result


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
    if raw.get("standby"):
        health = "standby"
    elif last_tick_str:
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
        "standby": raw.get("standby", False),
    }


_TABLE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|")


def read_budget(vault_dir: Path) -> list[dict]:
    month = datetime.now(_KL).strftime("%Y-%m")
    path = vault_dir / "finance" / f"{month}.md"
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    in_entries = False
    result = []
    for line in text.splitlines():
        if line.strip() == "## Entries":
            in_entries = True
            continue
        if in_entries and line.startswith("## "):
            break
        if not in_entries:
            continue
        m = _TABLE_ROW_RE.match(line)
        if not m:
            continue
        date_val, amount, category = m.group(1), m.group(2), m.group(3)
        # skip header and separator rows
        if not date_val or date_val in ("-", "Date") or set(date_val) <= {"-", " "}:
            continue
        if not amount.strip() or amount.strip() in ("-", "Amount"):
            continue
        result.append({"date": date_val.strip(), "amount": amount.strip(), "category": category.strip()})
    return result


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
            "deadlines": read_deadlines(vault_dir),
            "heartbeat": read_heartbeat_status(data_dir),
            "budget": read_budget(vault_dir),
            "schedule": read_schedule(vault_dir),
        })

    return app
