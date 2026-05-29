"""HABITS.md auto-detection and late-day nudge.

Two pillars are auto-detected from the snapshot + filesystem; the other two
are self-reported. Late-day nudge fires at most once per day after 18:00 KL,
listing whichever pillars are still unchecked."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
VAULT = PROJECT_DIR / "Dynamous" / "Memory"
HABITS = VAULT / "HABITS.md"
LECTURES = VAULT / "lectures"
NUDGE_STATE = PROJECT_DIR / ".claude" / "data" / "state" / "nudges.json"

KL = timezone(timedelta(hours=8))
NUDGE_HOUR = 18

PILLAR_NAMES = (
    "Lecture engagement",
    "Project progress",
    "Research / learning",
    "Personal goals",
)


def _today_kl() -> str:
    return datetime.now(KL).strftime("%Y-%m-%d")


def _pillar_line_re(pillar: str) -> re.Pattern[str]:
    return re.compile(
        r"^(- \[)([ xX])(\] \*\*" + re.escape(pillar) + r"\*\*)",
        re.MULTILINE,
    )


def _check_pillar(text: str, pillar: str) -> tuple[str, bool]:
    """Return (new_text, was_changed). Idempotent: already-checked stays checked."""
    pattern = _pillar_line_re(pillar)
    match = pattern.search(text)
    if not match:
        return text, False
    if match.group(2).lower() == "x":
        return text, False
    new_text = pattern.sub(r"\1x\3", text, count=1)
    return new_text, True


def _is_pillar_checked(text: str, pillar: str) -> bool:
    match = _pillar_line_re(pillar).search(text)
    return bool(match and match.group(2).lower() == "x")


# ---------- Auto-detection ----------

def _lectures_touched_today() -> bool:
    if not LECTURES.exists():
        return False
    today = _today_kl()
    for p in LECTURES.rglob("*.md"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=KL).strftime("%Y-%m-%d")
        except OSError:
            continue
        if mtime == today:
            return True
    return False


def _commits_today(snapshot: dict) -> bool:
    items = (snapshot.get("github") or {}).get("items") or []
    today = _today_kl()
    for c in items:
        if isinstance(c, dict) and (c.get("date") or "").startswith(today):
            return True
    return False


def auto_check(snapshot: dict) -> list[str]:
    """Tick auto-detected pillars in HABITS.md. Returns names of newly-ticked pillars."""
    if not HABITS.exists():
        return []
    text = HABITS.read_text(encoding="utf-8")
    newly: list[str] = []

    if _lectures_touched_today():
        text, changed = _check_pillar(text, "Lecture engagement")
        if changed:
            newly.append("Lecture engagement")

    if _commits_today(snapshot):
        text, changed = _check_pillar(text, "Project progress")
        if changed:
            newly.append("Project progress")

    if newly:
        HABITS.write_text(text, encoding="utf-8")
        import sys as _sys
        _sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
        from vault import daily  # type: ignore
        for pillar in newly:
            daily.append_line(f"Habit: {pillar}")
    return newly


# ---------- Late-day nudge ----------

def unchecked_pillars() -> list[str]:
    if not HABITS.exists():
        return []
    text = HABITS.read_text(encoding="utf-8")
    return [p for p in PILLAR_NAMES if not _is_pillar_checked(text, p)]


def _load_nudge_state() -> dict:
    if not NUDGE_STATE.exists():
        return {}
    try:
        return json.loads(NUDGE_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_nudge_state(state: dict) -> None:
    NUDGE_STATE.parent.mkdir(parents=True, exist_ok=True)
    NUDGE_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def should_nudge(now: datetime | None = None) -> bool:
    now = now or datetime.now(KL)
    if now.hour < NUDGE_HOUR:
        return False
    state = _load_nudge_state()
    return state.get("last_nudge") != now.strftime("%Y-%m-%d")


def mark_nudged(now: datetime | None = None) -> None:
    now = now or datetime.now(KL)
    _save_nudge_state({"last_nudge": now.strftime("%Y-%m-%d")})


def nudge_message(unchecked: list[str]) -> tuple[str, str]:
    """Build (title, body) for the toast. Plain, concrete, short."""
    if len(unchecked) == 1:
        title = "Habit nudge"
        body = f"Still unchecked: {unchecked[0]}."
    else:
        title = f"{len(unchecked)} habits unchecked"
        body = "Still open: " + ", ".join(unchecked) + "."
    return title, body
