"""Tests for .claude/scripts/memory_reflect.py::curate_knowledge() -- the
concept/research extraction lane added alongside the existing
decisions/lessons/facts curation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

import memory_reflect  # noqa: E402


def test_curate_knowledge_empty_items_returns_zero():
    assert memory_reflect.curate_knowledge({}) == 0
    assert memory_reflect.curate_knowledge(None) == 0


def test_curate_knowledge_writes_concepts_and_research(monkeypatch):
    concept_calls = []
    research_calls = []
    monkeypatch.setattr(
        memory_reflect.knowledge, "upsert_concept",
        lambda title, entry, date, source_date=None, tags=None: concept_calls.append(
            (title, entry, date, source_date)
        ) or True,
    )
    monkeypatch.setattr(
        memory_reflect.knowledge, "upsert_research",
        lambda title, entry, date, source_date=None: research_calls.append(
            (title, entry, date, source_date)
        ) or True,
    )
    items = {
        "new_concepts": [{"title": "Recursion", "note": "Calls itself."}],
        "new_research": [{"title": "Distributed Systems", "note": "Consensus algorithms."}],
    }
    written = memory_reflect.curate_knowledge(items)
    assert written == 2
    assert concept_calls == [("Recursion", "Calls itself.", memory_reflect.today_kl(), memory_reflect.yesterday_kl())]
    assert research_calls == [
        ("Distributed Systems", "Consensus algorithms.", memory_reflect.today_kl(), memory_reflect.yesterday_kl())
    ]


def test_curate_knowledge_skips_malformed_items(monkeypatch):
    calls = []
    monkeypatch.setattr(memory_reflect.knowledge, "upsert_concept", lambda *a, **k: calls.append(1) or True)
    monkeypatch.setattr(memory_reflect.knowledge, "upsert_research", lambda *a, **k: calls.append(1) or True)
    items = {
        "new_concepts": ["not a dict", {"title": "", "note": "x"}, {"title": "x", "note": ""}, {"note": "missing title"}],
        "new_research": [None],
    }
    assert memory_reflect.curate_knowledge(items) == 0
    assert calls == []


def test_curate_knowledge_only_counts_actual_writes(monkeypatch):
    monkeypatch.setattr(memory_reflect.knowledge, "upsert_concept", lambda *a, **k: False)
    items = {"new_concepts": [{"title": "Recursion", "note": "Already captured today."}]}
    assert memory_reflect.curate_knowledge(items) == 0


def test_append_to_memory_inserts_stances_into_existing_section(tmp_path, monkeypatch):
    target = tmp_path / "MEMORY.md"
    target.write_text("## Decisions\n- old decision\n\n## Stances\n\n## Open questions\n", encoding="utf-8")
    monkeypatch.setattr(memory_reflect, "MEMORY", target)
    n = memory_reflect.append_to_memory({"new_stances": ["Sleep before exams matters."]})
    text = target.read_text(encoding="utf-8")
    assert n == 1
    assert "## Stances" in text
    assert "Sleep before exams matters." in text
    # inserted before the next section, not appended past it
    assert text.index("Sleep before exams matters.") < text.index("## Open questions")


def test_append_to_memory_noop_when_stances_section_missing(tmp_path, monkeypatch):
    target = tmp_path / "MEMORY.md"
    target.write_text("## Decisions\n- old decision\n", encoding="utf-8")
    monkeypatch.setattr(memory_reflect, "MEMORY", target)
    n = memory_reflect.append_to_memory({"new_stances": ["Something."]})
    assert n == 0
    assert "Something." not in target.read_text(encoding="utf-8")
