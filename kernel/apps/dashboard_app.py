# kernel/apps/dashboard_app.py
from __future__ import annotations
import os
import sys
from pathlib import Path

from kernel.app import VesperApp
from kernel.events import Notify

_SCRIPTS = Path(__file__).resolve().parents[2] / ".claude" / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from integrations.discord_webhook import post as _webhook_post  # noqa: E402


def _post_notify(event: Notify) -> None:
    hook_env = {
        "heartbeat": "DISCORD_HOOK_HEARTBEAT",
        "vesper": "DISCORD_HOOK_VESPER",
    }.get(event.channel, "DISCORD_HOOK_HEARTBEAT")

    url = os.environ.get(hook_env)
    if not url:
        return

    if event.embed:
        _webhook_post(url, embeds=[event.embed])
    else:
        _webhook_post(url, content=event.text)


class DashboardApp(VesperApp):
    name = "dashboard"
    version = "1.0"
    subscribes = [Notify]

    def on_notify(self, event: Notify) -> None:
        try:
            _post_notify(event)
        except Exception as exc:
            self.log(f"notify failed: {exc}")
