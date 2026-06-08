"""Tests for vault writer functionality."""
import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime
from app.vault.writer import VaultWriter
from app.vault.schema import Note, Finance, Schedule, parse_vault_file


@pytest.fixture
def temp_vault():
    """Create a temporary vault directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_path = Path(temp_dir) / "vault"
        vault_path.mkdir(parents=True, exist_ok=True)
        yield vault_path
        # Cleanup happens automatically with context manager


@pytest.fixture
def vault_writer(temp_vault):
    """Create a VaultWriter instance with a temporary vault."""
    return VaultWriter(str(temp_vault))


class TestVaultWriterInitialization:
    """Test VaultWriter initialization."""

    def test_create_vault_writer(self, temp_vault):
        """Should create a VaultWriter with a vault path."""
        writer = VaultWriter(str(temp_vault))
        assert writer.vault_path == str(temp_vault)

    def test_vault_path_is_stored(self, vault_writer, temp_vault):
        """Vault path should be accessible."""
        assert vault_writer.vault_path == str(temp_vault)


class TestAddNote:
    """Test adding notes to the vault."""

    def test_add_simple_note(self, vault_writer, temp_vault):
        """Should write a note with title and content."""
        result = vault_writer.add_note(
            path="notes/test.md",
            content="This is a test note."
        )

        # Verify result
        assert isinstance(result, Note)
        assert result.type == "note"
        assert result.created is not None

        # Verify file was created
        file_path = temp_vault / "notes" / "test.md"
        assert file_path.exists()

        # Verify content
        content = file_path.read_text(encoding="utf-8")
        assert "---" in content
        assert "type: note" in content
        assert "This is a test note." in content

    def test_add_note_with_tags(self, vault_writer, temp_vault):
        """Should write a note with tags."""
        result = vault_writer.add_note(
            path="notes/research.md",
            content="Research findings.",
            tags=["research", "urgent"]
        )

        assert result.tags == ["research", "urgent"]

        file_path = temp_vault / "notes" / "research.md"
        content = file_path.read_text(encoding="utf-8")
        assert "research" in content
        assert "urgent" in content

    def test_add_note_without_tags(self, vault_writer, temp_vault):
        """Should add note when tags are not provided."""
        result = vault_writer.add_note(
            path="notes/simple.md",
            content="Simple content"
        )

        assert result.tags == [] or result.tags is None
        file_path = temp_vault / "notes" / "simple.md"
        assert file_path.exists()

    def test_add_note_creates_parent_directories(self, vault_writer, temp_vault):
        """Should create parent directories automatically."""
        result = vault_writer.add_note(
            path="deep/nested/path/note.md",
            content="Nested note"
        )

        file_path = temp_vault / "deep" / "nested" / "path" / "note.md"
        assert file_path.exists()
        assert result is not None

    def test_add_note_with_special_characters(self, vault_writer, temp_vault):
        """Should handle special characters in content."""
        content = "Test with émojis, ñotas, and 中文 characters."
        result = vault_writer.add_note(
            path="notes/special.md",
            content=content
        )

        file_path = temp_vault / "notes" / "special.md"
        file_content = file_path.read_text(encoding="utf-8")
        assert content in file_content

    def test_add_note_with_multiline_content(self, vault_writer, temp_vault):
        """Should preserve multiline markdown content."""
        content = """# Heading

- Item 1
- Item 2

**Bold text** and *italic text*."""
        result = vault_writer.add_note(
            path="notes/markdown.md",
            content=content
        )

        file_path = temp_vault / "notes" / "markdown.md"
        file_content = file_path.read_text(encoding="utf-8")
        assert "# Heading" in file_content
        assert "- Item 1" in file_content
        assert "**Bold text**" in file_content

    def test_add_note_defaults_created_date(self, vault_writer, temp_vault):
        """Should set created date to today if not provided."""
        result = vault_writer.add_note(
            path="notes/dated.md",
            content="Content"
        )

        # created should be in ISO format
        assert result.created is not None
        assert isinstance(result.created, str)
        # Should be in YYYY-MM-DD or ISO format
        assert len(result.created) >= 10

    def test_add_note_raises_on_absolute_path(self, vault_writer):
        """Should prevent writing outside vault directory."""
        with pytest.raises((ValueError, SecurityError)):
            vault_writer.add_note(
                path="/etc/passwd",
                content="Malicious"
            )

    def test_add_note_raises_on_path_traversal(self, vault_writer):
        """Should prevent path traversal attacks."""
        with pytest.raises((ValueError, SecurityError)):
            vault_writer.add_note(
                path="../../../etc/passwd",
                content="Malicious"
            )

    def test_add_note_enforces_md_extension(self, vault_writer, temp_vault):
        """Should enforce .md extension."""
        result = vault_writer.add_note(
            path="notes/test",
            content="Content"
        )

        # Either the path is converted to .md or raises an error
        # Implementation may vary
        file_path = temp_vault / "notes" / "test.md"
        # File should exist with .md extension
        found = False
        for f in (temp_vault / "notes").glob("*"):
            if f.name.endswith(".md"):
                found = True
                break
        assert found

    def test_add_note_prevents_overwrite(self, vault_writer, temp_vault):
        """Should prevent overwriting existing files."""
        path = "notes/existing.md"

        # First write
        vault_writer.add_note(path=path, content="Original")

        # Second write should fail
        with pytest.raises((FileExistsError, ValueError)):
            vault_writer.add_note(path=path, content="New")

    def test_add_note_with_explicit_date(self, vault_writer, temp_vault):
        """Should accept explicit created date."""
        result = vault_writer.add_note(
            path="notes/dated.md",
            content="Dated content",
            created="2026-06-01"
        )

        assert result.created == "2026-06-01"


class TestAddFinance:
    """Test adding finance transactions to the vault."""

    def test_add_finance_transaction(self, vault_writer, temp_vault):
        """Should write a finance transaction."""
        result = vault_writer.add_finance(
            amount=45.50,
            category="groceries",
            date="2026-06-08"
        )

        assert isinstance(result, Finance)
        assert result.type == "finance"
        assert result.amount == 45.50
        assert result.category == "groceries"
        assert result.created == "2026-06-08"

    def test_add_finance_with_description(self, vault_writer, temp_vault):
        """Should add finance with optional description."""
        result = vault_writer.add_finance(
            amount=100.00,
            category="utilities",
            date="2026-06-08",
            description="Monthly electricity bill"
        )

        assert result.description == "Monthly electricity bill"

    def test_add_finance_creates_file(self, vault_writer, temp_vault):
        """Finance entry should be written to file."""
        result = vault_writer.add_finance(
            amount=50.00,
            category="food",
            date="2026-06-08"
        )

        # Should be in finance directory with ISO date
        file_path = temp_vault / "finance" / "2026-06-08.md"
        assert file_path.exists()

        content = file_path.read_text(encoding="utf-8")
        assert "type: finance" in content
        assert "groceries" in content or "food" in content
        assert "50" in content

    def test_add_finance_without_description(self, vault_writer, temp_vault):
        """Should add finance without description."""
        result = vault_writer.add_finance(
            amount=25.00,
            category="entertainment",
            date="2026-06-08"
        )

        assert result.description is None

    def test_add_finance_defaults_date_to_today(self, vault_writer, temp_vault):
        """Should default date to today if not provided."""
        result = vault_writer.add_finance(
            amount=10.00,
            category="snacks"
        )

        assert result.created is not None
        # Should be roughly today's date
        assert isinstance(result.created, str)
        assert len(result.created) >= 10

    def test_add_finance_validates_category(self, vault_writer):
        """Should validate that category is not empty."""
        with pytest.raises(ValueError):
            vault_writer.add_finance(
                amount=50.00,
                category="",
                date="2026-06-08"
            )

    def test_add_finance_prevents_overwrite(self, vault_writer, temp_vault):
        """Should handle multiple transactions on same day."""
        # Add first transaction for the day
        result1 = vault_writer.add_finance(
            amount=30.00,
            category="groceries",
            date="2026-06-08"
        )

        # Add second transaction for the same day
        # This might append to the file or create a separate entry
        result2 = vault_writer.add_finance(
            amount=15.00,
            category="transport",
            date="2026-06-08"
        )

        # Both should be persisted
        assert result1.created == "2026-06-08"
        assert result2.created == "2026-06-08"

    def test_multiple_finance_entries_round_trip(self, vault_writer, temp_vault):
        """Should properly format multiple finance entries for parsing."""
        # Add first finance entry
        vault_writer.add_finance(
            amount=30.00,
            category="groceries",
            date="2026-06-08",
            description="Weekly groceries"
        )

        # Add second finance entry to same file
        vault_writer.add_finance(
            amount=15.00,
            category="transport",
            date="2026-06-08",
            description="Bus fare"
        )

        # Read and parse the file
        file_path = temp_vault / "finance" / "2026-06-08.md"
        assert file_path.exists()

        raw_content = file_path.read_text(encoding="utf-8")

        # The first entry should parse correctly
        metadata, body = parse_vault_file(raw_content)
        assert isinstance(metadata, Finance)
        assert metadata.type == "finance"
        assert metadata.amount == 30.00
        assert metadata.category == "groceries"

        # Verify both entries exist in raw content with proper YAML formatting
        # Should have two separate frontmatter blocks with newline separator
        assert raw_content.count("---") >= 4  # At least 2 frontmatters (opening and closing each)
        assert "type: finance" in raw_content
        assert "groceries" in raw_content
        assert "transport" in raw_content

        # Verify no malformed YAML (no direct concatenation like "---type:")
        assert "---type:" not in raw_content
        assert "---\ntype:" in raw_content


class TestAddSchedule:
    """Test adding schedule entries to the vault."""

    def test_add_schedule_entry(self, vault_writer, temp_vault):
        """Should write a schedule entry."""
        result = vault_writer.add_schedule(
            title="Team meeting",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00"
        )

        assert isinstance(result, Schedule)
        assert result.type == "schedule"
        assert result.title == "Team meeting"
        assert result.start_time == "14:00"
        assert result.end_time == "15:00"

    def test_add_schedule_with_description(self, vault_writer, temp_vault):
        """Should add schedule with optional description."""
        result = vault_writer.add_schedule(
            title="Review meeting",
            date="2026-06-08",
            start_time="10:00",
            end_time="11:00",
            description="Quarterly performance review"
        )

        assert result.description == "Quarterly performance review"

    def test_add_schedule_with_priority(self, vault_writer, temp_vault):
        """Should add schedule with optional priority."""
        result = vault_writer.add_schedule(
            title="Urgent task",
            date="2026-06-08",
            start_time="09:00",
            end_time="10:00",
            priority="high"
        )

        # priority might be stored as a custom field
        assert result is not None

    def test_add_schedule_with_location(self, vault_writer, temp_vault):
        """Should add schedule with optional location."""
        result = vault_writer.add_schedule(
            title="Conference",
            date="2026-06-08",
            start_time="09:00",
            end_time="17:00",
            location="Room 42B"
        )

        assert result is not None

    def test_add_schedule_creates_file(self, vault_writer, temp_vault):
        """Schedule entry should be written to file."""
        result = vault_writer.add_schedule(
            title="Meeting",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00"
        )

        # Should be in schedule directory with ISO date
        file_path = temp_vault / "schedule" / "2026-06-08.md"
        assert file_path.exists()

        content = file_path.read_text(encoding="utf-8")
        assert "type: schedule" in content
        assert "14:00" in content
        assert "15:00" in content

    def test_add_schedule_validates_times(self, vault_writer):
        """Should validate time format."""
        with pytest.raises(ValueError):
            vault_writer.add_schedule(
                title="Bad time",
                date="2026-06-08",
                start_time="25:00",  # Invalid hour
                end_time="15:00"
            )

    def test_add_schedule_handles_multiple_entries_same_day(self, vault_writer, temp_vault):
        """Should handle multiple schedule entries for the same day."""
        result1 = vault_writer.add_schedule(
            title="Meeting 1",
            date="2026-06-08",
            start_time="09:00",
            end_time="10:00"
        )

        result2 = vault_writer.add_schedule(
            title="Meeting 2",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00"
        )

        # Both entries should be persisted
        assert result1.title == "Meeting 1"
        assert result2.title == "Meeting 2"

    def test_multiple_schedule_entries_round_trip(self, vault_writer, temp_vault):
        """Should properly format multiple schedule entries for parsing."""
        # Add first schedule entry
        vault_writer.add_schedule(
            title="Morning standup",
            date="2026-06-08",
            start_time="09:00",
            end_time="09:30",
            description="Daily sync"
        )

        # Add second schedule entry to same file
        vault_writer.add_schedule(
            title="Afternoon meeting",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00",
            description="Project review"
        )

        # Read and parse the file
        file_path = temp_vault / "schedule" / "2026-06-08.md"
        assert file_path.exists()

        raw_content = file_path.read_text(encoding="utf-8")

        # The first entry should parse correctly
        metadata, body = parse_vault_file(raw_content)
        assert isinstance(metadata, Schedule)
        assert metadata.type == "schedule"
        assert metadata.start_time == "09:00"
        assert metadata.end_time == "09:30"

        # Verify both entries exist in raw content with proper YAML formatting
        # Should have two separate frontmatter blocks with newline separator
        assert raw_content.count("---") >= 4  # At least 2 frontmatters (opening and closing each)
        assert "type: schedule" in raw_content
        assert "09:00" in raw_content
        assert "14:00" in raw_content

        # Verify no malformed YAML (no direct concatenation like "---type:")
        assert "---type:" not in raw_content
        assert "---\ntype:" in raw_content


class TestUpdateFile:
    """Test updating existing file metadata and content."""

    def test_update_note_metadata(self, vault_writer, temp_vault):
        """Should update metadata on existing note."""
        # Create initial note
        vault_writer.add_note(
            path="notes/test.md",
            content="Original"
        )

        # Update metadata
        updated = vault_writer.update_file(
            path="notes/test.md",
            metadata=Note(
                type="note",
                created="2026-06-08",
                tags=["updated"]
            )
        )

        assert updated.tags == ["updated"]

        # Verify file
        file_path = temp_vault / "notes" / "test.md"
        content = file_path.read_text(encoding="utf-8")
        assert "updated" in content

    def test_update_file_content(self, vault_writer, temp_vault):
        """Should update file content."""
        # Create initial note
        vault_writer.add_note(
            path="notes/test.md",
            content="Original content"
        )

        # Update content
        vault_writer.update_file(
            path="notes/test.md",
            metadata=Note(type="note", created="2026-06-08"),
            content="Updated content"
        )

        file_path = temp_vault / "notes" / "test.md"
        content = file_path.read_text(encoding="utf-8")
        assert "Updated content" in content
        assert "Original content" not in content

    def test_update_nonexistent_file(self, vault_writer):
        """Should raise error when updating nonexistent file."""
        with pytest.raises(FileNotFoundError):
            vault_writer.update_file(
                path="notes/nonexistent.md",
                metadata=Note(type="note", created="2026-06-08")
            )

    def test_update_sets_modified_timestamp(self, vault_writer, temp_vault):
        """Should set modified timestamp when updating."""
        # Create initial note
        vault_writer.add_note(
            path="notes/test.md",
            content="Original"
        )

        # Update note
        result = vault_writer.update_file(
            path="notes/test.md",
            metadata=Note(type="note", created="2026-06-08"),
            content="Updated"
        )

        # modified should be set
        assert result.modified is not None


class TestEnsureDirectory:
    """Test directory creation."""

    def test_ensure_directory_creates_if_not_exists(self, vault_writer, temp_vault):
        """Should create directory if it doesn't exist."""
        dir_path = "notes/archived"
        vault_writer.ensure_directory(dir_path)

        full_path = temp_vault / "notes" / "archived"
        assert full_path.exists()
        assert full_path.is_dir()

    def test_ensure_directory_handles_existing(self, vault_writer, temp_vault):
        """Should handle directory that already exists."""
        dir_path = "notes/existing"
        vault_writer.ensure_directory(dir_path)
        vault_writer.ensure_directory(dir_path)  # Should not raise

        full_path = temp_vault / "notes" / "existing"
        assert full_path.exists()

    def test_ensure_directory_creates_parent_dirs(self, vault_writer, temp_vault):
        """Should create parent directories as needed."""
        dir_path = "deep/nested/structure"
        vault_writer.ensure_directory(dir_path)

        full_path = temp_vault / "deep" / "nested" / "structure"
        assert full_path.exists()


class TestSecurityAndValidation:
    """Test security and input validation."""

    def test_prevent_absolute_paths(self, vault_writer):
        """Should reject absolute paths."""
        with pytest.raises((ValueError, SecurityError)):
            vault_writer.add_note(
                path="/absolute/path.md",
                content="Bad"
            )

    def test_prevent_path_traversal_with_dotdot(self, vault_writer):
        """Should prevent .. path traversal."""
        with pytest.raises((ValueError, SecurityError)):
            vault_writer.add_note(
                path="../../etc/passwd",
                content="Bad"
            )

    def test_prevent_path_traversal_variations(self, vault_writer):
        """Should prevent various path traversal attempts."""
        bad_paths = [
            "../notes/file.md",
            "notes/../../../etc/passwd",
            "notes/.../.../file.md",
        ]
        for path in bad_paths:
            with pytest.raises((ValueError, SecurityError)):
                vault_writer.add_note(path=path, content="Bad")


class TestFileEncoding:
    """Test file encoding and special characters."""

    def test_utf8_encoding_special_chars(self, vault_writer, temp_vault):
        """Should properly encode special characters."""
        content = "Café, naïve, 中文, العربية, 🎉"
        vault_writer.add_note(
            path="notes/unicode.md",
            content=content
        )

        file_path = temp_vault / "notes" / "unicode.md"
        read_content = file_path.read_text(encoding="utf-8")
        assert content in read_content

    def test_utf8_encoding_in_metadata(self, vault_writer, temp_vault):
        """Should properly encode special characters in metadata."""
        vault_writer.add_note(
            path="notes/meta.md",
            content="Content",
            tags=["café", "naïve"]
        )

        file_path = temp_vault / "notes" / "meta.md"
        content = file_path.read_text(encoding="utf-8")
        assert "café" in content
        assert "naïve" in content


class TestExceptionHandling:
    """Test exception handling and edge cases."""

    def test_add_note_with_none_content(self, vault_writer, temp_vault):
        """Should handle None content gracefully."""
        # Either convert None to empty string or raise
        try:
            result = vault_writer.add_note(path="notes/empty.md", content=None)
            assert result is not None
        except (ValueError, TypeError):
            pass  # Also acceptable

    def test_add_note_with_empty_content(self, vault_writer, temp_vault):
        """Should handle empty content."""
        result = vault_writer.add_note(
            path="notes/empty.md",
            content=""
        )

        assert result is not None
        file_path = temp_vault / "notes" / "empty.md"
        assert file_path.exists()

    def test_add_note_with_empty_path(self, vault_writer):
        """Should handle empty path."""
        with pytest.raises((ValueError, SecurityError)):
            vault_writer.add_note(path="", content="Content")


# Helper exception for security checks
class SecurityError(Exception):
    """Raised when security check fails."""
    pass
