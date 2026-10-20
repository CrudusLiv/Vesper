"""ui_server.start() and Heartbeat.start() launch their daemon thread
through supervisor.supervise() instead of raw threading.Thread(...)."""
from __future__ import annotations

import queue
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _no_live_llm_probe(monkeypatch):
    from voice import llm
    monkeypatch.setattr(
        llm, "get_status",
        lambda: {"backend": "claude_cli", "model": "sonnet", "available": True},
    )


def test_ui_server_start_is_supervised(monkeypatch):
    from voice import ui_server
    monkeypatch.setattr("threading.Event.wait", lambda self, timeout=None: None)
    with patch("voice.supervisor.supervise") as mock_supervise:
        ui_server.start(port=17070, host="127.0.0.1")

    mock_supervise.assert_called_once()
    args, _ = mock_supervise.call_args
    assert args[0] == "vesper-ui"


def test_heartbeat_start_is_supervised():
    from voice.heartbeat import Heartbeat
    hb = Heartbeat(interval_minutes=30, idle_fn=lambda: None, speak_queue=queue.Queue())
    with patch("voice.supervisor.supervise") as mock_supervise:
        hb.start()

    mock_supervise.assert_called_once()
    args, _ = mock_supervise.call_args
    assert args[0] == "vesper-heartbeat"
    assert args[1] == hb._loop
