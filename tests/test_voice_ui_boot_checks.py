# tests/test_voice_ui_boot_checks.py
"""GET /cmd/boot-checks -- shape and failure isolation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_live_llm_probe(monkeypatch):
    """_llm() calls voice.llm.get_status(), which auto-detects the backend by
    opening a live socket to localhost (Ollama/LM Studio). In sandboxed or
    firewalled environments that connect can hang well past its own declared
    timeout, taking the whole test run down with it -- stub it so boot-check
    tests never touch the network."""
    from voice import llm

    monkeypatch.setattr(
        llm, "get_status",
        lambda: {"backend": "claude_cli", "model": "sonnet", "available": True},
    )


@pytest.fixture
def client():
    from voice import ui_server
    return TestClient(ui_server.app)


def test_returns_checks_list(client):
    resp = client.get("/cmd/boot-checks")
    assert resp.status_code == 200
    checks = resp.json()["checks"]
    assert checks and isinstance(checks, list)


def test_each_check_has_the_full_shape(client):
    for row in client.get("/cmd/boot-checks").json()["checks"]:
        assert set(row) == {"id", "label", "detail", "status", "error"}


def test_one_raising_probe_does_not_500(client, monkeypatch):
    from voice import boot_checks

    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setitem(boot_checks.PROBES, "llm", ("LLM", boom))
    resp = client.get("/cmd/boot-checks")
    assert resp.status_code == 200
    rows = {r["id"]: r for r in resp.json()["checks"]}
    assert rows["llm"]["status"] == "fail"
    assert "kaboom" in rows["llm"]["error"]


def test_threads_probe_skips_when_registry_empty(client, monkeypatch):
    from voice import supervisor
    monkeypatch.setattr(supervisor, "_registry", {})
    rows = {r["id"]: r for r in client.get("/cmd/boot-checks").json()["checks"]}
    assert rows["threads"]["status"] == "skip"


def test_threads_probe_ok_when_all_alive(client, monkeypatch):
    from voice import supervisor
    monkeypatch.setattr(supervisor, "_registry", {
        "vesper-clap": {"alive": True, "restarts": 0, "last_error": None, "last_restart_ts": None},
        "vesper-heartbeat": {"alive": True, "restarts": 2, "last_error": None, "last_restart_ts": None},
    })
    rows = {r["id"]: r for r in client.get("/cmd/boot-checks").json()["checks"]}
    assert rows["threads"]["status"] == "ok"
    assert "2 restart" in rows["threads"]["detail"]


def test_threads_probe_fails_naming_the_dead_thread(client, monkeypatch):
    from voice import supervisor
    monkeypatch.setattr(supervisor, "_registry", {
        "vesper-clap": {"alive": False, "restarts": 1, "last_error": "boom", "last_restart_ts": None},
        "vesper-heartbeat": {"alive": True, "restarts": 0, "last_error": None, "last_restart_ts": None},
    })
    rows = {r["id"]: r for r in client.get("/cmd/boot-checks").json()["checks"]}
    assert rows["threads"]["status"] == "fail"
    assert "vesper-clap" in rows["threads"]["detail"]


def test_threads_probe_ignores_cleanly_exited_thread(client, monkeypatch):
    from voice import supervisor
    monkeypatch.setattr(supervisor, "_registry", {
        "vesper-conversation": {"alive": False, "restarts": 0, "last_error": None, "last_restart_ts": None},
    })
    rows = {r["id"]: r for r in client.get("/cmd/boot-checks").json()["checks"]}
    assert rows["threads"]["status"] == "ok"
