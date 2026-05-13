"""Shared fixtures for second-brain plan tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_vault(tmp_path: Path, monkeypatch) -> Path:
    """Materialise a minimal vault under tmp_path and point modules at it.

    Modules under .claude/scripts/ derive VAULT from CLAUDE_PROJECT_DIR,
    so setting that env var redirects them at the temp tree."""
    vault = tmp_path / "Dynamous" / "Memory"
    (vault / "daily").mkdir(parents=True)
    (vault / "lectures").mkdir(parents=True)
    (vault / "projects").mkdir(parents=True)
    (vault / "finance").mkdir(parents=True)
    (vault / "inbox" / "_processed").mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    return vault


@pytest.fixture
def tmp_data(tmp_path: Path, monkeypatch) -> Path:
    """Provide an isolated .claude/data/ for state files."""
    data = tmp_path / ".claude" / "data"
    data.mkdir(parents=True)
    return data
