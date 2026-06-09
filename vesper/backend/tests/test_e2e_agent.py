"""
End-to-end integration tests for the full Vesper agent pipeline.

Exercises the complete flow:
  HTTP request → chat route → AgentLoop → ToolExecutor → VaultWriter/Reader

Ollama is not required — AgentLoop stubs its response for now.
Vault operations hit real temp directories.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agent.loop import AgentLoop
from app.agent.models import AgentRequest, AgentResponse, ToolCall
from app.agent.executor import ToolExecutor
from app.agent.tools.vault import VaultToolExecutor
from app.vault.writer import VaultWriter
from app.vault.reader import VaultReader

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-secret"}


# ── Chat route integration ────────────────────────────────────────────────────

class TestChatRouteE2E:
    """Tests that the /api/chat endpoint drives the full agent pipeline."""

    def test_chat_returns_agent_response(self):
        resp = client.post("/api/chat", json={"message": "Hello"}, headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert "response" in body
        assert "tool_calls" in body
        assert "tool_results" in body

    def test_chat_response_is_string(self):
        resp = client.post("/api/chat", json={"message": "What time is it?"}, headers=AUTH)
        assert resp.status_code == 200
        assert isinstance(resp.json()["response"], str)
        assert len(resp.json()["response"]) > 0

    def test_chat_with_history(self):
        resp = client.post(
            "/api/chat",
            json={
                "message": "Continue from before",
                "history": [
                    {"role": "user", "content": "Add a note"},
                    {"role": "assistant", "content": "Done"},
                ],
            },
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_chat_requires_auth(self):
        resp = client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 401

    def test_chat_tool_calls_list(self):
        resp = client.post("/api/chat", json={"message": "Add $20 for lunch"}, headers=AUTH)
        assert isinstance(resp.json()["tool_calls"], list)

    def test_chat_tool_results_list(self):
        resp = client.post("/api/chat", json={"message": "Search for meeting notes"}, headers=AUTH)
        assert isinstance(resp.json()["tool_results"], list)


# ── Agent loop integration ─────────────────────────────────────────────────────

class TestAgentLoopE2E:
    """Tests the AgentLoop processing pipeline end-to-end."""

    def test_process_returns_agent_response(self):
        agent = AgentLoop()
        req = AgentRequest(input="Remember to buy milk")
        resp = agent.process(req)
        assert isinstance(resp, AgentResponse)

    def test_process_with_voice_input_type(self):
        agent = AgentLoop()
        req = AgentRequest(input="Set timer for 30 minutes", input_type="voice")
        resp = agent.process(req)
        assert resp.response is not None

    def test_process_with_conversation_history(self):
        agent = AgentLoop()
        req = AgentRequest(
            input="And also add a note about the meeting",
            input_type="text",
            conversation_history=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
        )
        resp = agent.process(req)
        assert isinstance(resp, AgentResponse)

    def test_agent_loop_has_registry(self):
        agent = AgentLoop()
        assert agent.registry is not None
        tools = agent.registry.list_tools()
        assert len(tools) >= 4

    def test_agent_loop_has_executor(self):
        agent = AgentLoop()
        assert agent.executor is not None


# ── Tool executor pipeline ────────────────────────────────────────────────────

class TestToolExecutorE2E:
    """Tests ToolExecutor dispatching tools to real vault operations."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    def test_add_note_pipeline(self, temp_vault, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(temp_vault))
        executor = ToolExecutor()
        result = executor.execute(ToolCall(
            tool_name="vault_add_note",
            parameters={"path": "notes/test.md", "content": "Buy milk"}
        ))
        assert result["success"] is True
        assert (temp_vault / "notes" / "test.md").exists()

    def test_add_finance_pipeline(self, temp_vault, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(temp_vault))
        executor = ToolExecutor()
        result = executor.execute(ToolCall(
            tool_name="vault_add_finance",
            parameters={"amount": 15.50, "category": "lunch", "date": "2026-06-09"}
        ))
        assert result["success"] is True
        assert (temp_vault / "finance" / "2026-06-09.md").exists()

    def test_add_schedule_pipeline(self, temp_vault, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(temp_vault))
        executor = ToolExecutor()
        result = executor.execute(ToolCall(
            tool_name="vault_add_schedule",
            parameters={
                "title": "Study session",
                "date": "2026-06-10",
                "start_time": "09:00",
                "end_time": "11:00",
            }
        ))
        assert result["success"] is True

    def test_search_pipeline(self, temp_vault):
        executor = VaultToolExecutor(vault_path=str(temp_vault))
        executor.add_note(path="notes/study.md", content="CS lecture notes on algorithms")
        result = executor.search(query="algorithms")
        assert result["success"] is True
        assert len(result["result"]["matches"]) > 0


# ── Full write-then-read cycle ────────────────────────────────────────────────

class TestVaultRoundTrip:
    """Tests that data written through VaultWriter can be read by VaultReader."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    def test_note_roundtrip(self, temp_vault):
        writer = VaultWriter(str(temp_vault))
        reader = VaultReader(str(temp_vault))

        writer.add_note("notes/roundtrip.md", "Important: check deadlines")

        # search() returns List[Tuple[str, metadata]]
        results = reader.search("deadlines")
        assert len(results) > 0
        paths = [r[0] for r in results]
        assert any("roundtrip" in p for p in paths)

    def test_finance_roundtrip(self, temp_vault):
        writer = VaultWriter(str(temp_vault))
        reader = VaultReader(str(temp_vault))

        writer.add_finance(amount=99.99, category="electronics", date="2026-06-09")

        # list_finances() returns List[Finance] Pydantic models
        entries = reader.list_finances()
        assert len(entries) > 0
        amounts = [e.amount for e in entries]
        assert 99.99 in amounts

    def test_schedule_roundtrip(self, temp_vault):
        writer = VaultWriter(str(temp_vault))
        reader = VaultReader(str(temp_vault))

        writer.add_schedule(
            title="Final exam",
            date="2026-06-20",
            start_time="14:00",
            end_time="17:00",
        )

        # list_schedules() returns List[Schedule] Pydantic models
        events = reader.list_schedules()
        assert len(events) > 0
        titles = [e.title for e in events]
        assert "Final exam" in titles

    def test_multiple_finance_entries_same_day(self, temp_vault):
        writer = VaultWriter(str(temp_vault))
        reader = VaultReader(str(temp_vault))

        writer.add_finance(amount=5.00, category="coffee", date="2026-06-09")
        writer.add_finance(amount=12.00, category="lunch", date="2026-06-09")

        entries = reader.list_finances()
        amounts = [e.amount for e in entries]
        assert 5.0 in amounts
        assert 12.0 in amounts

    def test_multiple_schedule_events_same_day(self, temp_vault):
        writer = VaultWriter(str(temp_vault))
        reader = VaultReader(str(temp_vault))

        writer.add_schedule("Morning lecture", "2026-06-10", "09:00", "11:00")
        writer.add_schedule("Afternoon lab", "2026-06-10", "14:00", "16:00")

        events = reader.list_schedules()
        titles = [e.title for e in events]
        assert "Morning lecture" in titles
        assert "Afternoon lab" in titles


# ── Migration → read cycle ─────────────────────────────────────────────────────

class TestMigrationToReadPipeline:
    """Tests that migrated vault files can be read by VaultReader."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    def test_migrated_note_is_readable(self, temp_vault):
        from app.migrations.migrate_vault import migrate_vault

        note_dir = temp_vault / "notes"
        note_dir.mkdir()
        (note_dir / "legacy.md").write_text(
            "Old note content from before the migration", encoding="utf-8"
        )

        result = migrate_vault(str(temp_vault), backup=False)
        assert len(result.migrated) == 1
        assert len(result.errors) == 0

        # get_file returns (metadata, body) tuple
        reader = VaultReader(str(temp_vault))
        file_result = reader.get_file("notes/legacy.md")
        assert file_result is not None
        metadata, body = file_result
        assert metadata.type == "note"
        assert "Old note content" in body

    def test_migrated_finance_is_readable(self, temp_vault):
        from app.migrations.migrate_vault import migrate_vault

        fin_dir = temp_vault / "finance"
        fin_dir.mkdir()
        (fin_dir / "2026-01-15.md").write_text("Groceries 40.00", encoding="utf-8")

        migrate_vault(str(temp_vault), backup=False)

        reader = VaultReader(str(temp_vault))
        entries = reader.list_finances()
        assert len(entries) > 0
        assert entries[0].type == "finance"

    def test_migration_does_not_corrupt_already_valid_files(self, temp_vault):
        from app.migrations.migrate_vault import migrate_vault
        from app.vault.schema import parse_vault_file

        note_dir = temp_vault / "notes"
        note_dir.mkdir()
        valid_content = "---\ntype: note\ncreated: 2026-01-01\ntags: []\n---\nContent\n"
        (note_dir / "valid.md").write_text(valid_content, encoding="utf-8")

        migrate_vault(str(temp_vault), backup=False)

        content = (note_dir / "valid.md").read_text(encoding="utf-8")
        meta, body = parse_vault_file(content)
        assert meta.type == "note"
        assert "Content" in body


# ── Registry completeness check ───────────────────────────────────────────────

class TestToolRegistryCompleteness:
    """Verify that all expected tools are registered and have valid schemas."""

    REQUIRED_TOOLS = [
        "vault_add_note",
        "vault_add_finance",
        "vault_add_schedule",
        "vault_search",
        "summarize_document",
        "categorize_item",
    ]

    def test_all_required_tools_registered(self):
        from app.agent.registry import ToolRegistry
        registry = ToolRegistry()
        registered = {t.name for t in registry.list_tools()}
        for tool_name in self.REQUIRED_TOOLS:
            assert tool_name in registered, f"Missing tool: {tool_name}"

    def test_all_tools_have_valid_ollama_schema(self):
        from app.agent.registry import ToolRegistry
        registry = ToolRegistry()
        schemas = registry.to_ollama_schema()
        for schema in schemas:
            assert schema["type"] == "function"
            fn = schema["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
