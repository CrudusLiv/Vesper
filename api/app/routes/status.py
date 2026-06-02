from fastapi import APIRouter, Depends

from .. import bridge
from ..deps import require_auth

router = APIRouter()


@router.get("/status")
def status(_: None = Depends(require_auth)):
    return bridge.get_status()
