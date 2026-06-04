from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import bridge
from ..deps import require_auth

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


@router.post("/chat")
def chat(req: ChatRequest, _: None = Depends(require_auth)):
    try:
        return bridge.chat(req.message, [m.model_dump() for m in req.history])
    except bridge.LlmError:
        raise HTTPException(status_code=502, detail="llm unavailable")
