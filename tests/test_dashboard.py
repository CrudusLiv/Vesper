"""Discord embed formatters in heartbeat.dashboard.

All tests pass an explicit `ts` into payloads so the footer time is
deterministic. Discord rate-limited paths are not exercised; we only
assert on the dict shape returned by format_embed."""
from __future__ import annotations

import sys
from pathlib import Path


def _import_dashboard():
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / ".claude" / "scripts"))
    from heartbeat import dashboard  # type: ignore
    return dashboard


# A fixed unix timestamp inside KL (2026-05-27 13:00 KL == 05:00 UTC).
FIXED_TS = 1779_858_000.0
FIXED_WHEN = "13:00 KL"
