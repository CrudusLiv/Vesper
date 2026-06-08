"""Tests for vault schema parsing and metadata handling."""
import pytest
from datetime import datetime
from app.vault.schema import (
    VaultFileMetadata,
    Note,
    Finance,
    Schedule,
    parse_vault_file,
)


class TestVaultFileMetadata:
    """Test basic metadata parsing."""

    def test_create_metadata_with_required_fields(self):
        """Metadata should require type and created fields."""
        metadata = VaultFileMetadata(
            type="note",
            created="2026-06-08",
        )
        assert metadata.type == "note"
        assert metadata.created == "2026-06-08"

    def test_create_metadata_with_optional_fields(self):
        """Metadata should support optional fields."""
        metadata = VaultFileMetadata(
            type="note",
            created="2026-06-08",
            modified="2026-06-09",
            tags=["research", "urgent"],
        )
        assert metadata.modified == "2026-06-09"
        assert metadata.tags == ["research", "urgent"]

    def test_metadata_defaults_modified_to_created(self):
        """If modified is not provided, it should be optional."""
        metadata = VaultFileMetadata(
            type="note",
            created="2026-06-08",
        )
        assert metadata.modified is None


class TestNoteSchema:
    """Test Note-specific schema."""

    def test_create_note(self):
        """Note should require type='note' and have note-specific fields."""
        note = Note(
            type="note",
            created="2026-06-08",
        )
        assert note.type == "note"
        assert note.created == "2026-06-08"

    def test_note_with_tags(self):
        """Note should support tags."""
        note = Note(
            type="note",
            created="2026-06-08",
            tags=["meeting", "important"],
        )
        assert note.tags == ["meeting", "important"]

    def test_note_with_all_fields(self):
        """Note should support all optional fields."""
        note = Note(
            type="note",
            created="2026-06-08",
            modified="2026-06-09",
            tags=["research"],
        )
        assert note.modified == "2026-06-09"
        assert note.tags == ["research"]


class TestFinanceSchema:
    """Test Finance-specific schema."""

    def test_create_finance_entry(self):
        """Finance should require type='finance' and category."""
        finance = Finance(
            type="finance",
            created="2026-06-08",
            category="groceries",
        )
        assert finance.type == "finance"
        assert finance.category == "groceries"

    def test_finance_with_optional_fields(self):
        """Finance should support amount and description."""
        finance = Finance(
            type="finance",
            created="2026-06-08",
            category="groceries",
            amount=45.50,
            description="Weekly shopping",
        )
        assert finance.amount == 45.50
        assert finance.description == "Weekly shopping"

    def test_finance_with_tags(self):
        """Finance should support tags (e.g., for grouping)."""
        finance = Finance(
            type="finance",
            created="2026-06-08",
            category="groceries",
            tags=["weekly", "essential"],
        )
        assert finance.tags == ["weekly", "essential"]


class TestScheduleSchema:
    """Test Schedule-specific schema."""

    def test_create_schedule_entry(self):
        """Schedule should require type='schedule', start_time, and end_time."""
        schedule = Schedule(
            type="schedule",
            created="2026-06-08",
            start_time="14:00",
            end_time="15:00",
        )
        assert schedule.type == "schedule"
        assert schedule.start_time == "14:00"
        assert schedule.end_time == "15:00"

    def test_schedule_with_optional_fields(self):
        """Schedule should support title and description."""
        schedule = Schedule(
            type="schedule",
            created="2026-06-08",
            start_time="14:00",
            end_time="15:00",
            title="Team meeting",
            description="Quarterly review",
        )
        assert schedule.title == "Team meeting"
        assert schedule.description == "Quarterly review"

    def test_schedule_with_all_fields(self):
        """Schedule with all fields."""
        schedule = Schedule(
            type="schedule",
            created="2026-06-08",
            modified="2026-06-08",
            start_time="14:00",
            end_time="15:00",
            title="Team meeting",
            description="Quarterly review",
            tags=["work", "recurring"],
        )
        assert schedule.title == "Team meeting"
        assert schedule.tags == ["work", "recurring"]


class TestYAMLParsing:
    """Test YAML frontmatter parsing."""

    def test_parse_note_with_valid_frontmatter(self):
        """Should parse valid YAML frontmatter followed by content."""
        content = """---
type: note
created: 2026-06-08
tags: [research, urgent]
---
# My Research Note
This is the content of my note.
"""
        metadata, body = parse_vault_file(content)
        assert metadata.type == "note"
        assert metadata.created == "2026-06-08"
        assert metadata.tags == ["research", "urgent"]
        assert "# My Research Note" in body
        assert "This is the content of my note." in body

    def test_parse_file_without_frontmatter(self):
        """Should handle files with no frontmatter and provide defaults."""
        content = "# Just a heading\n\nSome content"
        metadata, body = parse_vault_file(content)
        # Should still parse, with minimal metadata
        assert metadata.type == "note"  # Default type
        assert body == content

    def test_parse_finance_entry(self):
        """Should parse finance-specific metadata."""
        content = """---
type: finance
created: 2026-06-08
category: groceries
amount: 45.50
description: Weekly shopping
---
Additional details about the transaction.
"""
        metadata, body = parse_vault_file(content)
        assert isinstance(metadata, Finance)
        assert metadata.category == "groceries"
        assert metadata.amount == 45.50
        assert "Additional details" in body

    def test_parse_schedule_entry(self):
        """Should parse schedule-specific metadata."""
        content = """---
type: schedule
created: 2026-06-08
start_time: "14:00"
end_time: "15:00"
title: Team meeting
---
Meeting agenda and notes.
"""
        metadata, body = parse_vault_file(content)
        assert isinstance(metadata, Schedule)
        assert metadata.start_time == "14:00"
        assert metadata.end_time == "15:00"
        assert metadata.title == "Team meeting"

    def test_parse_with_empty_body(self):
        """Should handle frontmatter with no body content."""
        content = """---
type: note
created: 2026-06-08
---
"""
        metadata, body = parse_vault_file(content)
        assert metadata.type == "note"
        assert body.strip() == ""

    def test_parse_preserves_markdown_formatting(self):
        """Should preserve markdown content exactly as-is."""
        content = """---
type: note
created: 2026-06-08
---
# Heading

- List item 1
- List item 2

**Bold** and *italic* text.
"""
        metadata, body = parse_vault_file(content)
        assert "# Heading" in body
        assert "- List item 1" in body
        assert "**Bold**" in body

    def test_parse_with_multiline_yaml_values(self):
        """Should handle multiline YAML values."""
        content = """---
type: note
created: 2026-06-08
description: |
  This is a multiline
  description that spans
  multiple lines.
---
Main content here.
"""
        metadata, body = parse_vault_file(content)
        assert metadata.type == "note"
        assert "Main content here." in body

    def test_parse_invalid_yaml_raises_error(self):
        """Should raise an error for malformed YAML."""
        content = """---
type: note
created: 2026-06-08
invalid: : : bad
---
Content
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_vault_file(content)

    def test_parse_missing_required_fields(self):
        """Should raise error if required fields are missing."""
        content = """---
type: finance
created: 2026-06-08
---
Content without required category
"""
        with pytest.raises(ValueError, match="validation error"):
            parse_vault_file(content)

    def test_parse_with_yaml_types(self):
        """Should properly parse YAML types (dates, numbers, booleans)."""
        content = """---
type: finance
created: 2026-06-08
category: groceries
amount: 45.50
---
Content
"""
        metadata, body = parse_vault_file(content)
        assert isinstance(metadata.amount, (int, float))
        assert metadata.amount == 45.50


class TestMetadataRoundTrip:
    """Test that parsed metadata can be serialized back."""

    def test_serialize_note_to_yaml(self):
        """Should serialize Note back to YAML format."""
        note = Note(
            type="note",
            created="2026-06-08",
            tags=["test"],
        )
        yaml_str = note.to_yaml_frontmatter()
        assert "type: note" in yaml_str
        assert "2026-06-08" in yaml_str  # Date may be quoted or not
        assert "tags:" in yaml_str or "test" in yaml_str

    def test_serialize_finance_to_yaml(self):
        """Should serialize Finance back to YAML format."""
        finance = Finance(
            type="finance",
            created="2026-06-08",
            category="groceries",
            amount=45.50,
        )
        yaml_str = finance.to_yaml_frontmatter()
        assert "type: finance" in yaml_str
        assert "category: groceries" in yaml_str
        assert "45.5" in yaml_str or "45.50" in yaml_str  # YAML may normalize float format

    def test_roundtrip_note(self):
        """Should parse and serialize back to equivalent YAML."""
        original = """---
type: note
created: 2026-06-08
tags: [research]
---
# Content"""
        metadata, body = parse_vault_file(original)
        yaml_header = metadata.to_yaml_frontmatter()
        assert "type: note" in yaml_header
        assert "2026-06-08" in yaml_header  # Date may be quoted or not
        assert body.strip() == "# Content"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_parse_file_with_triple_dashes_in_content(self):
        """Should not confuse triple dashes in content as frontmatter."""
        content = """---
type: note
created: 2026-06-08
---
Some content with
---
triple dashes inside.
"""
        metadata, body = parse_vault_file(content)
        assert metadata.type == "note"
        assert "triple dashes inside" in body

    def test_parse_empty_file(self):
        """Should handle empty file gracefully."""
        content = ""
        metadata, body = parse_vault_file(content)
        assert metadata.type == "note"
        assert body == ""

    def test_parse_only_frontmatter_marker(self):
        """Should handle file with only frontmatter markers - treats as no frontmatter."""
        content = "---\n---"
        # Empty frontmatter with no 'created' should use the fallback path
        # Actually, this should be treated as an empty body with no frontmatter
        metadata, body = parse_vault_file(content)
        # When frontmatter is truly empty/missing, should provide defaults
        assert metadata.type == "note"

    def test_default_metadata_values(self):
        """When parsing without frontmatter, should use sensible defaults."""
        content = "Just plain markdown content"
        metadata, body = parse_vault_file(content)
        assert metadata.type == "note"
        # created should be provided and be a non-empty string
        assert isinstance(metadata.created, str) and len(metadata.created) > 0
        assert body == content
