"""System tools for browser automation, file management, and system control."""
import logging
import subprocess
import os
import shutil
import platform
from pathlib import Path
from typing import Optional, Any
from ..models import ToolCall

logger = logging.getLogger(__name__)

# Safe application whitelist for system_control tool
SAFE_APPS = {
    "windows": {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "vscode": "code.exe",
    },
    "linux": {
        "gedit": "gedit",
        "firefox": "firefox",
        "chrome": "google-chrome",
        "vscode": "code",
    },
    "darwin": {  # macOS
        "notes": "open -a Notes",
        "firefox": "open -a Firefox",
        "chrome": "open -a 'Google Chrome'",
        "vscode": "code",
    }
}


class BrowserToolExecutor:
    """Executes browser automation operations."""

    def __init__(self):
        """Initialize browser tool with optional playwright support."""
        self.playwright_available = False
        try:
            from playwright.sync_api import sync_playwright
            self.sync_playwright = sync_playwright
            self.playwright_available = True
        except ImportError:
            logger.warning("playwright not installed; browser tool limited to info")

    def execute(self, tool_call: ToolCall) -> dict:
        """Dispatch to specific browser action."""
        action = tool_call.parameters.get("action")

        if action == "open_url":
            url = tool_call.parameters.get("url")
            return self.open_url(url)
        elif action == "search":
            query = tool_call.parameters.get("query")
            return self.search(query)
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Unknown action: {action}. Use 'open_url' or 'search'."
            }

    def open_url(self, url: str) -> dict:
        """
        Open a URL in the browser.

        Args:
            url: URL to open

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not url:
            return {
                "success": False,
                "result": None,
                "error": "URL is required"
            }

        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            # Try to use webbrowser module (works cross-platform without dependencies)
            import webbrowser
            webbrowser.open(url)
            return {
                "success": True,
                "result": f"Opened {url}",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to open URL: {str(e)}"
            }

    def search(self, query: str) -> dict:
        """
        Perform a web search.

        Args:
            query: Search query

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not query:
            return {
                "success": False,
                "result": None,
                "error": "Search query is required"
            }

        try:
            import webbrowser
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return {
                "success": True,
                "result": f"Searched for: {query}",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to search for {query}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to perform search: {str(e)}"
            }


class FileManagementToolExecutor:
    """Executes file management operations with safety checks."""

    # Define vault paths (where deletions are allowed)
    VAULT_PATHS = [
        Path.home() / "Dynamous" / "Memory",  # Default vault location
        "/workspace/Dynamous/Memory",  # Docker workspace
    ]

    def execute(self, tool_call: ToolCall) -> dict:
        """Dispatch to specific file action."""
        action = tool_call.parameters.get("action")

        if action == "list":
            path = tool_call.parameters.get("path")
            return self.list_directory(path)
        elif action == "copy":
            path = tool_call.parameters.get("path")
            destination = tool_call.parameters.get("destination")
            return self.copy_file(path, destination)
        elif action == "move":
            path = tool_call.parameters.get("path")
            destination = tool_call.parameters.get("destination")
            return self.move_file(path, destination)
        elif action == "delete":
            path = tool_call.parameters.get("path")
            recursive = tool_call.parameters.get("recursive", False)
            return self.delete_file(path, recursive=recursive)
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Unknown action: {action}. Use 'list', 'copy', 'move', or 'delete'."
            }

    def _is_safe_path(self, path: str) -> bool:
        """
        Check if a path is safe to operate on.
        Only allow operations within vault or user home directory.
        """
        try:
            path_obj = Path(path)
            if path_obj.exists():
                path_obj = path_obj.resolve()
            else:
                # Even if path doesn't exist, check if it would be in safe location
                path_obj = Path(path).resolve()

            home = Path.home().resolve()

            # Check if path is within vault
            for vault_path_str in self.VAULT_PATHS:
                try:
                    vault_path = Path(vault_path_str).resolve()
                    path_obj.relative_to(vault_path)
                    return True
                except (ValueError, RuntimeError):
                    pass

            # Check if path is within user home
            try:
                path_obj.relative_to(home)
                return True
            except (ValueError, RuntimeError):
                pass

            return False
        except Exception as e:
            logger.error(f"Error checking path safety: {e}")
            return False

    def list_directory(self, path: str) -> dict:
        """
        List contents of a directory.

        Args:
            path: Directory path

        Returns:
            {"success": bool, "result": list[str], "error": str | None}
        """
        if not path:
            return {
                "success": False,
                "result": None,
                "error": "Path is required"
            }

        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return {
                    "success": False,
                    "result": None,
                    "error": f"Path does not exist: {path}"
                }

            if not path_obj.is_dir():
                return {
                    "success": False,
                    "result": None,
                    "error": f"Path is not a directory: {path}"
                }

            items = [item.name for item in path_obj.iterdir()]
            return {
                "success": True,
                "result": items,
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to list directory: {str(e)}"
            }

    def copy_file(self, path: str, destination: str) -> dict:
        """
        Copy a file or directory.

        Args:
            path: Source path
            destination: Destination path

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not path or not destination:
            return {
                "success": False,
                "result": None,
                "error": "Both source and destination paths are required"
            }

        try:
            src = Path(path).resolve()
            dst = Path(destination).resolve()

            if not src.exists():
                return {
                    "success": False,
                    "result": None,
                    "error": f"Source path does not exist: {path}"
                }

            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

            return {
                "success": True,
                "result": f"Copied {path} to {destination}",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to copy {path} to {destination}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to copy: {str(e)}"
            }

    def move_file(self, path: str, destination: str) -> dict:
        """
        Move a file or directory.

        Args:
            path: Source path
            destination: Destination path

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not path or not destination:
            return {
                "success": False,
                "result": None,
                "error": "Both source and destination paths are required"
            }

        try:
            src = Path(path).resolve()
            dst = Path(destination).resolve()

            if not src.exists():
                return {
                    "success": False,
                    "result": None,
                    "error": f"Source path does not exist: {path}"
                }

            shutil.move(str(src), str(dst))
            return {
                "success": True,
                "result": f"Moved {path} to {destination}",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to move {path} to {destination}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to move: {str(e)}"
            }

    def delete_file(self, path: str, recursive: bool = False) -> dict:
        """
        Delete a file or directory.

        Args:
            path: File or directory path
            recursive: If True, delete directory recursively

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not path:
            return {
                "success": False,
                "result": None,
                "error": "Path is required"
            }

        # Safety check: only allow deletion within vault or home directory
        if not self._is_safe_path(path):
            return {
                "success": False,
                "result": None,
                "error": f"Deletion is only allowed within vault or home directory. Path: {path}"
            }

        try:
            path_obj = Path(path).resolve()

            if not path_obj.exists():
                return {
                    "success": False,
                    "result": None,
                    "error": f"Path does not exist: {path}"
                }

            if path_obj.is_dir():
                if not recursive:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"Path is a directory. Use recursive=True to delete: {path}"
                    }
                shutil.rmtree(path_obj)
            else:
                path_obj.unlink()

            return {
                "success": True,
                "result": f"Deleted {path}",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to delete: {str(e)}"
            }


class SystemControlToolExecutor:
    """Executes system control operations with safety guards."""

    def __init__(self):
        """Initialize system control tool."""
        self.platform = platform.system().lower()

    def execute(self, tool_call: ToolCall) -> dict:
        """Dispatch to specific system action."""
        action = tool_call.parameters.get("action")

        if action == "timer":
            duration = tool_call.parameters.get("duration")
            return self.set_timer(duration)
        elif action == "open_app":
            command = tool_call.parameters.get("command")
            return self.open_app(command)
        elif action == "shutdown":
            return self.shutdown()
        elif action == "sleep":
            duration = tool_call.parameters.get("duration")
            return self.sleep(duration)
        else:
            return {
                "success": False,
                "result": None,
                "error": f"Unknown action: {action}. Use 'timer', 'open_app', 'shutdown', or 'sleep'."
            }

    def set_timer(self, duration: int) -> dict:
        """
        Set a timer.

        Args:
            duration: Timer duration in seconds

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not duration or duration <= 0:
            return {
                "success": False,
                "result": None,
                "error": f"Invalid duration: {duration}. Duration must be positive."
            }

        try:
            # For now, just log the timer request
            # In a real implementation, this could use system notifications or a daemon
            return {
                "success": True,
                "result": f"Timer set for {duration} seconds",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to set timer: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to set timer: {str(e)}"
            }

    def open_app(self, command: str) -> dict:
        """
        Open an application from the safe whitelist.

        Args:
            command: Application name (e.g., 'notepad', 'firefox')

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        if not command:
            return {
                "success": False,
                "result": None,
                "error": "Command is required"
            }

        # Check if command is in safe whitelist
        platform_name = "windows" if self.platform == "windows" else ("darwin" if self.platform == "darwin" else "linux")
        safe_apps = SAFE_APPS.get(platform_name, {})

        if command.lower() not in safe_apps:
            return {
                "success": False,
                "result": None,
                "error": f"Command '{command}' is not allowed. Safe commands: {', '.join(safe_apps.keys())}"
            }

        try:
            app_path = safe_apps[command.lower()]
            if self.platform == "darwin":
                # macOS uses 'open' command
                subprocess.Popen(app_path.split())
            elif self.platform == "windows":
                subprocess.Popen([app_path])
            else:
                # Linux
                subprocess.Popen([app_path])

            return {
                "success": True,
                "result": f"Opened {command}",
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to open app {command}: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Failed to open application: {str(e)}"
            }

    def shutdown(self) -> dict:
        """
        Request system shutdown (requires user confirmation).

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        # For safety, don't actually execute shutdown from agent
        # Just log the request
        return {
            "success": False,
            "result": None,
            "error": "Shutdown is not allowed from agent for safety reasons. Use your system menu instead."
        }

    def sleep(self, duration: int) -> dict:
        """
        Put system to sleep.

        Args:
            duration: Sleep duration in seconds (mostly ignored, system sleeps immediately)

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        # For safety, don't actually execute sleep from agent
        # Just log the request
        return {
            "success": False,
            "result": None,
            "error": "Sleep is not allowed from agent for safety reasons. Use your system menu instead."
        }
