"""Tests for vault reader functionality."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from app.vault.reader import VaultReader
from app.vault.writer import VaultWriter
from app.vault.schema import Note, Finance, Schedule


@pytest.fixture
def temp_vault():
    """Create a temporary vault directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_path = Path(temp_dir) / "vault"
        vault_path.mkdir(parents=True, exist_ok=True)
        yield vault_path


@pytest.fixture
def vault_writer(temp_vault):
    """Create a VaultWriter instance with a temporary vault."""
    return VaultWriter(str(temp_vault))


@pytest.fixture
def vault_reader(temp_vault):
    """Create a VaultReader instance with a temporary vault."""
    return VaultReader(str(temp_vault))


class TestVaultReaderInitialization:
    """Test VaultReader initialization."""

    def test_create_vault_reader(self, temp_vault):
        """Should create a VaultReader with a vault path."""
        reader = VaultReader(str(temp_vault))
        assert reader.vault_path == str(temp_vault)

    def test_vault_path_is_stored(self, vault_reader, temp_vault):
        """Vault path should be accessible."""
        assert vault_reader.vault_path == str(temp_vault)


class TestGetNote:
    """Test getting individual notes."""

    def test_get_note_by_path(self, vault_writer, vault_reader, temp_vault):
        """Should retrieve a note by path."""
        # Write a note
        vault_writer.add_note(
            path="notes/test.md",
            content="Test content",
            tags=["tag1", "tag2"]
        )

        # Read it back
        note = vault_reader.get_note("notes/test.md")

        assert note is not None
        assert isinstance(note, Note)
        assert note.type == "note"
        assert note.tags == ["tag1", "tag2"]

    def test_get_note_with_md_extension_auto_added(self, vault_writer, vault_reader):
        """Should work with or without .md extension."""
        vault_writer.add_note(
            path="notes/auto.md",
            content="Auto extension test"
        )

        # Try without .md extension
        note = vault_reader.get_note("notes/auto")
        assert note is not None
        assert note.type == "note"

    def test_get_note_returns_content(self, vault_writer, vault_reader):
        """get_file should return both metadata and content."""
        expected_content = "This is the body content.\n\nWith multiple lines."
        vault_writer.add_note(
            path="notes/full.md",
            content=expected_content
        )

        metadata, content = vault_reader.get_file("notes/full.md")
        assert isinstance(metadata, Note)
        assert content == expected_content

    def test_get_note_with_special_characters(self, vault_writer, vault_reader):
        """Should handle special characters in content."""
        special_content = "Café with naïve 中文 and العربية"
        vault_writer.add_note(
            path="notes/special.md",
            content=special_content
        )

        note, content = vault_reader.get_file("notes/special.md")
        assert special_content in content

    def test_get_nonexistent_note_returns_none(self, vault_reader):
        """Should return None for nonexistent note."""
        note = vault_reader.get_note("notes/nonexistent.md")
        assert note is None

    def test_get_nonexistent_file_returns_none(self, vault_reader):
        """get_file should return None for nonexistent file."""
        result = vault_reader.get_file("notes/nonexistent.md")
        assert result is None

    def test_get_note_preserves_created_date(self, vault_writer, vault_reader):
        """Should preserve the created date from metadata."""
        created_date = "2026-01-15"
        vault_writer.add_note(
            path="notes/dated.md",
            content="Dated note",
            created=created_date
        )

        note = vault_reader.get_note("notes/dated.md")
        assert note.created == created_date


class TestListNotes:
    """Test listing notes in a directory."""

    def test_list_notes_empty_directory(self, vault_reader):
        """Should return empty list for empty directory."""
        notes = vault_reader.list_notes("notes")
        assert notes == []

    def test_list_notes_single_note(self, vault_writer, vault_reader):
        """Should list single note."""
        vault_writer.add_note(
            path="notes/single.md",
            content="Single note"
        )

        notes = vault_reader.list_notes("notes")
        assert len(notes) == 1
        assert notes[0].type == "note"

    def test_list_notes_multiple_notes(self, vault_writer, vault_reader):
        """Should list multiple notes."""
        vault_writer.add_note(path="notes/first.md", content="First")
        vault_writer.add_note(path="notes/second.md", content="Second")
        vault_writer.add_note(path="notes/third.md", content="Third")

        notes = vault_reader.list_notes("notes")
        assert len(notes) == 3

    def test_list_notes_nested_directory(self, vault_writer, vault_reader):
        """Should list notes in nested directory."""
        vault_writer.add_note(path="notes/archived/old.md", content="Old note")
        vault_writer.add_note(path="notes/archived/ancient.md", content="Ancient")

        notes = vault_reader.list_notes("notes/archived")
        assert len(notes) == 2

    def test_list_notes_ignores_non_markdown(self, vault_writer, vault_reader, temp_vault):
        """Should only list markdown files."""
        vault_writer.add_note(path="notes/valid.md", content="Valid")

        # Add a non-markdown file
        (temp_vault / "notes" / "ignore.txt").write_text("Not markdown")

        notes = vault_reader.list_notes("notes")
        assert len(notes) == 1
        assert all(n.type == "note" for n in notes)

    def test_list_notes_includes_metadata(self, vault_writer, vault_reader):
        """Listed notes should include full metadata."""
        vault_writer.add_note(
            path="notes/meta.md",
            content="Content",
            tags=["tag1", "tag2"]
        )

        notes = vault_reader.list_notes("notes")
        assert len(notes) == 1
        assert notes[0].tags == ["tag1", "tag2"]

    def test_list_notes_nonexistent_directory(self, vault_reader):
        """Should return empty list for nonexistent directory."""
        notes = vault_reader.list_notes("nonexistent")
        assert notes == []

    def test_list_notes_default_directory(self, vault_writer, vault_reader):
        """Should list from notes directory by default."""
        vault_writer.add_note(path="notes/default.md", content="Default")

        notes = vault_reader.list_notes()  # No argument = default "notes"
        assert len(notes) == 1


class TestListFinances:
    """Test listing finance entries."""

    def test_list_finances_empty(self, vault_reader):
        """Should return empty list when no finances."""
        finances = vault_reader.list_finances()
        assert finances == []

    def test_list_finances_single(self, vault_writer, vault_reader):
        """Should list single finance entry."""
        vault_writer.add_finance(
            amount=50.00,
            category="groceries",
            date="2026-06-08"
        )

        finances = vault_reader.list_finances()
        assert len(finances) == 1
        assert isinstance(finances[0], Finance)
        assert finances[0].amount == 50.00

    def test_list_finances_multiple(self, vault_writer, vault_reader):
        """Should list multiple finance entries."""
        vault_writer.add_finance(amount=30.00, category="groceries", date="2026-06-08")
        vault_writer.add_finance(amount=20.00, category="transport", date="2026-06-07")
        vault_writer.add_finance(amount=15.00, category="food", date="2026-06-06")

        finances = vault_reader.list_finances()
        assert len(finances) == 3

    def test_list_finances_sorted_by_date_descending(self, vault_writer, vault_reader):
        """Should sort finances by date (most recent first)."""
        vault_writer.add_finance(amount=10.00, category="test1", date="2026-06-06")
        vault_writer.add_finance(amount=20.00, category="test2", date="2026-06-08")
        vault_writer.add_finance(amount=15.00, category="test3", date="2026-06-07")

        finances = vault_reader.list_finances()
        assert len(finances) == 3
        # Should be sorted most recent first
        assert finances[0].created == "2026-06-08"
        assert finances[1].created == "2026-06-07"
        assert finances[2].created == "2026-06-06"

    def test_list_finances_multiple_same_date(self, vault_writer, vault_reader):
        """Should handle multiple entries on the same date."""
        vault_writer.add_finance(amount=30.00, category="groceries", date="2026-06-08")
        vault_writer.add_finance(amount=15.00, category="transport", date="2026-06-08")

        finances = vault_reader.list_finances("2026-06-08")
        assert len(finances) == 2
        assert all(f.created == "2026-06-08" for f in finances)

    def test_list_finances_filter_by_date(self, vault_writer, vault_reader):
        """Should filter finances by specific date."""
        vault_writer.add_finance(amount=10.00, category="cat1", date="2026-06-06")
        vault_writer.add_finance(amount=20.00, category="cat2", date="2026-06-08")
        vault_writer.add_finance(amount=15.00, category="cat3", date="2026-06-07")

        finances = vault_reader.list_finances("2026-06-08")
        assert len(finances) == 1
        assert finances[0].created == "2026-06-08"
        assert finances[0].amount == 20.00

    def test_list_finances_preserves_amount_and_category(self, vault_writer, vault_reader):
        """Should preserve amount and category fields."""
        vault_writer.add_finance(
            amount=123.45,
            category="entertainment",
            date="2026-06-08",
            description="Movie tickets"
        )

        finances = vault_reader.list_finances()
        assert finances[0].amount == 123.45
        assert finances[0].category == "entertainment"
        assert finances[0].description == "Movie tickets"

    def test_list_finances_no_directory_no_error(self, vault_reader):
        """Should not error when finance directory doesn't exist."""
        finances = vault_reader.list_finances()
        assert finances == []


class TestListSchedules:
    """Test listing schedule entries."""

    def test_list_schedules_empty(self, vault_reader):
        """Should return empty list when no schedules."""
        schedules = vault_reader.list_schedules()
        assert schedules == []

    def test_list_schedules_single(self, vault_writer, vault_reader):
        """Should list single schedule entry."""
        vault_writer.add_schedule(
            title="Meeting",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00"
        )

        schedules = vault_reader.list_schedules()
        assert len(schedules) == 1
        assert isinstance(schedules[0], Schedule)
        assert schedules[0].title == "Meeting"

    def test_list_schedules_multiple(self, vault_writer, vault_reader):
        """Should list multiple schedule entries."""
        vault_writer.add_schedule(
            title="Meeting 1",
            date="2026-06-08",
            start_time="09:00",
            end_time="10:00"
        )
        vault_writer.add_schedule(
            title="Meeting 2",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00"
        )
        vault_writer.add_schedule(
            title="Meeting 3",
            date="2026-06-07",
            start_time="10:00",
            end_time="11:00"
        )

        schedules = vault_reader.list_schedules()
        assert len(schedules) == 3

    def test_list_schedules_sorted_by_date_descending(self, vault_writer, vault_reader):
        """Should sort schedules by date (most recent first)."""
        vault_writer.add_schedule("Old", "2026-06-06", "09:00", "10:00")
        vault_writer.add_schedule("New", "2026-06-08", "14:00", "15:00")
        vault_writer.add_schedule("Middle", "2026-06-07", "10:00", "11:00")

        schedules = vault_reader.list_schedules()
        assert schedules[0].created == "2026-06-08"
        assert schedules[1].created == "2026-06-07"
        assert schedules[2].created == "2026-06-06"

    def test_list_schedules_filter_by_date(self, vault_writer, vault_reader):
        """Should filter schedules by specific date."""
        vault_writer.add_schedule("Old", "2026-06-06", "09:00", "10:00")
        vault_writer.add_schedule("Today1", "2026-06-08", "14:00", "15:00")
        vault_writer.add_schedule("Today2", "2026-06-08", "16:00", "17:00")

        schedules = vault_reader.list_schedules("2026-06-08")
        assert len(schedules) == 2
        assert all(s.created == "2026-06-08" for s in schedules)

    def test_list_schedules_preserves_times(self, vault_writer, vault_reader):
        """Should preserve start and end times."""
        vault_writer.add_schedule(
            title="Timed meeting",
            date="2026-06-08",
            start_time="14:30",
            end_time="15:45"
        )

        schedules = vault_reader.list_schedules()
        assert schedules[0].start_time == "14:30"
        assert schedules[0].end_time == "15:45"

    def test_list_schedules_preserves_metadata(self, vault_writer, vault_reader):
        """Should preserve description and other fields."""
        vault_writer.add_schedule(
            title="Full meeting",
            date="2026-06-08",
            start_time="10:00",
            end_time="11:00",
            description="Team sync",
            location="Room 42B"
        )

        schedules = vault_reader.list_schedules()
        assert schedules[0].description == "Team sync"

    def test_list_schedules_no_directory_no_error(self, vault_reader):
        """Should not error when schedule directory doesn't exist."""
        schedules = vault_reader.list_schedules()
        assert schedules == []


class TestSearch:
    """Test search functionality."""

    def test_search_empty_vault(self, vault_reader):
        """Should return empty list when vault is empty."""
        results = vault_reader.search("test")
        assert results == []

    def test_search_by_keyword_in_note_content(self, vault_writer, vault_reader):
        """Should find notes by keyword in content."""
        vault_writer.add_note(path="notes/test.md", content="This contains keyword xyz")

        results = vault_reader.search("keyword")
        assert len(results) > 0
        # Should find the note
        assert any("notes/test" in str(r) or "test" in str(r) for r in results)

    def test_search_by_keyword_in_note_tags(self, vault_writer, vault_reader):
        """Should find notes by keyword in tags."""
        vault_writer.add_note(
            path="notes/tagged.md",
            content="Some content",
            tags=["important", "urgent"]
        )

        results = vault_reader.search("important")
        assert len(results) > 0

    def test_search_case_insensitive(self, vault_writer, vault_reader):
        """Search should be case insensitive."""
        vault_writer.add_note(path="notes/case.md", content="UPPERCASE content")

        results_lower = vault_reader.search("uppercase")
        results_upper = vault_reader.search("UPPERCASE")
        assert len(results_lower) > 0
        assert len(results_upper) > 0

    def test_search_multiple_matches(self, vault_writer, vault_reader):
        """Should find multiple matches."""
        vault_writer.add_note(path="notes/one.md", content="contains search term")
        vault_writer.add_note(path="notes/two.md", content="also has search term")
        vault_writer.add_note(path="notes/three.md", content="different content")

        results = vault_reader.search("search")
        assert len(results) >= 2

    def test_search_by_type_note(self, vault_writer, vault_reader):
        """Should filter search by type."""
        vault_writer.add_note(path="notes/note.md", content="note content")
        vault_writer.add_finance(amount=50.00, category="searchable", date="2026-06-08")

        # Search for "searchable" in notes only
        results = vault_reader.search("searchable", search_type="note")
        # Should not find the finance entry
        assert len(results) == 0

    def test_search_by_type_finance(self, vault_writer, vault_reader):
        """Should filter search by finance type."""
        vault_writer.add_note(path="notes/note.md", content="searchable content")
        vault_writer.add_finance(amount=50.00, category="searchable", date="2026-06-08")

        results = vault_reader.search("searchable", search_type="finance")
        # Should find at least the finance entry
        assert len(results) > 0

    def test_search_by_type_all(self, vault_writer, vault_reader):
        """Should search all types by default."""
        vault_writer.add_note(path="notes/note.md", content="find me")
        vault_writer.add_finance(amount=50.00, category="find", date="2026-06-08")
        vault_writer.add_schedule("find", "2026-06-08", "10:00", "11:00")

        results = vault_reader.search("find", search_type="all")
        # Should find multiple entries
        assert len(results) >= 2

    def test_search_returns_file_paths(self, vault_writer, vault_reader):
        """Search should return file paths in results."""
        vault_writer.add_note(path="notes/searchable.md", content="term")

        results = vault_reader.search("term")
        # Results should contain file path information
        assert len(results) > 0
        # Each result should be a tuple with at least (path, metadata)
        result = results[0]
        assert isinstance(result, (tuple, list)) or hasattr(result, '__getitem__')

    def test_search_finance_by_amount(self, vault_writer, vault_reader):
        """Should be able to search finance by amount."""
        vault_writer.add_finance(amount=99.99, category="test", date="2026-06-08")

        results = vault_reader.search("99.99")
        assert len(results) > 0

    def test_search_schedule_by_title(self, vault_writer, vault_reader):
        """Should find schedule by title."""
        vault_writer.add_schedule(
            title="Conference",
            date="2026-06-08",
            start_time="09:00",
            end_time="17:00"
        )

        results = vault_reader.search("Conference")
        assert len(results) > 0

    def test_search_special_characters(self, vault_writer, vault_reader):
        """Should handle special characters in search."""
        vault_writer.add_note(path="notes/special.md", content="Café naïve")

        results = vault_reader.search("Café")
        assert len(results) > 0

    def test_search_empty_query_returns_empty(self, vault_writer, vault_reader):
        """Empty search should return empty list."""
        vault_writer.add_note(path="notes/note.md", content="content")

        results = vault_reader.search("")
        assert results == []

    def test_search_no_matches(self, vault_writer, vault_reader):
        """Should return empty list when no matches."""
        vault_writer.add_note(path="notes/note.md", content="content")

        results = vault_reader.search("nonexistent")
        assert results == []

    def test_search_results_sorted_by_date(self, vault_writer, vault_reader):
        """Search results should be sorted by date (most recent first)."""
        # Add notes with different dates
        vault_writer.add_note(
            path="notes/old.md",
            content="searchable content",
            created="2026-06-06"
        )
        vault_writer.add_note(
            path="notes/new.md",
            content="searchable content",
            created="2026-06-08"
        )
        vault_writer.add_note(
            path="notes/middle.md",
            content="searchable content",
            created="2026-06-07"
        )

        results = vault_reader.search("searchable")
        assert len(results) == 3
        # Results should be sorted most recent first
        assert results[0][1].created == "2026-06-08"
        assert results[1][1].created == "2026-06-07"
        assert results[2][1].created == "2026-06-06"


class TestRoundTrip:
    """Test write -> read round-trip consistency."""

    def test_note_round_trip(self, vault_writer, vault_reader):
        """Written note should read back identically."""
        original_content = "Test content with **bold** and *italic*"
        vault_writer.add_note(
            path="notes/roundtrip.md",
            content=original_content,
            tags=["test", "roundtrip"]
        )

        note = vault_reader.get_note("notes/roundtrip.md")
        assert note.tags == ["test", "roundtrip"]

        metadata, content = vault_reader.get_file("notes/roundtrip.md")
        assert content == original_content

    def test_finance_round_trip(self, vault_writer, vault_reader):
        """Written finance should read back identically."""
        vault_writer.add_finance(
            amount=123.45,
            category="groceries",
            date="2026-06-08",
            description="Weekly shopping"
        )

        finance = vault_reader.get_note("finance/2026-06-08.md")
        assert isinstance(finance, Finance)
        assert finance.amount == 123.45
        assert finance.category == "groceries"
        assert finance.description == "Weekly shopping"

    def test_schedule_round_trip(self, vault_writer, vault_reader):
        """Written schedule should read back identically."""
        vault_writer.add_schedule(
            title="Team meeting",
            date="2026-06-08",
            start_time="14:30",
            end_time="15:30",
            description="Sprint planning"
        )

        schedule = vault_reader.get_note("schedule/2026-06-08.md")
        assert isinstance(schedule, Schedule)
        assert schedule.title == "Team meeting"
        assert schedule.start_time == "14:30"
        assert schedule.end_time == "15:30"


class TestPathValidation:
    """Test path handling."""

    def test_get_note_validates_path(self, vault_reader):
        """Should validate paths."""
        # Should not allow traversal
        result = vault_reader.get_note("../etc/passwd")
        assert result is None

    def test_get_note_handles_missing_extension(self, vault_writer, vault_reader):
        """Should auto-add .md extension if missing."""
        vault_writer.add_note(path="notes/test.md", content="Test")

        # Should find it without .md
        note = vault_reader.get_note("notes/test")
        assert note is not None

        # Should also find it with .md
        note2 = vault_reader.get_note("notes/test.md")
        assert note2 is not None
