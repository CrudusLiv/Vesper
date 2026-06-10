import logging
import os
from pathlib import Path
from typing import Optional
from ..models import ToolCall
from app.vault.writer import VaultWriter
from app.vault.reader import VaultReader

logger = logging.getLogger(__name__)


class VaultToolExecutor:
    """Executes vault-related tools using VaultWriter and VaultReader"""

    def __init__(self, vault_path: Optional[str] = None):
        """
        Initialize VaultToolExecutor with a vault path.

        Args:
            vault_path: Optional path to vault root. If not provided, uses VAULT_PATH env var
                       or defaults to <project_dir>/Dynamous/Memory
        """
        if vault_path:
            self.vault_path = vault_path
        else:
            self.vault_path = os.environ.get("VAULT_PATH")
            if not self.vault_path:
                # Default to standard location
                project_dir = Path(__file__).resolve().parents[5]
                self.vault_path = str(project_dir / "Dynamous" / "Memory")

        self.writer = VaultWriter(self.vault_path)
        self.reader = VaultReader(self.vault_path)

    def execute(self, tool_call: ToolCall) -> dict:
        """Dispatch to specific tool handler"""
        if tool_call.tool_name == "vault_add_note":
            return self.add_note(**tool_call.parameters)
        elif tool_call.tool_name == "vault_add_finance":
            return self.add_finance(**tool_call.parameters)
        elif tool_call.tool_name == "vault_add_schedule":
            return self.add_schedule(**tool_call.parameters)
        elif tool_call.tool_name == "vault_search":
            return self.search(**tool_call.parameters)
        elif tool_call.tool_name == "vault_read_note":
            return self.read_note(**tool_call.parameters)
        elif tool_call.tool_name == "vault_list":
            return self.list_files(**tool_call.parameters)
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Unknown vault tool: {tool_call.tool_name}"
            }

    def add_note(
        self,
        path: str,
        content: str,
        tags: Optional[list] = None,
        overwrite: bool = False
    ) -> dict:
        """
        Add a note to the vault.

        Args:
            path: File path relative to vault root (e.g., "notes/reminders.md")
            content: Markdown content (without frontmatter)
            tags: Optional list of tags
            overwrite: If True, overwrite existing file

        Returns:
            {"success": bool, "result": {...}, "error": str | None}
        """
        try:
            note_metadata = self.writer.add_note(
                path=path,
                content=content,
                tags=tags or [],
                overwrite=overwrite
            )

            return {
                "success": True,
                "result": {
                    "type": "note",
                    "path": path,
                    "created": note_metadata.created,
                    "tags": note_metadata.tags or [],
                },
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to add note: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }

    def add_finance(
        self,
        amount: float,
        category: str,
        date: Optional[str] = None,
        description: Optional[str] = None
    ) -> dict:
        """
        Log a financial transaction.

        Args:
            amount: Transaction amount
            category: Transaction category (e.g., "groceries", "utilities")
            date: Optional ISO date string (defaults to today)
            description: Optional transaction description

        Returns:
            {"success": bool, "result": {...}, "error": str | None}
        """
        try:
            finance_metadata = self.writer.add_finance(
                amount=amount,
                category=category,
                date=date,
                description=description
            )

            return {
                "success": True,
                "result": {
                    "type": "finance",
                    "amount": finance_metadata.amount,
                    "category": finance_metadata.category,
                    "created": finance_metadata.created,
                    "description": finance_metadata.description or "",
                },
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to add finance entry: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }

    def add_schedule(
        self,
        title: str,
        date: str,
        start_time: str,
        end_time: str,
        priority: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None
    ) -> dict:
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

        Returns:
            {"success": bool, "result": {...}, "error": str | None}
        """
        try:
            schedule_metadata = self.writer.add_schedule(
                title=title,
                date=date,
                start_time=start_time,
                end_time=end_time,
                priority=priority,
                location=location,
                description=description
            )

            return {
                "success": True,
                "result": {
                    "type": "schedule",
                    "title": schedule_metadata.title,
                    "created": schedule_metadata.created,
                    "start_time": schedule_metadata.start_time,
                    "end_time": schedule_metadata.end_time,
                    "priority": getattr(schedule_metadata, "priority", None) or "",
                    "location": getattr(schedule_metadata, "location", None) or "",
                    "description": getattr(schedule_metadata, "description", None) or "",
                },
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to add schedule entry: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }

    def list_files(self, directory: str = "notes") -> dict:
        try:
            validated = self.reader._validate_path(directory)
            if not validated:
                return {"success": False, "result": None, "error": f"Invalid path: {directory}"}
            full_path = Path(self.vault_path) / validated
            if not full_path.exists() or not full_path.is_dir():
                return {"success": False, "result": None, "error": f"Directory not found: {directory}"}
            files = [
                str(f.relative_to(Path(self.vault_path))).replace("\\", "/")
                for f in full_path.rglob("*.md")
                if f.name != ".gitkeep"
            ]
            return {"success": True, "result": {"directory": directory, "files": sorted(files)}, "error": None}
        except Exception as e:
            logger.error(f"Failed to list files: {e}", exc_info=True)
            return {"success": False, "result": None, "error": str(e)}

    def read_note(self, path: str) -> dict:
        try:
            result = self.reader.get_file(path)
            if result is None:
                return {"success": False, "result": None, "error": f"File not found: {path}"}
            metadata, body = result
            return {
                "success": True,
                "result": {"path": path, "content": body},
                "error": None,
            }
        except Exception as e:
            logger.error(f"Failed to read note: {e}", exc_info=True)
            return {"success": False, "result": None, "error": str(e)}

    def search(self, query: str, search_type: str = "all", limit: int = 10) -> dict:
        """
        Search the vault.

        Args:
            query: Search query string
            search_type: Type to filter by ("note", "finance", "schedule", "all")
            limit: Maximum number of results to return

        Returns:
            {"success": bool, "result": {"matches": [...]}, "error": str | None}
        """
        try:
            search_results = self.reader.search(query=query, search_type=search_type)

            # Limit results
            limited_results = search_results[:limit] if limit > 0 else search_results

            matches = []
            for path, metadata in limited_results:
                matches.append({
                    "path": path,
                    "type": metadata.type,
                    "created": metadata.created,
                    "title": getattr(metadata, "title", None),
                    "category": getattr(metadata, "category", None),
                    "amount": getattr(metadata, "amount", None),
                })

            return {
                "success": True,
                "result": {
                    "query": query,
                    "type": search_type,
                    "count": len(matches),
                    "matches": matches
                },
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to search vault: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
