from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import bridge
from ..deps import require_auth

router = APIRouter()


class NoteRequest(BaseModel):
    text: str


@router.post("/note")
def note(req: NoteRequest, _: None = Depends(require_auth)):
    try:
        return bridge.note_append(req.text)
    except ValueError:
        raise HTTPException(status_code=422, detail="note was empty")
