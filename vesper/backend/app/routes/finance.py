from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import bridge
from ..deps import require_auth

router = APIRouter()


class FinanceRequest(BaseModel):
    amount: float
    category: str
    note: str = ""


@router.post("/finance")
def finance(req: FinanceRequest, _: None = Depends(require_auth)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    if not req.category.strip():
        raise HTTPException(status_code=400, detail="category required")
    return bridge.finance_log(req.amount, req.category.strip(), req.note)


@router.get("/finance/summary")
def finance_summary(_: None = Depends(require_auth)):
    return bridge.finance_summary()
