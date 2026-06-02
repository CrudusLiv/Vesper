"""Shared FastAPI dependencies. The auth gate is a single shared bearer secret
(API_SECRET) — LAN-only is acceptable for v1."""
from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """Reject any request whose Authorization header is not `Bearer <API_SECRET>`.

    Fails closed: if API_SECRET is unset, every request is rejected."""
    secret = os.environ.get("API_SECRET", "")
    expected = f"Bearer {secret}"
    if not secret or authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="unauthorized")
