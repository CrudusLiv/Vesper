"""Tests for vault migration script."""
import pytest
from pathlib import Path

from app.migrations.migrate_vault import (
    migrate_vault,
    _has_frontmatter,
    _infer_type,
    _infer_date,
    _build_frontmatter,
    MigrationResult,
)


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestHasFrontmatter:
    def test_detects_frontmatter(self):
        assert _has_frontmatter("---\ntype: note\n---\nContent") is True

    def test_detects_no_frontmatter(self):
        assert _has_frontmatter("Just a plain note") is False

    def test_empty_file(self):
        assert _has_frontmatter("") is False

    def test_leading_whitespace_still_detected(self):
        assert _has_frontmatter("  ---\ntype: note\n---\n") is True


class TestInferType:
    def test_finance_folder(self, tmp_path):
        f = tmp_path / "finance" / "2026-06-01.md"
        assert _infer_type(f) == "finance"

    def test_schedule_folder(self, tmp_path):
        f = tmp_path / "schedule" / "2026-06-01.md"
        assert _infer_type(f) == "schedule"

    def test_notes_folder_defaults_to_note(self, tmp_path):
        f = tmp_path / "notes" / "reminders.md"
        assert _infer_type(f) == "note"

    def test_root_file_defaults_to_note(self, tmp_path):
        f = tmp_path / "README.md"
        assert _infer_type(f) == "note"


class TestInferDate:
    def test_extracts_date_from_filename(self, tmp_path):
        f = tmp_path / "2026-06-09.md"
        assert _infer_date(f) == "2026-06-09"

    def test_date_in_stem_only(self, tmp_path):
        f = tmp_path / "2025-01-15-journal.md"
        assert _infer_date(f) == "2025-01-15"

    def test_no_date_returns_today(self, tmp_path):
        f = tmp_path / "no-date-here.md"
        date = _infer_date(f)
        # Should be a valid ISO date
        from datetime import datetime
        datetime.strptime(date, "%Y-%m-%d")  # Does not raise


class TestBuildFrontmatter:
    def test_note_frontmatter(self):
        fm = _build_frontmatter("note", "2026-06-09")
        assert "type: note" in fm
        assert "created: '2026-06-09'" in fm or "created: 2026-06-09" in fm
        assert fm.startswith("---\n")
        assert "---\n" in fm[3:]  # closing delimiter exists

    def test_finance_frontmatter_has_category(self):
        fm = _build_frontmatter("finance", "2026-06-01")
        assert "category: uncategorized" in fm
        assert "type: finance" in fm

    def test_schedule_frontmatter_has_times(self):
        fm = _build_frontmatter("schedule", "2026-06-01")
        assert "start_time" in fm
        assert "end_time" in fm
        assert "type: schedule" in fm


# ── Integration tests ─────────────────────────────────────────────────────────

@pytest.fixture
def vault(tmp_path):
    """Create a minimal vault structure with some plain files."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "finance").mkdir()
    (tmp_path / "schedule").mkdir()
    return tmp_path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestMigrateVault:
    def test_migrates_plain_note(self, vault):
        note = vault / "notes" / "reminders.md"
        _write(note, "Call mom\nBuy milk\n")

        result = migrate_vault(str(vault))

        assert len(result.migrated) == 1
        assert len(result.errors) == 0
        content = note.read_text()
        assert content.startswith("---")
        assert "type: note" in content
        assert "Call mom" in content

    def test_skips_file_with_existing_frontmatter(self, vault):
        note = vault / "notes" / "already.md"
        _write(note, "---\ntype: note\ncreated: 2026-01-01\n---\nExisting content\n")

        result = migrate_vault(str(vault))

        assert len(result.skipped) == 1
        assert len(result.migrated) == 0
        # File content unchanged
        assert note.read_text().startswith("---\ntype: note")

    def test_creates_backup_file(self, vault):
        note = vault / "notes" / "backup_me.md"
        _write(note, "Original content")

        migrate_vault(str(vault), backup=True)

        backup = vault / "notes" / "backup_me.md.backup"
        assert backup.exists()
        assert backup.read_text() == "Original content"

    def test_no_backup_when_disabled(self, vault):
        note = vault / "notes" / "no_backup.md"
        _write(note, "Content")

        migrate_vault(str(vault), backup=False)

        backup = vault / "notes" / "no_backup.md.backup"
        assert not backup.exists()

    def test_dry_run_does_not_write(self, vault):
        note = vault / "notes" / "dryrun.md"
        original = "Plain text - do not touch"
        _write(note, original)

        result = migrate_vault(str(vault), dry_run=True)

        assert len(result.migrated) == 1
        assert note.read_text() == original  # unchanged
        assert not (vault / "notes" / "dryrun.md.backup").exists()

    def test_finance_file_gets_correct_type(self, vault):
        f = vault / "finance" / "2026-06-01.md"
        _write(f, "Groceries: 45.00")

        migrate_vault(str(vault), backup=False)

        content = f.read_text()
        assert "type: finance" in content
        assert "category: uncategorized" in content

    def test_schedule_file_gets_correct_type(self, vault):
        f = vault / "schedule" / "2026-06-10.md"
        _write(f, "Dentist appointment")

        migrate_vault(str(vault), backup=False)

        content = f.read_text()
        assert "type: schedule" in content
        assert "start_time" in content

    def test_mixed_vault_partial_migration(self, vault):
        _write(vault / "notes" / "plain.md", "No frontmatter")
        _write(
            vault / "notes" / "already.md",
            "---\ntype: note\ncreated: 2026-01-01\n---\nHas frontmatter\n",
        )
        _write(vault / "finance" / "2026-06-01.md", "Expense entry")

        result = migrate_vault(str(vault), backup=False)

        assert len(result.migrated) == 2
        assert len(result.skipped) == 1
        assert len(result.errors) == 0

    def test_nonexistent_vault_raises(self):
        with pytest.raises(FileNotFoundError):
            migrate_vault("/nonexistent/path/to/vault")

    def test_result_summary_string(self, vault):
        _write(vault / "notes" / "a.md", "content")
        result = migrate_vault(str(vault), backup=False)
        summary = result.summary()
        assert "migrated" in summary
        assert "skipped" in summary

    def test_backup_files_are_not_remigrated(self, vault):
        """Backup files (.md.backup) should be ignored."""
        backup_file = vault / "notes" / "old.md.backup"
        _write(backup_file, "Old content")
        # Only a real .md file (with frontmatter) so result stays zero migrated
        _write(
            vault / "notes" / "real.md",
            "---\ntype: note\ncreated: 2026-01-01\n---\nContent\n",
        )

        result = migrate_vault(str(vault), backup=False)

        assert len(result.migrated) == 0  # real.md was skipped; backup file ignored
        assert len(result.errors) == 0

    def test_date_extracted_from_finance_filename(self, vault):
        f = vault / "finance" / "2025-03-15.md"
        _write(f, "Rent payment")

        migrate_vault(str(vault), backup=False)

        content = f.read_text()
        assert "2025-03-15" in content
