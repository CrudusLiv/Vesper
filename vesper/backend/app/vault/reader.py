"""Vault file reader for retrieving and searching vault files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union, Tuple, List
from app.vault.schema import Note, Finance, Schedule, VaultFileMetadata, parse_vault_file


def _parse_all_entries(content: str) -> List[Tuple[Union[Note, Finance, Schedule], str]]:
    """
    Parse all entries from a file that may contain multiple frontmatter blocks.

    This handles finance and schedule files that can have multiple entries
    appended with separate frontmatter blocks.

    Args:
        content: Raw file content with potentially multiple frontmatter blocks

    Returns:
        List of (metadata, body) tuples
    """
    entries = []

    if not content or not content.startswith("---"):
        # No frontmatter, return as single note entry
        return [(Note(type="note", created=""), content)]

    lines = content.split("\n")
    i = 1  # Skip first ---

    while i < len(lines):
        # Find closing --- for this entry
        closing_index = -1
        for j in range(i, len(lines)):
            if lines[j].strip() == "---":
                closing_index = j
                break

        if closing_index == -1:
            # No closing delimiter found, rest is body
            body = "\n".join(lines[i:]).lstrip()
            break

        # Extract YAML and body
        yaml_content = "\n".join(lines[i:closing_index])
        body_start = closing_index + 1

        # Find the next frontmatter or end of file
        next_closing = -1
        for j in range(body_start, len(lines)):
            if lines[j].strip() == "---":
                next_closing = j
                break

        if next_closing == -1:
            # No more frontmatters, rest is body
            body = "\n".join(lines[body_start:]).lstrip()
        else:
            # Body is between closing_index and next_closing (which is the start of next entry)
            body = "\n".join(lines[body_start:next_closing]).lstrip()

        # Parse this entry
        try:
            if not yaml_content.strip():
                metadata_dict = {}
            else:
                import yaml
                metadata_dict = yaml.safe_load(yaml_content)
                if metadata_dict is None:
                    metadata_dict = {}

            if "created" not in metadata_dict:
                metadata_dict["created"] = ""
            if "type" not in metadata_dict:
                metadata_dict["type"] = "note"

            file_type = metadata_dict.get("type", "note")

            from pydantic import ValidationError
            if file_type == "note":
                metadata = Note(**metadata_dict)
            elif file_type == "finance":
                metadata = Finance(**metadata_dict)
            elif file_type == "schedule":
                metadata = Schedule(**metadata_dict)
            else:
                raise ValueError(f"Unknown file type: {file_type}")

            entries.append((metadata, body))
        except (ValueError, ValidationError):
            # Skip malformed entries
            pass

        # Move to next entry
        if next_closing == -1:
            break
        i = next_closing + 1

    return entries if entries else [(Note(type="note", created=""), content)]


class VaultReader:
    """Read and search vault files."""

    def __init__(self, vault_path: str):
        """
        Initialize VaultReader with a vault root directory.

        Args:
            vault_path: Path to the vault root directory
        """
        self.vault_path = vault_path

    def _validate_path(self, relative_path: str) -> Optional[Path]:
        """
        Validate and resolve a relative path within the vault.

        Args:
            relative_path: Path relative to vault root

        Returns:
            Resolved Path object within vault, or None if invalid
        """
        if not relative_path or not relative_path.strip():
            return None

        # Prevent absolute paths
        if os.path.isabs(relative_path):
            return None

        # Check for explicit parent directory references
        if ".." in relative_path or relative_path.startswith("./.."):
            return None

        # Normalize and check for path traversal
        try:
            path = Path(relative_path)
            resolved = (Path(self.vault_path) / path).resolve()
            vault_root = Path(self.vault_path).resolve()

            # Ensure resolved path is within vault
            try:
                resolved.relative_to(vault_root)
            except ValueError:
                return None
        except (ValueError, RuntimeError):
            return None

        return path

    def _ensure_md_extension(self, path: Path) -> Path:
        """
        Ensure path has .md extension, or try both with/without.

        Args:
            path: Path object

        Returns:
            Path object that exists, or path with .md extension
        """
        if str(path).endswith(".md"):
            return path

        # Try without .md first, then with
        full_path_no_ext = Path(self.vault_path) / path
        full_path_with_ext = Path(self.vault_path) / (str(path) + ".md")

        if full_path_with_ext.exists():
            return path.parent / (path.name + ".md")
        elif full_path_no_ext.exists():
            return path

        # Default to .md extension
        return path.parent / (path.name + ".md")

    def get_file(
        self, path: str
    ) -> Optional[Tuple[Union[Note, Finance, Schedule], str]]:
        """
        Load metadata and content from a file.

        Args:
            path: File path relative to vault root

        Returns:
            Tuple of (metadata, content) or None if file not found
        """
        relative_path = self._validate_path(path)
        if not relative_path:
            return None

        # Try with .md extension if not present
        if not str(relative_path).endswith(".md"):
            # Try both with and without extension
            full_path_with_ext = Path(self.vault_path) / (str(relative_path) + ".md")
            full_path_no_ext = Path(self.vault_path) / relative_path

            if full_path_with_ext.exists():
                relative_path = relative_path.parent / (relative_path.name + ".md")
            elif not full_path_no_ext.exists():
                # Try with .md extension
                relative_path = relative_path.parent / (relative_path.name + ".md")

        full_path = Path(self.vault_path) / relative_path

        if not full_path.exists():
            return None

        try:
            content = full_path.read_text(encoding="utf-8")
            metadata, body = parse_vault_file(content)
            return metadata, body
        except (ValueError, IOError):
            return None

    def get_note(self, path: str) -> Optional[Union[Note, Finance, Schedule]]:
        """
        Load a note, finance entry, or schedule by path.

        Args:
            path: File path relative to vault root

        Returns:
            Metadata object or None if file not found
        """
        result = self.get_file(path)
        if result:
            metadata, _ = result
            return metadata
        return None

    def list_notes(self, directory: str = "notes") -> List[Note]:
        """
        List all notes in a directory.

        Args:
            directory: Directory path relative to vault root (default: "notes")

        Returns:
            List of Note objects
        """
        relative_path = self._validate_path(directory)
        if not relative_path:
            return []

        full_path = Path(self.vault_path) / relative_path

        if not full_path.exists() or not full_path.is_dir():
            return []

        notes = []
        try:
            # Walk directory for all .md files
            for md_file in full_path.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    metadata, _ = parse_vault_file(content)
                    # Filter to only Note type
                    if isinstance(metadata, Note):
                        notes.append(metadata)
                except (ValueError, IOError):
                    # Skip files that can't be parsed
                    continue
        except (OSError, PermissionError):
            pass

        return notes

    def list_finances(self, date: Optional[str] = None) -> List[Finance]:
        """
        List finance entries.

        Args:
            date: Optional ISO date string to filter by specific date

        Returns:
            List of Finance objects, sorted by date (newest first)
        """
        relative_path = self._validate_path("finance")
        if not relative_path:
            return []

        full_path = Path(self.vault_path) / relative_path

        if not full_path.exists() or not full_path.is_dir():
            return []

        finances = []
        try:
            # Walk directory for all .md files
            for md_file in full_path.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Parse all entries in file (may have multiple appended)
                    entries = _parse_all_entries(content)
                    for metadata, _ in entries:
                        if isinstance(metadata, Finance):
                            if date is None or metadata.created == date:
                                finances.append(metadata)
                except (ValueError, IOError):
                    continue
        except (OSError, PermissionError):
            pass

        # Sort by date, most recent first
        finances.sort(key=lambda f: f.created, reverse=True)
        return finances

    def list_schedules(self, date: Optional[str] = None) -> List[Schedule]:
        """
        List schedule entries.

        Args:
            date: Optional ISO date string to filter by specific date

        Returns:
            List of Schedule objects, sorted by date (newest first)
        """
        relative_path = self._validate_path("schedule")
        if not relative_path:
            return []

        full_path = Path(self.vault_path) / relative_path

        if not full_path.exists() or not full_path.is_dir():
            return []

        schedules = []
        try:
            # Walk directory for all .md files
            for md_file in full_path.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Parse all entries in file (may have multiple appended)
                    entries = _parse_all_entries(content)
                    for metadata, _ in entries:
                        if isinstance(metadata, Schedule):
                            if date is None or metadata.created == date:
                                schedules.append(metadata)
                except (ValueError, IOError):
                    continue
        except (OSError, PermissionError):
            pass

        # Sort by date, most recent first
        schedules.sort(key=lambda s: s.created, reverse=True)
        return schedules

    def search(
        self, query: str, search_type: str = "all"
    ) -> List[Tuple[str, Union[Note, Finance, Schedule]]]:
        """
        Search across vault content by keyword.

        Args:
            query: Search query string
            search_type: Type to filter by ("note", "finance", "schedule", "all")

        Returns:
            List of tuples (file_path, metadata) where query matches, sorted by date (newest first)
        """
        if not query or not query.strip():
            return []

        results = []
        query_lower = query.lower()

        try:
            # Search notes
            if search_type in ("all", "note"):
                for md_file in Path(self.vault_path).rglob("notes/*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        metadata, body = parse_vault_file(content)
                        if isinstance(metadata, Note):
                            # Search in body and tags
                            if (
                                query_lower in body.lower()
                                or any(query_lower in tag.lower() for tag in (metadata.tags or []))
                            ):
                                rel_path = str(
                                    md_file.relative_to(self.vault_path)
                                ).replace("\\", "/")
                                results.append((rel_path, metadata))
                    except (ValueError, IOError):
                        continue

            # Search finances
            if search_type in ("all", "finance"):
                for md_file in Path(self.vault_path).rglob("finance/*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        metadata, body = parse_vault_file(content)
                        if isinstance(metadata, Finance):
                            # Search in category, description, amount, body
                            match = (
                                query_lower in (metadata.category or "").lower()
                                or query_lower in (metadata.description or "").lower()
                                or query_lower in str(metadata.amount).lower()
                                or query_lower in body.lower()
                            )
                            if match:
                                rel_path = str(
                                    md_file.relative_to(self.vault_path)
                                ).replace("\\", "/")
                                results.append((rel_path, metadata))
                    except (ValueError, IOError):
                        continue

            # Search schedules
            if search_type in ("all", "schedule"):
                for md_file in Path(self.vault_path).rglob("schedule/*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        metadata, body = parse_vault_file(content)
                        if isinstance(metadata, Schedule):
                            # Search in title, description, location, body
                            match = (
                                query_lower in (metadata.title or "").lower()
                                or query_lower in (metadata.description or "").lower()
                                or query_lower in body.lower()
                            )
                            if match:
                                rel_path = str(
                                    md_file.relative_to(self.vault_path)
                                ).replace("\\", "/")
                                results.append((rel_path, metadata))
                    except (ValueError, IOError):
                        continue
        except (OSError, PermissionError):
            pass

        # Sort by date, most recent first
        results.sort(key=lambda x: x[1].created, reverse=True)
        return results
