# kernel/apps/heartbeat_app.py
"""Wraps the entire existing heartbeat tick as a single kernel app.

All existing heartbeat logic is preserved unchanged — this is a thin adapter
that calls heartbeat.tick() on each Tick event, subject to active-hours gating.
Future iterations can extract individual tasks into their own apps."""
from __future__ import annotations
import sys
import traceback
from pathlib import Path

from kernel.app import VesperApp
from kernel.events import Tick

_SCRIPTS = Path(__file__).resolve().parents[2] / ".claude" / "scripts"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "integrations"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from heartbeat import in_active_hours  # noqa: E402


def _run_heartbeat_tick() -> None:
    import heartbeat as hb
    hb.tick()


class HeartbeatApp(VesperApp):
    name = "heartbeat"
    version = "1.0"
    subscribes = [Tick]

    def on_tick(self, event: Tick) -> None:
        if not in_active_hours():
            self.log("outside active hours — skipping tick")
            return
        try:
            _run_heartbeat_tick()
        except Exception as exc:
            self.log(f"tick failed: {exc}")
            traceback.print_exc()
