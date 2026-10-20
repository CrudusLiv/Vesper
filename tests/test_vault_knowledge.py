"""Tests for .claude/scripts/vault/knowledge.py -- the concept/research
note writer used by memory_reflect.py's nightly curation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

from vault import knowledge  # noqa: E402


def test_existing_titles_empty_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "CONCEPTS_DIR", tmp_path / "concepts")
    assert knowledge.existing_titles("concepts") == []


def test_existing_titles_lists_stems_sorted(tmp_path, monkeypatch):
    d = tmp_path / "concepts"
    d.mkdir()
    (d / "recursion.md").write_text("x", encoding="utf-8")
    (d / "big-o-notation.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(knowledge, "CONCEPTS_DIR", d)
    assert knowledge.existing_titles("concepts") == ["big-o-notation", "recursion"]


def test_upsert_concept_creates_file_with_frontmatter(tmp_path, monkeypatch):
    d = tmp_path / "concepts"
    monkeypatch.setattr(knowledge, "CONCEPTS_DIR", d)
    ok = knowledge.upsert_concept(
        "Recursion", "A function that calls itself.", "2026-09-17",
        tags=["cs", "bit216"], source_date="2026-09-16",
    )
    assert ok is True
    text = (d / "recursion.md").read_text(encoding="utf-8")
    assert "title: Recursion" in text
    assert "created: 2026-09-17" in text
    assert "tags: [cs, bit216]" in text
    assert "# Recursion" in text
    assert "## 2026-09-17" in text
    assert "A function that calls itself." in text
    assert "(from [[2026-09-16]])" in text


def test_upsert_concept_appends_dated_section_to_existing_note(tmp_path, monkeypatch):
    d = tmp_path / "concepts"
    monkeypatch.setattr(knowledge, "CONCEPTS_DIR", d)
    knowledge.upsert_concept("Recursion", "First entry.", "2026-09-17")
    knowledge.upsert_concept("Recursion", "Second entry, different day.", "2026-09-18")
    text = (d / "recursion.md").read_text(encoding="utf-8")
    assert text.count("# Recursion") == 1  # heading not duplicated
    assert "## 2026-09-17" in text
    assert "## 2026-09-18" in text
    assert "First entry." in text
    assert "Second entry, different day." in text


def test_upsert_concept_dedupes_same_entry_same_day(tmp_path, monkeypatch):
    d = tmp_path / "concepts"
    monkeypatch.setattr(knowledge, "CONCEPTS_DIR", d)
    knowledge.upsert_concept("Recursion", "A function that calls itself.", "2026-09-17")
    ok = knowledge.upsert_concept("Recursion", "A function that calls itself.", "2026-09-17")
    text = (d / "recursion.md").read_text(encoding="utf-8")
    assert ok is False
    assert text.count("A function that calls itself.") == 1


def test_upsert_concept_noop_on_empty_title_or_entry(tmp_path, monkeypatch):
    d = tmp_path / "concepts"
    monkeypatch.setattr(knowledge, "CONCEPTS_DIR", d)
    assert knowledge.upsert_concept("", "entry", "2026-09-17") is False
    assert knowledge.upsert_concept("Title", "  ", "2026-09-17") is False
    assert not d.exists()


def test_upsert_research_creates_file_without_tags(tmp_path, monkeypatch):
    d = tmp_path / "research"
    monkeypatch.setattr(knowledge, "RESEARCH_DIR", d)
    ok = knowledge.upsert_research("Distributed Systems", "Explored consensus algorithms.", "2026-09-17")
    assert ok is True
    text = (d / "distributed-systems.md").read_text(encoding="utf-8")
    assert "title: Distributed Systems" in text
    assert "tags:" not in text
    assert "Explored consensus algorithms." in text


def test_slugify_handles_punctuation_and_spacing():
    assert knowledge._slugify("Big-O Notation!") == "big-o-notation"
    assert knowledge._slugify("  Recursion  ") == "recursion"
    assert knowledge._slugify("!!!") == "untitled"
