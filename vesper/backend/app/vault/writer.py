"""Vault file writer for persisting notes, finances, and schedules."""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Union
from app.vault.schema import Note, Finance, Schedule, VaultFileMetadata, parse_vault_file


class VaultWriter:
    """Write and update vault files with proper YAML formatting."""

    def __init__(self, vault_path: str):
        """
        Initialize VaultWriter with a vault root directory.

        Args:
            vault_path: Path to the vault root directory
        """
        self.vault_path = vault_path

    def _validate_path(self, relative_path: str) -> Path:
        """
        Validate and resolve a relative path within the vault.

        Args:
            relative_path: Path relative to vault root

        Raises:
            ValueError: If path is absolute, contains .. traversal, or is empty

        Returns:
            Resolved Path object within vault
        """
        if not relative_path or not relative_path.strip():
            raise ValueError("Path cannot be empty")

        # Prevent absolute paths
        if os.path.isabs(relative_path):
            raise ValueError(f"Absolute paths not allowed: {relative_path}")

        # Check for explicit parent directory references
        if ".." in relative_path or relative_path.startswith("./.."):
            raise ValueError(f"Path traversal detected: {relative_path}")

        # Normalize and check for path traversal
        path = Path(relative_path)

        # Check for .. components in path parts
        try:
            resolved = (Path(self.vault_path) / path).resolve()
            vault_root = Path(self.vault_path).resolve()

            # Ensure resolved path is within vault
            if not str(resolved).startswith(str(vault_root)):
                raise ValueError(f"Path traversal detected: {relative_path}")
        except (ValueError, RuntimeError) as e:
            raise ValueError(f"Invalid path: {relative_path}") from e

        return path

    def _ensure_md_extension(self, path: Path) -> Path:
        """
        Ensure path has .md extension.

        Args:
            path: Path object

        Returns:
            Path with .md extension
        """
        if not str(path).endswith(".md"):
            return path.parent / (path.name + ".md")
        return path

    def ensure_directory(self, relative_path: str) -> Path:
        """
        Create directory if it doesn't exist.

        Args:
            relative_path: Directory path relative to vault root

        Returns:
            Path object for the directory
        """
        path = self._validate_path(relative_path)
        full_path = Path(self.vault_path) / path
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def add_note(
        self,
        path: str,
        content: str,
        tags: Optional[list[str]] = None,
        created: Optional[str] = None,
        overwrite: bool = False,
    ) -> Note:
        """
        Write a markdown note with metadata.

        Args:
            path: File path relative to vault root (e.g., "notes/reminders.md")
            content: Markdown content (without frontmatter)
            tags: Optional list of tags
            created: Optional ISO date string (defaults to today)
            overwrite: If True, overwrite existing file (default: False)

        Returns:
            Note metadata object

        Raises:
            ValueError: If path is invalid
            FileExistsError: If file exists and overwrite is False
        """
        # Validate path
        relative_path = self._validate_path(path)
        relative_path = self._ensure_md_extension(relative_path)

        # Prepare metadata
        if created is None:
            created = datetime.now().strftime("%Y-%m-%d")

        note = Note(
            type="note",
            created=created,
            tags=tags or [],
        )

        # Write file
        self._write_file(
            relative_path=str(relative_path),
            metadata=note,
            content=content,
            overwrite=overwrite,
        )

        return note

    def add_finance(
        self,
        amount: float,
        category: str,
        date: Optional[str] = None,
        description: Optional[str] = None,
        overwrite: bool = False,
    ) -> Finance:
        """
        Log a financial transaction.

        Args:
            amount: Transaction amount
            category: Transaction category (e.g., "groceries", "utilities")
            date: ISO date string (defaults to today)
            description: Optional transaction description
            overwrite: If True, overwrite existing file (default: False)

        Returns:
            Finance metadata object

        Raises:
            ValueError: If inputs are invalid
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # Create finance entry
        finance = Finance(
            type="finance",
            created=date,
            category=category,
            amount=amount,
            description=description,
        )

        # Use ISO date for filename
        path = f"finance/{date}.md"
        relative_path = self._validate_path(path)
        relative_path = self._ensure_md_extension(relative_path)

        # Use description or category as content
        content = description or f"Category: {category}\nAmount: {amount}"

        self._write_file(
            relative_path=str(relative_path),
            metadata=finance,
            content=content,
            overwrite=overwrite,
            append=True,  # Multiple transactions per day
        )

        return finance

    def add_schedule(
        self,
        title: str,
        date: str,
        start_time: str,
        end_time: str,
        priority: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        overwrite: bool = False,
    ) -> Schedule:
        """
        Add a scheduled event.

        Args:
            title: Event title
            date: ISO date string (e.g., "2026-06-08")
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            priority: Optional priority level (e.g., "high", "medium", "low")
            location: Optional event location
            description: Optional event description
            overwrite: If True, overwrite existing file (default: False)

        Returns:
            Schedule metadata object

        Raises:
            ValueError: If inputs are invalid
        """
        # Create schedule entry
        schedule = Schedule(
            type="schedule",
            created=date,
            title=title,
            start_time=start_time,
            end_time=end_time,
        )

        # Add extra fields if provided
        if priority:
            schedule.priority = priority
        if location:
            schedule.location = location
        if description:
            schedule.description = description

        # Use ISO date for filename
        path = f"schedule/{date}.md"
        relative_path = self._validate_path(path)
        relative_path = self._ensure_md_extension(relative_path)

        # Build content
        content_parts = []
        if description:
            content_parts.append(description)
        if location:
            content_parts.append(f"Location: {location}")
        content = "\n".join(content_parts) if content_parts else f"Event: {title}"

        self._write_file(
            relative_path=str(relative_path),
            metadata=schedule,
            content=content,
            overwrite=overwrite,
            append=True,  # Multiple events per day
        )

        return schedule

    def update_file(
        self,
        path: str,
        metadata: Union[Note, Finance, Schedule],
        content: Optional[str] = None,
    ) -> Union[Note, Finance, Schedule]:
        """
        Update existing file's metadata and/or content.

        Args:
            path: File path relative to vault root
            metadata: Updated metadata object
            content: Optional new content (if None, preserves existing)

        Returns:
            Updated metadata object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is invalid
        """
        relative_path = self._validate_path(path)
        full_path = Path(self.vault_path) / relative_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # If content not provided, read existing
        if content is None:
            file_content = full_path.read_text(encoding="utf-8")
            _, content = parse_vault_file(file_content)

        # Update modified timestamp
        metadata.modified = datetime.now().isoformat()

        # Write updated file
        self._write_file(
            relative_path=str(relative_path),
            metadata=metadata,
            content=content,
            overwrite=True,
        )

        return metadata

    def _write_file(
        self,
        relative_path: str,
        metadata: VaultFileMetadata,
        content: str,
        overwrite: bool = False,
        append: bool = False,
    ) -> None:
        """
        Internal method to write a file with frontmatter.

        Args:
            relative_path: Path relative to vault root
            metadata: Metadata to serialize
            content: File content (markdown body)
            overwrite: If True, overwrite existing file
            append: If True, append to file instead of overwriting

        Raises:
            FileExistsError: If file exists and overwrite/append are False
        """
        # Ensure relative_path is normalized
        relative_path = str(self._validate_path(relative_path))
        full_path = Path(self.vault_path) / relative_path

        # Create parent directory
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle existing file
        if full_path.exists():
            if not overwrite and not append:
                raise FileExistsError(f"File already exists: {relative_path}")

            if append:
                # Read existing file and append new entry
                existing_content = full_path.read_text(encoding="utf-8")
                # For finance and schedule, append a new section
                frontmatter = metadata.to_yaml_frontmatter()
                new_entry = f"{frontmatter}\n{content}\n\n"
                full_content = existing_content + new_entry
                full_path.write_text(full_content, encoding="utf-8")
                return

        # Build file content
        frontmatter = metadata.to_yaml_frontmatter()
        file_content = f"{frontmatter}\n{content}"

        # Write file
        full_path.write_text(file_content, encoding="utf-8")
