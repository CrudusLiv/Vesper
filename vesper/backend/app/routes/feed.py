"""GET /api/feed + PATCH /api/feed/{id}/read for the Vesper notification feed."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import bridge
from ..deps import require_auth

router = APIRouter()


@router.get("/feed")
def get_feed(limit: int = 50, _: None = Depends(require_auth)):
    return bridge.feed_recent(limit=min(limit, 50))


@router.patch("/feed/{item_id}/read")
def mark_feed_item_read(item_id: str, _: None = Depends(require_auth)):
    result = bridge.feed_mark_read(item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="feed item not found")
    return result
