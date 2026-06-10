from pydantic import BaseModel, Field
from typing import Optional, Any


class ToolParameter(BaseModel):
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[list[str]] = None


class Tool(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)

    def to_ollama_schema(self) -> dict:
        """Export to Ollama function-calling schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        param.name: {
                            k: v for k, v in {
                                "type": param.type,
                                "description": param.description,
                                "enum": param.enum,
                            }.items() if v is not None
                        }
                        for param in self.parameters
                    },
                    "required": [p.name for p in self.parameters if p.required],
                }
            }
        }

    def to_anthropic_schema(self) -> dict:
        """Export to Anthropic tool-calling schema"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    param.name: {
                        k: v for k, v in {
                            "type": param.type,
                            "description": param.description,
                            "enum": param.enum,
                        }.items() if v is not None
                    }
                    for param in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required],
            }
        }


class ToolCall(BaseModel):
    tool_name: str
    parameters: dict[str, Any]


class AgentRequest(BaseModel):
    input: str  # user's voice transcript or text input
    input_type: str = "text"  # "text", "voice", "file"
    conversation_history: Optional[list[dict]] = None


class AgentResponse(BaseModel):
    response: str  # natural language response from Ollama
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)  # Results from executed tools
