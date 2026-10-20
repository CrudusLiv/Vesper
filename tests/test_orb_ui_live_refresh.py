"""voice/static/orb.html must act on the `data_changed` broadcast that
voice/tools/calendar.py emits after a write. Without the handler the
Calendar pane only refreshed on tab open, so a reminder added mid-
conversation stayed invisible while that tab was already on screen.
Parses the raw script text; no browser involved."""
from __future__ import annotations

import re
from pathlib import Path

ORB_HTML = Path(__file__).resolve().parents[1] / "voice" / "static" / "orb.html"


def _ws_handler() -> str:
    src = ORB_HTML.read_text(encoding="utf-8")
    block = re.search(r"ws\.onmessage = \(\{ data \}\) => \{(.*?)\n  \};", src, re.S)
    assert block, "could not find the WebSocket onmessage handler in orb.html"
    return block.group(1)


def test_onmessage_handles_data_changed():
    assert "ev.type === 'data_changed'" in _ws_handler()


def test_calendar_scope_triggers_a_calendar_reload():
    handler = _ws_handler()
    branch = handler[handler.index("ev.type === 'data_changed'"):]
    assert "'calendar'" in branch
    assert "loadCalendar()" in branch


def test_reload_is_gated_on_the_calendar_tab_being_open():
    """Refetching a hidden pane burns a Google API call for nothing --
    the pane refetches on open anyway (see the .ptab click handler)."""
    handler = _ws_handler()
    branch = handler[handler.index("ev.type === 'data_changed'"):]
    assert "ptab.active" in branch
