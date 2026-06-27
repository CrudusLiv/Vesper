"""Calendar tool: upcoming Google Calendar events."""
from __future__ import annotations
import voice  # noqa: F401


def upcoming_events(days: int = 7) -> str:
    try:
        from integrations import gcal_int  # type: ignore
        if hasattr(gcal_int, "list_upcoming"):
            events = gcal_int.list_upcoming(days=days)
            if not events:
                return f"No events in the next {days} day(s)."
            lines = [f"{len(events)} event(s) in the next {days} day(s):"]
            for e in events[:10]:
                start = e.get("start", "?")
                summary = e.get("summary", "?")
                lines.append(f"  {start}: {summary}")
            return "\n".join(lines)
        # Fallback: subprocess to query.py
        import subprocess, sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        r = subprocess.run(
            [sys.executable,
             str(root / ".claude" / "scripts" / "query.py"),
             "gcal", "upcoming", "--days", str(days)],
            capture_output=True, text=True, cwd=str(root), timeout=30,
        )
        return (r.stdout or "").strip() or "No upcoming events."
    except Exception as exc:
        return f"Calendar unavailable: {exc}"
