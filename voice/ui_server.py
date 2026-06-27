"""Vesper visual UI — FastAPI server with WebSocket event broadcast.

Serves the concept graph and streams brain state to the browser.
Runs in a daemon thread; all events are fire-and-forget.

Endpoints:
  GET  /                → orb.html
  GET  /graph           → vis.js node/edge JSON
  POST /input           → typed text → brain.turn() thread; response via WS
  GET  /cmd/finance     → month_summary() JSON
  POST /cmd/finance     → tracker.log(entry) JSON
  GET  /cmd/habits      → habits status JSON
  POST /cmd/habits/check → check_pillar(pillar) JSON
  POST /cmd/study/explain → concept_explainer.run(topic) text
  GET  /cmd/study/quiz    → quiz_generator.run() cards JSON
  GET  /cmd/study/plan    → study_planner.run() text
  POST /cmd/study/research → research_synthesizer.run(topic) text
  GET  /cmd/study/progress → progress_monitor.run() text
  POST /upload          → save .pdf/.pptx to Dynamous/Memory/inbox/
  WS   /ws              → live brain events
"""
from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

_STATIC = Path(__file__).parent / "static"
_clients: list[WebSocket] = []
_queue: asyncio.Queue | None = None
_loop: asyncio.AbstractEventLoop | None = None
_brain = None


def set_brain(brain) -> None:
    """Register the Brain instance so POST /input can call brain.turn()."""
    global _brain
    _brain = brain


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _queue, _loop
    _queue = asyncio.Queue()
    _loop = asyncio.get_event_loop()
    asyncio.create_task(_drain())
    yield


app = FastAPI(lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/")
async def index() -> HTMLResponse:
    html = (_STATIC / "orb.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/graph")
async def graph() -> JSONResponse:
    from voice.graph_builder import build
    return JSONResponse(build())


class _TextInput(BaseModel):
    text: str


_ROOT = Path(__file__).resolve().parents[1]


@app.post("/input", status_code=202)
async def text_input(body: _TextInput) -> Response:
    if _brain is None:
        raise HTTPException(503, "brain not initialised")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "empty text")

    def _run() -> None:
        try:
            for _ in _brain.turn(text):
                pass
        except Exception:
            post_event({"type": "state", "value": "idle"})

    threading.Thread(target=_run, daemon=True, name="vesper-input").start()
    return Response(status_code=202)


# ── Finance panel ────────────────────────────────────────────────────────────

class _FinanceEntry(BaseModel):
    entry: str


@app.get("/cmd/finance")
async def finance_summary() -> JSONResponse:
    def _run():
        import sys
        sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
        from finance.tracker import month_summary  # type: ignore
        return month_summary()

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            summary = ex.submit(_run).result(timeout=10)
            return JSONResponse({"summary": summary})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/cmd/finance")
async def finance_log(body: _FinanceEntry) -> JSONResponse:
    import sys
    sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
    try:
        from finance.tracker import parse, log  # type: ignore
    except ImportError as exc:
        return JSONResponse({"error": f"tracker unavailable: {exc}"}, status_code=500)

    parsed = parse(body.entry)
    if not parsed:
        return JSONResponse({"error": "couldn't parse — use: amount category [note]"}, status_code=400)

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            result = ex.submit(log, parsed["amount"], parsed["category"], parsed["note"]).result(timeout=10)
            msg = (
                f"Logged RM{parsed['amount']:.2f} · {parsed['category']}"
                + (f" · {parsed['note']}" if parsed["note"] else "")
                + f"\nMonth total: RM{result['month_total']:.2f}"
            )
            return JSONResponse({"message": msg})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


# ── Habits panel ─────────────────────────────────────────────────────────────

@app.get("/cmd/habits")
async def habits_status() -> JSONResponse:
    import sys
    sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
    try:
        from core.habits import get_status_data  # type: ignore
        data = get_status_data()
        # Pydantic can't serialise the returned dict directly if it has non-JSON types
        return JSONResponse({
            "today": data.get("today"),
            "checked": data.get("checked", {}),
            "done_count": data.get("done_count", 0),
            "total": data.get("total", 0),
            "current_streak": data.get("current_streak", 0),
            "best_streak": data.get("best_streak", 0),
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


class _HabitCheck(BaseModel):
    pillar: str


@app.post("/cmd/habits/check")
async def habits_check(body: _HabitCheck) -> JSONResponse:
    import sys
    sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))
    try:
        from core.habits import check_pillar  # type: ignore
        changed = check_pillar(body.pillar)
        return JSONResponse({"checked": changed})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# ── Notices feed ─────────────────────────────────────────────────────────────

@app.get("/cmd/notices")
async def get_notices() -> JSONResponse:
    import json
    p = _ROOT / ".claude" / "data" / "voice_notices.jsonl"
    entries: list[dict] = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return JSONResponse({"notices": list(reversed(entries[-50:]))})


# ── Study panel ──────────────────────────────────────────────────────────────

class _StudyQuery(BaseModel):
    topic: str


def _add_scripts_path() -> None:
    import sys
    p = str(_ROOT / ".claude" / "scripts")
    if p not in sys.path:
        sys.path.insert(0, p)


@app.post("/cmd/study/explain")
async def study_explain(body: _StudyQuery) -> JSONResponse:
    import concurrent.futures
    topic = body.topic.strip()
    if not topic:
        return JSONResponse({"error": "topic required"}, status_code=400)
    def _run():
        _add_scripts_path()
        from agents.concept_explainer import run  # type: ignore
        return run(topic)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return JSONResponse({"result": ex.submit(_run).result(timeout=30)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/cmd/study/quiz")
async def study_quiz() -> JSONResponse:
    import concurrent.futures
    def _run():
        _add_scripts_path()
        from agents.quiz_generator import run  # type: ignore
        return run()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return JSONResponse({"cards": ex.submit(_run).result(timeout=30)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/cmd/study/plan")
async def study_plan() -> JSONResponse:
    import concurrent.futures
    def _run():
        _add_scripts_path()
        from agents.study_planner import run  # type: ignore
        return run()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return JSONResponse({"result": ex.submit(_run).result(timeout=30)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/cmd/study/research")
async def study_research(body: _StudyQuery) -> JSONResponse:
    import concurrent.futures
    topic = body.topic.strip()
    if not topic:
        return JSONResponse({"error": "topic required"}, status_code=400)
    def _run():
        _add_scripts_path()
        from agents.research_synthesizer import run  # type: ignore
        return run(topic)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return JSONResponse({"result": ex.submit(_run).result(timeout=30)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/cmd/study/progress")
async def study_progress() -> JSONResponse:
    import concurrent.futures
    def _run():
        _add_scripts_path()
        from agents.progress_monitor import run  # type: ignore
        return run()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        try:
            return JSONResponse({"result": ex.submit(_run).result(timeout=30)})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)


# ── File upload (Phase C) ─────────────────────────────────────────────────────

_INBOX = _ROOT / "Dynamous" / "Memory" / "inbox"
_ALLOWED_EXTS = {".pdf", ".pptx"}


@app.post("/upload", status_code=202)
async def upload_file(file: UploadFile = File(...)) -> Response:
    from pathlib import PurePosixPath
    suffix = PurePosixPath(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTS:
        raise HTTPException(400, f"only {_ALLOWED_EXTS} accepted")
    _INBOX.mkdir(parents=True, exist_ok=True)
    dest = _INBOX / (file.filename or "upload" + suffix)
    content = await file.read()
    dest.write_bytes(content)
    return Response(status_code=202)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ws in _clients:
            _clients.remove(ws)


async def _drain() -> None:
    while True:
        event = await _queue.get()
        for client in list(_clients):
            try:
                await client.send_json(event)
            except Exception:
                if client in _clients:
                    _clients.remove(client)


def post_event(event: dict[str, Any]) -> None:
    """Thread-safe: enqueue an event for broadcast to all WS clients."""
    if _loop and _queue:
        _loop.call_soon_threadsafe(_queue.put_nowait, event)


def _open_app_window(port: int) -> None:
    """Open the orb in Edge/Chrome app mode (no browser chrome)."""
    import subprocess, webbrowser
    url = f"http://127.0.0.1:{port}"
    for browser in ["msedge", "chrome", "chromium"]:
        try:
            subprocess.Popen(
                f'start {browser} --app={url} --window-size=900,700',
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            continue
    webbrowser.open(url)


def start(port: int = 7070) -> None:
    """Start uvicorn in a daemon thread and open the browser."""
    def _run() -> None:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

    threading.Thread(target=_run, daemon=True, name="vesper-ui").start()
    threading.Event().wait(0.8)

    _open_app_window(port)
