from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..agent.loop import AgentLoop
from ..agent.models import AgentRequest
from ..deps import require_auth

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[Message]] = None


@router.post("/chat")
def chat(req: ChatRequest, _: None = Depends(require_auth)):
    try:
        agent = AgentLoop()
        agent_req = AgentRequest(
            input=req.message,
            input_type="text",
            conversation_history=[m.model_dump() for m in (req.history or [])]
        )
        agent_response = agent.process(agent_req)
        return {
            "response": agent_response.response,
            "tool_calls": agent_response.tool_calls,
            "tool_results": agent_response.tool_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
