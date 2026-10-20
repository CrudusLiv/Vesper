"""Local pytest runner for the once-daily build/test watcher — this repo
has no per-commit CI (only a manual-tag release build), so the only way
to catch a broken test locally is to actually run the suite."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_FAILED_RE = re.compile(r"(\d+) failed")
_PASSED_RE = re.compile(r"(\d+) passed")
_ERRORS_RE = re.compile(r"(\d+) errors?")
_FAILURE_LINE_RE = re.compile(r"^(?:FAILED|ERROR) (\S+)", re.MULTILINE)


def _parse_summary(line: str) -> dict:
    failed_match = _FAILED_RE.search(line)
    passed_match = _PASSED_RE.search(line)
    errors_match = _ERRORS_RE.search(line)
    return {
        "passed": int(passed_match.group(1)) if passed_match else 0,
        "failed": int(failed_match.group(1)) if failed_match else 0,
        "errors": int(errors_match.group(1)) if errors_match else 0,
    }


def describe_failure(result: dict, max_names: int = 3) -> str:
    """One-line notice text saying *what* broke and where the full output is."""
    if result.get("error"):
        return f"Build watch: test run didn't complete ({result['error']})."
    names = [n.rsplit("/", 1)[-1] for n in result.get("failures", [])]
    shown = ", ".join(names[:max_names]) + (f" (+{len(names) - max_names} more)" if len(names) > max_names else "")
    counts = f"{result.get('failed', 0)} failed, {result.get('errors', 0)} errors"
    msg = f"Build watch: {counts} locally" + (f": {shown}" if shown else f" (pytest exit {result.get('exit_code')})")
    return msg + (f". Log: {result['log']}" if result.get("log") else ".")


def run_test_suite(repo_root: Path, timeout: int = 300, log_path: Path | None = None) -> dict:
    """Run `py -m pytest -q` in repo_root. Returns passed/failed/errors counts,
    the node ids of what broke (`failures`), pytest's exit code, and an `ok`
    flag. When `log_path` is given the full stdout+stderr is saved there.
    Never raises — a failure to even launch pytest counts as not-ok so the
    caller still gets a notice."""
    try:
        result = subprocess.run(
            ["py", "-m", "pytest", "-q", "-rfE", "tests/"],
            cwd=repo_root, capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"passed": 0, "failed": 0, "errors": 0, "failures": [],
                "ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if log_path is not None:
        try:
            log_path.write_text(result.stdout + "\n--- stderr ---\n" + result.stderr, encoding="utf-8")
        except OSError:
            log_path = None

    summary_line = ""
    for line in reversed(result.stdout.splitlines()):
        if "passed" in line or "failed" in line or "no tests ran" in line or "error" in line:
            summary_line = line
            break
    return {
        **_parse_summary(summary_line),
        "failures": _FAILURE_LINE_RE.findall(result.stdout),
        "exit_code": result.returncode,
        "log": str(log_path) if log_path else None,
        "ok": result.returncode == 0,
    }
