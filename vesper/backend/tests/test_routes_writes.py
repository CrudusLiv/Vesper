from fastapi.testclient import TestClient

import app.bridge as bridge
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-secret"}


def test_finance_requires_auth():
    assert client.post("/api/finance", json={"amount": 5, "category": "food"}).status_code == 401


def test_finance_ok(monkeypatch):
    monkeypatch.setattr(bridge, "finance_log", lambda amount, category, note="": {
        "date": "06-03 12:00", "month_total": 5.0, "category_total": 5.0, "currency": "RM",
    })
    r = client.post("/api/finance", headers=AUTH, json={"amount": 5, "category": "food", "note": "x"})
    assert r.status_code == 200
    assert r.json()["currency"] == "RM"


def test_finance_rejects_nonpositive_amount():
    r = client.post("/api/finance", headers=AUTH, json={"amount": 0, "category": "food"})
    assert r.status_code == 400


def test_finance_rejects_blank_category():
    r = client.post("/api/finance", headers=AUTH, json={"amount": 5, "category": "   "})
    assert r.status_code == 400


def test_finance_summary_ok(monkeypatch):
    monkeypatch.setattr(bridge, "finance_summary", lambda: {"summary": "June 2026 -- RM5.00 total"})
    r = client.get("/api/finance/summary", headers=AUTH)
    assert r.status_code == 200
    assert "RM5.00" in r.json()["summary"]


def test_note_requires_auth():
    assert client.post("/api/note", json={"text": "hi"}).status_code == 401


def test_note_ok(monkeypatch):
    monkeypatch.setattr(bridge, "note_append", lambda text: {"ok": True, "appended_chars": len(text)})
    r = client.post("/api/note", headers=AUTH, json={"text": "buy milk"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_note_empty_is_422(monkeypatch):
    def boom(text):
        raise ValueError("empty")
    monkeypatch.setattr(bridge, "note_append", boom)
    r = client.post("/api/note", headers=AUTH, json={"text": "   "})
    assert r.status_code == 422


def test_schedule_get_ok(monkeypatch):
    monkeypatch.setattr(bridge, "schedule_get", lambda: {"schedule": "Mon 9-10 Maths"})
    r = client.get("/api/schedule", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["schedule"] == "Mon 9-10 Maths"


def test_schedule_set_ok(monkeypatch):
    monkeypatch.setattr(bridge, "schedule_set", lambda text, confirm: {"written": True, "summary": "ok"})
    r = client.post("/api/schedule", headers=AUTH, json={"text": "mon 9-10 maths", "confirm": False})
    assert r.status_code == 200
    assert r.json() == {"summary": "ok"}


def test_schedule_set_conflict_when_exists(monkeypatch):
    monkeypatch.setattr(bridge, "schedule_set", lambda text, confirm: {"written": False, "summary": "preview"})
    r = client.post("/api/schedule", headers=AUTH, json={"text": "mon 9-10 maths"})
    assert r.status_code == 409
    assert r.json() == {"summary": "preview", "exists": True}


def test_schedule_set_bad_parse_is_422(monkeypatch):
    def boom(text, confirm):
        raise ValueError("bad timetable")
    monkeypatch.setattr(bridge, "schedule_set", boom)
    r = client.post("/api/schedule", headers=AUTH, json={"text": "???"})
    assert r.status_code == 422


def test_schedule_set_llm_down_is_502(monkeypatch):
    def boom(text, confirm):
        raise bridge.LlmError("down")
    monkeypatch.setattr(bridge, "schedule_set", boom)
    r = client.post("/api/schedule", headers=AUTH, json={"text": "mon 9-10 maths"})
    assert r.status_code == 502


def test_vault_list_requires_auth():
    assert client.get("/api/vault/list").status_code == 401


def test_vault_list_ok(monkeypatch):
    monkeypatch.setattr(bridge, "vault_list", lambda directory="": {
        "directory": directory, "entries": [{"name": "notes", "is_dir": True}],
    })
    r = client.get("/api/vault/list?dir=", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["entries"][0]["is_dir"] is True


def test_vault_list_forbidden_is_400(monkeypatch):
    def boom(directory=""):
        raise ValueError("off-limits")
    monkeypatch.setattr(bridge, "vault_list", boom)
    r = client.get("/api/vault/list?dir=finance", headers=AUTH)
    assert r.status_code == 400


def test_vault_delete_ok(monkeypatch):
    monkeypatch.setattr(bridge, "vault_delete", lambda path: {"path": path, "trash_path": "_trash/x"})
    r = client.post("/api/vault/delete", headers=AUTH, json={"path": "notes/x.md"})
    assert r.status_code == 200
    assert r.json()["trash_path"] == "_trash/x"


def test_vault_delete_missing_is_404(monkeypatch):
    def boom(path):
        raise FileNotFoundError(path)
    monkeypatch.setattr(bridge, "vault_delete", boom)
    r = client.post("/api/vault/delete", headers=AUTH, json={"path": "notes/nope.md"})
    assert r.status_code == 404


def test_vault_undo_ok(monkeypatch):
    monkeypatch.setattr(bridge, "vault_undo", lambda: {"message": "nothing to undo"})
    r = client.post("/api/vault/undo", headers=AUTH)
    assert r.status_code == 200
    assert "undo" in r.json()["message"]
