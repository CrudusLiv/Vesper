"""The single seam between FastAPI and the existing BoredBot scripts.

Routes import THIS module, never `.claude/scripts` directly. Here we insert the
scripts dirs onto sys.path and re-export thin wrappers. Paths resolve from
CLAUDE_PROJECT_DIR (set to /workspace in the container), falling back to the
repo root computed from this file's location."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
_SCRIPTS = PROJECT_DIR / ".claude" / "scripts"
for _p in (_SCRIPTS, _SCRIPTS / "integrations", _SCRIPTS / "memory"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

# Existing BoredBot modules. _env loads .env on import.
import _env  # noqa: F401,E402  -- side effect: loads .env into os.environ
from integrations import registry  # noqa: E402
from memory import memory_search  # noqa: E402
from memory import db as memory_db  # noqa: E402
from heartbeat import llm  # noqa: E402
from finance import tracker  # noqa: E402
import schedule_parser  # noqa: E402
from vault import actions as vault_actions  # noqa: E402
from vault import paths as vault_paths  # noqa: E402
from heartbeat import discord_dm_capture  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

VAULT = Path(os.environ.get("VAULT_PATH") or (PROJECT_DIR / "Dynamous" / "Memory"))
_START = time.time()

MAX_TOP_K = 20
_CHAT_MODEL = "haiku"  # claude CLI model slug passed to llm.call
_SOUL_CACHE: str | None = None

_KL = timezone(timedelta(hours=8))


def _project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])


def _vault_dir() -> Path:
    return Path(os.environ.get("VAULT_PATH") or (_project_dir() / "Dynamous" / "Memory"))


class LlmError(RuntimeError):
    """Raised when llm.call returns an empty result (CLI failure or timeout)."""


def _memory_health() -> str:
    try:
        conn = memory_db.connect()
        try:
            n = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"]
        finally:
            conn.close()
        return "ok" if n and n > 0 else "degraded"
    except Exception:
        return "degraded"


def get_status() -> dict:
    integrations = {
        i.name: {"ready": i.ready(), "missing": i.missing()}
        for i in registry.INTEGRATIONS
    }
    return {
        "integrations": integrations,
        "vault": {"online": VAULT.is_dir(), "path": str(VAULT)},
        "memory": _memory_health(),
        "uptime": round(time.time() - _START, 1),
    }


def search(query: str, top_k: int = 5) -> dict:
    top_k = max(1, min(top_k, MAX_TOP_K))
    try:
        conn = memory_db.connect()
    except Exception:
        return {"results": [], "warning": "memory index unavailable"}
    try:
        n = conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"]
        if not n:
            return {"results": [], "warning": "memory index unavailable"}
        hits = memory_search.hybrid_search(conn, query, top_k=top_k)
    except Exception:
        return {"results": [], "warning": "memory index unavailable"}
    finally:
        conn.close()
    results = [
        {"path": h["path"], "heading": h["heading"], "content": h["content"], "score": h["score"]}
        for h in hits
    ]
    return {"results": results}


def _soul() -> str:
    global _SOUL_CACHE
    if _SOUL_CACHE is None:
        try:
            _SOUL_CACHE = (VAULT / "SOUL.md").read_text(encoding="utf-8")
        except OSError:
            _SOUL_CACHE = ""
    return _SOUL_CACHE


def _build_prompt(message: str, history: list[dict], hits: list[dict]) -> str:
    parts: list[str] = []
    if hits:
        ctx = "\n\n".join(
            f"[{h.get('path')}{(' / ' + h['heading']) if h.get('heading') else ''}]\n{h.get('content','')}"
            for h in hits
        )
        parts.append("RELEVANT VAULT CONTEXT (for reference, may be partial):\n" + ctx)
    if history:
        convo = "\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in history)
        parts.append("CONVERSATION SO FAR:\n" + convo)
    parts.append("USER MESSAGE:\n" + message)
    return "\n\n".join(parts)


def chat(message: str, history: list[dict]) -> dict:
    hits = search(message, top_k=5).get("results", [])
    prompt = _build_prompt(message, history, hits)
    reply = llm.call(prompt, system_prompt=_soul() or None, model=_CHAT_MODEL)
    if not reply:
        raise LlmError("llm unavailable")
    sources = [{"path": h["path"], "heading": h["heading"], "score": h["score"]} for h in hits]
    return {"reply": reply, "sources": sources}


def finance_log(amount: float, category: str, note: str = "") -> dict:
    r = tracker.log(amount, category, note)
    return {
        "date": r["date"],
        "month_total": r["month_total"],
        "category_total": r["category_total"],
        "currency": tracker.CURRENCY,
    }


def finance_summary() -> dict:
    return {"summary": tracker.month_summary()}


def note_append(text: str) -> dict:
    notes_file = _vault_dir() / "notes" / "NOTES.md"
    notes_file.parent.mkdir(parents=True, exist_ok=True)
    stripped = discord_dm_capture._append_note(notes_file, datetime.now(_KL), text)
    if not stripped:
        raise ValueError("note was empty after stripping")
    return {"ok": True, "appended_chars": len(stripped)}


def schedule_get() -> dict:
    return {"schedule": schedule_parser.format_for_discord()}


def schedule_set(text: str, confirm: bool = False) -> dict:
    if not llm.is_available():
        raise LlmError("llm unavailable")
    entries, summary = schedule_parser.parse_timetable(text)
    if schedule_parser.has_existing_schedule() and not confirm:
        return {"written": False, "summary": summary}
    schedule_parser.write_schedule(entries)
    return {"written": True, "summary": summary}


def vault_list(directory: str = "") -> dict:
    res = vault_actions.list_dir(directory)
    root = vault_paths.vault()
    entries = [
        {"name": name, "is_dir": (root / directory / name).is_dir()}
        for name in res["entries"]
    ]
    return {"directory": res["directory"], "entries": entries}


def vault_delete(path: str) -> dict:
    return vault_actions.delete(path)


def vault_undo() -> dict:
    return vault_actions.undo()
