from fastapi import APIRouter, Depends

from .. import bridge
from ..deps import require_auth

router = APIRouter()


@router.get("/memory/search")
def memory_search(q: str, top_k: int = 5, _: None = Depends(require_auth)):
    return bridge.search(q, top_k)
