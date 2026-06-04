from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import bridge
from ..deps import require_auth

router = APIRouter()


class ScheduleRequest(BaseModel):
    text: str
    confirm: bool = False


@router.get("/schedule")
def schedule_get(_: None = Depends(require_auth)):
    return bridge.schedule_get()


@router.post("/schedule")
def schedule_set(req: ScheduleRequest, _: None = Depends(require_auth)):
    try:
        result = bridge.schedule_set(req.text, req.confirm)
    except bridge.LlmError:
        raise HTTPException(status_code=502, detail="llm unavailable")
    except ValueError:
        raise HTTPException(status_code=422, detail="could not parse timetable")
    if not result["written"]:
        return JSONResponse(status_code=409, content={"summary": result["summary"], "exists": True})
    return {"summary": result["summary"]}
