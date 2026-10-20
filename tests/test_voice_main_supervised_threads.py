"""voice/main.py's daemon-thread launch sites go through supervisor.supervise()
instead of raw threading.Thread(...).start(), so a crash restarts instead of
dying silently."""
from __future__ import annotations

import queue
import threading
from unittest.mock import patch

from voice import main


def test_proactive_speaker_is_supervised():
    with patch("voice.supervisor.supervise") as mock_supervise:
        q: "queue.Queue[str]" = queue.Queue()
        stop = threading.Event()
        main._start_proactive_speaker(q, stop)

    mock_supervise.assert_called_once()
    args, kwargs = mock_supervise.call_args
    assert args[0] == "vesper-proactive-speaker"
    assert args[1] is main._proactive_speaker_loop
    assert kwargs.get("stop_event") is stop


def test_screen_read_hotkeys_is_supervised():
    with patch("voice.screen_overlay.ScreenOverlay"), \
         patch("voice.screen_read_hotkeys.ScreenReadHotkeys") as MockHotkeys, \
         patch("voice.supervisor.supervise") as mock_supervise:
        main._maybe_start_screen_read({"screen_read_enabled": True})

    mock_supervise.assert_called_once()
    args, kwargs = mock_supervise.call_args
    assert args[0] == "vesper-screen-read"
    assert args[1] == MockHotkeys.return_value.run
    assert "stop_event" in kwargs
