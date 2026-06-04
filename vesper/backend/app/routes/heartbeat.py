"""POST /api/heartbeat/run — manual heartbeat trigger.

The backend image is thin (no discord/google/pptx deps) and mounts the vault
read-only, so it can't run the heartbeat in-process. Instead it drops a sentinel
file into the shared .claude/data volume; the worker `scheduler` service picks it
up within a few seconds and runs a forced tick (HEARTBEAT_FORCE=1).

The project dir is resolved lazily per request (from CLAUDE_PROJECT_DIR) so tests
can redirect it to a tmp dir — a module-level constant would bake the real path
and survive monkeypatch."""
from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..deps import require_auth

router = APIRouter()


def _trigger_path() -> Path:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[4])
    return proj / ".claude" / "data" / "state" / "heartbeat-trigger"


@router.post("/heartbeat/run", status_code=202)
def heartbeat_run(_: None = Depends(require_auth)):
    path = _trigger_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail="could not queue heartbeat")
    return {"status": "queued"}
