"""Subprocess wrapper around `claude -p` so the heartbeat reasons over data.

Auth: we inject CLAUDE_CODE_OAUTH_TOKEN from a long-lived token tied to the
Max subscription (no per-token billing). `--bare` cannot be used here -- it
strictly accepts ANTHROPIC_API_KEY-style API keys, but setup-token issues
oat-prefixed OAuth tokens that the API rejects via the API-key header.
Setup:

    1. Run `claude setup-token` interactively.
    2. Save the token to `.claude/data/claude-token.txt` (one line, no quotes).
       That path is gitignored.

To still avoid booting hooks/skills/MCP on every call we pass
`--setting-sources user` (skip project settings.json, where the heartbeat's
own session-end-flush hook lives) and `--disable-slash-commands`."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

CLAUDE_BIN = shutil.which("claude") or "claude"
DEFAULT_MODEL = "haiku"
DEFAULT_TIMEOUT = 120
TOKEN_FILE = Path(__file__).resolve().parents[2] / "data" / "claude-token.txt"

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "llm-config.json"
_DEFAULTS: dict = {
    "default_backend": "claude",
    "fallback_backend": None,
    "backends": {
        "claude": {"type": "claude"},
    },
    "routing": {},
}
_config_cache: dict | None = None


def _load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    try:
        raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        _config_cache = {**_DEFAULTS, **raw}
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[llm] config load failed ({exc}), using defaults", file=sys.stderr)
        _config_cache = dict(_DEFAULTS)
    return _config_cache



def _build_env() -> dict[str, str]:
    """Return a copy of os.environ with CLAUDE_CODE_OAUTH_TOKEN set from the
    token file. The file wins over any pre-existing env value. We also clear
    ANTHROPIC_API_KEY so a stray paid key in the parent env doesn't override
    Max-plan billing."""
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    try:
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        token = ""
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    return env


def is_available() -> bool:
    """Quick check that the `claude` CLI is on PATH and runs."""
    if not shutil.which("claude"):
        return False
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _call_claude(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    cmd: list[str] = [
        CLAUDE_BIN, "-p",
        "--setting-sources", "user",
        "--disable-slash-commands",
        "--model", model,
        "--output-format", "json",
    ]
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", env=_build_env(),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"[llm.call] {type(exc).__name__}: {exc}", file=sys.stderr)
        return ""

    if result.returncode != 0:
        err = (result.stderr or "")[:500]
        print(f"[llm.call] non-zero exit {result.returncode}: {err}", file=sys.stderr)
        return ""

    out = (result.stdout or "").strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return out
    if data.get("is_error"):
        msg = (data.get("result") or "claude returned is_error=true").strip()
        print(f"[llm.call] CLI returned is_error: {msg}", file=sys.stderr)
        return ""
    return (data.get("result") or "").strip()


def _resolve_backend(task: Optional[str]) -> tuple[str, Optional[str]]:
    """Return (backend_name, model_override_or_None)."""
    force = os.environ.get("LLM_FORCE_BACKEND")
    if force:
        return force, None
    config = _load_config()
    if task:
        route = config.get("routing", {}).get(task)
        if route:
            return route["backend"], route.get("model")
    return config.get("default_backend", "claude"), None


def call(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    task: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Send prompt to the configured backend, return text. Empty string on failure."""
    backend, model_override = _resolve_backend(task)
    effective_model = model_override or model

    if backend == "claude":
        return _call_claude(prompt, system_prompt=system_prompt, model=effective_model, timeout=timeout)

    return ""


def call_json(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    task: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
):
    """Convenience: parse the LLM's response as JSON. Returns None on parse failure.

    Strips markdown code fences if the model wraps JSON in them despite instructions."""
    text = call(prompt, system_prompt=system_prompt, model=model, task=task, timeout=timeout)
    if not text:
        return None
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Tolerate prose around the JSON: models sometimes add a trailing remark
    # ("That's 8 entries.") or a lead-in despite instructions. Decode the first
    # JSON value starting at the first bracket and ignore any trailing data.
    start = next((i for i, c in enumerate(text) if c in "[{"), -1)
    if start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            return obj
        except json.JSONDecodeError:
            pass
    print(f"[llm.call_json] parse failed\nResponse: {text[:500]}", file=sys.stderr)
    return None
