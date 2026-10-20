"""Tests for voice/supervisor.py -- daemon-thread crash/restart supervision."""
from __future__ import annotations

import threading
import time

import pytest

from voice import supervisor


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Backoff sleeps would make these tests slow; replace with a no-op
    that just records how long it was asked to sleep."""
    calls: list[float] = []
    monkeypatch.setattr(supervisor.time, "sleep", lambda s: calls.append(s))
    return calls


@pytest.fixture(autouse=True)
def _clean_registry():
    """The registry is module-level global state -- each test starts fresh
    so results from one test's thread names never leak into another's."""
    supervisor._registry.clear()
    yield
    supervisor._registry.clear()


def _wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        threading.Event().wait(0.01)  # time.sleep is patched out by the autouse fixture
    return False


def test_clean_return_does_not_restart():
    calls = []

    def target():
        calls.append(1)

    t = supervisor.supervise("t-clean", target)
    t.join(timeout=2.0)
    assert not t.is_alive()
    assert calls == [1]
    snap = supervisor.registry_snapshot()
    assert snap["t-clean"]["alive"] is False
    assert snap["t-clean"]["restarts"] == 0


def test_crash_then_success_restarts_once():
    calls = []

    def target():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        # second call: return cleanly, ending supervision

    t = supervisor.supervise("t-crash-once", target)
    assert _wait_until(lambda: len(calls) == 2)
    t.join(timeout=2.0)
    assert not t.is_alive()
    snap = supervisor.registry_snapshot()
    assert snap["t-crash-once"]["restarts"] == 1
    assert "boom" in snap["t-crash-once"]["last_error"]


def test_stop_event_set_at_crash_time_prevents_restart():
    stop_event = threading.Event()
    calls = []

    def target(stop_event):
        calls.append(1)
        stop_event.set()
        raise RuntimeError("boom during shutdown")

    t = supervisor.supervise("t-stop-guard", target, stop_event=stop_event)
    t.join(timeout=2.0)
    assert not t.is_alive()
    assert calls == [1]  # never restarted
    assert supervisor.registry_snapshot()["t-stop-guard"]["restarts"] == 1


def test_fast_fail_doubles_backoff(_no_real_sleep):
    calls = []

    def target():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("boom")  # crashes fast every time -> fast-fail path

    t = supervisor.supervise("t-backoff", target)
    assert _wait_until(lambda: len(calls) == 3)
    t.join(timeout=2.0)
    # two crashes before the clean 3rd call -> two backoff sleeps, doubling
    assert _no_real_sleep[0] == supervisor._MIN_BACKOFF_S
    assert _no_real_sleep[1] == supervisor._MIN_BACKOFF_S * 2


def test_stable_run_resets_backoff(_no_real_sleep, monkeypatch):
    calls = []
    monkeypatch.setattr(supervisor, "_FAST_FAIL_WINDOW_S", 0)  # every run counts as stable

    def target():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("boom")

    t = supervisor.supervise("t-reset", target)
    assert _wait_until(lambda: len(calls) == 3)
    t.join(timeout=2.0)
    assert _no_real_sleep[0] == supervisor._MIN_BACKOFF_S
    assert _no_real_sleep[1] == supervisor._MIN_BACKOFF_S  # reset, not doubled


def test_registry_snapshot_is_a_copy_not_live_reference():
    supervisor.supervise("t-copy", lambda: None).join(timeout=2.0)
    snap = supervisor.registry_snapshot()
    snap["t-copy"]["restarts"] = 999
    assert supervisor.registry_snapshot()["t-copy"]["restarts"] == 0
