"""One-off smoke test for the Discord DM notify path. Delete when done."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations"))

import _env  # noqa: F401  -- loads .env
from heartbeat import notify

notify.send("Smoke test", "DM path works.", "normal")
print("done")
