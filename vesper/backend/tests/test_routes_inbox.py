from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.bridge as bridge
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-secret"}


def _file(name="x.pptx", data=b"data"):
    return {"file": (name, data, "application/octet-stream")}


def test_upload_requires_auth():
    assert client.post("/api/inbox/upload", files=_file()).status_code == 401


def test_upload_happy_path_schedules_background(monkeypatch):
    monkeypatch.setattr(bridge, "inbox_save", lambda filename, content: Path("/vault/inbox/x.pptx"))
    monkeypatch.setattr(bridge, "inbox_enqueue", lambda filename: {"id": "abc", "filename": filename, "status": "queued"})
    monkeypatch.setattr(bridge, "inbox_deps_available", lambda: True)
    seen = {}
    monkeypatch.setattr(bridge, "inbox_process_upload", lambda uid, path: seen.setdefault("uid", uid))
    monkeypatch.setattr(bridge, "inbox_trigger_heartbeat", lambda: pytest.fail("should not drop sentinel on host"))
    r = client.post("/api/inbox/upload", headers=AUTH, files=_file())
    assert r.status_code == 202
    assert r.json() == {"id": "abc", "filename": "x.pptx", "status": "queued"}
    assert seen["uid"] == "abc"  # BackgroundTasks ran after the response


def test_upload_docker_fallback_drops_sentinel(monkeypatch):
    monkeypatch.setattr(bridge, "inbox_save", lambda filename, content: Path("/vault/inbox/x.pdf"))
    monkeypatch.setattr(bridge, "inbox_enqueue", lambda filename: {"id": "id1", "filename": filename, "status": "queued"})
    monkeypatch.setattr(bridge, "inbox_deps_available", lambda: False)
    dropped = {}
    monkeypatch.setattr(bridge, "inbox_trigger_heartbeat", lambda: dropped.setdefault("hit", True))
    monkeypatch.setattr(bridge, "inbox_process_upload", lambda uid, path: pytest.fail("should not process in-proc"))
    r = client.post("/api/inbox/upload", headers=AUTH, files=_file("x.pdf"))
    assert r.status_code == 202
    assert dropped["hit"] is True


def test_upload_bad_extension_is_415():
    r = client.post("/api/inbox/upload", headers=AUTH, files=_file("notes.txt"))
    assert r.status_code == 415


def test_upload_legacy_ppt_is_415():
    r = client.post("/api/inbox/upload", headers=AUTH, files=_file("old.ppt"))
    assert r.status_code == 415
    assert "pptx" in r.json()["detail"].lower()


def test_upload_blank_filename_is_400():
    # Whitespace-only filename (not empty string, which Starlette may treat as a
    # plain form field): it is present but blank after strip -> 400.
    r = client.post("/api/inbox/upload", headers=AUTH, files={"file": ("   ", b"data", "application/octet-stream")})
    assert r.status_code == 400


def test_upload_too_large_is_413(monkeypatch):
    monkeypatch.setattr(bridge, "MAX_UPLOAD_BYTES", 3)
    monkeypatch.setattr(bridge, "inbox_save", lambda filename, content: pytest.fail("must reject before save"))
    r = client.post("/api/inbox/upload", headers=AUTH, files=_file("x.pptx", b"too-long"))
    assert r.status_code == 413


def test_uploads_list_ok(monkeypatch):
    monkeypatch.setattr(bridge, "inbox_recent", lambda limit=10: [{"id": "1", "filename": "a.pptx", "status": "done"}])
    r = client.get("/api/inbox/uploads", headers=AUTH)
    assert r.status_code == 200
    assert r.json()[0]["status"] == "done"


def test_uploads_list_requires_auth():
    assert client.get("/api/inbox/uploads").status_code == 401
