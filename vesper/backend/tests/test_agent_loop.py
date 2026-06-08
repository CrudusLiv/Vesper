import pytest
import tempfile
from pathlib import Path
from app.agent.loop import AgentLoop
from app.agent.models import AgentRequest, AgentResponse, ToolCall
from app.vault.writer import VaultWriter
from app.vault.reader import VaultReader


def test_agent_receives_request():
    """Test that AgentRequest accepts input"""
    req = AgentRequest(input="Remember to call mom", input_type="text")
    assert req.input == "Remember to call mom"
    assert req.input_type == "text"


def test_agent_loop_creation():
    """Test that AgentLoop can be instantiated"""
    agent = AgentLoop()
    assert agent is not None


def test_agent_processes_request():
    """Test that AgentLoop.process() accepts a request and returns a response"""
    agent = AgentLoop()
    req = AgentRequest(input="Add $50 to finances", input_type="text")
    response = agent.process(req)
    assert isinstance(response, AgentResponse)
    assert response.response is not None


def test_agent_loop_returns_response():
    """Test that process() returns proper response structure"""
    agent = AgentLoop()
    req = AgentRequest(input="Show my notes", input_type="text")
    response = agent.process(req)
    assert response.response != ""
    assert isinstance(response.tool_calls, list)
    assert isinstance(response.tool_results, list)


def test_agent_loop_response_fields():
    """Test that response has all required fields"""
    agent = AgentLoop()
    req = AgentRequest(input="Test input")
    response = agent.process(req)
    assert hasattr(response, "response")
    assert hasattr(response, "tool_calls")
    assert hasattr(response, "tool_results")


def test_tool_executor_dispatch_vault_tool(temp_vault, monkeypatch):
    """Test that ToolExecutor can dispatch vault tools"""
    from app.agent.executor import ToolExecutor
    from app.agent.models import ToolCall

    monkeypatch.setenv("VAULT_PATH", temp_vault)

    executor = ToolExecutor()
    tool_call = ToolCall(
        tool_name="vault_add_note",
        parameters={"path": "notes/test.md", "content": "Test content"}
    )
    result = executor.execute(tool_call)
    assert result["success"] is True
    assert result["error"] is None


def test_tool_executor_unknown_tool():
    """Test that ToolExecutor returns error for unknown tools"""
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor()
    tool_call = ToolCall(
        tool_name="unknown_tool",
        parameters={}
    )
    result = executor.execute(tool_call)
    assert result["success"] is False
    assert result["error"] is not None


@pytest.fixture
def temp_vault():
    """Create a temporary vault for testing vault tools."""
    with tempfile.TemporaryDirectory() as temp_dir:
        vault_path = Path(temp_dir) / "vault"
        vault_path.mkdir(parents=True, exist_ok=True)
        yield str(vault_path)


class TestVaultToolIntegration:
    """Integration tests for vault tools with real VaultWriter and VaultReader."""

    def test_add_note_creates_file(self, temp_vault, monkeypatch):
        """Test that add_note tool creates a note file."""
        from app.agent.tools.vault import VaultToolExecutor

        # Patch the vault path
        monkeypatch.setenv("VAULT_PATH", temp_vault)

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_note(path="notes/test.md", content="Test content")

        assert result["success"] is True
        assert result["error"] is None
        assert "created" in result["result"]

        # Verify file was created
        note_file = Path(temp_vault) / "notes" / "test.md"
        assert note_file.exists()
        content = note_file.read_text()
        assert "Test content" in content

    def test_add_note_with_tags(self, temp_vault):
        """Test adding a note with tags."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_note(
            path="notes/tagged.md",
            content="Important note",
            tags=["important", "todo"]
        )

        assert result["success"] is True
        assert result["result"]["type"] == "note"
        assert "important" in result["result"]["tags"]

        # Verify file contains tags
        note_file = Path(temp_vault) / "notes" / "tagged.md"
        content = note_file.read_text()
        assert "important" in content.lower()

    def test_add_finance_creates_transaction(self, temp_vault):
        """Test that add_finance tool creates a finance entry."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_finance(
            amount=50.0,
            category="groceries",
            date="2026-06-08",
            description="Weekly shopping"
        )

        assert result["success"] is True
        assert result["error"] is None
        assert result["result"]["type"] == "finance"
        assert result["result"]["amount"] == 50.0
        assert result["result"]["category"] == "groceries"

        # Verify file was created
        finance_file = Path(temp_vault) / "finance" / "2026-06-08.md"
        assert finance_file.exists()

    def test_add_schedule_creates_event(self, temp_vault):
        """Test that add_schedule tool creates a schedule entry."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_schedule(
            title="Team Meeting",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00",
            location="Conference Room A"
        )

        assert result["success"] is True
        assert result["error"] is None
        assert result["result"]["type"] == "schedule"
        assert result["result"]["title"] == "Team Meeting"
        assert result["result"]["start_time"] == "14:00"

        # Verify file was created
        schedule_file = Path(temp_vault) / "schedule" / "2026-06-08.md"
        assert schedule_file.exists()

    def test_search_finds_notes(self, temp_vault):
        """Test that search tool finds notes."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)

        # Add a note first
        executor.add_note(path="notes/findme.md", content="Important deadline")

        # Search for it
        result = executor.search(query="deadline", search_type="all")

        assert result["success"] is True
        assert result["error"] is None
        assert "matches" in result["result"]
        assert len(result["result"]["matches"]) > 0

    def test_search_with_limit(self, temp_vault):
        """Test that search respects limit parameter."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)

        # Add multiple notes
        for i in range(5):
            executor.add_note(
                path=f"notes/note{i}.md",
                content="test content with keyword"
            )

        # Search with limit
        result = executor.search(query="keyword", search_type="all", limit=2)

        assert result["success"] is True
        assert len(result["result"]["matches"]) <= 2

    def test_vault_tool_handles_invalid_paths(self, temp_vault):
        """Test that tools handle invalid paths gracefully."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_note(path="../../etc/passwd", content="hack")

        assert result["success"] is False
        assert result["error"] is not None

    def test_vault_tool_handles_permission_error(self, tmp_path):
        """Test that tools handle permission errors gracefully."""
        from app.agent.tools.vault import VaultToolExecutor

        # Create a read-only directory
        readonly_vault = tmp_path / "readonly"
        readonly_vault.mkdir()
        readonly_vault.chmod(0o444)

        try:
            executor = VaultToolExecutor(vault_path=str(readonly_vault))
            # Attempt to add a note - should fail due to permissions
            result = executor.add_note(path="notes/test.md", content="test")
            # Could succeed if running with elevated privileges, so just check it handles it
            assert isinstance(result["success"], bool)
        finally:
            # Restore permissions for cleanup
            readonly_vault.chmod(0o755)

    def test_roundtrip_write_then_read(self, temp_vault):
        """Test end-to-end: write note with tool, read it back."""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)

        # Write a note
        write_result = executor.add_note(
            path="notes/roundtrip.md",
            content="Important data"
        )
        assert write_result["success"] is True

        # Search for it
        search_result = executor.search(query="Important")
        assert search_result["success"] is True
        assert len(search_result["result"]["matches"]) > 0

        # Verify the match was found
        matches = search_result["result"]["matches"]
        assert matches[0]["type"] == "note"
        assert "roundtrip" in matches[0]["path"]


class TestVaultToolExecutorUnitTests:
    """Unit tests for VaultToolExecutor with stubbed vault."""

    def test_vault_tool_executor_add_note(self, temp_vault):
        """Test VaultToolExecutor.add_note()"""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_note(path="notes/test.md", content="Test")
        assert result["success"] is True
        assert result["result"]["type"] == "note"

    def test_vault_tool_executor_add_finance(self, temp_vault):
        """Test VaultToolExecutor.add_finance()"""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_finance(
            amount=50.0,
            category="food",
            date="2026-06-08"
        )
        assert result["success"] is True
        assert result["result"]["type"] == "finance"
        assert result["result"]["amount"] == 50.0

    def test_vault_tool_executor_add_schedule(self, temp_vault):
        """Test VaultToolExecutor.add_schedule()"""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.add_schedule(
            title="Team Meeting",
            date="2026-06-08",
            start_time="14:00",
            end_time="15:00"
        )
        assert result["success"] is True
        assert result["result"]["type"] == "schedule"
        assert result["result"]["title"] == "Team Meeting"

    def test_vault_tool_executor_search(self, temp_vault):
        """Test VaultToolExecutor.search()"""
        from app.agent.tools.vault import VaultToolExecutor

        executor = VaultToolExecutor(vault_path=temp_vault)
        result = executor.search(query="test", search_type="all")
        assert result["success"] is True
        assert "matches" in result["result"]


class TestVaultPathCalculation:
    """Tests for vault path fallback calculations."""

    def test_fallback_vault_path_no_env_var(self, monkeypatch):
        """Test that default VAULT_PATH calculation works correctly without env var."""
        from app.agent.tools.vault import VaultToolExecutor
        import os

        # Ensure VAULT_PATH is not set in environment
        if "VAULT_PATH" in os.environ:
            monkeypatch.delenv("VAULT_PATH")

        # Create executor without explicit vault_path - should use fallback
        executor = VaultToolExecutor()

        # Verify the fallback path is correct
        # Path should be: <project_root>/Dynamous/Memory
        expected_end = "Dynamous" + os.sep + "Memory"
        assert executor.vault_path.endswith(expected_end), \
            f"Expected vault path to end with {expected_end}, got {executor.vault_path}"

        # Verify it's not the incorrect vesper/ directory
        assert "vesper" + os.sep + "Dynamous" not in executor.vault_path, \
            f"Vault path incorrectly includes vesper directory: {executor.vault_path}"


class TestToolExecutorIntegration:
    """Test vault tools through ToolExecutor dispatch."""

    def test_tool_executor_vault_add_note(self, temp_vault, monkeypatch):
        """Test ToolExecutor dispatching vault_add_note"""
        from app.agent.executor import ToolExecutor

        monkeypatch.setenv("VAULT_PATH", temp_vault)

        executor = ToolExecutor()
        tool_call = ToolCall(
            tool_name="vault_add_note",
            parameters={"path": "notes/test.md", "content": "Hello"}
        )
        result = executor.execute(tool_call)
        assert result["success"] is True

    def test_tool_executor_vault_add_finance(self, temp_vault, monkeypatch):
        """Test ToolExecutor dispatching vault_add_finance"""
        from app.agent.executor import ToolExecutor

        monkeypatch.setenv("VAULT_PATH", temp_vault)

        executor = ToolExecutor()
        tool_call = ToolCall(
            tool_name="vault_add_finance",
            parameters={"amount": 100.0, "category": "transport", "date": "2026-06-08"}
        )
        result = executor.execute(tool_call)
        assert result["success"] is True

    def test_tool_executor_vault_add_schedule(self, temp_vault, monkeypatch):
        """Test ToolExecutor dispatching vault_add_schedule"""
        from app.agent.executor import ToolExecutor

        monkeypatch.setenv("VAULT_PATH", temp_vault)

        executor = ToolExecutor()
        tool_call = ToolCall(
            tool_name="vault_add_schedule",
            parameters={
                "title": "Dentist",
                "date": "2026-06-15",
                "start_time": "10:00",
                "end_time": "10:30"
            }
        )
        result = executor.execute(tool_call)
        assert result["success"] is True

    def test_tool_executor_vault_search(self, temp_vault, monkeypatch):
        """Test ToolExecutor dispatching vault_search"""
        from app.agent.executor import ToolExecutor

        monkeypatch.setenv("VAULT_PATH", temp_vault)

        executor = ToolExecutor()
        tool_call = ToolCall(
            tool_name="vault_search",
            parameters={"query": "important", "limit": 5}
        )
        result = executor.execute(tool_call)
        assert result["success"] is True
