import pytest
from app.agent.loop import AgentLoop
from app.agent.models import AgentRequest, AgentResponse, ToolCall


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


def test_tool_executor_dispatch_vault_tool():
    """Test that ToolExecutor can dispatch vault tools"""
    from app.agent.executor import ToolExecutor
    from app.agent.models import ToolCall

    executor = ToolExecutor()
    tool_call = ToolCall(
        tool_name="vault_add_note",
        parameters={"path": "test.md", "content": "Test content"}
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


def test_vault_tool_executor_add_note():
    """Test VaultToolExecutor.add_note()"""
    from app.agent.tools.vault import VaultToolExecutor

    executor = VaultToolExecutor()
    result = executor.add_note(path="notes/test.md", content="Test")
    assert result["success"] is True
    assert "Test" in result["result"] or "added" in result["result"].lower()


def test_vault_tool_executor_add_finance():
    """Test VaultToolExecutor.add_finance()"""
    from app.agent.tools.vault import VaultToolExecutor

    executor = VaultToolExecutor()
    result = executor.add_finance(
        amount=50.0,
        category="food",
        date="2026-06-08"
    )
    assert result["success"] is True
    assert "50" in result["result"] or "food" in result["result"]


def test_vault_tool_executor_add_schedule():
    """Test VaultToolExecutor.add_schedule()"""
    from app.agent.tools.vault import VaultToolExecutor

    executor = VaultToolExecutor()
    result = executor.add_schedule(
        title="Team Meeting",
        date="2026-06-08",
        start_time="14:00",
        end_time="15:00"
    )
    assert result["success"] is True
    assert "Team Meeting" in result["result"]


def test_vault_tool_executor_search():
    """Test VaultToolExecutor.search()"""
    from app.agent.tools.vault import VaultToolExecutor

    executor = VaultToolExecutor()
    result = executor.search(query="test", search_type="all")
    assert result["success"] is True
    assert "matches" in result["result"]


def test_tool_executor_vault_add_note():
    """Test ToolExecutor dispatching vault_add_note"""
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor()
    tool_call = ToolCall(
        tool_name="vault_add_note",
        parameters={"path": "test.md", "content": "Hello"}
    )
    result = executor.execute(tool_call)
    assert result["success"] is True


def test_tool_executor_vault_add_finance():
    """Test ToolExecutor dispatching vault_add_finance"""
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor()
    tool_call = ToolCall(
        tool_name="vault_add_finance",
        parameters={"amount": 100.0, "category": "transport", "date": "2026-06-08"}
    )
    result = executor.execute(tool_call)
    assert result["success"] is True


def test_tool_executor_vault_add_schedule():
    """Test ToolExecutor dispatching vault_add_schedule"""
    from app.agent.executor import ToolExecutor

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


def test_tool_executor_vault_search():
    """Test ToolExecutor dispatching vault_search"""
    from app.agent.executor import ToolExecutor

    executor = ToolExecutor()
    tool_call = ToolCall(
        tool_name="vault_search",
        parameters={"query": "important", "limit": 5}
    )
    result = executor.execute(tool_call)
    assert result["success"] is True
