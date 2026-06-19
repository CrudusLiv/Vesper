from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any


def _get_project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[1])


PROJECT_DIR = _get_project_dir()

sys.path.insert(0, str(PROJECT_DIR / ".claude" / "scripts"))
sys.path.insert(0, str(PROJECT_DIR / "scripts"))


class VesperApp:
    name: str = ""
    version: str = "1.0"
    subscribes: list = []

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def emit(self, event: Any) -> None:
        self._runtime.post_external(event)

    def log(self, msg: str) -> None:
        print(f"[{self.name}] {msg}", flush=True)

    @property
    def vault(self) -> Path:
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[1])
        return project_dir / "Dynamous" / "Memory"

    @property
    def data(self) -> Path:
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[1])
        return project_dir / ".claude" / "data"
