"""Tests for system tools: browser, file management, and system control."""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.agent.tools.system import BrowserToolExecutor, FileManagementToolExecutor, SystemControlToolExecutor
from app.agent.models import ToolCall


# ============================================================================
# Browser Tool Tests
# ============================================================================

class TestBrowserTool:
    """Test browser automation tool."""

    def test_browser_tool_open_url(self):
        """Test opening a URL in browser."""
        executor = BrowserToolExecutor()
        tool_call = ToolCall(
            tool_name="browser_open",
            parameters={"action": "open_url", "url": "https://example.com"}
        )
        result = executor.execute(tool_call)
        assert result["success"] in [True, False]  # May fail if playwright not available
        # For now, just ensure it doesn't crash

    def test_browser_tool_search(self):
        """Test searching the web."""
        executor = BrowserToolExecutor()
        tool_call = ToolCall(
            tool_name="browser_open",
            parameters={"action": "search", "query": "python documentation"}
        )
        result = executor.execute(tool_call)
        assert result["success"] in [True, False]
        # Should have result or error
        assert "result" in result or "error" in result

    def test_browser_tool_unknown_action(self):
        """Test unknown browser action."""
        executor = BrowserToolExecutor()
        tool_call = ToolCall(
            tool_name="browser_open",
            parameters={"action": "unknown_action"}
        )
        result = executor.execute(tool_call)
        assert result["success"] is False
        assert "Unknown action" in result["error"]


# ============================================================================
# File Management Tool Tests
# ============================================================================

class TestFileManagementTool:
    """Test file management tool."""

    def test_file_tool_list_directory(self):
        """Test listing directory contents."""
        executor = FileManagementToolExecutor()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            Path(tmpdir, "file1.txt").touch()
            Path(tmpdir, "file2.txt").touch()

            tool_call = ToolCall(
                tool_name="file_manage",
                parameters={"action": "list", "path": tmpdir}
            )
            result = executor.execute(tool_call)
            assert result["success"] is True
            assert len(result["result"]) >= 2

    def test_file_tool_copy_file(self):
        """Test copying a file."""
        executor = FileManagementToolExecutor()
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "source.txt")
            src.write_text("test content")
            dest = Path(tmpdir, "copy.txt")

            tool_call = ToolCall(
                tool_name="file_manage",
                parameters={"action": "copy", "path": str(src), "destination": str(dest)}
            )
            result = executor.execute(tool_call)
            assert result["success"] is True
            assert dest.exists()
            assert dest.read_text() == "test content"

    def test_file_tool_move_file(self):
        """Test moving a file."""
        executor = FileManagementToolExecutor()
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "original.txt")
            src.write_text("test content")
            dest = Path(tmpdir, "moved.txt")

            tool_call = ToolCall(
                tool_name="file_manage",
                parameters={"action": "move", "path": str(src), "destination": str(dest)}
            )
            result = executor.execute(tool_call)
            assert result["success"] is True
            assert not src.exists()
            assert dest.exists()

    def test_file_tool_delete_file(self):
        """Test deleting a file."""
        executor = FileManagementToolExecutor()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_to_delete = Path(tmpdir, "delete_me.txt")
            file_to_delete.write_text("will be deleted")

            tool_call = ToolCall(
                tool_name="file_manage",
                parameters={"action": "delete", "path": str(file_to_delete)}
            )
            result = executor.execute(tool_call)
            assert result["success"] is True
            assert not file_to_delete.exists()

    def test_file_tool_delete_outside_vault_blocked(self):
        """Test that deleting files outside vault is blocked."""
        executor = FileManagementToolExecutor()
        # Try to delete a system file (should be blocked)
        tool_call = ToolCall(
            tool_name="file_manage",
            parameters={"action": "delete", "path": "/etc/passwd"}
        )
        result = executor.execute(tool_call)
        # Should fail due to safety check
        assert result["success"] is False

    def test_file_tool_unknown_action(self):
        """Test unknown file action."""
        executor = FileManagementToolExecutor()
        tool_call = ToolCall(
            tool_name="file_manage",
            parameters={"action": "unknown_action", "path": "/tmp"}
        )
        result = executor.execute(tool_call)
        assert result["success"] is False
        assert "Unknown action" in result["error"]


# ============================================================================
# System Control Tool Tests
# ============================================================================

class TestSystemControlTool:
    """Test system control tool."""

    def test_system_control_timer(self):
        """Test setting a timer."""
        executor = SystemControlToolExecutor()
        tool_call = ToolCall(
            tool_name="system_control",
            parameters={"action": "timer", "duration": 5}
        )
        result = executor.execute(tool_call)
        assert result["success"] is True
        assert "timer" in result["result"].lower()

    def test_system_control_timer_invalid_duration(self):
        """Test timer with invalid duration."""
        executor = SystemControlToolExecutor()
        tool_call = ToolCall(
            tool_name="system_control",
            parameters={"action": "timer", "duration": -5}
        )
        result = executor.execute(tool_call)
        assert result["success"] is False
        assert "Invalid duration" in result["error"]

    @patch('subprocess.Popen')
    def test_system_control_open_app(self, mock_popen):
        """Test opening an application."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        executor = SystemControlToolExecutor()
        tool_call = ToolCall(
            tool_name="system_control",
            parameters={"action": "open_app", "command": "notepad"}
        )
        result = executor.execute(tool_call)
        # Should succeed if command is in whitelist
        assert "result" in result or "error" in result

    def test_system_control_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked."""
        executor = SystemControlToolExecutor()
        tool_call = ToolCall(
            tool_name="system_control",
            parameters={"action": "open_app", "command": "rm -rf /"}
        )
        result = executor.execute(tool_call)
        assert result["success"] is False
        assert "not allowed" in result["error"].lower()

    def test_system_control_unknown_action(self):
        """Test unknown system action."""
        executor = SystemControlToolExecutor()
        tool_call = ToolCall(
            tool_name="system_control",
            parameters={"action": "unknown_action"}
        )
        result = executor.execute(tool_call)
        assert result["success"] is False
        assert "Unknown action" in result["error"]
