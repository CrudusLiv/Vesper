"""launch_app tool — opens configured app shortcuts."""
from __future__ import annotations

import json
import subprocess
import sys


def launch_app(name: str) -> str:
    from voice import config as cfg
    conf = cfg.load()
    shortcuts: dict = conf.get("app_shortcuts", {})

    key = next((k for k in shortcuts if k.lower() == name.lower()), None)
    if key is None:
        available = ", ".join(shortcuts.keys()) or "none — add entries to app_shortcuts in config.json"
        return json.dumps({"error": f"No shortcut named {name!r}. Available: {available}"})

    cmds = shortcuts[key]
    if isinstance(cmds, str):
        cmds = [cmds]

    launched: list[str] = []
    errors: list[str] = []
    for cmd in cmds:
        try:
            if isinstance(cmd, list):
                subprocess.Popen(cmd)
                launched.append(" ".join(str(c) for c in cmd))
            elif sys.platform == "win32":
                # "start" goes through ShellExecute — finds apps via App Paths registry
                # (bare app names like "spotify" aren't on PATH but are in App Paths)
                subprocess.Popen(f'start "" "{cmd}"', shell=True)
                launched.append(cmd)
            else:
                subprocess.Popen(cmd.split())
                launched.append(cmd)
        except Exception as exc:
            errors.append(f"{cmd}: {exc}")

    if errors:
        return json.dumps({"launched": launched, "errors": errors})
    return json.dumps({"launched": launched, "status": "ok"})
