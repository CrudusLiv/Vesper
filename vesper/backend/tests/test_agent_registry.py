import pytest
from app.agent.registry import ToolRegistry
from app.agent.models import Tool


def test_registry_creation():
    """Test that registry creates with default tools"""
    registry = ToolRegistry()
    assert len(registry.tools) > 0  # Should have some default tools


def test_registry_has_eight_default_tools():
    """Test that registry has exactly 8 default tools"""
    registry = ToolRegistry()
    assert len(registry.tools) == 8


def test_registry_default_tools_exist():
    """Test that all 8 core tools are registered"""
    registry = ToolRegistry()
    expected_tools = {
        "vault_add_note",
        "vault_add_finance",
        "vault_add_schedule",
        "vault_search",
        "summarize_document",
        "categorize_item",
        "gcal_sync",
        "github_sync",
    }
    assert set(registry.tools.keys()) == expected_tools


def test_registry_get_tool():
    """Test getting a tool by name"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_add_note")
    assert tool is not None
    assert tool.name == "vault_add_note"


def test_registry_get_nonexistent_tool():
    """Test getting a tool that doesn't exist"""
    registry = ToolRegistry()
    tool = registry.get_tool("nonexistent_tool")
    assert tool is None


def test_registry_list_tools():
    """Test listing all tools"""
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert len(tools) == 8
    assert all(isinstance(tool, Tool) for tool in tools)


def test_registry_to_ollama_schema():
    """Test exporting to Ollama schema"""
    registry = ToolRegistry()
    schema = registry.to_ollama_schema()
    assert isinstance(schema, list)
    assert len(schema) == 8
    assert all(item["type"] == "function" for item in schema)


def test_registry_ollama_schema_has_function_key():
    """Test that Ollama schema includes function key"""
    registry = ToolRegistry()
    schema = registry.to_ollama_schema()
    assert all("function" in item for item in schema)


def test_registry_ollama_schema_has_required_fields():
    """Test that each function in Ollama schema has required fields"""
    registry = ToolRegistry()
    schema = registry.to_ollama_schema()
    for item in schema:
        func = item["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func


def test_vault_add_note_parameters():
    """Test vault_add_note has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_add_note")
    param_names = {p.name for p in tool.parameters}
    assert "path" in param_names
    assert "content" in param_names
    assert "overwrite" in param_names


def test_vault_add_finance_parameters():
    """Test vault_add_finance has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_add_finance")
    param_names = {p.name for p in tool.parameters}
    assert "amount" in param_names
    assert "category" in param_names
    assert "date" in param_names
    assert "description" in param_names


def test_vault_add_schedule_parameters():
    """Test vault_add_schedule has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_add_schedule")
    param_names = {p.name for p in tool.parameters}
    assert "title" in param_names
    assert "date" in param_names
    assert "start_time" in param_names
    assert "end_time" in param_names
    assert "priority" in param_names
    assert "location" in param_names
    assert "description" in param_names


def test_vault_add_schedule_priority_enum():
    """Test vault_add_schedule priority has enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_add_schedule")
    priority_param = next(p for p in tool.parameters if p.name == "priority")
    assert priority_param.enum == ["low", "medium", "high"]


def test_vault_search_parameters():
    """Test vault_search has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_search")
    param_names = {p.name for p in tool.parameters}
    assert "query" in param_names
    assert "search_type" in param_names
    assert "limit" in param_names


def test_vault_search_enum():
    """Test vault_search search_type has enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_search")
    search_type_param = next(p for p in tool.parameters if p.name == "search_type")
    assert set(search_type_param.enum) == {"all", "notes", "finances", "schedule"}


def test_summarize_document_parameters():
    """Test summarize_document has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("summarize_document")
    param_names = {p.name for p in tool.parameters}
    assert "file_path" in param_names
    assert "file_type" in param_names


def test_summarize_document_file_type_enum():
    """Test summarize_document file_type has enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("summarize_document")
    file_type_param = next(p for p in tool.parameters if p.name == "file_type")
    assert set(file_type_param.enum) == {"pptx", "pdf", "txt", "md"}


def test_categorize_item_parameters():
    """Test categorize_item has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("categorize_item")
    param_names = {p.name for p in tool.parameters}
    assert "item_type" in param_names
    assert "content" in param_names


def test_categorize_item_enum():
    """Test categorize_item item_type has enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("categorize_item")
    item_type_param = next(p for p in tool.parameters if p.name == "item_type")
    assert set(item_type_param.enum) == {"finance", "note", "schedule"}


def test_gcal_sync_parameters():
    """Test gcal_sync has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("gcal_sync")
    assert tool is not None
    param_names = {p.name for p in tool.parameters}
    assert "action" in param_names
    assert "data" in param_names
    assert "limit" in param_names
    assert "days" in param_names


def test_gcal_sync_action_enum():
    """Test gcal_sync action has enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("gcal_sync")
    assert tool is not None
    action_param = next(p for p in tool.parameters if p.name == "action")
    assert action_param.enum is not None
    assert set(action_param.enum) == {"push", "pull"}


def test_register_custom_tool():
    """Test registering a custom tool"""
    from app.agent.models import ToolParameter

    registry = ToolRegistry()
    custom_tool = Tool(
        name="custom_tool",
        description="A custom tool",
        parameters=[
            ToolParameter(name="param1", type="string", description="Test param")
        ]
    )
    registry.register(custom_tool)
    assert len(registry.tools) == 9
    assert registry.get_tool("custom_tool") == custom_tool


def test_registry_tool_descriptions_not_empty():
    """Test that all tools have descriptions"""
    registry = ToolRegistry()
    for tool in registry.list_tools():
        assert tool.description is not None
        assert len(tool.description) > 0


def test_registry_parameter_required_flags():
    """Test that parameter required flags are set correctly"""
    registry = ToolRegistry()
    tool = registry.get_tool("vault_add_note")

    # Required parameters
    required_params = {p.name for p in tool.parameters if p.required}
    assert "path" in required_params
    assert "content" in required_params

    # Optional parameters
    optional_params = {p.name for p in tool.parameters if not p.required}
    assert "overwrite" in optional_params


def test_github_sync_parameters():
    """Test github_sync has correct parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("github_sync")
    assert tool is not None
    param_names = {p.name for p in tool.parameters}
    assert "action" in param_names
    assert "owner_repo" in param_names
    assert "state" in param_names
    assert "labels" in param_names
    assert "limit" in param_names


def test_github_sync_action_enum():
    """Test github_sync action has correct enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("github_sync")
    assert tool is not None
    action_param = next(p for p in tool.parameters if p.name == "action")
    assert action_param.enum is not None
    assert set(action_param.enum) == {"pull_prs", "pull_issues"}


def test_github_sync_state_enum():
    """Test github_sync state has correct enum values"""
    registry = ToolRegistry()
    tool = registry.get_tool("github_sync")
    assert tool is not None
    state_param = next(p for p in tool.parameters if p.name == "state")
    assert state_param.enum is not None
    assert set(state_param.enum) == {"open", "closed", "all"}


def test_github_sync_required_parameters():
    """Test github_sync required parameters"""
    registry = ToolRegistry()
    tool = registry.get_tool("github_sync")
    assert tool is not None

    required_params = {p.name for p in tool.parameters if p.required}
    assert "action" in required_params
    assert "owner_repo" in required_params

    optional_params = {p.name for p in tool.parameters if not p.required}
    assert "state" in optional_params
    assert "labels" in optional_params
    assert "limit" in optional_params
