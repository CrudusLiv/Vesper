"""
Migrate existing vault files to the structured YAML-frontmatter format.

Walks all .md files in the vault, detects files that lack frontmatter, infers
the file type from the folder path, adds appropriate YAML frontmatter, and
writes a .backup copy of every file it touches.

Usage:
    python -m app.migrations.migrate_vault [--vault-path /path/to/vault] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _infer_date(file_path: Path) -> str:
    """Infer an ISO date from the filename or fall back to today."""
    match = _DATE_RE.search(file_path.stem)
    if match:
        return match.group(1)
    return datetime.now().strftime("%Y-%m-%d")


def _infer_type(file_path: Path) -> str:
    """Determine vault type from the folder the file lives in."""
    parts = {p.lower() for p in file_path.parts}
    if "finance" in parts:
        return "finance"
    if "schedule" in parts:
        return "schedule"
    return "note"


def _build_frontmatter(file_type: str, date: str) -> str:
    """Build minimal YAML frontmatter for the given type."""
    data: dict = {"type": file_type, "created": date}

    if file_type == "finance":
        data["category"] = "uncategorized"
        data["amount"] = None
    elif file_type == "schedule":
        data["start_time"] = "00:00"
        data["end_time"] = "23:59"

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n"


def _has_frontmatter(content: str) -> bool:
    """Return True if the file already starts with a YAML frontmatter block."""
    return content.lstrip().startswith("---")


class MigrationResult:
    """Accumulates statistics from a migration run."""

    def __init__(self) -> None:
        self.migrated: list[Path] = []
        self.skipped: list[Path] = []
        self.errors: list[tuple[Path, str]] = []

    @property
    def total(self) -> int:
        return len(self.migrated) + len(self.skipped) + len(self.errors)

    def summary(self) -> str:
        return (
            f"Migration complete: {len(self.migrated)} migrated, "
            f"{len(self.skipped)} skipped (already have frontmatter), "
            f"{len(self.errors)} errors out of {self.total} files."
        )


def migrate_vault(
    vault_path: str,
    dry_run: bool = False,
    backup: bool = True,
) -> MigrationResult:
    """
    Migrate all .md files in the vault that lack YAML frontmatter.

    Args:
        vault_path: Root directory of the vault.
        dry_run: If True, report what would change without writing anything.
        backup: If True (default), write a .backup copy before modifying.

    Returns:
        MigrationResult with per-file outcomes.
    """
    root = Path(vault_path)
    if not root.exists():
        raise FileNotFoundError(f"Vault path does not exist: {vault_path}")

    result = MigrationResult()

    for md_file in sorted(root.rglob("*.md")):
        # Skip backup files from a previous run
        if md_file.suffix == ".backup" or ".backup" in md_file.name:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            result.errors.append((md_file, str(exc)))
            logger.warning("Could not read %s: %s", md_file, exc)
            continue

        if _has_frontmatter(content):
            result.skipped.append(md_file)
            logger.debug("Skipping %s (already has frontmatter)", md_file)
            continue

        # Determine migration values
        file_type = _infer_type(md_file)
        date = _infer_date(md_file)
        frontmatter = _build_frontmatter(file_type, date)
        new_content = frontmatter + content

        if dry_run:
            logger.info("[DRY RUN] Would migrate %s → type=%s date=%s", md_file, file_type, date)
            result.migrated.append(md_file)
            continue

        # Backup
        if backup:
            backup_path = md_file.with_suffix(".md.backup")
            shutil.copy2(md_file, backup_path)
            logger.debug("Backed up %s → %s", md_file, backup_path)

        # Write migrated content
        try:
            md_file.write_text(new_content, encoding="utf-8")
            result.migrated.append(md_file)
            logger.info("Migrated %s (type=%s)", md_file, file_type)
        except OSError as exc:
            result.errors.append((md_file, str(exc)))
            logger.warning("Could not write %s: %s", md_file, exc)

    return result


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Migrate vault files to YAML-frontmatter format.")
    parser.add_argument(
        "--vault-path",
        default=None,
        help="Path to vault root (defaults to VAULT_PATH env var or /workspace/Dynamous/Memory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating .backup copies",
    )
    args = parser.parse_args()

    if args.vault_path is None:
        import os
        args.vault_path = os.getenv("VAULT_PATH", "/workspace/Dynamous/Memory")

    result = migrate_vault(
        vault_path=args.vault_path,
        dry_run=args.dry_run,
        backup=not args.no_backup,
    )
    print(result.summary())
    if result.errors:
        for path, msg in result.errors:
            print(f"  ERROR {path}: {msg}")


if __name__ == "__main__":
    _main()
