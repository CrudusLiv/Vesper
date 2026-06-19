from __future__ import annotations
import sys
from pathlib import Path

from kernel.app import VesperApp
from kernel.events import Tick, VaultWrite, Notify

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".claude" / "scripts"))
from core import inbox  # noqa: E402


class InboxApp(VesperApp):
    name = "inbox"
    version = "1.0"
    subscribes = [Tick]

    def on_tick(self, event: Tick) -> None:
        results = inbox.process_new_files()
        for r in results:
            note_path = r.get("path")
            title = r.get("title") or r.get("source") or "unknown"
            doc_type = r.get("type", "lecture")
            name = r.get("name", "")
            cards = r.get("study_cards", 0)
            tldr = r.get("tldr") or []

            if note_path:
                self.emit(VaultWrite(path=note_path, kind="created"))

            summary = f"[{doc_type.upper()}] {name} — {title}"
            if tldr:
                summary += "\n" + "\n".join(f"• {line}" for line in tldr[:3])
            if cards:
                summary += f"\n{cards} study cards generated."
            self.emit(Notify(text=summary, channel="heartbeat"))
            self.log(f"processed: {title}")
