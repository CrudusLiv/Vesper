"""POST /api/inbox/upload + GET /api/inbox/uploads.

Saves a .pptx/.pdf into the vault inbox and triggers the existing summariser.
On a host with the heavy deps the job runs in-process via BackgroundTasks; on a
thin Docker backend it drops the heartbeat-trigger sentinel for the worker.

The route is sync, so the multipart body is read synchronously through
`file.file.read()` (a sync route cannot await `UploadFile.read()`)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from .. import bridge
from ..deps import require_auth

router = APIRouter()

# Bare extensions (no dot) derived from the bridge's allow-list so the two
# can't drift if a new format is ever added there.
_ALLOWED = {ext.lstrip(".") for ext in bridge.INBOX_ALLOWED_EXT}


@router.post("/inbox/upload", status_code=202)
def inbox_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: None = Depends(require_auth),
):
    name = (file.filename or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="filename required")
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "ppt":
        raise HTTPException(status_code=415, detail="legacy .ppt is not supported -- re-save as .pptx")
    if ext not in _ALLOWED:
        raise HTTPException(status_code=415, detail="only .pptx and .pdf are supported")
    content = file.file.read()
    if len(content) > bridge.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds the 50 MB limit")

    try:
        saved_path = bridge.inbox_save(name, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    record = bridge.inbox_enqueue(saved_path.name)
    if bridge.inbox_deps_available():
        background_tasks.add_task(bridge.inbox_process_upload, record["id"], saved_path)
    else:
        bridge.inbox_trigger_heartbeat()
    return {"id": record["id"], "filename": saved_path.name, "status": "queued"}


@router.get("/inbox/uploads")
def inbox_uploads(_: None = Depends(require_auth)):
    return bridge.inbox_recent()
