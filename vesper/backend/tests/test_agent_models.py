import pytest
from app.agent.models import Tool, ToolParameter


def test_tool_creation():
    tool = Tool(
        name="vault_add_note",
        description="Add a note to the vault",
        parameters=[
            ToolParameter(name="path", type="string", description="Vault path", required=True),
            ToolParameter(name="content", type="string", description="Note content", required=True),
        ]
    )
    assert tool.name == "vault_add_note"
    assert len(tool.parameters) == 2


def test_tool_to_ollama_schema():
    """Tool should export to Ollama function-calling schema"""
    tool = Tool(
        name="vault_add_note",
        description="Add a note",
        parameters=[
            ToolParameter(name="path", type="string", description="Path", required=True),
        ]
    )
    schema = tool.to_ollama_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "vault_add_note"
    assert "parameters" in schema["function"]
