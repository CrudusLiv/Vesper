"""Vault file schema and YAML frontmatter parsing."""
from __future__ import annotations

from typing import Optional, Literal, Union, Tuple, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError
import yaml


class VaultFileMetadata(BaseModel):
    """Base metadata for all vault files."""

    model_config = ConfigDict(extra="allow")

    type: Literal["note", "finance", "schedule"]
    created: str  # ISO format: YYYY-MM-DD or timestamp
    modified: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)

    @field_validator("created", mode="before")
    @classmethod
    def convert_created_to_string(cls, v: Any) -> str:
        """Convert date objects to ISO format strings."""
        if isinstance(v, date) and not isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, datetime):
            return v.isoformat()
        if v is None:
            raise ValueError("created field is required")
        return str(v)

    @field_validator("modified", mode="before")
    @classmethod
    def convert_modified_to_string(cls, v: Any) -> Optional[str]:
        """Convert date objects to ISO format strings."""
        if v is None:
            return None
        if isinstance(v, date) and not isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

    def to_yaml_frontmatter(self) -> str:
        """Serialize metadata to YAML frontmatter format."""
        data = self.model_dump(exclude_none=True)
        # Filter out default type if it's the same
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return f"---\n{yaml_str}---"


class Note(VaultFileMetadata):
    """Metadata for a note file."""

    type: Literal["note"] = "note"


class Finance(VaultFileMetadata):
    """Metadata for a finance transaction entry."""

    type: Literal["finance"] = "finance"
    category: str  # e.g., "groceries", "utilities", "entertainment"
    amount: Optional[float] = None
    description: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is not empty."""
        if not v or not v.strip():
            raise ValueError("category cannot be empty")
        return v.strip()


class Schedule(VaultFileMetadata):
    """Metadata for a schedule entry."""

    type: Literal["schedule"] = "schedule"
    start_time: str  # HH:MM format
    end_time: str    # HH:MM format
    title: Optional[str] = None
    description: Optional[str] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_time_format(cls, v: Any) -> str:
        """Validate time format is HH:MM."""
        if not isinstance(v, str):
            v = str(v)
        v = v.strip().strip('"').strip("'")  # Handle quoted strings from YAML
        # Simple validation: HH:MM format
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError(f"Time must be in HH:MM format, got '{v}'")
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError(
                    f"Invalid time values: hour={hour}, minute={minute}"
                )
        except ValueError as e:
            raise ValueError(f"Invalid time format '{v}': {e}")
        return f"{hour:02d}:{minute:02d}"


def parse_vault_file(
    content: str,
) -> Tuple[Union[Note, Finance, Schedule], str]:
    """
    Parse a vault file with YAML frontmatter.

    Args:
        content: Raw file content with optional YAML frontmatter

    Returns:
        Tuple of (parsed_metadata, markdown_body)

    Raises:
        ValueError: If YAML is malformed or validation fails
    """
    content = content or ""

    # Check if file starts with frontmatter delimiter
    if not content.startswith("---"):
        # No frontmatter, treat entire content as body
        # Default to Note type
        return Note(type="note", created=datetime.now().strftime("%Y-%m-%d")), content

    # Find the closing --- delimiter
    lines = content.split("\n")
    if len(lines) < 2:
        # No closing delimiter found
        return Note(type="note", created=datetime.now().strftime("%Y-%m-%d")), content

    # Find closing delimiter
    closing_index = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_index = i
            break

    if closing_index == -1:
        # No closing delimiter found, treat as regular content
        return Note(type="note", created=datetime.now().strftime("%Y-%m-%d")), content

    # Extract YAML and body
    yaml_content = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])

    # Parse YAML
    try:
        if not yaml_content.strip():
            # Empty frontmatter
            metadata_dict = {}
        else:
            metadata_dict = yaml.safe_load(yaml_content)
            if metadata_dict is None:
                metadata_dict = {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in frontmatter: {e}")

    # Ensure metadata_dict is a dict
    if not isinstance(metadata_dict, dict):
        raise ValueError(f"Frontmatter must be a YAML object, got {type(metadata_dict)}")

    # Provide defaults if missing required fields
    if "created" not in metadata_dict:
        metadata_dict["created"] = datetime.now().strftime("%Y-%m-%d")
    if "type" not in metadata_dict:
        metadata_dict["type"] = "note"

    # Determine file type and create appropriate metadata object
    file_type = metadata_dict.get("type", "note")

    try:
        if file_type == "note":
            metadata = Note(**metadata_dict)
        elif file_type == "finance":
            metadata = Finance(**metadata_dict)
        elif file_type == "schedule":
            metadata = Schedule(**metadata_dict)
        else:
            raise ValueError(f"Unknown file type: {file_type}")
    except ValidationError as e:
        # Re-raise Pydantic validation errors as ValueError
        raise ValueError(f"Metadata validation error: {e}")

    return metadata, body.lstrip()
