"""Tests for backfill_lectures.py: frontmatter parser + dry-run behaviour."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKFILL = ROOT / ".claude" / "scripts" / "heartbeat" / "backfill_lectures.py"


def _fresh_backfill():
    """Import backfill_lectures.py fresh each time (no module cache reuse)."""
    # Ensure heartbeat package is importable for the script's internal imports.
    scripts = ROOT / ".claude" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("backfill_lectures", BACKFILL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── _parse_frontmatter ────────────────────────────────────────────────────


def test_parse_frontmatter_extracts_course_source_date():
    bl = _fresh_backfill()
    note = (
        "---\n"
        "type: lecture\n"
        "course: DIP215\n"
        "source_file: Lecture 3.pptx\n"
        "date: 2026-05-11\n"
        "tags: [lecture, DIP215]\n"
        "---\n"
        "\n# Lecture 3\n"
    )
    fm = bl._parse_frontmatter(note)
    assert fm["course"] == "DIP215"
    assert fm["source_file"] == "Lecture 3.pptx"
    assert fm["date"] == "2026-05-11"


def test_parse_frontmatter_empty_when_no_delimiter():
    bl = _fresh_backfill()
    assert bl._parse_frontmatter("# Just a title\n\nSome text") == {}


def test_parse_frontmatter_empty_when_only_opening_dash():
    bl = _fresh_backfill()
    # No closing `---`, treat as malformed.
    assert bl._parse_frontmatter("---\ncourse: DIP215\n") == {}


# ── main(): dry run + skip-already-posted ────────────────────────────────


def _make_vault(tmp_path: Path, files: dict[str, str]) -> Path:
    """Build a temporary vault rooted at tmp_path/Memory with given files."""
    vault = tmp_path / "Memory"
    for rel, body in files.items():
        f = vault / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return vault


def _redirect(bl, vault: Path):
    bl.VAULT = vault
    bl.LECTURES = vault / "lectures"
    bl.MANIFEST = vault / "state" / "discord-lectures-posted.json"
    bl.SLEEP_BETWEEN_POSTS = 0  # don't actually sleep in tests


def test_main_dry_run_no_webhook(tmp_path: Path):
    """When dashboard.notify returns None, no manifest entry is written."""
    note = (
        "---\ntype: lecture\ncourse: TEST\nsource_file: t.pptx\ndate: 2026-05-11\n---\n"
        "# Test lecture\n\n"
        "## Key concepts\n- A concept\n\n"
        "## Study cards\n- Q: Q? | A: A\n"
    )
    vault = _make_vault(tmp_path, {"lectures/TEST/2026-05-11_t.md": note})

    bl = _fresh_backfill()
    _redirect(bl, vault)

    with patch.object(bl.dashboard, "notify", return_value=None) as mock_notify:
        bl.main()

    assert mock_notify.call_count == 1
    args, kwargs = mock_notify.call_args
    assert args[0] == "lecture_new"
    payload = args[1]
    assert payload["name"] == "TEST"
    assert payload["date"] == "2026-05-11"
    assert payload["study_cards"] == 1
    assert payload["title"] == "Test lecture"
    assert payload["vault_path"] == "lectures/TEST/2026-05-11_t.md"
    assert payload["tldr"] == ["A concept"]
    assert kwargs["thread_name"] == "[TEST] Test lecture"

    assert not bl.MANIFEST.exists()


def test_main_skips_already_posted(tmp_path: Path):
    """Lectures already in the manifest are not re-posted."""
    note = "---\ntype: lecture\ncourse: TEST\nsource_file: t.pptx\ndate: 2026-05-11\n---\n# T\n"
    vault = _make_vault(tmp_path, {"lectures/TEST/2026-05-11_t.md": note})

    rel = "lectures/TEST/2026-05-11_t.md"
    manifest_path = vault / "state" / "discord-lectures-posted.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({rel: "111222333"}), encoding="utf-8")

    bl = _fresh_backfill()
    _redirect(bl, vault)

    with patch.object(bl.dashboard, "notify") as mock_notify:
        bl.main()

    mock_notify.assert_not_called()


def test_main_writes_manifest_on_successful_post(tmp_path: Path):
    """A truthy result from dashboard.notify records the thread id."""
    note = (
        "---\ntype: lecture\ncourse: CS101\nsource_file: x.pptx\ndate: 2026-05-12\n---\n"
        "# Intro\n\n## Key concepts\n- A\n- B\n\n## Study cards\n- Q: q | A: a\n"
    )
    vault = _make_vault(tmp_path, {"lectures/CS101/2026-05-12_intro.md": note})

    bl = _fresh_backfill()
    _redirect(bl, vault)

    with patch.object(bl.dashboard, "notify", return_value={"id": "999000111"}):
        bl.main()

    assert bl.MANIFEST.exists()
    written = json.loads(bl.MANIFEST.read_text(encoding="utf-8"))
    assert written == {"lectures/CS101/2026-05-12_intro.md": "999000111"}


def test_main_thread_name_truncated_to_100_chars(tmp_path: Path):
    long_title = "Very long lecture title that goes on and on and on and on and on and on and on and on indeed"
    note = (
        f"---\ntype: lecture\ncourse: COURSE\nsource_file: s.pptx\ndate: 2026-05-12\n---\n"
        f"# {long_title}\n"
    )
    vault = _make_vault(tmp_path, {"lectures/COURSE/x.md": note})

    bl = _fresh_backfill()
    _redirect(bl, vault)

    with patch.object(bl.dashboard, "notify", return_value=None) as mock_notify:
        bl.main()

    thread_name = mock_notify.call_args.kwargs["thread_name"]
    assert len(thread_name) <= 100
    assert thread_name.startswith("[COURSE] ")
